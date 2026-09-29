from pathlib import Path

import httpx
import pytest

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    BenchmarkSettingKind,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    ValidityAssessment,
)
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.adaptation import KeepWorkflowPolicy
from infra_joint.control.adaptive_runner import AdaptiveWorkflowBenchmarkRunner
from infra_joint.control.contracts import ExecutionRequirements, LogicalModelAction
from infra_joint.control.prior import PriorWorkflowStore, StaticPriorWorkflowGenerator
from infra_joint.control.workflow import SemanticWorkflowPlan
from infra_joint.core.state import (
    AgentSpec,
    ArtifactPlacement,
    DeploymentSpec,
    EnvironmentSpec,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.worker.model_backend import ModelDeployment, StaticModelBackend
from infra_joint.worker.server import create_worker_app


@pytest.mark.asyncio
async def test_adaptive_runner_reuses_frozen_prior_and_original_evaluator(
    tmp_path: Path,
) -> None:
    content = b'[{"text":"option A"}]'
    artifact = PreparedArtifact.create(
        ArtifactSpec(
            artifact_id="evidence",
            logical_type="document",
            media_type="application/json",
            size_bytes=len(content),
            source_ref="private://runner-source",
        ),
        content,
    )
    task = TaskContract(
        task_id="adaptive-runner-smoke",
        benchmark_id="synthetic",
        objective="Choose A or B from the evidence.",
        artifacts=(artifact.spec,),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-exact",
    )
    bundle = AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(),
            validity=ValidityAssessment(
                information_equivalent=True,
                query_equivalent=True,
                evaluator_equivalent=True,
                setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
            ),
        ),
        private_evaluation=PrivateChoiceEvaluation(
            task_id=task.task_id,
            evaluator_id=task.evaluator_id,
            gold_answer="A",
        ),
        prepared_artifacts=(artifact,),
    )
    plan = SemanticWorkflowPlan(
        workflow_id="adaptive-runner-workflow",
        version=0,
        actions=(
            LogicalModelAction(
                action_id="answer",
                owner_agent_id="manager",
                inputs=("evidence",),
                prompt="Return only A or B.",
                requirements=ExecutionRequirements(
                    min_context_tokens=256,
                    reserved_output_tokens=32,
                ),
            ),
        ),
        terminal_action_id="answer",
    )
    agent_id = "physical-worker-secret"
    deployment_id = "physical-deployment-secret"
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id=agent_id,
                device="synthetic",
                capabilities=frozenset(
                    {"model", "retrieval", "structured", "media.image", "media.video"}
                ),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id=deployment_id,
                agent_id=agent_id,
                model_id="static-model",
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            ),
        ),
        initial_placements=(ArtifactPlacement(artifact_id="evidence", agent_id=agent_id),),
    )
    config = RunnerConfig(
        environment=environment,
        worker_urls={agent_id: "http://worker"},
        planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
        output_root=tmp_path / "runs",
    )
    app = create_worker_app(
        agent_id,
        {
            deployment_id: ModelDeployment(
                deployment_id=deployment_id,
                model_id="static-model",
                backend=StaticModelBackend("A"),
                modalities=frozenset({"text"}),
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            )
        },
    )
    prior_store = PriorWorkflowStore(tmp_path / "prior_workflows")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://worker",
    ) as client:
        result = await AdaptiveWorkflowBenchmarkRunner(
            config,
            StaticPriorWorkflowGenerator(plan, build_operator_catalog()),
            KeepWorkflowPolicy(),
            ("invoke_model",),
            prior_store=prior_store,
            prior_model="static-prior",
            prior_prompt="deterministic prior",
            worker_clients={agent_id: HttpWorkerClient(agent_id, client)},
        ).run(bundle, run_id="formal-run")

    assert result.execution_completed
    assert result.final_answer == "A"
    assert result.evaluation is not None
    assert result.evaluation.benchmark_score == 1
    frozen = prior_store.load(task.task_id)
    assert frozen.plan_sha256 == plan.canonical_sha256()
    trace_path = tmp_path / "runs" / "formal-run" / "trace.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    assert '"event_type":"workflow.plan.version"' in trace_text
    assert '"event_type":"workflow.plan.patch"' in trace_text
    assert '"event_type":"workflow.execution.snapshot"' in trace_text
    logical_lines = "\n".join(
        line for line in trace_text.splitlines() if '"event_type":"workflow.' in line
    )
    assert "private://runner-source" not in logical_lines
    assert "private-exact" not in logical_lines
    assert agent_id not in logical_lines
    assert deployment_id not in logical_lines
