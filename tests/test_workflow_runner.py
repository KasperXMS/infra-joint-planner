import json
from pathlib import Path
from urllib.parse import urlparse

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
    LinkSpec,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowEdge, WorkflowNode, WorkflowPlan
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.worker.artifact_fetcher import FetchedArtifact
from infra_joint.worker.model_backend import (
    ModelCompletion,
    ModelDeployment,
    ModelRequest,
    StaticModelBackend,
)
from infra_joint.worker.server import create_worker_app
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.replanning import (
    ReplanTrigger,
    ReviseWorkflowProposal,
    ScriptedWorkflowReplanner,
)
from infra_joint.workflow.runner import WorkflowBenchmarkRunner
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler
from infra_joint.workflow.workload import WorkloadSpec


class SourceClientFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, source_url: str) -> FetchedArtifact:
        response = await self._client.get(urlparse(source_url).path)
        response.raise_for_status()
        return FetchedArtifact(
            content=response.content,
            media_type=response.headers["content-type"].split(";", maxsplit=1)[0],
            sha256_hex=response.headers.get("x-artifact-sha256"),
        )


class ForbiddenFinalizerBackend:
    def __init__(self) -> None:
        self.calls = 0

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        del request
        self.calls += 1
        raise AssertionError("workflow completion must not invoke a semantic finalizer")


def bundle() -> AdaptationBundle:
    prepared = tuple(
        PreparedArtifact.create(
            ArtifactSpec(
                artifact_id=f"shard-{suffix}",
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=len(content),
            ),
            content,
        )
        for suffix, content in (
            ("a", b'[{"text":"answer A evidence"}]'),
            ("b", b'[{"text":"other evidence"}]'),
        )
    )
    task = TaskContract(
        task_id="workflow-runner",
        benchmark_id="synthetic",
        objective="Return A from the evidence.",
        artifacts=tuple(item.spec for item in prepared),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="exact",
    )
    return AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(
                TransformationRecord(
                    benchmark_id="synthetic",
                    source_revision="test",
                    source_task_id=task.task_id,
                    transformation="two_shards",
                    information_preserved=True,
                    order_preserved=True,
                    gold_independent=True,
                ),
            ),
            validity=ValidityAssessment(
                information_equivalent=True,
                query_equivalent=True,
                evaluator_equivalent=True,
                setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
            ),
        ),
        private_evaluation=PrivateChoiceEvaluation(
            task_id=task.task_id,
            evaluator_id="exact",
            gold_answer="A",
        ),
        prepared_artifacts=prepared,
    )


def environment() -> EnvironmentSpec:
    capabilities = frozenset(
        {"retrieval", "model", "structured", "media.image"}
    )
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="A",
                device="edge",
                capabilities=capabilities,
            ),
            AgentSpec(
                agent_id="B",
                device="gpu",
                capabilities=capabilities,
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="text",
                agent_id="B",
                model_id="text-model",
                context_window=4096,
                reserved_output_tokens=512,
            ),
        ),
        initial_placements=(
            ArtifactPlacement(artifact_id="shard-a", agent_id="A"),
            ArtifactPlacement(artifact_id="shard-b", agent_id="B"),
        ),
        links=(LinkSpec(source_agent_id="A", target_agent_id="B"),),
    )


def plan() -> WorkflowPlan:
    agents = tuple(
        LogicalAgent(
            agent_id=value,
            role="retriever" if value != "synth" else "synthesis",
            objective="use an independent logical context",
            model_instance_id="text",
        )
        for value in ("retriever-a", "retriever-b", "synth")
    )
    retrievals = tuple(
        WorkflowNode(
            node_id=f"retrieve-{suffix}",
            agent_id=f"retriever-{suffix}",
            operator="bm25_retrieve",
            inputs=(f"shard-{suffix}",),
            arguments={
                "query": "answer",
                "top_k": 1,
                "text_field": "text",
                "output_artifact_id": f"evidence-{suffix}",
            },
            outputs=(f"evidence-{suffix}",),
        )
        for suffix in ("a", "b")
    )
    synthesis = WorkflowNode(
        node_id="synthesize",
        agent_id="synth",
        operator="invoke_model",
        inputs=("evidence-a", "evidence-b"),
        arguments={"prompt": "Return the canonical answer label."},
    )
    return WorkflowPlan(
        agents=agents,
        nodes=(*retrievals, synthesis),
        edges=tuple(
            WorkflowEdge(
                producer_node=f"retrieve-{suffix}",
                consumer_node="synthesize",
                artifact_id=f"evidence-{suffix}",
            )
            for suffix in ("a", "b")
        ),
    )


def partial_plan() -> WorkflowPlan:
    full = plan()
    return WorkflowPlan(
        agents=(full.agents[0], full.agents[2]),
        nodes=(
            full.nodes[0],
            full.nodes[2].model_copy(update={"inputs": ("evidence-a",)}),
        ),
        edges=(full.edges[0],),
    )


@pytest.mark.asyncio
async def test_workflow_runner_persists_real_runtime_fanout_fanin(
    tmp_path: Path,
) -> None:
    current_bundle = bundle()
    current_environment = environment()
    forbidden_finalizer = ForbiddenFinalizerBackend()
    source_app = create_worker_app("A", {})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source_app),
        base_url="http://A",
    ) as source_http:
        target_app = create_worker_app(
            "B",
            {
                "text": ModelDeployment(
                    deployment_id="text",
                    model_id="text-model",
                    backend=StaticModelBackend("A"),
                    modalities=frozenset({"text"}),
                    context_window=4096,
                    reserved_output_tokens=512,
                    image_token_cost=4096,
                ),
            },
            artifact_fetcher=SourceClientFetcher(source_http),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target_app),
            base_url="http://B",
        ) as target_http:
            config = RunnerConfig(
                environment=current_environment,
                worker_urls={"A": "http://A", "B": "http://B"},
                planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                output_root=tmp_path,
            )
            workload = WorkloadSpec.from_task_environment(
                current_bundle.execution.task,
                current_environment,
                available_operations=("bm25_retrieve", "invoke_model"),
                min_agents=3,
                max_agents=3,
            )
            result = await WorkflowBenchmarkRunner(
                config,
                workload,
                LocalityAwareMyopicScheduler(),
                worker_clients={
                    "A": HttpWorkerClient("A", source_http),
                    "B": HttpWorkerClient("B", target_http),
                },
                planner_backend=forbidden_finalizer,
                planner=ScriptedWorkflowPlanner((plan(),)),
            ).run(current_bundle, run_id="workflow-run")

    assert result.execution_completed
    assert result.evaluation is not None
    assert result.evaluation.benchmark_score == 1
    assert result.final_answer == "A"
    assert result.telemetry is not None
    assert result.telemetry.finalizer.model is None
    assert forbidden_finalizer.calls == 0
    assert result.workflow is not None
    assert [item.scheduling_batch for item in result.workflow.records[:2]] == [0, 0]
    assert result.workflow.telemetry.total_transfer_bytes > 0
    assert result.plan is not None
    assert len(result.plan.agents) == 3
    persisted = json.loads((tmp_path / "workflow-run" / "result.json").read_text())
    events = [
        json.loads(line)
        for line in (tmp_path / "workflow-run" / "trace.jsonl").read_text().splitlines()
    ]
    assert persisted["execution_completed"]
    assert {event["event_type"] for event in events} >= {
        "workflow.planner.end",
        "scheduler.decision",
        "workflow.node.start",
        "workflow.node.end",
        "artifact.transfer.end",
        "evaluation.result",
        "run.end",
    }
    finalize_start = next(
        event for event in events if event["event_type"] == "finalize.start"
    )
    assert finalize_start["payload"] == {
        "mode": "deterministic_terminal_extraction",
        "terminal_node_id": "synthesize",
    }
    assert all(
        event["parent_id"] == events[index - 1]["step_id"]
        for index, event in enumerate(events[1:], start=1)
    )


@pytest.mark.asyncio
async def test_workflow_runner_persists_replanning_versions_and_does_not_replay(
    tmp_path: Path,
) -> None:
    current_bundle = bundle()
    current_environment = environment()
    source_app = create_worker_app("A", {})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source_app),
        base_url="http://A",
    ) as source_http:
        target_app = create_worker_app(
            "B",
            {
                "text": ModelDeployment(
                    deployment_id="text",
                    model_id="text-model",
                    backend=StaticModelBackend("A"),
                    modalities=frozenset({"text"}),
                    context_window=4096,
                    reserved_output_tokens=512,
                    image_token_cost=4096,
                ),
            },
            artifact_fetcher=SourceClientFetcher(source_http),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target_app),
            base_url="http://B",
        ) as target_http:
            config = RunnerConfig(
                environment=current_environment,
                worker_urls={"A": "http://A", "B": "http://B"},
                planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                output_root=tmp_path,
            )
            workload = WorkloadSpec.from_task_environment(
                current_bundle.execution.task,
                current_environment,
                available_operations=("bm25_retrieve", "invoke_model"),
                max_agents=3,
            )
            result = await WorkflowBenchmarkRunner(
                config,
                workload,
                LocalityAwareMyopicScheduler(),
                worker_clients={
                    "A": HttpWorkerClient("A", source_http),
                    "B": HttpWorkerClient("B", target_http),
                },
                planner=ScriptedWorkflowPlanner((partial_plan(),)),
                replanner=ScriptedWorkflowReplanner(
                    (
                        ReviseWorkflowProposal(
                            trigger=ReplanTrigger.EVIDENCE_INSUFFICIENT,
                            reason="the unsearched shard may contain relevant evidence",
                            plan=plan(),
                        ),
                    )
                ),
            ).run(current_bundle, run_id="workflow-replanning-run")

    assert result.execution_completed
    assert result.replanning is not None
    assert len(result.replanning.versions) == 2
    assert result.replanning.revisions[0].trigger == ReplanTrigger.EVIDENCE_INSUFFICIENT
    assert result.workflow is not None
    assert [record.node_id for record in result.workflow.records].count("retrieve-a") == 1
    assert [record.node_id for record in result.workflow.records] == [
        "retrieve-a",
        "retrieve-b",
        "synthesize",
    ]
    persisted = json.loads(
        (tmp_path / "workflow-replanning-run" / "result.json").read_text()
    )
    assert [version["revision_index"] for version in persisted["replanning"]["versions"]] == [
        0,
        1,
    ]
    events = [
        json.loads(line)
        for line in (tmp_path / "workflow-replanning-run" / "trace.jsonl")
        .read_text()
        .splitlines()
    ]
    assert {event["event_type"] for event in events} >= {
        "workflow.execution.paused",
        "workflow.replanner.start",
        "workflow.replanner.end",
        "workflow.execution.resume",
        "run.end",
    }
