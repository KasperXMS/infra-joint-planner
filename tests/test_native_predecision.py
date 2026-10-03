# pyright: reportPrivateUsage=false
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest
from agents import Model
from agents.items import ModelResponse
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)
from test_native_agents import (
    FakePhysicalService,
    FakeVerifier,
    MemorySink,
    benchmark_task,
    complete_verdict,
    ready_verdict,
)

from infra_joint.control.contracts import PhysicalProfileView, ProfileVisibility
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.ledger_native import LedgerNativeRuntime
from infra_joint.control.loop import AgentLoopError
from infra_joint.control.native_agents import (
    OpenAIAgentsNativeRuntime,
    _deterministic_terminal_answer,
)
from infra_joint.control.provenance import PROFILE_MESSAGE_PREFIX, semantic_input_items
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.core.task import OutputContract, OutputFormat
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder


class SyntheticSDKModel(Model):
    """Real SDK runner and tools, deterministic provider; zero network/model calls."""

    def __init__(self) -> None:
        self.inputs: list[list[dict[str, Any]]] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = kwargs.get("input", args[1] if len(args) > 1 else [])
        self.inputs.append(semantic_input_items(items))
        index = len(self.inputs)
        name = "bm25_retrieve" if index == 1 else "invoke_model"
        payload = (
            {"inputs": ["source-0"], "arguments": {
                "query": "synthetic", "top_k": 1, "output_artifact_id": "evidence",
            }}
            if index == 1 else
            {"inputs": ["source-0"], "arguments": {"prompt": "Respond to the task."}}
        )
        return ModelResponse(
            output=[ResponseFunctionToolCall(
                id=f"fc-{index}", call_id=f"call-{index}", type="function_call",
                name=name, arguments=json.dumps(payload),
            )],
            usage=Usage(requests=1, input_tokens=20, output_tokens=10), response_id=None,
        )

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise AssertionError("test is non-streaming")
        yield  # pragma: no cover


class SnapshotPhysical(FakePhysicalService):
    def __init__(self, model_text: str) -> None:
        super().__init__(model_text=model_text)
        self.snapshot_calls = 0

    async def profile_overview(self) -> PhysicalProfileView:
        self.snapshot_calls += 1
        # The first fresh observation must precede all physical actions.
        if self.snapshot_calls == 1:
            assert not self.actions
        return PhysicalProfileView(
            candidate_count=2, input_bytes=0, remote_input_count_range=(0, 0),
            queue_pressure_range=(self.snapshot_calls, self.snapshot_calls),
            network_class="constrained", unknown_reasons=("service profile unavailable",),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility", [ProfileVisibility.BLIND, ProfileVisibility.AWARE])
async def test_actual_sdk_predecision_input_provenance_and_private_isolation(
    visibility: ProfileVisibility,
) -> None:
    task = benchmark_task().model_copy(update={
        "output_contract": OutputContract(format=OutputFormat.SHORT_TEXT,
                                          canonical_labels=("Yes", "No")),
    })
    registry = build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    physical = SnapshotPhysical("Yes")
    gateway = RuntimeActionGateway(
        SemanticActionValidator(task, registry, operations), physical,  # type: ignore[arg-type]
    )
    model = SyntheticSDKModel()
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    sink = MemorySink()
    runtime = OpenAIAgentsNativeRuntime(
        name="manager", instructions="Solve faithfully.", model=model,
        registry=registry, available_operations=operations, blind_verifier=verifier,
        predecision_profiles=True, record_input_provenance=True,
    )
    result = await runtime.run(task, gateway, profile_visibility=visibility,
                               trace=WorkflowTraceRecorder("predecision", sink))
    assert result.final_answer == "Yes"
    assert len(model.inputs) == 2
    expected = 2 if visibility == ProfileVisibility.AWARE else 0
    assert physical.snapshot_calls == expected
    profile_events = [e for e in sink.events if e.event_type == "logical.profile.predecision"]
    input_events = [e for e in sink.events if e.event_type == "logical.reasoning.input"]
    for index, items in enumerate(model.inputs):
        profiles = [item for item in items
                    if str(item.get("content", "")).startswith(PROFILE_MESSAGE_PREFIX)]
        assert len(profiles) == (1 if expected else 0)
        assert input_events[index].payload["input_items"] == items
        if expected:
            assert sink.events.index(profile_events[index]) < sink.events.index(input_events[index])
            assert json.loads(profiles[0]["content"][len(PROFILE_MESSAGE_PREFIX):])[
                "queue_pressure_range"] == [index + 1, index + 1]
    assert len([e for e in sink.events if e.event_type == "action.started"]) == 2
    assert len([e for e in sink.events if e.event_type == "action.completed"]) == 2
    assert len([e for e in sink.events if e.event_type == "logical.action.selected"]) == 2
    assert len([e for e in sink.events if e.event_type == "logical.verification.input"]) == 2
    verifier_json = json.dumps([c.model_dump(mode="json") for c in verifier.contexts])
    assert "physical_profile" not in verifier_json
    assert "network_class" not in verifier_json
    logical_json = json.dumps([e.payload for e in sink.events
                              if e.event_type != "physical.execution"])
    for private in ("private://", "private-evaluator", "worker_id", "deployment_id",
                    "192.168.", "source_ref", "evaluator_id"):
        assert private not in logical_json
    if not expected:
        assert "network_class" not in logical_json


@pytest.mark.asyncio
@pytest.mark.parametrize("ledger_only", [False, True])
async def test_real_sdk_specialist_continuation_does_not_receive_tool_result_profile(
    ledger_only: bool,
) -> None:
    class DelegatingSDKModel(SyntheticSDKModel):
        def __init__(self) -> None:
            super().__init__()
            self.manager_calls = 0
            self.specialist_calls = 0
            self.specialist_inputs: list[list[dict[str, Any]]] = []

        async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
            items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
            specialist = False
            for item in items:
                if item.get("role") == "user" and isinstance(item.get("content"), str):
                    try:
                        message = json.loads(item["content"])
                    except json.JSONDecodeError:
                        continue
                    specialist |= isinstance(message, dict) and "assignment" in message
            self.inputs.append(items)
            if specialist:
                self.specialist_calls += 1
                self.specialist_inputs.append(items)
                assert "network_class" not in json.dumps(items)
                if self.specialist_calls == 3:
                    return ModelResponse(output=[ResponseOutputMessage(
                        id="specialist-final", type="message", role="assistant", status="completed",
                        content=[ResponseOutputText(type="output_text", text="evidence ready",
                                                    annotations=[])],
                    )], usage=Usage(requests=1, input_tokens=20, output_tokens=10),
                        response_id=None)
                name = "read_artifact" if self.specialist_calls == 1 else "invoke_model"
                payload = {"inputs": ["source-0"], "arguments": (
                    {} if self.specialist_calls == 1 else {
                        "prompt": "Extract evidence.", "output_artifact_id": "evidence-note",
                        "output_semantic_type": "evidence_note", "output_media_type": "text/plain",
                    }
                )}
            else:
                self.manager_calls += 1
                if self.manager_calls == 1:
                    name = "consult_specialist"
                    payload = {"logical_agent_id": "evidence-specialist",
                               "role": "evidence analyst",
                               "objective": "extract evidence", "instruction": "Produce a note.",
                               "input_artifacts": ["source-0"]}
                else:
                    delegated = next(json.loads(item["output"]) for item in items
                                     if item.get("type") == "function_call_output")
                    name = "invoke_model"
                    payload = {"inputs": [delegated["produced_artifact_ids"][0]],
                               "arguments": {"prompt": "Return only A."}}
            index = len(self.inputs)
            return ModelResponse(output=[ResponseFunctionToolCall(
                id=f"fc-{index}", call_id=f"call-{index}", type="function_call",
                name=name, arguments=json.dumps(payload),
            )], usage=Usage(requests=1, input_tokens=20, output_tokens=10), response_id=None)

    task = benchmark_task()
    registry = build_operator_catalog()
    operations = ("read_artifact", "invoke_model")
    physical = SnapshotPhysical("A")
    gateway = RuntimeActionGateway(
        SemanticActionValidator(task, registry, operations), physical,  # type: ignore[arg-type]
    )
    model = DelegatingSDKModel()
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    sink = MemorySink()
    runtime_class = LedgerNativeRuntime if ledger_only else OpenAIAgentsNativeRuntime
    runtime = runtime_class(
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier,
        predecision_profiles=True, record_input_provenance=True,
    )
    visibility = ProfileVisibility.BLIND if ledger_only else ProfileVisibility.AWARE
    result = await runtime.run(task, gateway, profile_visibility=visibility,
                               trace=WorkflowTraceRecorder("specialist-isolation", sink))
    assert result.final_answer == "A"
    assert model.manager_calls == 2 and model.specialist_calls == 3
    assert physical.expose_profile_values == [False, False, not ledger_only]
    assert physical.snapshot_calls == (0 if ledger_only else 2)
    assert len([e for e in sink.events if e.event_type == "logical.profile.predecision"]) == (
        0 if ledger_only else 2
    )
    assert "network_class" not in json.dumps([c.model_dump(mode="json") for c in verifier.contexts])
    specialist_json = json.dumps(model.specialist_inputs)
    for forbidden in ("network_class", "private://", "private-evaluator", "source_ref",
                      "evaluator_id", "worker_id", "deployment_id", "192.168.",
                      "spent-cost-ledger", "Measured execution spending so far"):
        assert forbidden not in specialist_json


@pytest.mark.asyncio
@pytest.mark.parametrize("owner,visibility", [
    ("bounded_specialist", ProfileVisibility.AWARE), ("manager", ProfileVisibility.BLIND),
])
@pytest.mark.parametrize("route", ["tool-result", "profile-message"])
async def test_sdk_input_filter_rejects_blind_recipient_dynamic_profile_before_model(
    owner: str, visibility: ProfileVisibility, route: str,
) -> None:
    sdk = SimpleNamespace(RunConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    state = SimpleNamespace(visibility=visibility,
                            root_agent=SimpleNamespace(logical_agent_id="manager"))
    config = OpenAIAgentsNativeRuntime._predecision_run_config(sdk, state)  # type: ignore[arg-type]
    item = ({"type": "function_call_output", "call_id": "call-1", "output": json.dumps({
        "physical_profile": {"network_class": "constrained"},
    })} if route == "tool-result" else
        {"role": "user", "content": PROFILE_MESSAGE_PREFIX + '{"network_class":"constrained"}'})
    data = SimpleNamespace(agent=SimpleNamespace(name=owner), model_data=SimpleNamespace(
        input=[item], instructions="unchanged",
    ))
    with pytest.raises(AgentLoopError, match="Blind recipient dynamic profile isolation"):
        await config.call_model_input_filter(data)


@pytest.mark.asyncio
async def test_invalid_canonical_candidate_returns_to_existing_synthesis_transition() -> None:
    class FormatOncePhysical(SnapshotPhysical):
        async def execute(self, action: Any, *, expose_profile: bool) -> Any:
            if getattr(action, "action_type", "") == "model":
                self.model_text = "Yes." if len(self.actions) == 1 else "Yes"
            return await super().execute(action, expose_profile=expose_profile)

    task = benchmark_task().model_copy(update={
        "output_contract": OutputContract(format=OutputFormat.SHORT_TEXT,
                                          canonical_labels=("Yes", "No")),
    })
    registry = build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    physical = FormatOncePhysical("Yes.")
    verifier = FakeVerifier((ready_verdict(), complete_verdict(), complete_verdict()))
    sink = MemorySink()
    runtime = OpenAIAgentsNativeRuntime(
        name="manager", instructions="Solve faithfully.", model=SyntheticSDKModel(),
        registry=registry, available_operations=operations, blind_verifier=verifier,
        predecision_profiles=True, record_input_provenance=True,
    )
    gateway = RuntimeActionGateway(
        SemanticActionValidator(task, registry, operations), physical,  # type: ignore[arg-type]
    )
    result = await runtime.run(task, gateway, trace=WorkflowTraceRecorder("contract", sink))
    assert result.final_answer == "Yes"
    assert result.usage.manager_turns == 3
    assert result.usage.verifier_calls == 3
    assert sum(e.event_type == "logical.verification.terminal_contract_enforced"
               for e in sink.events) == 1
    # Intermediate materialized model notes remain unrestricted; only terminal output is exact.
    assert "No punctuation" in physical.actions[-1].prompt


@pytest.mark.parametrize("labels", [(), ("Yes", "Yes"), (" Yes", "No"), ("", "No")])
def test_canonical_labels_fail_closed_on_invalid_contract(labels: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        OutputContract(format=OutputFormat.SHORT_TEXT, canonical_labels=labels)


@pytest.mark.parametrize("answer", ["Yes", "No"])
def test_canonical_terminal_accepts_exact_declared_label(answer: str) -> None:
    contract = OutputContract(format=OutputFormat.SHORT_TEXT, canonical_labels=("Yes", "No"))
    assert _deterministic_terminal_answer(contract, answer) == answer


@pytest.mark.parametrize("answer", ["Yes.", "**Yes.**", "Yes, because...", "no",
                                   "Both guides are similar. Yes."])
def test_canonical_terminal_rejects_punctuation_and_prose(answer: str) -> None:
    contract = OutputContract(format=OutputFormat.SHORT_TEXT, canonical_labels=("Yes", "No"))
    with pytest.raises(AgentLoopError, match="canonical-label"):
        _deterministic_terminal_answer(contract, answer)


def test_provenance_does_not_record_provider_private_reasoning() -> None:
    items = semantic_input_items([
        {"type": "reasoning", "summary": "secret"},
        {"role": "assistant", "content": "visible answer", "reasoning_content": "secret"},
    ])
    assert items == [{"role": "assistant", "content": "visible answer"}]
