import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import (
    LogicalModelAction,
    LogicalObservation,
    ProducedInformation,
    ProfileVisibility,
    StaticCapabilityContract,
    StaticModelCapabilityClass,
    WorkflowGraphSnapshot,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError
from infra_joint.control.native_agents import (
    OpenAIAgentsNativeRuntime,
    _native_tool_schema,
)
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.control.verification import (
    OpenAIAgentsBlindVerifier,
    VerificationContext,
    VerificationResponse,
    VerificationResult,
    VerifierBudgetView,
)
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.evaluation.trace import TraceEvent
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder


class MemorySink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, event: TraceEvent) -> None:
        self.events.append(event)


class FakeFunctionTool:
    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs["name"]
        self.description = kwargs["description"]
        self.params_json_schema = kwargs["params_json_schema"]
        self.on_invoke_tool = kwargs["on_invoke_tool"]


class FakeModelSettings:
    def __init__(
        self,
        *,
        parallel_tool_calls: bool,
        temperature: float | None = None,
        tool_choice: str | None = None,
    ) -> None:
        self.parallel_tool_calls = parallel_tool_calls
        self.temperature = temperature
        self.tool_choice = tool_choice


class FakeToolsToFinalOutputResult:
    def __init__(self, *, is_final_output: bool, final_output: object) -> None:
        self.is_final_output = is_final_output
        self.final_output = final_output


class FakeRunHooks:
    pass


class FakeAgent:
    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs["name"]
        self.instructions = kwargs["instructions"]
        self.tools = kwargs["tools"]
        self.model_settings = kwargs.get("model_settings")
        self.tool_use_behavior = kwargs.get("tool_use_behavior", "run_llm_again")

    def as_tool(self, **kwargs: Any) -> FakeFunctionTool:
        hooks = kwargs["hooks"]
        max_turns = kwargs["max_turns"]

        async def invoke(context: object, input_json: str) -> str:
            request = json.loads(input_json)
            nested_context = SimpleNamespace(
                context=context.context,
                tool_input=request,
            )
            result = await FakeRunner.run(
                self,
                input=input_json,
                context=nested_context,
                max_turns=max_turns,
                hooks=hooks,
            )
            return str(result.final_output)

        return FakeFunctionTool(
            name=kwargs["tool_name"],
            description=kwargs["tool_description"],
            params_json_schema={},
            on_invoke_tool=invoke,
        )


class FakeRunner:
    behavior: Any = None

    @staticmethod
    async def run(
        agent: FakeAgent,
        input: str,
        *,
        context: object,
        max_turns: int,
        hooks: object,
    ) -> object:
        assert max_turns > 0
        assert FakeRunner.behavior is not None
        output = await FakeRunner.behavior(agent, input, context, hooks)
        return SimpleNamespace(final_output=output)


FAKE_SDK = SimpleNamespace(
    Agent=FakeAgent,
    FunctionTool=FakeFunctionTool,
    ModelSettings=FakeModelSettings,
    RunHooks=FakeRunHooks,
    Runner=FakeRunner,
    ToolsToFinalOutputResult=FakeToolsToFinalOutputResult,
)


class FakeVerifier:
    def __init__(self, results: tuple[VerificationResult, ...]) -> None:
        self._results = list(results)
        self.contexts: list[VerificationContext] = []

    async def verify(self, context: VerificationContext) -> VerificationResponse:
        self.contexts.append(context)
        if not self._results:
            raise AssertionError("fake verifier has no remaining result")
        return VerificationResponse(
            result=self._results.pop(0),
            input_tokens=11,
            output_tokens=7,
        )


class FakePhysicalService:
    def __init__(
        self,
        *,
        fail_read_once: bool = False,
        fail_model_once: bool = False,
        bm25_barrier: int = 0,
    ) -> None:
        self.fail_read_once = fail_read_once
        self.fail_model_once = fail_model_once
        self.bm25_barrier = bm25_barrier
        self.actions: list[object] = []
        self.active_bm25 = 0
        self.peak_bm25 = 0
        self.entered_bm25 = 0
        self.release = asyncio.Event()

    async def execute(self, action: object, *, expose_profile: bool) -> PhysicalExecutionOutcome:
        assert not expose_profile
        self.actions.append(action)
        operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
        if operator == "bm25_retrieve" and self.bm25_barrier:
            self.entered_bm25 += 1
            self.active_bm25 += 1
            self.peak_bm25 = max(self.peak_bm25, self.active_bm25)
            if self.entered_bm25 == self.bm25_barrier:
                self.release.set()
            await asyncio.wait_for(self.release.wait(), timeout=1)
            await asyncio.sleep(0)
            self.active_bm25 -= 1
        if operator == "read_artifact" and self.fail_read_once:
            self.fail_read_once = False
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=False,
                failure_code="artifact_too_large",
                failure_message="artifact exceeds the bounded read limit",
            )
        elif operator == "invoke_model" and self.fail_model_once:
            self.fail_model_once = False
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=False,
                failure_code="context_limit_exceeded",
                failure_message="model request exceeds the static context envelope",
            )
        else:
            produced = tuple(
                ProducedInformation(
                    artifact_id=item.artifact_id,
                    semantic_type=item.semantic_type,
                    media_type=item.media_type,
                    size_bytes=12,
                )
                for item in action.outputs
            )
            if isinstance(action, LogicalModelAction):
                text = "evidence" if action.outputs else "A"
                output = {"text": text}
            else:
                output = {"text": "small artifact"} if operator == "read_artifact" else {}
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
                output=output,
                produced_information=produced,
            )
        current = InfrastructureState(
            agents=(),
            deployments=(),
            artifacts=(),
            links=(),
            observed_at=datetime.now(UTC),
        )
        return PhysicalExecutionOutcome(
            observation=observation,
            infrastructure_before=current,
            infrastructure_after=current,
        )


class CancelOncePhysicalService(FakePhysicalService):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self._block_once = True

    async def execute(self, action: object, *, expose_profile: bool) -> PhysicalExecutionOutcome:
        if self._block_once:
            self._block_once = False
            self.started.set()
            await asyncio.Event().wait()
        return await super().execute(action, expose_profile=expose_profile)


def benchmark_task(*, shards: int = 1) -> TaskContract:
    return TaskContract(
        task_id="native-smoke",
        benchmark_id="synthetic",
        objective="Choose A from the available evidence.",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=f"source-{index}",
                logical_type="records",
                media_type="application/json",
                size_bytes=10,
                source_ref=f"private://source-{index}",
            )
            for index in range(shards)
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-evaluator",
    )


def video_task() -> TaskContract:
    return TaskContract(
        task_id="native-video-smoke",
        benchmark_id="synthetic",
        objective="Choose A from the video.",
        artifacts=(
            ArtifactSpec(
                artifact_id="video",
                logical_type="complete_video",
                media_type="video/mp4",
                size_bytes=10,
                content_schema=ArtifactContentSchema(
                    kind="video",
                    duration_seconds=150,
                ),
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-evaluator",
    )


def runtime_and_gateway(
    task: TaskContract,
    physical: FakePhysicalService,
    operations: tuple[str, ...],
    *,
    verifier: FakeVerifier | None = None,
) -> tuple[OpenAIAgentsNativeRuntime, RuntimeActionGateway]:
    registry = build_operator_catalog()
    runtime = OpenAIAgentsNativeRuntime(
        name="manager",
        instructions="Solve faithfully.",
        model="planner-model",
        registry=registry,
        available_operations=operations,
        sdk_module=FAKE_SDK,
        blind_verifier=verifier,
    )
    gateway = RuntimeActionGateway(
        SemanticActionValidator(task, registry, operations),
        physical,  # type: ignore[arg-type]
    )
    return runtime, gateway


def test_native_schema_rebases_nested_operator_definitions() -> None:
    spec = build_operator_catalog().binding("aggregate_records").spec
    schema = _native_tool_schema(spec)
    reference = schema["properties"]["arguments"]["properties"]["aggregations"][
        "items"
    ]["$ref"]
    assert reference == "#/properties/arguments/$defs/Aggregation"


def tool(agent: FakeAgent, name: str) -> FakeFunctionTool:
    return next(item for item in agent.tools if item.name == name)


def tool_context(
    agent: FakeAgent,
    run_context: object,
    call_id: str,
) -> object:
    return SimpleNamespace(
        agent=agent,
        tool_call_id=call_id,
        tool_input=getattr(run_context, "tool_input", None),
        context=getattr(run_context, "context", run_context),
        run_config=None,
    )


async def reasoning_start(hooks: object, context: object, agent: FakeAgent) -> None:
    await hooks.on_llm_start(context, agent, None, [])


async def reasoning_end(hooks: object, context: object, agent: FakeAgent) -> None:
    await hooks.on_llm_end(context, agent, SimpleNamespace())


async def complete_tool_batch(
    agent: FakeAgent,
    results: tuple[tuple[FakeFunctionTool, str], ...],
) -> tuple[str, ...]:
    behavior = agent.tool_use_behavior
    if not callable(behavior):
        return tuple(output for _, output in results)
    wrapped: list[object] = []
    for function_tool, output in results:
        run_item = SimpleNamespace(output=output, raw_item={"output": output})
        wrapped.append(
            SimpleNamespace(
                tool=function_tool,
                output=output,
                run_item=run_item,
            )
        )
    decision = await behavior(SimpleNamespace(), wrapped)
    assert not decision.is_final_output
    return tuple(str(item.output) for item in wrapped)


@pytest.mark.asyncio
async def test_native_function_tools_cross_gateway_and_recover_from_typed_failure() -> None:
    task = benchmark_task()
    physical = FakePhysicalService(fail_read_once=True)
    runtime, gateway = runtime_and_gateway(
        task, physical, ("read_artifact", "invoke_model")
    )

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        failure = await tool(agent, "read_artifact").on_invoke_tool(
            tool_context(agent, context, "read-1"),
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        assert json.loads(failure)["failure_code"] == "artifact_too_large"
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        answer = await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer-1"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A or B."},
                }
            ),
        )
        assert json.loads(answer)["output"]["text"] == "A"
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert result.terminal_action_id == "manager:answer-1"
    assert [item.succeeded for item in result.observations] == [False, True]
    assert [
        "invoke_model" if isinstance(item, LogicalModelAction) else item.operator
        for item in physical.actions
    ] == ["read_artifact", "invoke_model"]


@pytest.mark.asyncio
async def test_malformed_native_tool_arguments_return_typed_failure() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("read_artifact", "invoke_model"))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        failure = await tool(agent, "read_artifact").on_invoke_tool(
            tool_context(agent, context, "malformed"),
            '{"inputs":["source-0"]}{"arguments":{}}',
        )
        assert json.loads(failure)["failure_code"] == "semantic_validation_failed"
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert result.observations[0].action_id == "manager:malformed"
    assert not result.observations[0].succeeded


@pytest.mark.asyncio
async def test_cancelled_native_tool_call_closes_running_graph_node() -> None:
    task = benchmark_task()
    physical = CancelOncePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("read_artifact", "invoke_model"))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        pending = asyncio.create_task(
            tool(agent, "read_artifact").on_invoke_tool(
                tool_context(agent, context, "cancelled"),
                json.dumps({"inputs": ["source-0"], "arguments": {}}),
            )
        )
        await physical.started.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    cancelled = next(
        item for item in result.observations if item.action_id == "manager:cancelled"
    )
    assert cancelled.failure_code == "action_cancelled"
    statuses = {
        item.action_id: item.status for item in result.graph_snapshots[-1].nodes
    }
    assert statuses == {"manager:cancelled": "failed", "manager:answer": "succeeded"}


@pytest.mark.asyncio
async def test_sample_frames_contract_failure_is_typed_and_recoverable() -> None:
    task = video_task()
    physical = FakePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("sample_frames", "invoke_model"))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        invalid = await tool(agent, "sample_frames").on_invoke_tool(
            tool_context(agent, context, "too-sparse"),
            json.dumps(
                {
                    "inputs": ["video"],
                    "arguments": {
                        "every_seconds": 100,
                        "max_frames": 2,
                        "output_prefix": "bad",
                    },
                }
            ),
        )
        assert json.loads(invalid)["failure_code"] == "semantic_validation_failed"
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        corrected = await tool(agent, "sample_frames").on_invoke_tool(
            tool_context(agent, context, "corrected"),
            json.dumps(
                {
                    "inputs": ["video"],
                    "arguments": {
                        "every_seconds": 5,
                        "output_prefix": "good",
                    },
                }
            ),
        )
        assert json.loads(corrected)["succeeded"]
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["video"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    sample = next(
        item
        for item in physical.actions
        if not isinstance(item, LogicalModelAction) and item.operator == "sample_frames"
    )
    assert len(sample.outputs) == 16


@pytest.mark.asyncio
async def test_two_native_bm25_tools_run_in_parallel() -> None:
    task = benchmark_task(shards=2)
    physical = FakePhysicalService(bm25_barrier=2)
    runtime, gateway = runtime_and_gateway(task, physical, ("bm25_retrieve", "invoke_model"))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)

        async def retrieve(index: int) -> str:
            return await tool(agent, "bm25_retrieve").on_invoke_tool(
                tool_context(agent, context, f"bm25-{index}"),
                json.dumps(
                    {
                        "inputs": [f"source-{index}"],
                        "arguments": {
                            "query": "evidence",
                            "top_k": 2,
                            "text_field": "text",
                            "output_artifact_id": f"hits-{index}",
                        },
                    }
                ),
            )

        results = await asyncio.gather(retrieve(0), retrieve(1))
        assert all(json.loads(item)["succeeded"] for item in results)
        hits = [
            json.loads(item)["produced_information"][0]["artifact_id"]
            for item in results
        ]
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": hits,
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert physical.peak_bm25 == 2
    assert {item.action_id for item in result.observations[:2]} == {
        "manager:bm25-0",
        "manager:bm25-1",
    }


@pytest.mark.asyncio
async def test_dependent_native_call_waits_for_producer_result() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("bm25_retrieve", "invoke_model"))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        producer = tool(agent, "bm25_retrieve").on_invoke_tool(
            tool_context(agent, context, "producer"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {
                        "query": "evidence",
                        "top_k": 2,
                        "text_field": "text",
                        "output_artifact_id": "hits",
                    },
                }
            ),
        )
        premature = tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "premature"),
            json.dumps(
                {
                    "inputs": ["hits"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        producer_result, premature_result = await asyncio.gather(producer, premature)
        assert json.loads(producer_result)["succeeded"]
        assert json.loads(premature_result)["failure_code"] == "artifact_not_materialized"
        hits = json.loads(producer_result)["produced_information"][0]["artifact_id"]
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        final = await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "after-observation"),
            json.dumps(
                {
                    "inputs": [hits],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        assert json.loads(final)["succeeded"]
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    model_actions = [item for item in physical.actions if isinstance(item, LogicalModelAction)]
    assert len(model_actions) == 1
    assert model_actions[0].action_id == "manager:after-observation"
    assert any(
        item.action_id == "manager:premature" and not item.succeeded
        for item in result.observations
    )


@pytest.mark.asyncio
async def test_manager_specialist_tool_handoff_then_manager_continues() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("invoke_model",))

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        if agent.name == "bounded_specialist":
            evidence = await tool(agent, "invoke_model").on_invoke_tool(
                tool_context(agent, context, "specialist-evidence"),
                json.dumps(
                    {
                        "inputs": ["source-0"],
                        "arguments": {
                            "prompt": "Extract evidence.",
                            "output_artifact_id": "evidence-note",
                            "output_semantic_type": "evidence_note",
                            "output_media_type": "text/plain",
                        },
                    }
                ),
            )
            assert json.loads(evidence)["succeeded"]
            await reasoning_end(hooks, context, agent)
            return "evidence ready"

        specialist_result = await tool(agent, "consult_specialist").on_invoke_tool(
            tool_context(agent, context, "specialist-call"),
            json.dumps(
                {
                    "logical_agent_id": "evidence-specialist",
                    "role": "evidence specialist",
                    "objective": "extract bounded evidence",
                    "instruction": "Produce an evidence note.",
                    "input_artifacts": ["source-0"],
                }
            ),
        )
        specialist_payload = json.loads(specialist_result)
        assert specialist_payload["specialist_answer"] == "evidence ready"
        evidence_note = specialist_payload["produced_artifact_ids"][0]
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        answer = await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "manager-answer"),
            json.dumps(
                {
                    "inputs": [evidence_note],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        assert json.loads(answer)["output"]["text"] == "A"
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert result.terminal_action_id == "manager:manager-answer"
    assert len(result.subagent_results) == 1
    assert result.subagent_results[0].logical_agent_id == "evidence-specialist"
    assert any(
        item.information_id.endswith("/evidence-note")
        for item in result.graph_snapshots[-1].edges
    )


@pytest.mark.asyncio
async def test_native_blind_logical_trace_has_no_physical_or_private_leakage() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    runtime, gateway = runtime_and_gateway(task, physical, ("invoke_model",))
    sink = MemorySink()

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "terminal"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(
        task,
        gateway,
        profile_visibility=ProfileVisibility.BLIND,
        budget=AgentLoopBudget(
            max_manager_turns=4,
            max_subagent_turns=2,
            max_tool_model_calls=4,
            max_created_subagents=1,
            max_active_subagents=1,
        ),
        trace=WorkflowTraceRecorder("native-blind", sink),
        static_capabilities=StaticCapabilityContract(
            operators=(),
            model_classes=(
                StaticModelCapabilityClass(
                    capability_class="model-class-01",
                    modalities=frozenset({"text", "image"}),
                    capabilities=frozenset({"model"}),
                    context_window=16_384,
                    reserved_output_tokens=1_024,
                    image_token_cost=512,
                ),
            ),
        ),
    )

    assert result.final_answer == "A"
    logical = json.dumps(
        [item.payload for item in sink.events if item.event_type.startswith("logical.")],
        sort_keys=True,
    )
    for forbidden in (
        "private://source-0",
        "private-evaluator",
        "worker_id",
        "deployment_id",
        "selected_agent_id",
        "network",
        "placement",
    ):
        assert forbidden not in logical
    assert all(item.physical_profile is None for item in result.observations)
    requirements = next(
        item for item in sink.events if item.event_type == "logical.model.requirements"
    )
    assert requirements.payload["static_feasible"] is True
    assert requirements.payload["matching_model_classes"] == ["model-class-01"]
    outcome = next(
        item for item in sink.events if item.event_type == "logical.model.outcome"
    )
    assert outcome.payload["reached_model_inference"] is False


def continue_verdict(reason: str = "more evidence is required") -> VerificationResult:
    return VerificationResult(
        status="continue",
        failure_stage="evidence_collection",
        reason=reason,
        missing_requirements=("independent supporting evidence",),
    )


def ready_verdict() -> VerificationResult:
    return VerificationResult(
        status="ready_for_synthesis",
        failure_stage="none",
        reason="materialized evidence is sufficient for a synthesis attempt",
    )


@pytest.mark.asyncio
async def test_openai_agents_blind_verifier_uses_required_function_tool() -> None:
    class VerifierRunner:
        @staticmethod
        async def run(
            agent: FakeAgent,
            input: str,
            *,
            max_turns: int,
        ) -> object:
            assert max_turns == 1
            parsed_context = json.loads(input)
            assert parsed_context["task"]["objective"] == (
                "Choose A from the available evidence."
            )
            submit = tool(agent, "submit_verification")
            output = await submit.on_invoke_tool(
                SimpleNamespace(),
                ready_verdict().model_dump_json(),
            )
            return SimpleNamespace(
                final_output=output,
                context_wrapper=SimpleNamespace(
                    usage=SimpleNamespace(input_tokens=23, output_tokens=9)
                ),
            )

    sdk = SimpleNamespace(
        Agent=FakeAgent,
        FunctionTool=FakeFunctionTool,
        ModelSettings=FakeModelSettings,
        Runner=VerifierRunner,
    )
    verifier = OpenAIAgentsBlindVerifier(model="verifier-model", sdk_module=sdk)
    response = await verifier.verify(
        VerificationContext(
            task=AgentTaskView.from_contract(benchmark_task()),
            workflow=WorkflowGraphSnapshot(version=0, nodes=(), edges=()),
            observations=(),
            produced_artifacts=(),
            phase="evidence_collection",
            remaining_budget=VerifierBudgetView(
                remaining_manager_turns=11,
                remaining_tool_model_calls=12,
                remaining_created_subagents=4,
                remaining_verifier_calls=11,
            ),
        )
    )

    verifier_agent = verifier._agent
    assert isinstance(verifier_agent, FakeAgent)
    assert [item.name for item in verifier_agent.tools] == ["submit_verification"]
    assert verifier_agent.tool_use_behavior == "stop_on_first_tool"
    assert verifier_agent.model_settings.temperature == 0
    assert verifier_agent.model_settings.parallel_tool_calls is False
    assert verifier_agent.model_settings.tool_choice == "required"
    assert response.result.status == "ready_for_synthesis"
    assert response.input_tokens == 23
    assert response.output_tokens == 9


@pytest.mark.asyncio
async def test_blind_verifier_feedback_reaches_next_manager_turn_without_leakage() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    verifier = FakeVerifier((continue_verdict(), ready_verdict()))
    runtime, gateway = runtime_and_gateway(
        task,
        physical,
        ("read_artifact", "invoke_model"),
        verifier=verifier,
    )
    sink = MemorySink()

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        read_tool = tool(agent, "read_artifact")
        read = await read_tool.on_invoke_tool(
            tool_context(agent, context, "read"),
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        await reasoning_end(hooks, context, agent)
        feedback = await complete_tool_batch(agent, ((read_tool, read),))
        verification = json.loads(feedback[0])["blind_verification"]
        assert verification["status"] == "continue"
        assert verification["missing_requirements"] == [
            "independent supporting evidence"
        ]
        assert "task incomplete" in json.loads(feedback[0])["verifier_feedback"]

        await reasoning_start(hooks, context, agent)
        model_tool = tool(agent, "invoke_model")
        answer = await model_tool.on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((model_tool, answer),))
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(
        task,
        gateway,
        trace=WorkflowTraceRecorder("blind-verifier", sink),
        budget=AgentLoopBudget(max_tool_model_calls=2),
    )

    assert result.final_answer == "A"
    assert result.usage.tool_model_calls == 2
    assert result.usage.verifier_calls == 2
    assert len(result.verification_steps) == 2
    assert [item.result.status for item in result.verification_steps] == [
        "continue",
        "ready_for_synthesis",
    ]
    serialized_contexts = json.dumps(
        [item.model_dump(mode="json") for item in verifier.contexts],
        sort_keys=True,
    )
    for forbidden in (
        "private://",
        "private-evaluator",
        "source_ref",
        "evaluator_id",
        "physical_profile",
        "deployment_id",
        "worker_id",
        "network",
        "placement",
    ):
        assert forbidden not in serialized_contexts
    verification_events = [
        item for item in sink.events if item.event_type == "logical.verification"
    ]
    assert len(verification_events) == 2
    assert verification_events[0].payload["input_tokens"] == 11
    assert any(item.event_type == "logical.phase.changed" for item in sink.events)


@pytest.mark.asyncio
async def test_blind_verifier_failure_is_traced_and_typed() -> None:
    class FailingVerifier:
        async def verify(self, context: VerificationContext) -> VerificationResponse:
            del context
            raise RuntimeError("response transport rejected")

    task = benchmark_task()
    runtime, gateway = runtime_and_gateway(
        task,
        FakePhysicalService(),
        ("read_artifact",),
        verifier=FailingVerifier(),  # type: ignore[arg-type]
    )
    sink = MemorySink()

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        read_tool = tool(agent, "read_artifact")
        read = await read_tool.on_invoke_tool(
            tool_context(agent, context, "read"),
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((read_tool, read),))
        return "unreachable"

    FakeRunner.behavior = behavior
    with pytest.raises(
        AgentLoopError,
        match="Blind verifier failed: RuntimeError: response transport rejected",
    ):
        await runtime.run(
            task,
            gateway,
            trace=WorkflowTraceRecorder("failed-verifier", sink),
        )

    event_types = [item.event_type for item in sink.events]
    assert "logical.verification.started" in event_types
    failure = next(
        item for item in sink.events if item.event_type == "logical.verification.failed"
    )
    assert failure.payload["exception_type"] == "RuntimeError"
    assert failure.payload["phase"] == "evidence_collection"


@pytest.mark.asyncio
async def test_ready_phase_rejects_expansion_but_permits_model_synthesis() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    verifier = FakeVerifier((ready_verdict(), ready_verdict()))
    runtime, gateway = runtime_and_gateway(
        task,
        physical,
        ("read_artifact", "bm25_retrieve", "invoke_model"),
        verifier=verifier,
    )

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        read_tool = tool(agent, "read_artifact")
        read = await read_tool.on_invoke_tool(
            tool_context(agent, context, "read"),
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((read_tool, read),))

        await reasoning_start(hooks, context, agent)
        retrieval_tool = tool(agent, "bm25_retrieve")
        rejected = await retrieval_tool.on_invoke_tool(
            tool_context(agent, context, "late-retrieval"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {
                        "query": "more",
                        "top_k": 2,
                        "text_field": "text",
                        "output_artifact_id": "late-hits",
                    },
                }
            ),
        )
        assert json.loads(rejected)["failure_code"] == "phase_restricted"
        model_tool = tool(agent, "invoke_model")
        answer = await model_tool.on_invoke_tool(
            tool_context(agent, context, "synthesis"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        assert json.loads(answer)["succeeded"]
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(
            agent,
            ((retrieval_tool, rejected), (model_tool, answer)),
        )
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert result.usage.tool_model_calls == 2
    assert len(physical.actions) == 2
    assert any(item.failure_code == "phase_restricted" for item in result.observations)


@pytest.mark.asyncio
async def test_failed_synthesis_can_return_to_planning() -> None:
    task = benchmark_task()
    physical = FakePhysicalService(fail_model_once=True)
    verifier = FakeVerifier(
        (
            ready_verdict(),
            VerificationResult(
                status="continue",
                failure_stage="synthesis",
                reason="the synthesis model call failed before producing an answer",
                missing_requirements=("successful synthesis result",),
            ),
            ready_verdict(),
            ready_verdict(),
        )
    )
    runtime, gateway = runtime_and_gateway(
        task,
        physical,
        ("read_artifact", "invoke_model"),
        verifier=verifier,
    )

    async def call_batch(
        agent: FakeAgent,
        context: object,
        hooks: object,
        name: str,
        input_json: str,
    ) -> str:
        await reasoning_start(hooks, context, agent)
        selected = tool(agent, name)
        output = await selected.on_invoke_tool(
            tool_context(agent, context, name + "-" + str(len(physical.actions))),
            input_json,
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((selected, output),))
        return output

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await call_batch(
            agent,
            context,
            hooks,
            "read_artifact",
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        failed = await call_batch(
            agent,
            context,
            hooks,
            "invoke_model",
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        assert json.loads(failed)["failure_code"] == "context_limit_exceeded"
        recovered = await call_batch(
            agent,
            context,
            hooks,
            "read_artifact",
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        assert json.loads(recovered)["succeeded"]
        succeeded = await call_batch(
            agent,
            context,
            hooks,
            "invoke_model",
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        assert json.loads(succeeded)["succeeded"]
        return "A"

    FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)

    assert result.final_answer == "A"
    assert [item.result.status for item in result.verification_steps] == [
        "ready_for_synthesis",
        "continue",
        "ready_for_synthesis",
        "ready_for_synthesis",
    ]
    assert result.usage.tool_model_calls == 4


@pytest.mark.asyncio
async def test_verifier_has_independent_hard_budget_and_cannot_authorize_terminal_early() -> None:
    task = benchmark_task()
    physical = FakePhysicalService()
    verifier = FakeVerifier((continue_verdict(),))
    runtime, gateway = runtime_and_gateway(
        task,
        physical,
        ("read_artifact", "invoke_model"),
        verifier=verifier,
    )

    async def behavior(agent: FakeAgent, _input: str, context: object, hooks: object) -> str:
        await reasoning_start(hooks, context, agent)
        read_tool = tool(agent, "read_artifact")
        read = await read_tool.on_invoke_tool(
            tool_context(agent, context, "read"),
            json.dumps({"inputs": ["source-0"], "arguments": {}}),
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((read_tool, read),))
        await reasoning_start(hooks, context, agent)
        model_tool = tool(agent, "invoke_model")
        model = await model_tool.on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["source-0"],
                    "arguments": {"prompt": "Return only A."},
                }
            ),
        )
        await reasoning_end(hooks, context, agent)
        await complete_tool_batch(agent, ((model_tool, model),))
        return "A"

    FakeRunner.behavior = behavior
    with pytest.raises(AgentLoopError, match="verifier call budget exhausted"):
        await runtime.run(
            task,
            gateway,
            budget=AgentLoopBudget(
                max_manager_turns=4,
                max_subagent_turns=2,
                max_tool_model_calls=2,
                max_created_subagents=0,
                max_active_subagents=0,
                max_verifier_calls=1,
            ),
        )
