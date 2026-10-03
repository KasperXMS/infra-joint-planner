import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from agents.items import ModelResponse
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)
from test_action_consequence import action, environment, estimator, snapshot
from test_control_plane import FrozenSelectionExecutor, SequencedObserver
from test_native_agents import (
    FakePhysicalService,
    FakeVerifier,
    MemorySink,
    benchmark_task,
    complete_verdict,
    continue_verdict,
    ready_verdict,
)
from test_native_predecision import SyntheticSDKModel

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.consequence_profiles import CostHistory
from infra_joint.control.contracts import LogicalOutput, ProfileVisibility
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import AgentLoopError
from infra_joint.control.physical import PhysicalExecutionService
from infra_joint.control.provenance import semantic_input_items
from infra_joint.control.quote import QuoteLedgerGateway, QuoteProtocolError, ReadyActionQuotes
from infra_joint.control.quote_native import QuoteNativeRuntime
from infra_joint.control.validation import SemanticActionValidator, SemanticValidationError
from infra_joint.core.state import ArtifactRuntimeState, InfrastructureState
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder


def quote_fixture(
    *, observer: SequencedObserver | None = None, ttl: float = 120, max_proposals: int = 128,
    clock: Any = None,
) -> tuple[ReadyActionQuotes, FakePhysicalService, list[tuple[str, dict[str, Any]]]]:
    registry = build_operator_catalog()
    task = benchmark_task().model_copy(update={"artifacts": tuple(
        item.model_copy(update={"artifact_id": "source-中文", "media_type": "text/plain"})
        for item in benchmark_task().artifacts
    )})
    execution = FakePhysicalService()
    gateway = RuntimeActionGateway(SemanticActionValidator(task, registry, ("invoke_model",)),
                                   execution)  # type: ignore[arg-type]
    quote_executor = FrozenSelectionExecutor()
    physical = PhysicalExecutionService(registry, environment(), observer or SequencedObserver(
        snapshot()), quote_executor)  # type: ignore[arg-type]
    events: list[tuple[str, dict[str, Any]]] = []
    options: dict[str, Any] = {"clock": clock} if clock is not None else {}
    quotes = ReadyActionQuotes(physical=physical, estimator=estimator(), gateway=gateway,
                              owner_agent_id="manager", emit=lambda k, p: events.append((k, p)),
                              quote_ttl_seconds=ttl, max_proposals=max_proposals, **options)
    return quotes, execution, events


@pytest.mark.asyncio
async def test_quote_does_not_reserve_materialize_or_execute_and_commit_is_single_use() -> None:
    quotes, execution, events = quote_fixture()
    logical = action()
    quote = await quotes.propose(logical, payload_json="{}", operator="invoke_model")
    assert not execution.actions
    assert isinstance(quotes.gateway, RuntimeActionGateway)
    assert quotes.gateway.validator.known_artifacts == frozenset({"source-中文"})
    pending = await quotes.authorize(quote.quote_id, owner="manager")
    gateway = QuoteLedgerGateway(quotes.gateway, quotes)
    outcome = await gateway.execute_batch((pending.action,), expose_profile=False)
    assert outcome[0].observation.succeeded
    assert len(execution.actions) == 1
    assert any(kind == "logical.cost_quote.observed" for kind, _ in events)
    with pytest.raises(QuoteProtocolError, match="already_consumed"):
        await quotes.authorize(quote.quote_id, owner="manager")
    with pytest.raises(QuoteProtocolError, match="requires_explicit"):
        await gateway.execute_batch((logical,), expose_profile=False)


@pytest.mark.asyncio
async def test_quote_owner_expiry_discard_and_proposal_guard_are_fail_closed() -> None:
    now = [0.0]
    quotes, execution, _ = quote_fixture(ttl=2, max_proposals=2, clock=lambda: now[0])
    quote = await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    with pytest.raises(QuoteProtocolError, match="owner_mismatch"):
        await quotes.authorize(quote.quote_id, owner="specialist")
    now[0] = 3
    with pytest.raises(QuoteProtocolError, match="expired"):
        await quotes.authorize(quote.quote_id, owner="manager")
    quote2 = await quotes.propose(action(action_id="second"), payload_json="{}",
                                  operator="invoke_model")
    quotes.discard(quote2.quote_id, owner="manager")
    with pytest.raises(QuoteProtocolError, match="already_consumed"):
        await quotes.authorize(quote2.quote_id, owner="manager")
    with pytest.raises(QuoteProtocolError, match="proposal_budget"):
        await quotes.propose(action(action_id="third"), payload_json="{}", operator="invoke_model")
    assert not execution.actions


@pytest.mark.asyncio
async def test_changed_anonymous_consequence_requires_explicit_new_quote() -> None:
    quotes, execution, events = quote_fixture(observer=SequencedObserver(
        snapshot(bandwidth=3), snapshot(bandwidth=100),
    ))
    quote = await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    with pytest.raises(QuoteProtocolError, match="consequence_changed"):
        await quotes.authorize(quote.quote_id, owner="manager")
    assert not execution.actions
    assert any(kind == "logical.cost_quote.stale" for kind, _ in events)


@pytest.mark.asyncio
async def test_quote_commit_cannot_change_action_arguments() -> None:
    quotes, execution, _ = quote_fixture()
    quote = await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    pending = await quotes.authorize(quote.quote_id, owner="manager")
    gateway = QuoteLedgerGateway(quotes.gateway, quotes)
    changed = pending.action.model_copy(update={"prompt": "Different action"})
    with pytest.raises(QuoteProtocolError, match="differs_from_quote"):
        await gateway.execute_batch((changed,), expose_profile=False)
    assert not execution.actions


@pytest.mark.asyncio
async def test_unknown_quote_and_concurrent_duplicate_commit_never_execute_twice() -> None:
    quotes, execution, _ = quote_fixture()
    with pytest.raises(QuoteProtocolError, match="unknown_quote"):
        await quotes.authorize("missing", owner="manager")
    quote = await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    attempts = await asyncio.gather(*(
        quotes.authorize(quote.quote_id, owner="manager") for _ in range(2)
    ), return_exceptions=True)
    assert sum(isinstance(item, QuoteProtocolError) for item in attempts) == 1
    assert not execution.actions
    assert quotes.summary()["timed_control_calls"] == 4


@pytest.mark.asyncio
async def test_quote_service_harness_value_error_is_not_masked_as_semantic_rejection() -> None:
    class BrokenEstimator:
        def evaluate(self, *args: Any) -> Any:
            raise ValueError("estimator implementation defect")

    quotes, execution, events = quote_fixture()
    quotes.estimator = BrokenEstimator()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="implementation defect"):
        await quotes.propose(action(), payload_json="{}", operator="invoke_model")
    assert not execution.actions
    timings = [payload for kind, payload in events if kind == "logical.cost_quote.control_timing"]
    assert timings[0]["succeeded"] is False and timings[0]["control_work_ms"] >= 0


@pytest.mark.asyncio
async def test_future_quote_outputs_are_not_ready_for_a_dependent_proposal() -> None:
    quotes, execution, _ = quote_fixture()
    producer = action(outputs=(LogicalOutput(artifact_id="future", semantic_type="note",
                                             media_type="text/plain"),))
    await quotes.propose(producer, payload_json="{}", operator="invoke_model")
    consumer = action(action_id="consumer", inputs=("future",))
    with pytest.raises(SemanticValidationError, match="unknown input"):
        await quotes.propose(consumer, payload_json="{}", operator="invoke_model")
    assert not execution.actions


class ReadyQuoteObserver:
    """Materialized metadata follows actual successful gateway completion only."""

    def __init__(self, validator: SemanticActionValidator, execution: FakePhysicalService) -> None:
        self.validator = validator
        self.execution = execution

    async def observe(self) -> InfrastructureState:
        outputs = {output.artifact_id: output for action in self.execution.actions
                   for output in action.outputs}
        return snapshot().model_copy(update={"artifacts": tuple(
            ArtifactRuntimeState(
                artifact_id=identifier, locations=("private-A",),
                media_type=outputs[identifier].media_type if identifier in outputs
                else "application/json", size_bytes=12,
            ) for identifier in sorted(self.validator.known_artifacts)
        ), "observed_at": datetime.now(UTC)})


def tool_response(index: int, calls: list[tuple[str, dict[str, Any]]]) -> ModelResponse:
    return ModelResponse(output=[ResponseFunctionToolCall(
        id=f"fc-{index}-{i}", call_id=f"call-{index}-{i}", type="function_call", name=name,
        arguments=json.dumps(payload),
    ) for i, (name, payload) in enumerate(calls)],
        usage=Usage(requests=1, input_tokens=20, output_tokens=10), response_id=None)


class QuoteSDKModel(SyntheticSDKModel):
    def __init__(self, execution: FakePhysicalService) -> None:
        super().__init__()
        self.execution = execution

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
        self.inputs.append(items)
        index = len(self.inputs)
        results = [json.loads(item["output"]) for item in items
                   if item.get("type") == "function_call_output"]
        if index == 1:
            calls = [("bm25_retrieve", {"inputs": ["source-0"], "arguments": {
                "query": f"query-{i}", "top_k": 1, "output_artifact_id": f"evidence-{i}",
            }}) for i in range(2)]
        elif index == 2:
            assert not self.execution.actions
            calls = [("commit_quote", {"quote_id": item["quote_id"]})
                     for item in results if "quote_id" in item]
        elif index == 3:
            assert len(self.execution.actions) == 2
            evidence = next(item["produced_information"][0]["artifact_id"] for item in results
                            if item.get("produced_information"))
            calls = [("invoke_model", {"inputs": [evidence], "arguments": {"prompt": "Return A."}})]
        else:
            assert index == 4 and len(self.execution.actions) == 2
            latest = [item for item in results if "quote_id" in item][-1]
            calls = [("commit_quote", {"quote_id": latest["quote_id"]})]
        return tool_response(index, calls)


@pytest.mark.asyncio
async def test_real_sdk_quote_commit_parallelism_terminal_and_privacy() -> None:
    task = benchmark_task()
    registry = build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    execution = FakePhysicalService(bm25_barrier=2)
    validator = SemanticActionValidator(task, registry, operations)
    gateway = RuntimeActionGateway(validator, execution)  # type: ignore[arg-type]
    never_executed = FrozenSelectionExecutor()
    physical = PhysicalExecutionService(registry, environment(),
                                        ReadyQuoteObserver(validator, execution),
                                        never_executed)  # type: ignore[arg-type]
    model = QuoteSDKModel(execution)
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    sink = MemorySink()
    runtime = QuoteNativeRuntime(
        physical=physical, environment=environment(), cost_history=CostHistory(),
        network_category="constrained", reachable_workers=frozenset({"private-A"}),
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier, record_input_provenance=True,
    )
    result = await asyncio.wait_for(runtime.run(
        task, gateway, static_capabilities=build_static_capability_contract(environment(), registry,
                                                                          operations),
        trace=WorkflowTraceRecorder("quote-sdk", sink), profile_visibility=ProfileVisibility.BLIND,
    ), timeout=5)
    assert result.final_answer == "A"
    assert result.usage.manager_turns == 4 and result.usage.tool_model_calls == 3
    assert result.usage.verifier_calls == 2
    assert execution.peak_bm25 == 2 and len(execution.actions) == 3
    assert never_executed.decisions == []
    assert len(result.graph_snapshots[-1].nodes) == 3
    quotes = [event for event in sink.events if event.event_type == "logical.cost_quote.created"]
    observed = [event for event in sink.events if event.event_type == "logical.cost_quote.observed"]
    assert len(quotes) == len(observed) == 3
    usage_events = [event for event in sink.events
                    if event.event_type == "logical.method.reasoning_usage"]
    assert len(usage_events) == 4
    assert sum(event.payload["input_tokens"] for event in usage_events) == 80
    assert sum(event.payload["output_tokens"] for event in usage_events) == 40
    actual = {event.payload["action"]["action_id"]: event.payload["action"] for event in sink.events
              if event.event_type == "logical.action.prepared"}
    for quote in quotes:
        assert actual[quote.payload["action"]["action_id"]] == quote.payload["action"]
    logical = json.dumps([event.payload for event in sink.events
                          if event.event_type.startswith("logical.")])
    for forbidden in ("private-A", "private-B", "private-C", "private-model", "private-blob",
                      "private://", "private-evaluator", "source_ref", "deployment_id"):
        assert forbidden not in logical and forbidden not in json.dumps(model.inputs)
    verifier_inputs = json.dumps([item.model_dump(mode="json") for item in verifier.contexts])
    assert "consequence" not in verifier_inputs and "cost_quote" not in verifier_inputs


class FailureRecoverySDKModel(SyntheticSDKModel):
    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
        self.inputs.append(items)
        index = len(self.inputs)
        results = [json.loads(item["output"]) for item in items
                   if item.get("type") == "function_call_output"]
        if index % 2:
            if index == 3:
                assert any(item.get("failure_code") == "context_limit_exceeded" for item in results)
            calls = [("invoke_model", {"inputs": ["source-0"],
                                       "arguments": {"prompt": "Return A."}})]
        else:
            quote = [item for item in results if "quote_id" in item][-1]
            calls = [("commit_quote", {"quote_id": quote["quote_id"]})]
        return tool_response(index, calls)


@pytest.mark.asyncio
async def test_real_sdk_typed_physical_failure_returns_for_explicit_continuation() -> None:
    task, registry = benchmark_task(), build_operator_catalog()
    operations = ("invoke_model",)
    execution = FakePhysicalService(fail_model_once=True)
    validator = SemanticActionValidator(task, registry, operations)
    gateway = RuntimeActionGateway(validator, execution)  # type: ignore[arg-type]
    physical = PhysicalExecutionService(registry, environment(),
                                        ReadyQuoteObserver(validator, execution),
                                        FrozenSelectionExecutor())  # type: ignore[arg-type]
    verifier = FakeVerifier((continue_verdict(), complete_verdict()))
    model = FailureRecoverySDKModel()
    sink = MemorySink()
    runtime = QuoteNativeRuntime(
        physical=physical, environment=environment(), cost_history=CostHistory(),
        network_category="fast", reachable_workers=frozenset({"private-A"}),
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier, record_input_provenance=True,
    )
    result = await runtime.run(
        task, gateway, static_capabilities=build_static_capability_contract(environment(), registry,
                                                                          operations),
        trace=WorkflowTraceRecorder("quote-recovery", sink),
    )
    assert result.final_answer == "A" and result.usage.tool_model_calls == 2
    assert result.usage.manager_turns == 4 and result.usage.verifier_calls == 2
    assert len([item for item in result.observations if not item.succeeded]) == 1
    observed = [event for event in sink.events if event.event_type == "logical.cost_quote.observed"]
    assert len(observed) == 2 and observed[0].payload["actual_model_service_ms"] is None


class SpecialistQuoteSDKModel(SyntheticSDKModel):
    def __init__(self) -> None:
        super().__init__()
        self.manager_calls = 0
        self.specialist_inputs: list[list[dict[str, Any]]] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
        self.inputs.append(items)
        specialist = any(item.get("role") == "user" and isinstance(item.get("content"), str)
                         and '"assignment"' in item["content"] for item in items)
        if specialist:
            tools = kwargs.get("tools", args[3] if len(args) > 3 else [])
            assert not any(tool.name in {"commit_quote", "discard_quote"} for tool in tools)
            assert all("Manager protocol" not in tool.description for tool in tools)
            self.specialist_inputs.append(items)
            index = len(self.specialist_inputs)
            if index == 1:
                calls = [("read_artifact", {"inputs": ["source-0"], "arguments": {}})]
            elif index == 2:
                calls = [("invoke_model", {"inputs": ["source-0"], "arguments": {
                    "prompt": "Extract evidence.", "output_artifact_id": "note",
                    "output_semantic_type": "evidence_note", "output_media_type": "text/plain",
                }})]
            else:
                return ModelResponse(output=[ResponseOutputMessage(
                    id="child-final", type="message", role="assistant", status="completed",
                    content=[ResponseOutputText(type="output_text", text="Evidence ready.",
                                                annotations=[])],
                )], usage=Usage(requests=1, input_tokens=20, output_tokens=10), response_id=None)
        else:
            self.manager_calls += 1
            if self.manager_calls == 1:
                calls = [("consult_specialist", {"logical_agent_id": "evidence-specialist",
                          "role": "analyst", "objective": "extract evidence",
                          "instruction": "Produce a note.", "input_artifacts": ["source-0"]})]
            elif self.manager_calls == 2:
                delegated = next(json.loads(item["output"]) for item in items
                                 if item.get("type") == "function_call_output")
                calls = [("invoke_model", {"inputs": [delegated["produced_artifact_ids"][0]],
                                           "arguments": {"prompt": "Return A."}})]
            else:
                quote = [json.loads(item["output"]) for item in items
                         if item.get("type") == "function_call_output"][-1]
                calls = [("commit_quote", {"quote_id": quote["quote_id"]})]
        return tool_response(len(self.inputs), calls)


@pytest.mark.asyncio
async def test_real_sdk_specialists_remain_blind_unquoted_and_manager_continues() -> None:
    task, registry = benchmark_task(), build_operator_catalog()
    operations = ("read_artifact", "invoke_model")
    execution = FakePhysicalService(fail_read_once=True)
    validator = SemanticActionValidator(task, registry, operations)
    gateway = RuntimeActionGateway(validator, execution)  # type: ignore[arg-type]
    physical = PhysicalExecutionService(registry, environment(),
                                        ReadyQuoteObserver(validator, execution),
                                        FrozenSelectionExecutor())  # type: ignore[arg-type]
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    model = SpecialistQuoteSDKModel()
    sink = MemorySink()
    runtime = QuoteNativeRuntime(
        physical=physical, environment=environment(), cost_history=CostHistory(),
        network_category="fast", reachable_workers=frozenset({"private-A"}),
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier, record_input_provenance=True,
    )
    result = await runtime.run(
        task, gateway, static_capabilities=build_static_capability_contract(environment(), registry,
                                                                          operations),
        trace=WorkflowTraceRecorder("quote-specialist", sink),
    )
    assert result.final_answer == "A" and result.usage.created_subagents == 1
    assert result.usage.manager_turns == 3 and result.usage.subagent_turns == 3
    assert result.usage.tool_model_calls == 3 and result.usage.verifier_calls == 2
    child_input = json.dumps(model.specialist_inputs)
    for forbidden in ("consequence", "quote_id", "Measured execution spending", "private-model",
                      "source_ref", "network_class", "physical_profile", "deployment_id"):
        assert forbidden not in child_input
    quotes = [event for event in sink.events if event.event_type == "logical.cost_quote.created"]
    assert len(quotes) == 1
    assert any(event.event_type == "logical.information.handoff" for event in sink.events)
    usage_events = [event for event in sink.events
                    if event.event_type == "logical.method.reasoning_usage"]
    assert len(usage_events) == 6
    assert sum(event.payload["recipient"] == "manager" for event in usage_events) == 3
    assert sum(event.payload["recipient"] == "specialist" for event in usage_events) == 3


@pytest.mark.asyncio
async def test_input_filter_fails_closed_on_inherited_quote_in_child_context() -> None:
    sdk = SimpleNamespace(RunConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    state = SimpleNamespace(visibility=ProfileVisibility.BLIND,
                            root_agent=SimpleNamespace(logical_agent_id="manager"))
    config = QuoteNativeRuntime._predecision_run_config(sdk, state)  # type: ignore[arg-type]
    data = SimpleNamespace(agent=SimpleNamespace(name="bounded_specialist"),
                           model_data=SimpleNamespace(input=[{
                               "type": "function_call_output", "output": json.dumps({
                                   "quote_id": "quote", "action_sha256": "0" * 64,
                                   "consequence": {"model_service": {"p50_ms": 100}},
                               }),
                           }], instructions="unchanged"))
    with pytest.raises(AgentLoopError, match="quote isolation"):
        await config.call_model_input_filter(data)
