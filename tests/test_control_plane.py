import asyncio
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
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import (
    ContinueDecision,
    ExecutionRequirements,
    FinishDecision,
    LogicalAgentSpec,
    LogicalModelAction,
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
    ManagerContext,
    ProducedInformation,
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
    PhysicalExecutionOutcome,
    PhysicalExecutionService,
    PhysicalProfiler,
    PhysicalSelection,
)
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.control.validation import (
    SemanticActionValidator,
    SemanticValidationError,
    semantic_action,
)
from infra_joint.control.workflow import SemanticWorkflowPlan, WorkflowRuntimeState
from infra_joint.control.workflow_cost import SemanticWorkflowCostEvaluator
from infra_joint.core.action import JointAction, PhysicalPolicy
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactPlacement,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
    LinkSpec,
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
from infra_joint.runtime.executor import ExecutionResult, RuntimeExecutor
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelDeployment,
    ModelRequest,
)
from infra_joint.worker.server import create_worker_app
from infra_joint.workflow.costing import ExecutionCostProfile
from infra_joint.workflow.trace import WorkflowTraceRecorder


class SequencedObserver:
    def __init__(self, *states: InfrastructureState) -> None:
        self._states = states
        self.calls = 0

    async def observe(self) -> InfrastructureState:
        state = self._states[min(self.calls, len(self._states) - 1)]
        self.calls += 1
        return state


class FrozenSelectionExecutor:
    def __init__(self) -> None:
        self.decisions: list[object] = []
        self.snapshots: list[InfrastructureState] = []

    async def execute(
        self,
        action: object,
        infrastructure: InfrastructureState,
    ) -> ExecutionResult:
        self.decisions.append(action)
        self.snapshots.append(infrastructure)
        return ExecutionResult(
            operator="invoke_model",
            agent_ids=("A",),
            deployment_id="dep-a",
            output={"text": "A"},
        )


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


class ConcurrentPhysicalService:
    def __init__(self, expected: int) -> None:
        self.expected = expected
        self.entered = 0
        self.active = 0
        self.peak_active = 0
        self.release = asyncio.Event()

    async def execute(self, action, *, expose_profile: bool):
        assert not expose_profile
        self.entered += 1
        self.active += 1
        self.peak_active = max(self.peak_active, self.active)
        if self.entered == self.expected:
            self.release.set()
        await asyncio.wait_for(self.release.wait(), timeout=1)
        await asyncio.sleep(0)
        self.active -= 1
        current_state = state("A")
        return PhysicalExecutionOutcome(
            observation=LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
            ),
            infrastructure_before=current_state,
            infrastructure_after=current_state,
        )


class MixedPhysicalService:
    async def execute(self, action, *, expose_profile: bool):
        assert not expose_profile
        current_state = state("A")
        selection = PhysicalSelection(
            decision={"policy": "auto"},
            selected_agent_id="secret-worker",
            selected_deployment_id=(
                "secret-deployment" if isinstance(action, LogicalModelAction) else None
            ),
            rationale="test selection",
        )
        if action.action_id == "bad-retrieval":
            return PhysicalExecutionOutcome(
                observation=LogicalObservation(
                    action_id=action.action_id,
                    owner_agent_id=action.owner_agent_id,
                    succeeded=False,
                    failure_code="operator_failed",
                    failure_message="bounded failure",
                ),
                infrastructure_before=current_state,
                infrastructure_after=current_state,
                selection=selection,
            )
        produced = tuple(
            ProducedInformation(
                artifact_id=item.artifact_id,
                semantic_type=item.semantic_type,
                media_type=item.media_type,
                size_bytes=12,
            )
            for item in action.outputs
        )
        output = {"text": "A"} if isinstance(action, LogicalModelAction) else {}
        return PhysicalExecutionOutcome(
            observation=LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
                output=output,
                produced_information=produced,
            ),
            infrastructure_before=current_state,
            infrastructure_after=current_state,
            selection=selection,
            execution=ExecutionResult(
                operator=(
                    "invoke_model"
                    if isinstance(action, LogicalModelAction)
                    else action.operator
                ),
                agent_ids=("secret-worker",),
                deployment_id=selection.selected_deployment_id,
                output=output,
            ),
        )


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


def retrieval_task(count: int) -> TaskContract:
    return TaskContract(
        task_id=f"retrieval-{count}",
        benchmark_id="synthetic",
        objective="Retrieve independent evidence.",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=f"shard-{index}",
                logical_type="records",
                media_type="application/json",
                size_bytes=2,
            )
            for index in range(count)
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private-evaluator",
    )


def retrieval_actions(count: int) -> tuple[LogicalToolAction, ...]:
    return tuple(
        LogicalToolAction(
            action_id=f"retrieve-{index}",
            owner_agent_id="manager",
            operator="bm25_retrieve",
            inputs=(f"shard-{index}",),
            outputs=(
                LogicalOutput(
                    artifact_id=f"hits-{index}",
                    semantic_type="retrieval_hits",
                    media_type="application/json",
                ),
            ),
            arguments={
                "query": "target evidence",
                "top_k": 2,
                "text_field": "text",
                "output_artifact_id": f"hits-{index}",
            },
        )
        for index in range(count)
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


async def _assert_same_owner_retrieval_batch_runs_in_parallel(count: int) -> None:
    current_task = retrieval_task(count)
    physical = ConcurrentPhysicalService(count)
    gateway = RuntimeActionGateway(
        SemanticActionValidator(
            current_task,
            build_operator_catalog(),
            ("bm25_retrieve",),
        ),
        physical,  # type: ignore[arg-type]
    )
    outcomes = await gateway.execute_batch(
        retrieval_actions(count),
        expose_profile=False,
    )
    assert len(outcomes) == count
    assert physical.peak_active == count


@pytest.mark.asyncio
async def test_same_agent_four_independent_bm25_actions_run_in_parallel() -> None:
    await _assert_same_owner_retrieval_batch_runs_in_parallel(4)


@pytest.mark.asyncio
async def test_same_agent_six_cross_shard_bm25_actions_run_in_parallel() -> None:
    await _assert_same_owner_retrieval_batch_runs_in_parallel(6)


@pytest.mark.asyncio
async def test_real_gateway_freezes_one_shared_scheduling_snapshot() -> None:
    current_task = TaskContract(
        task_id="shared-frontier-snapshot",
        benchmark_id="synthetic",
        objective="Answer from the shared evidence.",
        artifacts=(
            ArtifactSpec(
                artifact_id="raw",
                logical_type="evidence",
                media_type="application/json",
                size_bytes=100,
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private",
    )
    environment = EnvironmentSpec(
        agents=tuple(
            AgentSpec(
                agent_id=agent_id,
                device="gpu",
                capabilities=frozenset({"model"}),
            )
            for agent_id in ("A", "B")
        ),
        deployments=tuple(
            DeploymentSpec(
                deployment_id=f"dep-{agent_id.lower()}",
                agent_id=agent_id,
                model_id="test-model",
                context_window=4_096,
                reserved_output_tokens=64,
                image_token_cost=256,
            )
            for agent_id in ("A", "B")
        ),
        links=tuple(
            LinkSpec(
                source_agent_id=source,
                target_agent_id=target,
                bandwidth_mbps=10,
                rtt_ms=10,
            )
            for source, target in (("A", "B"), ("B", "A"))
        ),
    )

    def snapshot(location: str, second: int) -> InfrastructureState:
        return InfrastructureState(
            agents=tuple(
                AgentRuntimeState(agent_id=agent_id, available=True)
                for agent_id in ("A", "B")
            ),
            deployments=tuple(
                DeploymentRuntimeState(
                    deployment_id=f"dep-{agent_id.lower()}",
                    available=True,
                )
                for agent_id in ("A", "B")
            ),
            artifacts=(
                ArtifactRuntimeState(
                    artifact_id="raw",
                    locations=(location,),
                    media_type="application/json",
                    size_bytes=100,
                ),
            ),
            links=tuple(
                LinkRuntimeState(
                    source_agent_id=source,
                    target_agent_id=target,
                    available=True,
                    bandwidth_mbps=10,
                    rtt_ms=10,
                )
                for source, target in (("A", "B"), ("B", "A"))
            ),
            observed_at=datetime(2026, 1, 1, 0, 0, second, tzinfo=UTC),
        )

    before = snapshot("A", 1)
    after = snapshot("B", 2)
    observer = SequencedObserver(before, after)
    executor = FrozenSelectionExecutor()
    registry = build_operator_catalog()
    gateway = RuntimeActionGateway(
        SemanticActionValidator(current_task, registry, ("invoke_model",)),
        PhysicalExecutionService(
            registry,
            environment,
            observer,
            executor,  # type: ignore[arg-type]
        ),
    )
    actions = tuple(
        LogicalModelAction(
            action_id=f"sibling-{index}",
            owner_agent_id="manager",
            inputs=("raw",),
            prompt="Return A or B.",
        )
        for index in range(2)
    )
    outcomes = await gateway.execute_batch(actions, expose_profile=False)

    assert observer.calls == 2  # one pre-frontier scheduling observation, one post-frontier
    assert [item.selection.selected_agent_id for item in outcomes if item.selection] == [
        "A",
        "A",
    ]
    assert all(item.infrastructure_before == before for item in outcomes)
    assert all(item.infrastructure_after == after for item in outcomes)
    assert executor.snapshots == [before, before]
    assert all(isinstance(item, JointAction) for item in executor.decisions)
    assert all(
        item.physical.policy == PhysicalPolicy.TARGET_DEPLOYMENT
        and item.physical.target_deployment_id == "dep-a"
        for item in executor.decisions
        if isinstance(item, JointAction)
    )
    assert len({item.batch_id for item in outcomes}) == 1
    assert len({item.shared_snapshot_sha256 for item in outcomes}) == 1
    assert all(item.shared_snapshot_observed_at == before.observed_at for item in outcomes)

    plan = SemanticWorkflowPlan(
        workflow_id="shared-frontier-snapshot",
        version=0,
        actions=actions,
        terminal_action_id="sibling-0",
    )
    predicted = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        tuple(
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id=agent_id,
                deployment_id=f"dep-{agent_id.lower()}",
                unit_kind="fixed",
                service_latency_ms=10,
                source="test",
            )
            for agent_id in ("A", "B")
        ),
        current_task,
        build_static_capability_contract(environment, registry, ("invoke_model",)),
    ).evaluate_detailed(plan, WorkflowRuntimeState.initialize(plan), before)
    assert [item.selected_agent_id for item in predicted.selected_bindings] == [
        item.selection.selected_agent_id
        for item in outcomes
        if item.selection is not None
    ]


def test_same_batch_producer_consumer_is_rejected() -> None:
    current_task = TaskContract(
        task_id="dependent-batch",
        benchmark_id="synthetic",
        objective="Inspect images.",
        artifacts=(
            ArtifactSpec(
                artifact_id="frame-1",
                logical_type="video_frame",
                media_type="image/jpeg",
                size_bytes=10,
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private-evaluator",
    )
    contact = LogicalToolAction(
        action_id="contact",
        owner_agent_id="manager",
        operator="make_contact_sheet",
        inputs=("frame-1",),
        outputs=(
            LogicalOutput(
                artifact_id="contact-sheet",
                semantic_type="contact_sheet",
                media_type="image/jpeg",
            ),
        ),
        arguments={"output_artifact_id": "contact-sheet"},
    )
    analyze = LogicalModelAction(
        action_id="analyze",
        owner_agent_id="manager",
        inputs=("contact-sheet",),
        prompt="Analyze the contact sheet.",
        requirements=ExecutionRequirements(modalities=frozenset({"text", "image"})),
    )
    with pytest.raises(
        SemanticValidationError,
        match="same-batch producer-consumer dependency",
    ):
        SemanticActionValidator(
            current_task,
            build_operator_catalog(),
            ("make_contact_sheet", "invoke_model"),
        ).validate_batch((contact, analyze))


@pytest.mark.asyncio
async def test_mixed_batch_observations_arrive_together_and_graph_states_are_correct() -> None:
    current_task = retrieval_task(2).model_copy(
        update={
            "output_contract": OutputContract(
                format=OutputFormat.CHOICE,
                choices=("A", "B"),
            )
        }
    )
    good, bad = retrieval_actions(2)
    bad = bad.model_copy(update={"action_id": "bad-retrieval"})
    policy = ScriptedManagerPolicy(
        (
            ContinueDecision(
                rationale="run an independent mixed batch",
                actions=(good, bad),
            ),
            ContinueDecision(
                rationale="answer from the successful observation",
                actions=(
                    LogicalModelAction(
                        action_id="terminal",
                        owner_agent_id="manager",
                        inputs=("hits-0",),
                        prompt="Return A.",
                    ),
                ),
            ),
            FinishDecision(reason="done", source_action_id="terminal"),
        )
    )
    registry = build_operator_catalog()
    gateway = RuntimeActionGateway(
        SemanticActionValidator(
            current_task,
            registry,
            ("bm25_retrieve", "invoke_model"),
        ),
        MixedPhysicalService(),  # type: ignore[arg-type]
    )
    sink = MemorySink()
    result = await PersistentManagerLoop(
        gateway,
        policy,
        profile_visibility=ProfileVisibility.BLIND,
        trace=WorkflowTraceRecorder("mixed-batch", sink),
    ).run(current_task)

    assert result.final_answer == "A"
    assert len(policy.contexts[1].observations) == 2
    assert {item.succeeded for item in policy.contexts[1].observations} == {True, False}
    final_nodes = {item.action_id: item.status for item in result.graph_snapshots[-1].nodes}
    assert final_nodes == {
        "retrieve-0": "succeeded",
        "bad-retrieval": "failed",
        "terminal": "succeeded",
    }
    batch_events = [
        item for item in sink.events if item.event_type.startswith("logical.batch.")
    ]
    assert [item.event_type for item in batch_events[:3]] == [
        "logical.batch.validation",
        "logical.batch.started",
        "logical.batch.completed",
    ]
    first_completion = batch_events[2].payload
    assert first_completion["succeeded_action_ids"] == ["retrieve-0"]
    assert first_completion["failed_action_ids"] == ["bad-retrieval"]
    logical_serialized = json.dumps(
        [
            item.payload
            for item in sink.events
            if item.event_type.startswith("logical.")
        ],
        sort_keys=True,
    )
    assert "secret-worker" not in logical_serialized
    assert "secret-deployment" not in logical_serialized
    assert "private-evaluator" not in logical_serialized


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


@pytest.mark.asyncio
async def test_failed_physical_action_retains_selection_and_failure_telemetry() -> None:
    content = b"too large"
    store = InMemoryArtifactStore(
        (StoredArtifact.create("source", "text/plain", content),)
    )
    app = create_worker_app(
        "A",
        {},
        artifact_store=store,
        max_read_artifact_bytes=4,
    )
    current_environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="A", device="edge"),),
        deployments=(),
    )
    registry = build_operator_catalog()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://A",
    ) as http:
        clients = {"A": HttpWorkerClient("A", http)}
        outcome = await PhysicalExecutionService(
            registry,
            current_environment,
            LiveWorkerObserver(current_environment, clients),
            RuntimeExecutor(registry, current_environment, clients),
        ).execute(
            LogicalToolAction(
                action_id="read",
                owner_agent_id="manager",
                operator="read_artifact",
                inputs=("source",),
            ),
            expose_profile=False,
        )

    assert not outcome.observation.succeeded
    assert outcome.observation.failure_code == "artifact_too_large"
    assert outcome.observation.physical_profile is None
    assert outcome.selection is not None
    assert outcome.selection.selected_agent_id == "A"
    assert outcome.failure is not None
    assert outcome.failure.stage == "execution"
    assert outcome.failure.operator == "read_artifact"
    assert outcome.failure.duration_ms >= 0
    logical_json = outcome.observation.model_dump_json()
    assert "selected_agent_id" not in logical_json
    assert "deployment_id" not in logical_json


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


@pytest.mark.asyncio
async def test_control_plane_evaluator_is_not_built_before_terminal_answer(
    tmp_path,
) -> None:
    runner_task = TaskContract(
        task_id="no-terminal",
        benchmark_id="synthetic",
        objective="Return A.",
        artifacts=(),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-spy",
    )

    class PrivateEvaluatorSpy:
        task_id = "no-terminal"
        evaluator_id = "private-spy"

        def __init__(self) -> None:
            self.built = False

        def build_evaluator(self) -> object:
            self.built = True
            raise AssertionError("evaluator must not be built before a terminal answer")

    class FailingLogicalRuntime:
        async def run(self, *_args: object, **_kwargs: object) -> object:
            raise AgentLoopError("verifier did not authorize synthesis")

    private = PrivateEvaluatorSpy()
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
        private_evaluation=private,  # type: ignore[arg-type]
    )
    config = RunnerConfig(
        environment=EnvironmentSpec(agents=(), deployments=()),
        worker_urls={},
        planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
        output_root=tmp_path / "runs",
    )

    result = await ControlPlaneBenchmarkRunner(
        config,
        None,
        (),
        worker_clients={},
        logical_runtime=FailingLogicalRuntime(),  # type: ignore[arg-type]
    ).run(bundle, run_id="no-terminal")

    assert not result.execution_completed
    assert result.evaluation is None
    assert not private.built
    trace = (tmp_path / "runs" / "no-terminal" / "trace.jsonl").read_text("utf-8")
    assert '"event_type":"evaluation.result"' not in trace
