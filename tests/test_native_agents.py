import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from infra_joint.control.contracts import (
    LogicalModelAction,
    LogicalObservation,
    ProducedInformation,
    ProfileVisibility,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import (
    OpenAIAgentsNativeRuntime,
    _native_tool_schema,
)
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.validation import SemanticActionValidator
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
    def __init__(self, *, parallel_tool_calls: bool) -> None:
        self.parallel_tool_calls = parallel_tool_calls


class FakeRunHooks:
    pass


class FakeAgent:
    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs["name"]
        self.instructions = kwargs["instructions"]
        self.tools = kwargs["tools"]
        self.model_settings = kwargs.get("model_settings")

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
)


class FakePhysicalService:
    def __init__(self, *, fail_read_once: bool = False, bm25_barrier: int = 0) -> None:
        self.fail_read_once = fail_read_once
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
) -> tuple[OpenAIAgentsNativeRuntime, RuntimeActionGateway]:
    registry = build_operator_catalog()
    runtime = OpenAIAgentsNativeRuntime(
        name="manager",
        instructions="Solve faithfully.",
        model="planner-model",
        registry=registry,
        available_operations=operations,
        sdk_module=FAKE_SDK,
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
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "answer"),
            json.dumps(
                {
                    "inputs": ["hits-0", "hits-1"],
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
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        final = await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "after-observation"),
            json.dumps(
                {
                    "inputs": ["hits"],
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
        assert specialist_result == "evidence ready"
        await reasoning_end(hooks, context, agent)
        await reasoning_start(hooks, context, agent)
        answer = await tool(agent, "invoke_model").on_invoke_tool(
            tool_context(agent, context, "manager-answer"),
            json.dumps(
                {
                    "inputs": ["evidence-note"],
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
    assert any(item.information_id == "evidence-note" for item in result.graph_snapshots[-1].edges)


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
