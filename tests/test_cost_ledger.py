import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from agents.items import ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall
from test_native_agents import (
    FakePhysicalService,
    FakeVerifier,
    MemorySink,
    benchmark_task,
    complete_verdict,
    ready_verdict,
)
from test_native_predecision import SyntheticSDKModel

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    LogicalObservation,
    LogicalToolAction,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX, SpentCostLedger
from infra_joint.control.ledger_native import LedgerNativeRuntime
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError, AgentLoopUsage
from infra_joint.control.method_usage import MeasuredLedgerRuntime
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.provenance import semantic_input_items
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.core.state import InfrastructureState
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.executor import ArtifactTransferTelemetry, ExecutionResult
from infra_joint.worker.model_backend import ModelCallTelemetry
from infra_joint.workflow.trace import WorkflowTraceRecorder


def action(identifier: str, *, model: bool = False) -> LogicalAction:
    if model:
        return LogicalModelAction(action_id=identifier, owner_agent_id="manager", prompt="Solve.")
    return LogicalToolAction(
        action_id=identifier, owner_agent_id="manager", operator="read_artifact",
    )


def outcome(
    identifier: str,
    *,
    model: bool = False,
    code: str | None = None,
    measured: bool = True,
) -> PhysicalExecutionOutcome:
    observation = LogicalObservation(
        action_id=identifier, owner_agent_id="manager", succeeded=code is None,
        failure_code=code,
    )
    infrastructure = InfrastructureState(
        agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now(UTC),
    )
    execution = None
    if measured:
        execution = ExecutionResult(
            operator="invoke_model" if model else "read_artifact",
            agent_ids=("private-worker",), deployment_id="private-deployment",
            output={"text": "private result"}, operator_latency_ms=100,
            model_telemetry=ModelCallTelemetry(service_latency_ms=80) if model else None,
            transfers=(ArtifactTransferTelemetry(
                artifact_id="private-artifact", source_agent_id="private-source",
                target_agent_id="private-target", bytes_transferred=123, duration_ms=10,
            ),),
        )
    return PhysicalExecutionOutcome(
        observation=observation, infrastructure_before=infrastructure,
        infrastructure_after=infrastructure, execution=execution,
    )


def snapshot(ledger: SpentCostLedger) -> dict[str, Any]:
    return ledger.snapshot(
        usage=AgentLoopUsage(manager_turns=2, subagent_turns=3, tool_model_calls=5,
                             created_subagents=1, peak_active_subagents=1, verifier_calls=2),
        budget=AgentLoopBudget(max_manager_turns=20, max_tool_model_calls=64,
                               max_verifier_calls=20),
        logical_loop_elapsed_ms=50,
    ).model_dump(mode="json")


def test_parallel_work_is_not_wall_time_and_duplicate_receipts_are_idempotent() -> None:
    ledger = SpentCostLedger()
    for identifier in ("first", "second"):
        receipt = outcome(identifier)
        ledger.record(action(identifier), receipt)
        ledger.record(action(identifier), receipt)
    result = snapshot(ledger)
    assert result["completed_actions"] == result["successful_tools"] == 2
    assert result["action_transfer_bytes"]["complete_total"] == 246
    assert result["tool_wrapper_work_ms"]["complete_total"] == 200
    assert result["logical_loop_elapsed_ms"] == 50
    assert result["work_sums_are_e2e"] is False
    assert result["initial_placement_included"] is False
    assert result["remaining_manager_turns"] == 18
    assert result["remaining_physical_calls"] == 59
    for private in ("private-worker", "private-deployment", "private result", "private-source"):
        assert private not in json.dumps(result)


def test_preflight_is_not_inference_and_failed_transfer_cost_stays_unknown() -> None:
    ledger = SpentCostLedger()
    ledger.record(action("good", model=True), outcome("good", model=True))
    ledger.record(action("preflight", model=True), outcome(
        "preflight", model=True, code="context_limit_exceeded", measured=False,
    ))
    ledger.record(action("backend", model=True), outcome(
        "backend", model=True, code="model_service_error", measured=False,
    ))
    result = snapshot(ledger)
    assert result["successful_models"] == result["confirmed_inference_calls"] == 1
    assert result["failed_models"] == 2
    assert result["unknown_inference_calls"] == 1
    assert result["model_service_work_ms"]["observed_sum"] == 80
    assert result["model_service_work_ms"]["unknown_receipts"] == 1
    assert result["action_transfer_bytes"]["unknown_receipts"] == 2
    assert result["action_transfer_bytes"]["complete_total"] is None
    assert result["tool_wrapper_work_ms"]["complete_total"] == 0


def test_mismatching_or_conflicting_receipts_fail_closed() -> None:
    ledger = SpentCostLedger()
    with pytest.raises(ValueError, match="ID mismatch"):
        ledger.record(action("first"), outcome("other"))
    ledger.record(action("first"), outcome("first"))
    with pytest.raises(ValueError, match="conflicting"):
        ledger.record(action("first"), outcome("first", code="operator_failed", measured=False))
    assert snapshot(ledger)["completed_actions"] == 1


class ParallelLedgerModel(SyntheticSDKModel):
    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
        self.inputs.append(items)
        index = len(self.inputs)
        payloads = (
            [("bm25_retrieve", {"inputs": ["source-0"], "arguments": {
                "query": f"query-{i}", "top_k": 1, "output_artifact_id": f"evidence-{i}",
            }}) for i in range(2)]
            if index == 1 else
            [("invoke_model", {"inputs": ["source-0"], "arguments": {"prompt": "Return A."}})]
        )
        return ModelResponse(output=[ResponseFunctionToolCall(
            id=f"fc-{index}-{i}", call_id=f"call-{index}-{i}", type="function_call",
            name=name, arguments=json.dumps(payload),
        ) for i, (name, payload) in enumerate(payloads)],
            usage=Usage(requests=1, input_tokens=20, output_tokens=10), response_id=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_real_sdk_manager_ledger_is_fresh_and_preserves_parallel_execution(
    enabled: bool,
) -> None:
    task = benchmark_task()
    registry = build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    physical = FakePhysicalService(bm25_barrier=2)
    gateway = RuntimeActionGateway(
        SemanticActionValidator(task, registry, operations), physical,  # type: ignore[arg-type]
    )
    model = ParallelLedgerModel()
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    sink = MemorySink()
    runtime_class = MeasuredLedgerRuntime if enabled else OpenAIAgentsNativeRuntime
    runtime = runtime_class(
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier,
        record_input_provenance=True,
    )
    result = await runtime.run(task, gateway, trace=WorkflowTraceRecorder("ledger-sdk", sink))
    assert result.final_answer == "A"
    assert physical.peak_bm25 == 2
    assert physical.expose_profile_values == [False, False, False]
    ledgers: list[dict[str, Any]] = []
    for items in model.inputs:
        messages = [item for item in items if str(item.get("content", "")).startswith(
            LEDGER_MESSAGE_PREFIX)]
        assert len(messages) == int(enabled)
        if messages:
            ledgers.append(json.loads(messages[0]["content"][len(LEDGER_MESSAGE_PREFIX):]))
    if enabled:
        assert ledgers[0]["completed_actions"] == 0
        assert ledgers[1]["successful_tools"] == 2
        assert ledgers[1]["confirmed_inference_calls"] == 0
        assert ledgers[1]["action_transfer_bytes"]["complete_total"] is None
    contexts = json.dumps([item.model_dump(mode="json") for item in verifier.contexts])
    assert "spent-cost-ledger" not in contexts and LEDGER_MESSAGE_PREFIX not in contexts
    events = [e for e in sink.events if e.event_type == "logical.cost_ledger.predecision"]
    assert len(events) == (2 if enabled else 0)
    inputs = [e for e in sink.events if e.event_type == "logical.reasoning.input"]
    assert [event.payload["input_items"] for event in inputs] == model.inputs
    for private in ("source_ref", "evaluator_id", "deployment_id", "network_class", "192.168."):
        assert private not in json.dumps(model.inputs)
    metered = [event for event in sink.events
               if event.event_type == "logical.method.reasoning_usage"]
    assert len(metered) == (2 if enabled else 0)
    assert all(event.payload["input_tokens"] == 20 and event.payload["output_tokens"] == 10
               for event in metered)


@pytest.mark.asyncio
async def test_specialist_input_filter_rejects_inherited_manager_ledger() -> None:
    sdk = SimpleNamespace(RunConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    state = SimpleNamespace(
        visibility="BLIND", root_agent=SimpleNamespace(logical_agent_id="manager"),
    )
    config = LedgerNativeRuntime._predecision_run_config(
        sdk, state,  # type: ignore[arg-type]
    )
    data = SimpleNamespace(agent=SimpleNamespace(name="bounded_specialist"),
                           model_data=SimpleNamespace(input=[{
                               "role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}",
                           }], instructions="unchanged"))
    with pytest.raises(AgentLoopError, match="ledger isolation"):
        await config.call_model_input_filter(data)
