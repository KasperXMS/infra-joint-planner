from datetime import UTC, datetime

import pytest

from infra_joint.core.action import (
    FinishDecision,
    JointAction,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract
from infra_joint.evaluation.evaluator import ExactChoiceEvaluator
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.infrastructure.observer import StaticObserver
from infra_joint.planning.finalize import LastModelOutputFinalizer
from infra_joint.planning.graph import PlanningGraph
from infra_joint.planning.planner import ScriptedBlindPlanner
from infra_joint.runtime.executor import ExecutionResult


class StubExecutor:
    async def execute(
        self, action: JointAction, infrastructure: InfrastructureState
    ) -> ExecutionResult:
        del action, infrastructure
        return ExecutionResult(
            operator="invoke_model",
            agent_ids=("worker",),
            output={"text": "A"},
        )


@pytest.mark.asyncio
async def test_planning_graph_writes_reconstructable_trace(tmp_path) -> None:
    task = TaskContract(
        task_id="trace-task",
        benchmark_id="synthetic",
        objective="Return A",
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.CHOICE, choices=("A", "B")),
        evaluator_id="exact",
    )
    action = JointAction(
        semantic=SemanticAction(operator="invoke_model", arguments={"prompt": "Return A"}),
        physical=PhysicalDecision(policy=PhysicalPolicy.AUTO),
    )
    infrastructure = InfrastructureState(
        agents=(),
        deployments=(),
        artifacts=(),
        links=(),
        observed_at=datetime.now(UTC),
    )
    writer = JsonlTraceWriter(tmp_path / "run.jsonl")
    graph = PlanningGraph(
        planner=ScriptedBlindPlanner((action, FinishDecision(reason="sufficient evidence"))),
        observer=StaticObserver(infrastructure),
        executor=StubExecutor(),
        finalizer=LastModelOutputFinalizer(),
        evaluator=ExactChoiceEvaluator("A"),
        max_planning_steps=2,
        trace_sink=writer,
    )

    result = await graph.run(task, run_id="run-1")
    events = writer.read_all()

    assert result["final_answer"] == "A"
    assert events[0]["event_type"] == "task.start"
    assert events[-1]["event_type"] == "run.end"
    assert {event["event_type"] for event in events} >= {
        "infra.snapshot",
        "joint_action.proposed",
        "operator.start",
        "operator.end",
        "finish.proposed",
        "finalize.start",
        "finalize.end",
        "evaluation.result",
    }
    assert all(event["run_id"] == "run-1" for event in events)
    assert events[0]["parent_id"] is None
    assert all(
        event["parent_id"] == events[index - 1]["step_id"]
        for index, event in enumerate(events[1:], start=1)
    )
