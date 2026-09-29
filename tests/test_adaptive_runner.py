import json
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
from infra_joint.control.prior import (
    LLMPriorWorkflowGenerator,
    PriorAttemptStore,
    PriorWorkflowDraft,
    PriorWorkflowStore,
    StaticPriorWorkflowGenerator,
)
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
    llm_attempts = PriorAttemptStore(tmp_path / "prior_attempts")
    llm_generator = LLMPriorWorkflowGenerator(
        StaticModelBackend(
            PriorWorkflowDraft(
                actions=plan.actions,
                dependencies=plan.dependencies,
                terminal_action_id=plan.terminal_action_id,
            ).model_dump_json()
        ),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=llm_attempts,
    )
    llm_store = PriorWorkflowStore(tmp_path / "llm_prior_workflows")
    prepared = await AdaptiveWorkflowBenchmarkRunner(
        config,
        llm_generator,
        KeepWorkflowPolicy(),
        ("invoke_model",),
        prior_store=llm_store,
        require_frozen_prior=True,
    ).prepare_prior_workflow(bundle)
    assert prepared.plan.version == 0
    assert prepared.plan.workflow_id.startswith("prior-")
    attempt = next((tmp_path / "prior_attempts" / task.task_id).iterdir())
    validation = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert validation["attempt_status"] == "frozen_success"
    assert validation["plan_sha256"] == prepared.plan_sha256
    assert Path(validation["frozen_prior_path"]) == llm_store.path_for(task.task_id)
    assert (attempt / "raw_completion.txt").exists()
    assert (attempt / "draft.json").exists()
    assert (attempt / "constructed-g0.json").exists()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://worker",
    ) as client:
        worker_clients = {agent_id: HttpWorkerClient(agent_id, client)}
        result = await AdaptiveWorkflowBenchmarkRunner(
            config,
            StaticPriorWorkflowGenerator(plan, build_operator_catalog()),
            KeepWorkflowPolicy(),
            ("invoke_model",),
            prior_store=prior_store,
            require_frozen_prior=False,
            worker_clients=worker_clients,
        ).run(bundle, run_id="formal-run")
        missing = await AdaptiveWorkflowBenchmarkRunner(
            config,
            StaticPriorWorkflowGenerator(plan, build_operator_catalog()),
            KeepWorkflowPolicy(),
            ("invoke_model",),
            prior_store=PriorWorkflowStore(tmp_path / "missing-priors"),
            worker_clients=worker_clients,
        ).run(bundle, run_id="formal-missing-prior")

    assert result.execution_completed
    assert result.final_answer == "A"
    assert result.evaluation is not None
    assert result.evaluation.benchmark_score == 1
    assert not missing.execution_completed
    assert missing.failure is not None
    assert "requires a frozen prior workflow" in missing.failure.message
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

    invalid_app = create_worker_app(
        agent_id,
        {
            deployment_id: ModelDeployment(
                deployment_id=deployment_id,
                model_id="static-model",
                backend=StaticModelBackend("C"),
                modalities=frozenset({"text"}),
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            )
        },
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=invalid_app),
        base_url="http://worker",
    ) as invalid_client:
        invalid = await AdaptiveWorkflowBenchmarkRunner(
            config,
            StaticPriorWorkflowGenerator(plan, build_operator_catalog()),
            KeepWorkflowPolicy(),
            ("invoke_model",),
            prior_store=prior_store,
            require_frozen_prior=True,
            worker_clients={agent_id: HttpWorkerClient(agent_id, invalid_client)},
        ).run(bundle, run_id="formal-invalid-choice")
    assert invalid.execution_completed
    assert invalid.terminal_output_contract_valid is False
    assert invalid.evaluation is not None
    assert not invalid.evaluation.format_valid
    assert invalid.evaluation.benchmark_score == 0
