import json
import sys
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    BenchmarkSettingKind,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    ValidityAssessment,
)
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.contracts import (
    ContinueDecision,
    ExecutionRequirements,
    FinishDecision,
    LogicalAgentSpec,
    LogicalModelAction,
    LogicalOutput,
    LogicalToolAction,
    ManagerContext,
    ProfileVisibility,
    SubagentCall,
    WorkflowGraphSnapshot,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import (
    AgentLoopBudget,
    AgentLoopError,
    PersistentManagerLoop,
    ScriptedManagerPolicy,
    ScriptedSubagentFactory,
)
from infra_joint.control.openai_agents import OpenAIAgentsManagerPolicy
from infra_joint.control.physical import (
    AutoPhysicalScheduler,
    PhysicalExecutionService,
    PhysicalProfiler,
)
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.control.validation import SemanticActionValidator, semantic_action
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactPlacement,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
)
from infra_joint.core.task import (
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.evaluation.trace import TraceEvent
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import RuntimeExecutor
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelDeployment,
    ModelRequest,
)
from infra_joint.worker.server import create_worker_app
from infra_joint.workflow.trace import WorkflowTraceRecorder


class QueueBackend:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.requests: list[ModelRequest] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        return ModelCompletion(
            text=self._responses.pop(0),
            telemetry=ModelCallTelemetry(
                service_latency_ms=1,
                input_tokens=8,
                output_tokens=2,
                finish_reason="stop",
            ),
        )

    async def complete(self, prompt: str) -> str:
        return (await self.invoke(ModelRequest(prompt=prompt))).text


class MemorySink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self.events.append(event)


def task() -> TaskContract:
    return TaskContract(
        task_id="control-smoke",
        benchmark_id="synthetic",
        objective="Answer from the source.",
        artifacts=(
            ArtifactSpec(
                artifact_id="source",
                logical_type="evidence",
                media_type="text/plain",
                size_bytes=11,
                source_ref="private://must-not-leak",
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private-evaluator",
    )


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
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
                reserved_output_tokens=64,
            ),
            DeploymentSpec(
                deployment_id="model-b",
                agent_id="B",
                model_id="same-model",
                context_window=4096,
                reserved_output_tokens=64,
            ),
        ),
    )


def state(source_location: str) -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="A", available=True),
            AgentRuntimeState(agent_id="B", available=True),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="model-a", available=True),
            DeploymentRuntimeState(deployment_id="model-b", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="source",
                locations=(source_location,),
                media_type="text/plain",
                size_bytes=11,
            ),
        ),
        links=(),
        observed_at=datetime.now(UTC),
    )


def test_logical_action_contract_rejects_physical_binding() -> None:
    with pytest.raises(ValidationError):
        LogicalModelAction.model_validate(
            {
                "action_id": "answer",
                "owner_agent_id": "manager",
                "prompt": "answer",
                "deployment_id": "model-a",
            }
        )
    with pytest.raises(ValidationError, match="forbidden physical field"):
        LogicalToolAction(
            action_id="tool",
            owner_agent_id="manager",
            operator="read_artifact",
            arguments={"target_agent_id": "A"},
        )


def test_semantic_validation_does_not_require_environment() -> None:
    registry = build_operator_catalog()
    validator = SemanticActionValidator(
        task(), registry, ("read_artifact", "invoke_model")
    )
    action = LogicalModelAction(
        action_id="answer",
        owner_agent_id="manager",
        prompt="answer",
        inputs=("source",),
    )
    validator.validate_batch((action,))
    with pytest.raises(ValueError, match="outside the system action space"):
        SemanticActionValidator(task(), registry, ("read_artifact",)).validate_batch(
            (action,)
        )


def test_same_logical_model_action_can_bind_to_different_devices() -> None:
    registry = build_operator_catalog()
    current_environment = environment()
    scheduler = AutoPhysicalScheduler()
    action = LogicalModelAction(
        action_id="answer",
        owner_agent_id="manager",
        prompt="answer",
        inputs=("source",),
        requirements=ExecutionRequirements(
            modalities=frozenset({"text"}),
            min_context_tokens=512,
        ),
    )
    semantic = semantic_action(action)
    on_a = scheduler.select(
        action,
        semantic,
        current_environment,
        state("A"),
        registry,
    )
    on_b = scheduler.select(
        action,
        semantic,
        current_environment,
        state("B"),
        registry,
    )
    assert on_a.selected_agent_id == "A"
    assert on_a.selected_deployment_id == "model-a"
    assert on_b.selected_agent_id == "B"
    assert on_b.selected_deployment_id == "model-b"
    serialized = action.model_dump_json()
    assert "model-a" not in serialized
    assert "model-b" not in serialized


def test_aware_profile_is_abstract_and_identifier_free() -> None:
    action = LogicalModelAction(
        action_id="answer",
        owner_agent_id="manager",
        prompt="answer",
        inputs=("source",),
    )
    view = PhysicalProfiler(environment(), build_operator_catalog()).for_action(
        action, state("A")
    )
    serialized = view.model_dump_json()
    assert view.candidate_count == 2
    assert "model-a" not in serialized
    assert '"A"' not in serialized
    assert "deployment" not in serialized
    assert "worker" not in serialized


@pytest.mark.asyncio
async def test_openai_agents_adapter_emits_only_logical_decisions(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, **kwargs) -> None:
            captured["agent"] = kwargs

    class FakeRunner:
        @staticmethod
        async def run(agent, input: str):
            captured["input"] = input
            return SimpleNamespace(
                final_output={
                    "decision": {
                        "decision_type": "continue",
                        "rationale": "take one semantic action",
                        "actions": [
                            {
                                "action_type": "model",
                                "action_id": "answer",
                                "owner_agent_id": "manager",
                                "prompt": "answer semantically",
                            }
                        ],
                    }
                }
            )

    monkeypatch.setitem(
        sys.modules,
        "agents",
        SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner),
    )
    policy = OpenAIAgentsManagerPolicy(
        name="manager",
        instructions="Solve the task.",
        model="planner-model",
        registry=build_operator_catalog(),
        available_operations=("invoke_model",),
    )
    decision = await policy.decide(
        ManagerContext(
            task=AgentTaskView.from_contract(task()),
            agent=LogicalAgentSpec(
                logical_agent_id="manager",
                role="manager",
                objective="solve",
            ),
            assigned_artifacts=("source",),
            unresolved_requirements=("solve",),
            observations=(),
            subagent_results=(),
            workflow=WorkflowGraphSnapshot(version=0, nodes=(), edges=()),
        )
    )
    assert isinstance(decision, ContinueDecision)
    assert isinstance(decision.actions[0], LogicalModelAction)
    serialized = str(captured["input"])
    assert "private://must-not-leak" not in serialized
    assert "private-evaluator" not in serialized
    assert "deployment_id" not in serialized
    assert "worker_id" not in serialized


@pytest.mark.asyncio
async def test_openai_agents_adapter_supports_strict_text_json(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    class FakeRunner:
        @staticmethod
        async def run(agent, input: str):
            captured["input"] = input
            return SimpleNamespace(
                final_output=json.dumps(
                    {
                        "decision": {
                            "decision_type": "continue",
                            "rationale": "take a model step",
                            "actions": [
                                {
                                    "action_type": "model",
                                    "action_id": "answer",
                                    "owner_agent_id": "manager",
                                    "prompt": "answer",
                                }
                            ],
                        }
                    }
                )
            )

    monkeypatch.setitem(
        sys.modules,
        "agents",
        SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner),
    )
    decision = await OpenAIAgentsManagerPolicy(
        name="manager",
        instructions="Solve.",
        model="planner-model",
        registry=build_operator_catalog(),
        available_operations=("invoke_model",),
        structured_output=False,
    ).decide(
        ManagerContext(
            task=AgentTaskView.from_contract(task()),
            agent=LogicalAgentSpec(
                logical_agent_id="manager",
                role="manager",
                objective="solve",
            ),
            assigned_artifacts=("source",),
            unresolved_requirements=("solve",),
            observations=(),
            subagent_results=(),
            workflow=WorkflowGraphSnapshot(version=0, nodes=(), edges=()),
        )
    )
    assert isinstance(decision, ContinueDecision)
    assert captured["output_type"] is str
    assert "decision_json_schema" in str(captured["input"])


@pytest.mark.asyncio
async def test_persistent_manager_subagent_gateway_and_trace_smoke() -> None:
    registry = build_operator_catalog()
    backend = QueueBackend(["bounded evidence", "terminal answer"])
    store = InMemoryArtifactStore(
        (StoredArtifact.create("source", "text/plain", b"hello world"),)
    )
    app = create_worker_app(
        "A",
        {
            "model-a": ModelDeployment(
                deployment_id="model-a",
                model_id="test-model",
                backend=backend,
                modalities=frozenset({"text"}),
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            )
        },
        artifact_store=store,
    )
    current_environment = EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="A", device="edge", capabilities=frozenset({"model"})),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="model-a",
                agent_id="A",
                model_id="test-model",
                context_window=4096,
                reserved_output_tokens=64,
            ),
        ),
    )
    specialist = LogicalAgentSpec(
        logical_agent_id="researcher",
        role="evidence researcher",
        objective="inspect and materialize bounded evidence",
    )
    subagent_call = SubagentCall(
        call_id="research-call",
        agent=specialist,
        instruction="inspect source and produce evidence",
        input_artifacts=("source",),
    )
    root_policy = ScriptedManagerPolicy(
        (
            ContinueDecision(
                rationale="delegate bounded evidence work",
                subagent_calls=(subagent_call,),
            ),
            ContinueDecision(
                rationale="synthesize after observing the specialist",
                actions=(
                    LogicalModelAction(
                        action_id="manager-answer",
                        owner_agent_id="manager",
                        prompt="Return the final answer from the evidence.",
                        inputs=("evidence",),
                    ),
                ),
            ),
            FinishDecision(
                reason="terminal model produced the benchmark answer",
                source_action_id="manager-answer",
            ),
        )
    )
    child_policy = ScriptedManagerPolicy(
        (
            ContinueDecision(
                rationale="inspect metadata first",
                actions=(
                    LogicalToolAction(
                        action_id="inspect-source",
                        owner_agent_id="researcher",
                        operator="read_artifact",
                        inputs=("source",),
                    ),
                ),
            ),
            ContinueDecision(
                rationale="materialize reusable evidence after observation",
                actions=(
                    LogicalModelAction(
                        action_id="research-evidence",
                        owner_agent_id="researcher",
                        prompt="Extract bounded evidence.",
                        inputs=("source",),
                        outputs=(
                            LogicalOutput(
                                artifact_id="evidence",
                                semantic_type="evidence_note",
                                media_type="text/plain",
                            ),
                        ),
                    ),
                ),
            ),
            FinishDecision(
                reason="bounded specialist work is complete",
                source_action_id="research-evidence",
            ),
        )
    )
    sink = MemorySink()
    async with AsyncExitStack() as stack:
        http = await stack.enter_async_context(
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://A",
            )
        )
        clients = {"A": HttpWorkerClient("A", http)}
        observer = LiveWorkerObserver(current_environment, clients)
        gateway = RuntimeActionGateway(
            SemanticActionValidator(
                task(), registry, ("read_artifact", "invoke_model")
            ),
            PhysicalExecutionService(
                registry,
                current_environment,
                observer,
                RuntimeExecutor(registry, current_environment, clients),
            ),
        )
        result = await PersistentManagerLoop(
            gateway,
            root_policy,
            subagent_factory=ScriptedSubagentFactory(
                {"research-call": child_policy}
            ),
            profile_visibility=ProfileVisibility.BLIND,
            trace=WorkflowTraceRecorder("control-smoke", sink),
        ).run(task())

    assert result.final_answer == "terminal answer"
    assert result.terminal_action_id == "manager-answer"
    assert tuple(item.action_id for item in result.observations) == (
        "inspect-source",
        "research-evidence",
        "manager-answer",
    )
    assert all(item.physical_profile is None for item in result.observations)
    assert len(result.subagent_results) == 1
    assert result.graph_snapshots[0].version == 0
    assert result.graph_snapshots[-1].version >= 6
    final_graph = result.graph_snapshots[-1]
    assert {item.owner_agent_id for item in final_graph.nodes} == {
        "manager",
        "researcher",
    }
    assert any(item.information_id == "evidence" for item in final_graph.edges)
    assert root_policy.contexts[0].physical_profile is None
    assert "evidence" in root_policy.contexts[1].assigned_artifacts
    assert child_policy.contexts[0].assigned_artifacts == ("source",)
    assert tuple(
        item.artifact_id for item in child_policy.contexts[0].task.artifacts
    ) == ("source",)

    event_types = [item.event_type for item in sink.events]
    assert "logical.subagent.start" in event_types
    assert "logical.observation" in event_types
    assert "workflow.graph.snapshot" in event_types
    assert event_types.count("physical.execution") == 3
    physical_events = [
        item for item in sink.events if item.event_type == "physical.execution"
    ]
    assert physical_events[-1].payload["selection"]["selected_deployment_id"] == "model-a"
    logical_serialized = json.dumps(
        [
            item.payload
            for item in sink.events
            if item.event_type.startswith("logical.")
        ],
        sort_keys=True,
    )
    assert "private://must-not-leak" not in logical_serialized
    assert "private-evaluator" not in logical_serialized
    assert "model-a" not in logical_serialized
    assert '"A"' not in logical_serialized


@pytest.mark.asyncio
async def test_persistent_loop_enforces_uniform_subagent_budget() -> None:
    manager = ScriptedManagerPolicy(
        (
            ContinueDecision(
                rationale="request too many specialists",
                subagent_calls=(
                    SubagentCall(
                        call_id="one",
                        agent=LogicalAgentSpec(
                            logical_agent_id="one",
                            role="researcher",
                            objective="inspect",
                        ),
                        instruction="inspect",
                    ),
                    SubagentCall(
                        call_id="two",
                        agent=LogicalAgentSpec(
                            logical_agent_id="two",
                            role="researcher",
                            objective="inspect",
                        ),
                        instruction="inspect",
                    ),
                ),
            ),
        )
    )
    with pytest.raises(AgentLoopError, match="created subagent budget exceeded"):
        await PersistentManagerLoop(
            gateway=SimpleNamespace(),
            manager=manager,
            subagent_factory=ScriptedSubagentFactory({}),
            budget=AgentLoopBudget(
                max_manager_turns=2,
                max_subagent_turns=2,
                max_tool_model_calls=2,
                max_created_subagents=1,
                max_active_subagents=1,
            ),
        ).run(task())


@pytest.mark.asyncio
async def test_control_plane_runner_uses_terminal_answer_and_original_evaluator(
    tmp_path,
) -> None:
    content = b"choose option A"
    artifact = PreparedArtifact.create(
        ArtifactSpec(
            artifact_id="evidence",
            logical_type="document",
            media_type="text/plain",
            size_bytes=len(content),
            source_ref="private://runner-source",
        ),
        content,
    )
    runner_task = TaskContract(
        task_id="control-runner",
        benchmark_id="synthetic",
        objective="Choose A or B.",
        artifacts=(artifact.spec,),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-exact",
    )
    bundle = AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=runner_task,
            transformations=(),
            validity=ValidityAssessment(
                information_equivalent=True,
                query_equivalent=True,
                evaluator_equivalent=True,
                setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
            ),
        ),
        private_evaluation=PrivateChoiceEvaluation(
            task_id="control-runner",
            evaluator_id="private-exact",
            gold_answer="A",
        ),
        prepared_artifacts=(artifact,),
    )
    backend = QueueBackend(["A"])
    worker_app = create_worker_app(
        "worker-secret",
        {
            "deployment-secret": ModelDeployment(
                deployment_id="deployment-secret",
                model_id="test-model",
                backend=backend,
                modalities=frozenset({"text"}),
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            )
        },
    )
    runner_environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="worker-secret",
                device="test-device",
                capabilities=frozenset(
                    {"model", "structured", "retrieval", "media.image"}
                ),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="deployment-secret",
                agent_id="worker-secret",
                model_id="test-model",
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            ),
        ),
        initial_placements=(
            ArtifactPlacement(artifact_id="evidence", agent_id="worker-secret"),
        ),
    )
    config = RunnerConfig(
        environment=runner_environment,
        worker_urls={"worker-secret": "http://worker-secret"},
        planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
        output_root=tmp_path / "runs",
        max_planning_steps=2,
    )
    policy = ScriptedManagerPolicy(
        (
            ContinueDecision(
                rationale="answer using evidence",
                actions=(
                    LogicalModelAction(
                        action_id="terminal",
                        owner_agent_id="manager",
                        prompt="Return only A or B.",
                        inputs=("evidence",),
                    ),
                ),
            ),
            FinishDecision(
                reason="terminal answer ready",
                source_action_id="terminal",
            ),
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=worker_app),
        base_url="http://worker-secret",
    ) as client:
        result = await ControlPlaneBenchmarkRunner(
            config,
            policy,
            ("invoke_model",),
            worker_clients={
                "worker-secret": HttpWorkerClient("worker-secret", client)
            },
        ).run(bundle, run_id="control-run")

    assert result.execution_completed
    assert result.final_answer == "A"
    assert result.evaluation is not None
    assert result.evaluation.benchmark_score == 1
    assert result.loop is not None
    assert result.loop.terminal_action_id == "terminal"
    trace_text = (tmp_path / "runs" / "control-run" / "trace.jsonl").read_text(
        encoding="utf-8"
    )
    logical_lines = "\n".join(
        line
        for line in trace_text.splitlines()
        if '"event_type":"logical.' in line
    )
    assert "private://runner-source" not in logical_lines
    assert "private-exact" not in logical_lines
    assert "worker-secret" not in logical_lines
    assert "deployment-secret" not in logical_lines
