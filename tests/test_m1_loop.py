from datetime import UTC, datetime

import httpx
import pytest

from infra_joint.core.action import (
    FinishDecision,
    JointAction,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    EnvironmentSpec,
    InfrastructureState,
)
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract
from infra_joint.evaluation.evaluator import ExactChoiceEvaluator
from infra_joint.infrastructure.observer import StaticObserver
from infra_joint.operators.builtin import invoke_model_spec, unavailable_handler
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.finalize import LastModelOutputFinalizer
from infra_joint.planning.graph import PlanningGraph
from infra_joint.planning.planner import ScriptedBlindPlanner
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import RuntimeExecutor
from infra_joint.worker.model_backend import StaticModelBackend
from infra_joint.worker.server import create_worker_app


@pytest.mark.asyncio
async def test_blind_planner_worker_finalize_evaluate_loop() -> None:
    task = TaskContract(
        task_id="m1-smoke",
        benchmark_id="synthetic-choice",
        objective="Return the canonical answer choice.",
        artifacts=(),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B", "C", "D"),
        ),
        evaluator_id="exact-choice-v1",
    )
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="worker-1",
                device="test-cpu",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(),
    )
    infrastructure = InfrastructureState(
        agents=(AgentRuntimeState(agent_id="worker-1", available=True),),
        deployments=(),
        artifacts=(),
        links=(),
        observed_at=datetime.now(UTC),
    )
    registry = OperatorRegistry()
    registry.register(invoke_model_spec(), unavailable_handler)
    planner = ScriptedBlindPlanner(
        (
            JointAction(
                semantic=SemanticAction(
                    operator="invoke_model",
                    arguments={"prompt": task.objective},
                ),
                physical=PhysicalDecision(policy=PhysicalPolicy.AUTO),
            ),
            FinishDecision(reason="model returned sufficient evidence"),
        )
    )

    app = create_worker_app("worker-1", StaticModelBackend("A"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://worker-1") as client:
        executor = RuntimeExecutor(
            registry=registry,
            environment=environment,
            worker_clients={"worker-1": HttpWorkerClient("worker-1", client)},
        )
        graph = PlanningGraph(
            planner=planner,
            observer=StaticObserver(infrastructure),
            executor=executor,
            finalizer=LastModelOutputFinalizer(),
            evaluator=ExactChoiceEvaluator("A"),
            max_planning_steps=3,
        )
        result = await graph.run(task)

    assert result["final_answer"] == "A"
    assert result["evaluation"].format_valid
    assert result["evaluation"].benchmark_score == 1.0
    assert len(result["observations"]) == 1
    assert result["observations"][0].agent_ids == ("worker-1",)


@pytest.mark.asyncio
async def test_planning_budget_still_runs_finalization() -> None:
    task = TaskContract(
        task_id="budget-smoke",
        benchmark_id="synthetic-choice",
        objective="Return A.",
        artifacts=(),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="exact-choice-v1",
    )
    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="worker-1", device="cpu", capabilities={"model"}),),
        deployments=(),
    )
    infrastructure = InfrastructureState(
        agents=(AgentRuntimeState(agent_id="worker-1", available=True),),
        deployments=(),
        artifacts=(),
        links=(),
        observed_at=datetime.now(UTC),
    )
    registry = OperatorRegistry()
    registry.register(invoke_model_spec(), unavailable_handler)
    action = JointAction(
        semantic=SemanticAction(operator="invoke_model", arguments={"prompt": "Return A"}),
        physical=PhysicalDecision(policy=PhysicalPolicy.AUTO),
    )
    app = create_worker_app("worker-1", StaticModelBackend("A"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://worker-1") as client:
        graph = PlanningGraph(
            planner=ScriptedBlindPlanner((action,)),
            observer=StaticObserver(infrastructure),
            executor=RuntimeExecutor(
                registry,
                environment,
                {"worker-1": HttpWorkerClient("worker-1", client)},
            ),
            finalizer=LastModelOutputFinalizer(),
            evaluator=ExactChoiceEvaluator("A"),
            max_planning_steps=1,
        )
        result = await graph.run(task)

    assert result["final_answer"] == "A"
    assert result["evaluation"].benchmark_score == 1.0
