from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from infra_joint.control.adaptation import (
    KeepWorkflow,
    KeepWorkflowPolicy,
    LLMInfraAwareWorkflowAdapter,
    PatchWorkflow,
    ScriptedWorkflowAdaptationPolicy,
)
from infra_joint.control.adaptive_executor import AdaptiveWorkflowExecutor
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalModelAction,
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
)
from infra_joint.control.physical import (
    PhysicalExecutionOutcome,
    PhysicalSelection,
)
from infra_joint.control.prior import (
    FrozenPriorWorkflow,
    LLMPriorWorkflowGenerator,
    PriorAttemptStore,
    PriorWorkflowDraft,
    PriorWorkflowStore,
    StaticPriorWorkflowGenerator,
)
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.control.workflow import (
    AddAction,
    AddDependency,
    RemovePendingAction,
    RemovePendingDependency,
    ReplacePendingAction,
    SemanticWorkflowPlan,
    WorkflowDependency,
    WorkflowPatch,
    WorkflowRuntimeState,
)
from infra_joint.control.workflow_cost import SemanticWorkflowCostEvaluator
from infra_joint.control.workflow_profile import WorkflowPhysicalView
from infra_joint.control.workflow_validation import (
    WorkflowValidationError,
    apply_workflow_patch,
    validate_semantic_workflow,
)
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
    LinkSpec,
)
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.evaluation.trace import TraceEvent
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelRequest,
)
from infra_joint.workflow.costing import ExecutionCostProfile
from infra_joint.workflow.trace import WorkflowTraceRecorder


class MemorySink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self.events.append(event)


class CapturingBackend:
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
                output_tokens=3,
                finish_reason="stop",
            ),
        )


class FailingBackend:
    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        del request
        raise RuntimeError("backend unavailable")


class FixedProfileProvider:
    def __init__(self, network_class: str) -> None:
        self.network_class = network_class
        self.contexts: list[tuple[SemanticWorkflowPlan, WorkflowRuntimeState]] = []

    async def build(self, plan, state):
        self.contexts.append((plan, state))
        return WorkflowPhysicalView(
            plan_version=plan.version,
            pending_action_profiles=(),
            predicted_transfer_bytes=10_000 if self.network_class == "constrained" else 0,
            predicted_transfer_latency_ms=(1000 if self.network_class == "constrained" else 1),
            predicted_service_latency_ms=10,
            predicted_queue_latency_ms=0,
            predicted_critical_path_ms=(1010 if self.network_class == "constrained" else 11),
            predicted_total_work_ms=(1010 if self.network_class == "constrained" else 11),
        )


class RecordingGateway:
    def __init__(
        self,
        task: TaskContract,
        binding: str = "worker-secret-a",
        answer: str = "A",
    ) -> None:
        self.validator = SemanticActionValidator(
            task,
            build_operator_catalog(),
            ("bm25_retrieve", "invoke_model"),
        )
        self.binding = binding
        self.answer = answer
        self.batches: list[tuple[str, ...]] = []
        self.outcomes: list[PhysicalExecutionOutcome] = []

    def validate_batch(self, actions):
        self.validator.validate_batch(actions)

    async def profile_overview(self):
        raise AssertionError("formal executor uses workflow-level profiling")

    async def execute_batch(self, actions, *, expose_profile):
        assert not expose_profile
        self.validator.validate_batch(actions)
        self.validator.reserve_batch(actions)
        self.batches.append(tuple(item.action_id for item in actions))
        current = infrastructure_state()
        results: list[PhysicalExecutionOutcome] = []
        for action in actions:
            produced = tuple(
                {
                    "artifact_id": item.artifact_id,
                    "semantic_type": item.semantic_type,
                    "media_type": item.media_type,
                    "size_bytes": 50,
                }
                for item in action.outputs
            )
            output = {"text": self.answer} if isinstance(action, LogicalModelAction) else {}
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
                output=output,
                produced_information=produced,
            )
            outcome = PhysicalExecutionOutcome(
                observation=observation,
                infrastructure_before=current,
                infrastructure_after=current,
                selection=PhysicalSelection(
                    decision={"policy": "auto"},
                    selected_agent_id=self.binding,
                    selected_deployment_id=(
                        f"deployment-on-{self.binding}"
                        if isinstance(action, LogicalModelAction)
                        else None
                    ),
                    rationale="deterministic test binding",
                ),
            )
            results.append(outcome)
        self.validator.complete_batch(
            actions,
            frozenset(item.action_id for item in actions),
        )
        self.outcomes.extend(results)
        return tuple(results)


def task() -> TaskContract:
    return TaskContract(
        task_id="formal-smoke",
        benchmark_id="synthetic",
        objective="Find the answer in the corpus.",
        artifacts=(
            ArtifactSpec(
                artifact_id="raw",
                logical_type="corpus",
                media_type="application/json",
                size_bytes=10_000,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"text": "string"},
                    text_field="text",
                    record_count=10,
                    max_record_bytes=1_000,
                ),
                source_ref="private://never-leak",
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-evaluator",
    )


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="worker-secret-a",
                device="edge",
                capabilities=frozenset({"model", "retrieval"}),
            ),
            AgentSpec(
                agent_id="worker-secret-b",
                device="gpu",
                capabilities=frozenset({"model", "retrieval"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="deployment-secret-a",
                agent_id="worker-secret-a",
                model_id="test",
                context_window=32768,
                reserved_output_tokens=64,
                max_output_bytes=256,
            ),
            DeploymentSpec(
                deployment_id="deployment-secret-b",
                agent_id="worker-secret-b",
                model_id="test",
                context_window=32768,
                reserved_output_tokens=64,
                max_output_bytes=256,
            ),
        ),
    )


def infrastructure_state() -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="worker-secret-a", available=True),
            AgentRuntimeState(agent_id="worker-secret-b", available=True),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="deployment-secret-a", available=True),
            DeploymentRuntimeState(deployment_id="deployment-secret-b", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw",
                locations=("worker-secret-a",),
                media_type="application/json",
                size_bytes=10_000,
            ),
        ),
        links=(),
        observed_at=datetime.now(UTC),
    )


def capabilities():
    return build_static_capability_contract(
        environment(),
        build_operator_catalog(),
        ("bm25_retrieve", "invoke_model"),
    )


def model_action(
    action_id: str = "answer",
    inputs: tuple[str, ...] = ("raw",),
) -> LogicalModelAction:
    return LogicalModelAction(
        action_id=action_id,
        owner_agent_id="manager",
        inputs=inputs,
        prompt="Return only A or B.",
        requirements=ExecutionRequirements(
            modalities=frozenset({"text"}),
            min_context_tokens=512,
            reserved_output_tokens=32,
        ),
    )


def reduction_action(
    action_id: str = "reduce",
    output_id: str = "reduced",
) -> LogicalToolAction:
    return LogicalToolAction(
        action_id=action_id,
        owner_agent_id="manager",
        operator="bm25_retrieve",
        inputs=("raw",),
        outputs=(
            LogicalOutput(
                artifact_id=output_id,
                semantic_type="retrieval_hits",
                media_type="application/json",
            ),
        ),
        arguments={
            "query": "answer evidence",
            "top_k": 2,
            "text_field": "text",
            "output_artifact_id": output_id,
        },
    )


def direct_plan() -> SemanticWorkflowPlan:
    return SemanticWorkflowPlan(
        workflow_id="workflow-formal-smoke",
        version=0,
        actions=(model_action(),),
        terminal_action_id="answer",
    )


def prior_draft(plan: SemanticWorkflowPlan | None = None) -> PriorWorkflowDraft:
    source = plan or direct_plan()
    return PriorWorkflowDraft(
        actions=source.actions,
        dependencies=source.dependencies,
        terminal_action_id=source.terminal_action_id,
    )


def reduction_patch() -> WorkflowPatch:
    return WorkflowPatch(
        patch_id="prefer-near-data-reduction",
        reason="large remote input dominates under constrained networking",
        edits=(
            AddAction(action=reduction_action()),
            ReplacePendingAction(
                action_id="answer",
                replacement=model_action(inputs=("reduced",)),
            ),
            AddDependency(
                dependency=WorkflowDependency(
                    dependency_type="artifact",
                    producer_action_id="reduce",
                    consumer_action_id="answer",
                    information_id="reduced",
                )
            ),
        ),
    )


def test_semantic_plan_forbids_physical_fields_and_has_no_private_task_data() -> None:
    with pytest.raises(ValidationError):
        SemanticWorkflowPlan.model_validate(
            {
                **direct_plan().model_dump(mode="json"),
                "worker_id": "worker-secret-a",
            }
        )
    serialized = direct_plan().model_dump_json()
    assert "private://" not in serialized
    assert "private-evaluator" not in serialized
    assert "worker-secret" not in serialized


def test_static_prior_and_persistence_reuse_same_g0(tmp_path) -> None:
    plan = direct_plan()
    generator = StaticPriorWorkflowGenerator(plan, build_operator_catalog())
    generated = __import__("asyncio").run(generator.generate(task(), capabilities()))
    frozen = FrozenPriorWorkflow.create(
        task=task(),
        generation=generated,
        capabilities=capabilities(),
        public_bundle_sha256="a" * 64,
    )
    store = PriorWorkflowStore(tmp_path / "prior_workflows")
    path = store.save(frozen)
    assert path.name == "formal-smoke.json"
    assert store.save(frozen) == path
    loaded = store.load(task().task_id)
    loaded.verify(
        task(),
        capabilities(),
        "a" * 64,
        generator.provenance(task(), capabilities()),
    )
    assert loaded.plan_sha256 == plan.canonical_sha256()


@pytest.mark.asyncio
async def test_llm_prior_prompt_is_sanitized_and_infrastructure_independent() -> None:
    backend = CapturingBackend(prior_draft().model_dump_json())
    generator = LLMPriorWorkflowGenerator(
        backend,
        build_operator_catalog(),
        model_id="test-prior-model",
    )
    generated = await generator.generate(task(), capabilities())
    assert generated.plan.version == 0
    assert generated.plan.workflow_id.startswith("prior-")
    assert generated.plan.actions == direct_plan().actions
    assert generated.plan.dependencies == direct_plan().dependencies
    assert generated.plan.terminal_action_id == direct_plan().terminal_action_id
    prompt = backend.requests[0].prompt
    assert "private://never-leak" not in prompt
    assert "private-evaluator" not in prompt
    assert "worker-secret" not in prompt
    assert "deployment-secret" not in prompt
    assert "100 Mbps" not in prompt
    payload = json.loads(prompt.splitlines()[-1])
    output_properties = payload["workflow_output_schema"]["properties"]
    assert "version" not in output_properties
    assert "workflow_id" not in output_properties
    assert generated.provenance.generator_version == "llm-prior-v2"


@pytest.mark.asyncio
async def test_llm_prior_system_metadata_is_stable_and_model_cannot_control_it() -> None:
    draft = prior_draft()
    first = LLMPriorWorkflowGenerator(
        CapturingBackend(draft.model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
    )
    second = LLMPriorWorkflowGenerator(
        CapturingBackend(draft.model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
    )
    one = await first.generate(task(), capabilities())
    two = await second.generate(task(), capabilities())
    assert one.plan.workflow_id == two.plan.workflow_id
    assert one.plan.version == two.plan.version == 0
    with pytest.raises(ValidationError):
        PriorWorkflowDraft.model_validate(
            {**draft.model_dump(mode="json"), "version": 99, "workflow_id": "model-owned"}
        )


@pytest.mark.asyncio
async def test_llm_prior_rejected_raw_completion_is_persisted_before_parse(
    tmp_path: Path,
) -> None:
    raw = '{"schema_version":"prior-workflow-draft-v1","not":"a draft"}'
    attempts = PriorAttemptStore(tmp_path / "prior_attempts")
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(raw),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=attempts,
    )
    with pytest.raises(ValueError, match="invalid semantic workflow draft"):
        await generator.generate(
            task(), capabilities(), public_bundle_sha256="a" * 64
        )
    directories = tuple((tmp_path / "prior_attempts" / task().task_id).iterdir())
    assert len(directories) == 1
    attempt = directories[0]
    assert (attempt / "raw_completion.txt").read_text("utf-8") == raw
    assert json.loads((attempt / "parse_result.json").read_text("utf-8"))["status"] == "failed"
    validation = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert validation["attempt_status"] == "parse_failed"
    assert not (tmp_path / "prior_workflows" / f"{task().task_id}.json").exists()


@pytest.mark.asyncio
async def test_llm_prior_backend_failure_has_typed_attempt_evidence(tmp_path: Path) -> None:
    generator = LLMPriorWorkflowGenerator(
        FailingBackend(),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=PriorAttemptStore(tmp_path / "attempts"),
    )
    with pytest.raises(RuntimeError, match="backend unavailable"):
        await generator.generate(
            task(), capabilities(), public_bundle_sha256="1" * 64
        )
    attempt = next((tmp_path / "attempts" / task().task_id).iterdir())
    assert (attempt / "raw_completion.txt").read_text("utf-8") == ""
    parse = json.loads((attempt / "parse_result.json").read_text("utf-8"))
    validation = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert parse["status"] == "skipped"
    assert validation["attempt_status"] == "backend_failed"


@pytest.mark.asyncio
async def test_llm_prior_semantic_failure_persists_draft_and_constructed_g0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = prior_draft(
        direct_plan().model_copy(
            update={"actions": (model_action(inputs=("dangling",)),)}
        )
    )
    secret = "sk-test-secret-that-must-not-appear"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    attempts = PriorAttemptStore(tmp_path / "prior_attempts")
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(invalid.model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=attempts,
    )
    with pytest.raises(WorkflowValidationError, match="dangling"):
        await generator.generate(
            task(), capabilities(), public_bundle_sha256="b" * 64
        )
    attempt = next((tmp_path / "prior_attempts" / task().task_id).iterdir())
    assert (attempt / "draft.json").exists()
    constructed = json.loads((attempt / "constructed-g0.json").read_text("utf-8"))
    assert constructed["version"] == 0
    result = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert result["attempt_status"] == "semantic_validation_failed"
    assert secret not in "".join(
        path.read_text("utf-8") for path in attempt.iterdir() if path.is_file()
    )


@pytest.mark.asyncio
async def test_llm_prior_cyclic_draft_remains_rejected(tmp_path: Path) -> None:
    plan = SemanticWorkflowPlan(
        workflow_id="discarded",
        version=0,
        actions=(reduction_action(), model_action(inputs=("reduced",))),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="reduce",
                consumer_action_id="answer",
                information_id="reduced",
            ),
            WorkflowDependency(
                dependency_type="control",
                producer_action_id="answer",
                consumer_action_id="reduce",
            ),
        ),
        terminal_action_id="answer",
    )
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(prior_draft(plan).model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=PriorAttemptStore(tmp_path / "attempts"),
    )
    with pytest.raises(WorkflowValidationError, match="acyclic"):
        await generator.generate(
            task(), capabilities(), public_bundle_sha256="c" * 64
        )


@pytest.mark.asyncio
async def test_llm_prior_static_context_failure_remains_rejected(tmp_path: Path) -> None:
    constrained_environment = environment().model_copy(
        update={
            "deployments": tuple(
                item.model_copy(update={"context_window": 8192})
                for item in environment().deployments
            )
        }
    )
    constrained_capabilities = build_static_capability_contract(
        constrained_environment,
        build_operator_catalog(),
        ("bm25_retrieve", "invoke_model"),
    )
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(prior_draft().model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=PriorAttemptStore(tmp_path / "attempts"),
    )
    with pytest.raises(WorkflowValidationError, match="context"):
        await generator.generate(
            task(), constrained_capabilities, public_bundle_sha256="d" * 64
        )
    attempt = next((tmp_path / "attempts" / task().task_id).iterdir())
    validation = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert validation["attempt_status"] == "static_feasibility_failed"


@pytest.mark.asyncio
async def test_successful_llm_prior_evidence_can_be_marked_frozen(tmp_path: Path) -> None:
    attempts = PriorAttemptStore(tmp_path / "attempts")
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(prior_draft().model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
        attempt_store=attempts,
    )
    generation = await generator.generate(
        task(), capabilities(), public_bundle_sha256="e" * 64
    )
    assert generation.attempt is not None
    frozen_path = tmp_path / "prior_workflows" / "formal-smoke.json"
    PriorAttemptStore.persist_frozen_success(
        generation.attempt,
        generation.plan,
        frozen_path,
    )
    attempt = Path(generation.attempt.directory)
    assert (attempt / "raw_completion.txt").read_text("utf-8") == prior_draft().model_dump_json()
    assert (attempt / "draft.json").exists()
    assert (attempt / "constructed-g0.json").exists()
    validation = json.loads((attempt / "validation_result.json").read_text("utf-8"))
    assert validation["attempt_status"] == "frozen_success"
    assert validation["plan_sha256"] == generation.plan.canonical_sha256()


def test_static_model_capability_misuse_is_rejected() -> None:
    impossible = direct_plan().model_copy(
        update={
            "actions": (
                model_action().model_copy(
                    update={
                        "requirements": ExecutionRequirements(
                            modalities=frozenset({"text", "image"}),
                            min_context_tokens=512,
                            reserved_output_tokens=32,
                        )
                    }
                ),
            )
        }
    )
    with pytest.raises(WorkflowValidationError, match="statically infeasible"):
        validate_semantic_workflow(
            impossible,
            task(),
            capabilities(),
            build_operator_catalog(),
        )


@pytest.mark.asyncio
async def test_keep_policy_leaves_workflow_unchanged() -> None:
    profile = WorkflowPhysicalView(
        plan_version=0,
        pending_action_profiles=(),
        unknown_reasons=("profiles unavailable",),
    )
    provider = FixedProfileProvider("fast")
    gateway = RecordingGateway(task())
    result = await AdaptiveWorkflowExecutor(
        gateway,
        provider,
        KeepWorkflowPolicy(),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("keep", MemorySink()))
    assert profile.predicted_critical_path_ms is None
    assert result.final_plan == direct_plan()
    assert result.patch_records[0].decision == "keep"


def test_semantic_workflow_cost_uses_feasible_bindings_and_preserves_unknowns() -> None:
    remote_environment = EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="source", device="edge"),
            AgentSpec(
                agent_id="compute",
                device="gpu",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="runtime-only-deployment",
                agent_id="compute",
                model_id="test",
                context_window=32768,
                reserved_output_tokens=64,
            ),
        ),
        links=(
            LinkSpec(
                source_agent_id="source",
                target_agent_id="compute",
                bandwidth_mbps=3,
                rtt_ms=20,
            ),
        ),
    )
    current = InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="source", available=True),
            AgentRuntimeState(agent_id="compute", available=True, queue_depth=1),
        ),
        deployments=(
            DeploymentRuntimeState(
                deployment_id="runtime-only-deployment",
                available=True,
            ),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw",
                locations=("source",),
                media_type="application/json",
                size_bytes=10_000,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="source",
                target_agent_id="compute",
                available=True,
                bandwidth_mbps=3,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )
    registry = build_operator_catalog()
    evaluator = SemanticWorkflowCostEvaluator(
        remote_environment,
        registry,
        (
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id="compute",
                deployment_id="runtime-only-deployment",
                input_units=10_000,
                unit_kind="bytes",
                service_latency_ms=100,
                source="deterministic-test",
            ),
        ),
        task(),
        build_static_capability_contract(
            remote_environment,
            registry,
            ("invoke_model",),
        ),
    )
    view = evaluator.evaluate(
        direct_plan(),
        WorkflowRuntimeState.initialize(direct_plan()),
        current,
    )
    assert view.predicted_transfer_bytes == 10_000
    assert view.predicted_transfer_latency_ms is not None
    assert view.predicted_service_latency_ms == 100
    assert view.predicted_queue_latency_ms == 100
    assert view.predicted_critical_path_ms is not None
    serialized = view.model_dump_json()
    assert "source" not in serialized
    assert "compute" not in serialized
    assert "runtime-only-deployment" not in serialized


def test_valid_patch_changes_only_pending_suffix() -> None:
    proposed = apply_workflow_patch(
        direct_plan(),
        WorkflowRuntimeState.initialize(direct_plan()),
        reduction_patch(),
        task(),
        capabilities(),
        build_operator_catalog(),
    )
    assert proposed.version == 1
    assert tuple(item.action_id for item in proposed.actions) == ("answer", "reduce")
    assert proposed.action_map()["answer"].inputs == ("reduced",)


def test_patch_cannot_modify_completed_or_running_action() -> None:
    plan = direct_plan()
    patch = WorkflowPatch(
        patch_id="illegal",
        reason="attempt immutable rewrite",
        edits=(ReplacePendingAction(action_id="answer", replacement=model_action(inputs=())),),
    )
    state = WorkflowRuntimeState(running_action_ids=("answer",))
    with pytest.raises(WorkflowValidationError, match="only pending"):
        apply_workflow_patch(
            plan,
            state,
            patch,
            task(),
            capabilities(),
            build_operator_catalog(),
        )


def test_patch_cannot_modify_completed_action() -> None:
    plan = direct_plan()
    state = WorkflowRuntimeState(completed_action_ids=("answer",))
    patch = WorkflowPatch(
        patch_id="illegal-completed",
        reason="attempt completed rewrite",
        edits=(ReplacePendingAction(action_id="answer", replacement=model_action(inputs=())),),
    )
    with pytest.raises(WorkflowValidationError, match="only pending"):
        apply_workflow_patch(
            plan,
            state,
            patch,
            task(),
            capabilities(),
            build_operator_catalog(),
        )


def test_remove_pending_action_requires_edges_removed_first() -> None:
    reduce = reduction_action()
    answer = model_action(inputs=("reduced",))
    plan = SemanticWorkflowPlan(
        workflow_id="remove-test",
        version=0,
        actions=(reduce, answer),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="reduce",
                consumer_action_id="answer",
                information_id="reduced",
            ),
        ),
        terminal_action_id="answer",
    )
    patch = WorkflowPatch(
        patch_id="remove",
        reason="invalid removal order",
        edits=(RemovePendingAction(action_id="reduce"),),
    )
    with pytest.raises(WorkflowValidationError, match="remove dependencies"):
        apply_workflow_patch(
            plan,
            WorkflowRuntimeState.initialize(plan),
            patch,
            task(),
            capabilities(),
            build_operator_catalog(),
        )


def test_cycle_dangling_input_and_invalid_terminal_fail_closed() -> None:
    registry = build_operator_catalog()
    reduce_a = reduction_action("a", "a-out").model_copy(update={"inputs": ("b-out",)})
    reduce_b = reduction_action("b", "b-out").model_copy(update={"inputs": ("a-out",)})
    cyclic = SemanticWorkflowPlan(
        workflow_id="cycle",
        version=0,
        actions=(reduce_a, reduce_b, model_action(inputs=("a-out",))),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="b",
                consumer_action_id="a",
                information_id="b-out",
            ),
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="a",
                consumer_action_id="b",
                information_id="a-out",
            ),
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="a",
                consumer_action_id="answer",
                information_id="a-out",
            ),
        ),
        terminal_action_id="answer",
    )
    with pytest.raises(WorkflowValidationError, match="acyclic"):
        validate_semantic_workflow(cyclic, task(), capabilities(), registry)
    dangling = direct_plan().model_copy(update={"actions": (model_action(inputs=("missing",)),)})
    with pytest.raises(WorkflowValidationError, match="dangling"):
        validate_semantic_workflow(dangling, task(), capabilities(), registry)
    invalid_terminal = SemanticWorkflowPlan(
        workflow_id="bad-terminal",
        version=0,
        actions=(reduction_action(),),
        terminal_action_id="reduce",
    )
    with pytest.raises(WorkflowValidationError, match="terminal action must"):
        validate_semantic_workflow(invalid_terminal, task(), capabilities(), registry)
    unreachable = SemanticWorkflowPlan(
        workflow_id="unreachable",
        version=0,
        actions=(reduction_action(), model_action()),
        terminal_action_id="answer",
    )
    with pytest.raises(WorkflowValidationError, match="reach the terminal"):
        validate_semantic_workflow(unreachable, task(), capabilities(), registry)


def test_remove_pending_branch_and_add_remove_dependency() -> None:
    branch_zero = reduction_action("branch-0", "hits-0")
    branch_one = reduction_action("branch-1", "hits-1")
    answer = model_action(inputs=("hits-0", "hits-1"))
    edge_zero = WorkflowDependency(
        dependency_type="artifact",
        producer_action_id="branch-0",
        consumer_action_id="answer",
        information_id="hits-0",
    )
    edge_one = WorkflowDependency(
        dependency_type="artifact",
        producer_action_id="branch-1",
        consumer_action_id="answer",
        information_id="hits-1",
    )
    plan = SemanticWorkflowPlan(
        workflow_id="remove-branch",
        version=0,
        actions=(branch_zero, branch_one, answer),
        dependencies=(edge_zero, edge_one),
        terminal_action_id="answer",
    )
    removed = apply_workflow_patch(
        plan,
        WorkflowRuntimeState.initialize(plan),
        WorkflowPatch(
            patch_id="remove-one-branch",
            reason="one pending branch is unnecessary",
            edits=(
                RemovePendingDependency(dependency=edge_one),
                ReplacePendingAction(
                    action_id="answer",
                    replacement=model_action(inputs=("hits-0",)),
                ),
                RemovePendingAction(action_id="branch-1"),
            ),
        ),
        task(),
        capabilities(),
        build_operator_catalog(),
    )
    assert set(removed.action_map()) == {"branch-0", "answer"}

    control = WorkflowDependency(
        dependency_type="control",
        producer_action_id="branch-0",
        consumer_action_id="answer",
    )
    added = apply_workflow_patch(
        removed,
        WorkflowRuntimeState.initialize(removed),
        WorkflowPatch(
            patch_id="add-control",
            reason="test finite dependency edit",
            edits=(AddDependency(dependency=control),),
        ),
        task(),
        capabilities(),
        build_operator_catalog(),
    )
    restored = apply_workflow_patch(
        added,
        WorkflowRuntimeState.initialize(added),
        WorkflowPatch(
            patch_id="remove-control",
            reason="test inverse dependency edit",
            edits=(RemovePendingDependency(dependency=control),),
        ),
        task(),
        capabilities(),
        build_operator_catalog(),
    )
    assert control not in restored.dependencies


@pytest.mark.asyncio
async def test_slow_network_inserts_reduction_but_fast_network_keeps_g0() -> None:
    slow_gateway = RecordingGateway(task())
    slow_sink = MemorySink()
    slow = await AdaptiveWorkflowExecutor(
        slow_gateway,
        FixedProfileProvider("constrained"),
        ScriptedWorkflowAdaptationPolicy(
            (PatchWorkflow(reason="reduce transfer cost", patch=reduction_patch()),)
        ),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("slow", slow_sink))
    assert slow.succeeded
    assert slow_gateway.batches == [("reduce",), ("answer",)]
    assert slow.final_plan.version == 1

    fast_gateway = RecordingGateway(task())
    fast = await AdaptiveWorkflowExecutor(
        fast_gateway,
        FixedProfileProvider("fast"),
        ScriptedWorkflowAdaptationPolicy((KeepWorkflow(reason="movement is cheap"),)),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("fast", MemorySink()))
    assert fast.succeeded
    assert fast_gateway.batches == [("answer",)]
    assert fast.final_plan.canonical_sha256() == direct_plan().canonical_sha256()


def parallel_plan() -> SemanticWorkflowPlan:
    branches = tuple(
        model_action(f"branch-{index}").model_copy(
            update={
                "outputs": (
                    LogicalOutput(
                        artifact_id=f"hits-{index}",
                        semantic_type="analysis",
                        media_type="text/plain",
                    ),
                )
            }
        )
        for index in range(3)
    )
    answer = model_action(inputs=tuple(f"hits-{index}" for index in range(3)))
    edges = tuple(
        WorkflowDependency(
            dependency_type="artifact",
            producer_action_id=f"branch-{index}",
            consumer_action_id="answer",
            information_id=f"hits-{index}",
        )
        for index in range(3)
    )
    return SemanticWorkflowPlan(
        workflow_id="parallel-smoke",
        version=0,
        actions=branches + (answer,),
        dependencies=edges,
        terminal_action_id="answer",
    )


@pytest.mark.asyncio
async def test_dependency_edits_change_parallel_frontier_without_hidden_serialization() -> None:
    plan = parallel_plan()
    validate_semantic_workflow(plan, task(), capabilities(), build_operator_catalog())
    parallel_gateway = RecordingGateway(task())
    parallel = await AdaptiveWorkflowExecutor(
        parallel_gateway,
        FixedProfileProvider("fast"),
        ScriptedWorkflowAdaptationPolicy((KeepWorkflow(reason="parallel capacity"),)),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), plan, WorkflowTraceRecorder("parallel", MemorySink()))
    assert parallel.succeeded
    assert parallel_gateway.batches[0] == ("branch-0", "branch-1", "branch-2")

    patch = WorkflowPatch(
        patch_id="serialize-contention",
        reason="abstract queue contention makes serialized branches cheaper",
        edits=(
            AddDependency(
                dependency=WorkflowDependency(
                    dependency_type="control",
                    producer_action_id="branch-0",
                    consumer_action_id="branch-1",
                )
            ),
            AddDependency(
                dependency=WorkflowDependency(
                    dependency_type="control",
                    producer_action_id="branch-1",
                    consumer_action_id="branch-2",
                )
            ),
        ),
    )
    serial_gateway = RecordingGateway(task())
    serial = await AdaptiveWorkflowExecutor(
        serial_gateway,
        FixedProfileProvider("constrained"),
        ScriptedWorkflowAdaptationPolicy((PatchWorkflow(reason="avoid contention", patch=patch),)),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), plan, WorkflowTraceRecorder("serial", MemorySink()))
    assert serial.succeeded
    assert serial_gateway.batches == [
        ("branch-0",),
        ("branch-1",),
        ("branch-2",),
        ("answer",),
    ]


@pytest.mark.asyncio
async def test_same_g0_can_receive_different_physical_bindings() -> None:
    plan = direct_plan()
    bindings: list[str] = []
    for binding in ("worker-secret-a", "worker-secret-b"):
        gateway = RecordingGateway(task(), binding)
        result = await AdaptiveWorkflowExecutor(
            gateway,
            FixedProfileProvider("fast"),
            ScriptedWorkflowAdaptationPolicy((KeepWorkflow(reason="same semantic plan"),)),
            build_operator_catalog(),
            capabilities(),
        ).execute(task(), plan, WorkflowTraceRecorder(binding, MemorySink()))
        assert result.final_plan.canonical_sha256() == plan.canonical_sha256()
        assert gateway.outcomes[0].selection is not None
        bindings.append(gateway.outcomes[0].selection.selected_agent_id)
    assert bindings == ["worker-secret-a", "worker-secret-b"]


@pytest.mark.asyncio
async def test_trace_reconstructs_versions_and_logical_events_do_not_leak() -> None:
    sink = MemorySink()
    result = await AdaptiveWorkflowExecutor(
        RecordingGateway(task()),
        FixedProfileProvider("constrained"),
        ScriptedWorkflowAdaptationPolicy(
            (PatchWorkflow(reason="reduce transfer cost", patch=reduction_patch()),)
        ),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("trace", sink))
    versions = [
        event.payload for event in sink.events if event.event_type == "workflow.plan.version"
    ]
    patches = [event for event in sink.events if event.event_type == "workflow.plan.patch"]
    snapshots = [
        event for event in sink.events if event.event_type == "workflow.execution.snapshot"
    ]
    assert [item["version"] for item in versions] == [0, 1]
    assert versions[-1]["canonical_sha256"] == result.final_plan.canonical_sha256()
    assert patches and snapshots
    logical_trace = json.dumps(versions + [item.payload for item in patches], sort_keys=True)
    assert "worker-secret" not in logical_trace
    assert "deployment-secret" not in logical_trace
    assert "private://never-leak" not in logical_trace
    assert "private-evaluator" not in logical_trace


@pytest.mark.asyncio
async def test_llm_adaptation_telemetry_is_complete() -> None:
    backend = CapturingBackend(
        '{"decision_type":"keep","reason":"current workflow is efficient"}'
    )
    sink = MemorySink()
    result = await AdaptiveWorkflowExecutor(
        RecordingGateway(task()),
        FixedProfileProvider("fast"),
        LLMInfraAwareWorkflowAdapter(backend),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("adapt-telemetry", sink))
    telemetry = result.adaptation_telemetry[0]
    assert telemetry.decision_type == "keep"
    assert telemetry.patch_edit_count == 0
    assert telemetry.adaptation_latency_ms >= 0
    assert telemetry.model_service_latency_ms == 1
    assert telemetry.input_tokens == 10
    assert telemetry.output_tokens == 3
    assert any(item.event_type == "workflow.adaptation" for item in sink.events)


@pytest.mark.asyncio
async def test_invalid_terminal_choice_and_json_are_recorded_not_execution_failures() -> None:
    invalid_choice = await AdaptiveWorkflowExecutor(
        RecordingGateway(task(), answer="C"),
        FixedProfileProvider("fast"),
        KeepWorkflowPolicy(),
        build_operator_catalog(),
        capabilities(),
    ).execute(task(), direct_plan(), WorkflowTraceRecorder("bad-choice", MemorySink()))
    assert invalid_choice.succeeded
    assert invalid_choice.terminal_output_contract is not None
    assert not invalid_choice.terminal_output_contract.valid
    assert invalid_choice.terminal_output_contract.failure_code == "invalid_choice_output"

    json_task = task().model_copy(
        update={
            "output_contract": OutputContract(
                format=OutputFormat.JSON,
                schema={
                    "type": "object",
                    "properties": {"answer": {"type": "integer"}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
            )
        }
    )
    invalid_json = await AdaptiveWorkflowExecutor(
        RecordingGateway(json_task, answer='{"answer":"not-an-integer"}'),
        FixedProfileProvider("fast"),
        KeepWorkflowPolicy(),
        build_operator_catalog(),
        capabilities(),
    ).execute(
        json_task,
        direct_plan(),
        WorkflowTraceRecorder("bad-json", MemorySink()),
    )
    assert invalid_json.succeeded
    assert invalid_json.terminal_output_contract is not None
    assert invalid_json.terminal_output_contract.failure_code == "output_schema_mismatch"


def test_frozen_prior_model_and_prompt_mismatch_fail_closed() -> None:
    generator = StaticPriorWorkflowGenerator(direct_plan(), build_operator_catalog())
    generation = __import__("asyncio").run(generator.generate(task(), capabilities()))
    frozen = FrozenPriorWorkflow.create(
        task=task(),
        generation=generation,
        capabilities=capabilities(),
        public_bundle_sha256="b" * 64,
    )
    expected = generator.provenance(task(), capabilities())
    with pytest.raises(ValueError, match="model mismatch"):
        frozen.verify(
            task(),
            capabilities(),
            "b" * 64,
            expected.model_copy(update={"model_id": "different-model"}),
        )
    with pytest.raises(ValueError, match="prompt mismatch"):
        frozen.verify(
            task(),
            capabilities(),
            "b" * 64,
            expected.model_copy(update={"prompt_sha256": "c" * 64}),
        )


@pytest.mark.asyncio
async def test_llm_prior_v1_frozen_provenance_is_not_reused_by_v2() -> None:
    generator = LLMPriorWorkflowGenerator(
        CapturingBackend(prior_draft().model_dump_json()),
        build_operator_catalog(),
        model_id="test-prior-model",
    )
    generation = await generator.generate(task(), capabilities())
    frozen = FrozenPriorWorkflow.create(
        task=task(),
        generation=generation,
        capabilities=capabilities(),
        public_bundle_sha256="f" * 64,
    )
    expected = generator.provenance(task(), capabilities())
    with pytest.raises(ValueError, match="generator version mismatch"):
        frozen.verify(
            task(),
            capabilities(),
            "f" * 64,
            expected.model_copy(update={"generator_version": "llm-prior-v1"}),
        )
