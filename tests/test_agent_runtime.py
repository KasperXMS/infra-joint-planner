import asyncio
import json
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
import pytest

from infra_joint.agents import AgentManager, AgentStatus, AgentTaskView
from infra_joint.core.action import JointAction
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowEdge, WorkflowNode, WorkflowPlan
from infra_joint.evaluation.trace import TraceEvent
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import ExecutionResult, RuntimeExecutor
from infra_joint.worker.artifact_fetcher import FetchedArtifact
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelDeployment,
    ModelRequest,
)
from infra_joint.worker.server import create_worker_app
from infra_joint.workflow.orchestrator import WorkflowOrchestrator
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler
from infra_joint.workflow.trace import WorkflowTraceRecorder

SHA = "a" * 64


def task(*artifact_ids: str) -> TaskContract:
    return TaskContract(
        task_id="agent-runtime",
        benchmark_id="synthetic",
        objective="Combine the explicit evidence.",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=artifact_id,
                logical_type="evidence",
                media_type="text/plain",
                size_bytes=6,
            )
            for artifact_id in artifact_ids
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="exact",
    )


def logical_agent(agent_id: str, role: str, deployment: str = "shared") -> LogicalAgent:
    return LogicalAgent(
        agent_id=agent_id,
        role=role,
        objective=f"Act as {role}.",
        model_instance_id=deployment,
    )


def infrastructure(*artifact_ids: str) -> InfrastructureState:
    return InfrastructureState(
        agents=(AgentRuntimeState(agent_id="physical", available=True),),
        deployments=(DeploymentRuntimeState(deployment_id="shared", available=True),),
        artifacts=tuple(
            ArtifactRuntimeState(
                artifact_id=artifact_id,
                locations=("physical",),
                media_type="text/plain",
                size_bytes=6,
                sha256_hex=SHA,
            )
            for artifact_id in artifact_ids
        ),
        links=(),
        observed_at=datetime.now(UTC),
    )


def test_role_conditioning_and_agent_state_are_logically_isolated() -> None:
    current_task = task("source")
    plan = WorkflowPlan(
        agents=(
            logical_agent("analyst", "evidence analyst"),
            logical_agent("critic", "skeptical critic"),
        ),
        nodes=(
            WorkflowNode(
                node_id="analyze",
                agent_id="analyst",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Inspect it."},
            ),
            WorkflowNode(
                node_id="critique",
                agent_id="critic",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Inspect it."},
            ),
        ),
    )
    manager = AgentManager(
        current_task,
        plan,
        {"analyst": frozenset({"invoke_model"}), "critic": frozenset({"invoke_model"})},
    )

    analyst = manager.prepare(plan.nodes[0], infrastructure("source"))
    critic = manager.prepare(plan.nodes[1], infrastructure("source"))

    assert analyst.action.arguments["prompt"] != critic.action.arguments["prompt"]
    assert "Role: evidence analyst" in analyst.action.arguments["prompt"]
    assert "Role: skeptical critic" in critic.action.arguments["prompt"]
    assert analyst.context.inputs[0].object_id == "source"
    assert analyst.context.state.history == ()
    assert critic.context.state.history == ()
    assert manager.states[0] is not manager.states[1]
    assert "skeptical critic" not in analyst.context.model_dump_json()
    assert "evidence analyst" not in critic.context.model_dump_json()


def test_agent_context_prompt_and_trace_exclude_private_task_fields() -> None:
    source_secret = "private://source-must-not-leak"
    evaluator_secret = "private-evaluator-must-not-leak"
    current_task = TaskContract(
        task_id="sanitized-agent-task",
        benchmark_id="synthetic",
        objective="Answer from the artifact.",
        artifacts=(
            ArtifactSpec(
                artifact_id="source",
                logical_type="evidence",
                media_type="text/plain",
                size_bytes=6,
                source_ref=source_secret,
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id=evaluator_secret,
    )
    plan = WorkflowPlan(
        agents=(logical_agent("analyst", "analyst"),),
        nodes=(
            WorkflowNode(
                node_id="answer",
                agent_id="analyst",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Answer now."},
            ),
        ),
    )
    events: list[tuple[str, dict[str, object]]] = []
    manager = AgentManager(
        current_task,
        plan,
        {"analyst": frozenset({"invoke_model"})},
        emit=lambda event_type, payload: events.append((event_type, payload)),
    )

    prepared = manager.prepare(plan.nodes[0], infrastructure("source"))
    manager.start(prepared)

    serialized = "\n".join(
        (
            prepared.context.model_dump_json(),
            str(prepared.action.arguments["prompt"]),
            json.dumps(events, sort_keys=True),
        )
    )
    assert source_secret not in serialized
    assert evaluator_secret not in serialized
    assert set(AgentTaskView.model_json_schema()["properties"]) == {
        "task_id",
        "benchmark_id",
        "objective",
        "artifacts",
        "output_contract",
    }
    assert "source_ref" not in serialized
    assert "evaluator_id" not in serialized
    assert "gold" not in serialized
    assert "supporting_evidence" not in serialized


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


class RecordingBackend:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[ModelRequest] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        return ModelCompletion(
            text=self.response,
            telemetry=ModelCallTelemetry(
                service_latency_ms=1,
                input_tokens=10,
                output_tokens=2,
                finish_reason="stop",
            ),
        )

    async def complete(self, prompt: str) -> str:
        return (await self.invoke(ModelRequest(prompt=prompt))).text


class MemoryTraceSink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_model_output_is_materialized_transferred_and_consumed_by_next_agent() -> None:
    upstream_backend = RecordingBackend("explicit upstream reasoning")
    downstream_backend = RecordingBackend("final answer")
    store_a = InMemoryArtifactStore((StoredArtifact.create("source", "text/plain", b"source"),))
    app_a = create_worker_app(
        "A",
        {
            "model-a": ModelDeployment(
                deployment_id="model-a",
                model_id="same-model",
                backend=upstream_backend,
                modalities=frozenset({"text"}),
                context_window=4096,
                reserved_output_tokens=256,
                image_token_cost=1024,
            )
        },
        artifact_store=store_a,
    )
    current_task = task("source")
    plan = WorkflowPlan(
        agents=(
            logical_agent("researcher", "researcher", "model-a"),
            logical_agent("synthesizer", "synthesizer", "model-b"),
        ),
        nodes=(
            WorkflowNode(
                node_id="research",
                agent_id="researcher",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Extract evidence."},
                outputs=("reasoning-a",),
            ),
            WorkflowNode(
                node_id="synthesize",
                agent_id="synthesizer",
                operator="invoke_model",
                inputs=("reasoning-a",),
                arguments={"prompt": "Use the received evidence."},
            ),
        ),
        edges=(
            WorkflowEdge(
                producer_node="research",
                consumer_node="synthesize",
                artifact_id="reasoning-a",
            ),
        ),
    )
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="A", device="edge", capabilities=frozenset({"model"})),
            AgentSpec(agent_id="B", device="gpu", capabilities=frozenset({"model"})),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="model-a",
                agent_id="A",
                model_id="same-model",
                context_window=4096,
                reserved_output_tokens=256,
            ),
            DeploymentSpec(
                deployment_id="model-b",
                agent_id="B",
                model_id="same-model",
                context_window=4096,
                reserved_output_tokens=256,
            ),
        ),
    )
    sink = MemoryTraceSink()
    async with AsyncExitStack() as stack:
        http_a = await stack.enter_async_context(
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app_a), base_url="http://A")
        )
        app_b = create_worker_app(
            "B",
            {
                "model-b": ModelDeployment(
                    deployment_id="model-b",
                    model_id="same-model",
                    backend=downstream_backend,
                    modalities=frozenset({"text"}),
                    context_window=4096,
                    reserved_output_tokens=256,
                    image_token_cost=1024,
                )
            },
            artifact_fetcher=SourceClientFetcher(http_a),
        )
        http_b = await stack.enter_async_context(
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app_b), base_url="http://B")
        )
        clients = {
            "A": HttpWorkerClient("A", http_a),
            "B": HttpWorkerClient("B", http_b),
        }
        result = await WorkflowOrchestrator(
            build_operator_catalog(),
            environment,
            LiveWorkerObserver(environment, clients),
            RuntimeExecutor(build_operator_catalog(), environment, clients),
            LocalityAwareMyopicScheduler(),
            available_operations=("invoke_model",),
            trace=WorkflowTraceRecorder("agent-runtime", sink),
        ).execute(current_task, plan)

    assert result.completed
    assert result.telemetry.total_transfer_bytes == len(b"explicit upstream reasoning")
    assert downstream_backend.requests[0].artifacts[0].artifact_id == "reasoning-a"
    assert downstream_backend.requests[0].artifacts[0].content == b"explicit upstream reasoning"
    assert "Role: researcher" in upstream_backend.requests[0].prompt
    assert "Role: synthesizer" in downstream_backend.requests[0].prompt
    assert {item.status for item in result.agent_states} == {AgentStatus.DONE}
    event_types = {item.event_type for item in sink.events}
    assert {
        "agent.created",
        "agent.state.changed",
        "agent.action.start",
        "agent.action.end",
        "agent.information.received",
        "agent.information.produced",
        "artifact.transfer.end",
    } <= event_types


class MutableObserver:
    def __init__(self) -> None:
        self.artifacts = {
            artifact_id: ArtifactRuntimeState(
                artifact_id=artifact_id,
                locations=(location,),
                media_type="application/json",
                size_bytes=6,
                sha256_hex=SHA,
            )
            for artifact_id, location in (("left", "A"), ("right", "B"))
        }

    async def observe(self) -> InfrastructureState:
        return InfrastructureState(
            agents=tuple(AgentRuntimeState(agent_id=item, available=True) for item in ("A", "B")),
            deployments=(DeploymentRuntimeState(deployment_id="shared", available=True),),
            artifacts=tuple(self.artifacts.values()),
            links=(),
            observed_at=datetime.now(UTC),
        )


class ConcurrencyExecutor:
    def __init__(self, observer: MutableObserver) -> None:
        self.observer = observer
        self.active = 0
        self.max_active = 0

    async def execute(
        self, action: JointAction, infrastructure: InfrastructureState
    ) -> ExecutionResult:
        del infrastructure
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        output_id = str(action.semantic.arguments["output_artifact_id"])
        location = "A" if action.semantic.inputs == ("left",) else "B"
        self.observer.artifacts[output_id] = ArtifactRuntimeState(
            artifact_id=output_id,
            locations=(location,),
            media_type="application/json",
            size_bytes=1,
            sha256_hex=SHA,
        )
        self.active -= 1
        return ExecutionResult(
            operator="bm25_retrieve",
            agent_ids=(location,),
            output={
                "artifact_id": output_id,
                "media_type": "application/json",
                "size_bytes": 1,
                "sha256_hex": SHA,
            },
        )


@pytest.mark.asyncio
async def test_two_ready_nodes_owned_by_same_logical_agent_are_serialized() -> None:
    current_task = TaskContract(
        task_id="serialize",
        benchmark_id="synthetic",
        objective="retrieve",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=item,
                logical_type="records",
                media_type="application/json",
                size_bytes=6,
            )
            for item in ("left", "right")
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="none",
    )
    plan = WorkflowPlan(
        agents=(logical_agent("one-agent", "retriever"),),
        nodes=tuple(
            WorkflowNode(
                node_id=f"retrieve-{source}",
                agent_id="one-agent",
                operator="bm25_retrieve",
                inputs=(source,),
                arguments={
                    "query": "x",
                    "top_k": 1,
                    "output_artifact_id": f"out-{source}",
                },
                outputs=(f"out-{source}",),
            )
            for source in ("left", "right")
        ),
    )
    environment = EnvironmentSpec(
        agents=tuple(
            AgentSpec(
                agent_id=item,
                device="test",
                capabilities=frozenset({"retrieval", "model"}),
            )
            for item in ("A", "B")
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="shared",
                agent_id="A",
                model_id="model",
                context_window=4096,
            ),
        ),
    )
    observer = MutableObserver()
    executor = ConcurrencyExecutor(observer)
    result = await WorkflowOrchestrator(
        build_operator_catalog(),
        environment,
        observer,
        executor,
        LocalityAwareMyopicScheduler(),
        available_operations=("bm25_retrieve",),
    ).execute(current_task, plan)

    assert result.completed
    assert executor.max_active == 1
    assert [item.scheduling_batch for item in result.records] == [0, 1]
    assert len(result.agent_states) == 1
    assert len(result.agent_states[0].history) == 2
