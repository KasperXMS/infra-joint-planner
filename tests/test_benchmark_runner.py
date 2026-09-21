import json

import httpx
import pytest

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    BenchmarkSettingKind,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    TransformationRecord,
    ValidityAssessment,
)
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.core.state import (
    AgentSpec,
    ArtifactPlacement,
    DeploymentSpec,
    EnvironmentSpec,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.experiments.runner import BenchmarkRunner
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelDeployment,
    ModelRequest,
    StaticModelBackend,
)
from infra_joint.worker.server import create_worker_app


class SequenceBackend:
    def __init__(self, responses: tuple[str, ...]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.prompts.append(request.prompt)
        return ModelCompletion(
            text=self._responses.pop(0),
            telemetry=ModelCallTelemetry(
                service_latency_ms=3,
                input_tokens=20,
                output_tokens=5,
                finish_reason="stop",
            ),
        )


def bundle() -> AdaptationBundle:
    content = b"The evidence says option A."
    artifact = PreparedArtifact.create(
        ArtifactSpec(
            artifact_id="evidence",
            logical_type="document",
            media_type="text/plain",
            size_bytes=len(content),
            source_ref="prepared://test/evidence",
        ),
        content,
    )
    task = TaskContract(
        task_id="runner-smoke",
        benchmark_id="synthetic",
        objective="Choose A or B from the evidence.",
        artifacts=(artifact.spec,),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="exact",
    )
    transformation = TransformationRecord(
        benchmark_id="synthetic",
        source_revision="test",
        source_task_id="runner-smoke",
        transformation="identity",
        information_preserved=True,
        order_preserved=True,
        gold_independent=True,
    )
    return AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=ValidityAssessment(
                information_equivalent=True,
                query_equivalent=True,
                evaluator_equivalent=True,
                setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
            ),
        ),
        private_evaluation=PrivateChoiceEvaluation(
            task_id="runner-smoke",
            evaluator_id="exact",
            gold_answer="A",
        ),
        prepared_artifacts=(artifact,),
    )


def runner_config(tmp_path) -> RunnerConfig:
    return RunnerConfig(
        environment=EnvironmentSpec(
            agents=(
                AgentSpec(
                    agent_id="remote-worker-secret",
                    device="secret-device",
                    capabilities=frozenset({"model", "structured", "retrieval", "media.image"}),
                ),
            ),
            deployments=(
                DeploymentSpec(
                    deployment_id="reader",
                    agent_id="remote-worker-secret",
                    model_id="reader-model",
                    context_window=4096,
                    reserved_output_tokens=512,
                ),
            ),
            initial_placements=(
                ArtifactPlacement(
                    artifact_id="evidence",
                    agent_id="remote-worker-secret",
                ),
            ),
        ),
        worker_urls={"remote-worker-secret": "http://secret-worker-address"},
        planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
        output_root=tmp_path / "runs",
        max_planning_steps=2,
    )


@pytest.mark.asyncio
async def test_runner_executes_and_persists_complete_blind_pipeline(tmp_path) -> None:
    worker_deployment = ModelDeployment(
        deployment_id="reader",
        model_id="reader-model",
        backend=StaticModelBackend("A"),
        modalities=frozenset({"text"}),
        context_window=4096,
        reserved_output_tokens=512,
        image_token_cost=4096,
    )
    worker_app = create_worker_app(
        "remote-worker-secret",
        {"reader": worker_deployment},
    )
    planner = SequenceBackend(
        (
            json.dumps(
                {
                    "decision_type": "action",
                    "operator": "invoke_model",
                    "inputs": ["evidence"],
                    "arguments": {"prompt": "Answer from the evidence."},
                }
            ),
            json.dumps(
                {
                    "decision_type": "finish",
                    "reason": "model produced an answer",
                }
            ),
            "A",
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=worker_app),
        base_url="http://secret-worker-address",
    ) as client:
        result = await BenchmarkRunner(
            runner_config(tmp_path),
            worker_clients={
                "remote-worker-secret": HttpWorkerClient(
                    "remote-worker-secret",
                    client,
                )
            },
            planner_backend=planner,
        ).run(bundle(), run_id="run-1")

    assert result.execution_completed
    assert result.final_answer == "A"
    assert result.evaluation is not None
    assert result.evaluation.benchmark_score == 1
    assert result.telemetry is not None
    assert result.telemetry.total_operator_latency_ms > 0
    assert result.telemetry.total_transfer_bytes == len(b"The evidence says option A.")
    assert result.initial_transfers[0].source_agent_id == "controller"
    assert result.observations[0].deployment_id == "reader"
    assert result.observations[0].model_telemetry is not None
    assert result.observations[0].model_telemetry.finish_reason == "stop"
    assert all("remote-worker-secret" not in prompt for prompt in planner.prompts)
    assert all("secret-worker-address" not in prompt for prompt in planner.prompts)

    persisted = json.loads(
        (tmp_path / "runs" / "run-1" / "result.json").read_text(encoding="utf-8")
    )
    events = [
        json.loads(line)
        for line in (tmp_path / "runs" / "run-1" / "trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert persisted["execution_completed"]
    assert {event["event_type"] for event in events} >= {
        "artifact.materialize.end",
        "planner.end",
        "operator.end",
        "finalize.end",
        "evaluation.result",
        "run.end",
    }
    assert all(
        event["parent_id"] == events[index - 1]["step_id"]
        for index, event in enumerate(events[1:], start=1)
    )
