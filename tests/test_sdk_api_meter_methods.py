"""Real native SDK runners/gateway tools, synthetic physical/backend executions."""

import asyncio
import importlib
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import agents
import httpx
import pytest
from agents.items import ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from test_action_consequence import environment
from test_bde_native import BDEModel, rules
from test_control_plane import FrozenSelectionExecutor
from test_cost_quotes import QuoteSDKModel, ReadyQuoteObserver, tool_response
from test_native_agents import MemorySink, benchmark_task, complete_verdict, ready_verdict
from test_native_predecision import SnapshotPhysical, SyntheticSDKModel
from test_sdk_api_meter import build_meter, usage

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.consequence_profiles import CostHistory
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.physical import PhysicalExecutionService
from infra_joint.control.provenance import PROFILE_MESSAGE_PREFIX
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.control.verification import OpenAIAgentsBlindVerifier
from infra_joint.experiments.recipient_audit import audit_effective_inputs
from infra_joint.experiments.sdk_api_meter import metered_sdk
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
formal = importlib.import_module("large_scale_execution_v1")


class HTTPMeasuredDelegate(agents.Model):
    def __init__(self, client: httpx.AsyncClient, delegate: agents.Model, identifier: str) -> None:
        self.client, self.delegate, self.identifier = client, delegate, identifier

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        # Raw provider counts deliberately differ from the synthetic SDK Usage.
        response = await self.client.post("https://synthetic.invalid/v1/chat/completions",
                                          json={"model": self.identifier})
        response.raise_for_status()
        return await self.delegate.get_response(*args, **kwargs)

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise AssertionError("frozen non-streaming path")
        yield  # pragma: no cover


class VerifierModel(SyntheticSDKModel):
    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        context = json.loads(kwargs["input"][0]["content"])
        self.inputs.append(context)
        verdict = complete_verdict() if context["phase"] == "synthesis" else ready_verdict()
        return tool_response(len(self.inputs), [
            ("submit_verification", verdict.model_dump(mode="json"))])


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["B0", "B1", "A", "B", "C", "D", "E"])
async def test_all_seven_frozen_native_variants_meter_manager_and_fixed_qwen_verifier(
    method: str,
) -> None:
    meter, writes = build_meter()
    task, registry = benchmark_task(), build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    execution = SnapshotPhysical("A")
    validator = SemanticActionValidator(task, registry, operations)
    gateway = RuntimeActionGateway(validator, execution)  # type: ignore[arg-type]
    physical = PhysicalExecutionService(registry, environment(),
                                        ReadyQuoteObserver(validator, execution),
                                        FrozenSelectionExecutor())  # type: ignore[arg-type]
    source = (BDEModel(method, query=method != "E") if method in {"B", "D", "E"}
              else QuoteSDKModel(execution) if method == "C" else SyntheticSDKModel())
    verifier_source = VerifierModel()
    sink = MemorySink()

    def transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": json.loads(request.content)["model"],
                                        "usage": usage(123)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), event_hooks={
        "request": [meter.request_hook], "response": [meter.response_hook],
    }) as client:
        model = HTTPMeasuredDelegate(client, source, "deepseek-v4-pro")
        verifier = OpenAIAgentsBlindVerifier(model=meter.model(
            HTTPMeasuredDelegate(client, verifier_source, "qwen3.8-max"),
            recipient="verifier", agent_name="blind_evidence_verifier",
            requested_model="qwen3.8-max"))
        runtime = formal.build_native_runtime(
            method, model=model, verifier=verifier,
            sdk=metered_sdk(agents, meter, manager_model="deepseek-v4-pro"),
            registry=registry, operations=operations, physical=physical,
            environment=environment(), history=CostHistory(), network="fast",
            rules=rules() if method == "E" else None,
        )
        result = await asyncio.wait_for(runtime.run(
            task, gateway, static_capabilities=build_static_capability_contract(
                environment(), registry, operations), trace=WorkflowTraceRecorder("meter", sink),
            profile_visibility=ProfileVisibility.AWARE if method == "B1"
            else ProfileVisibility.BLIND), timeout=5)
    assert result.final_answer == "A"
    assert not audit_effective_inputs(
        [event.model_dump(mode="json") for event in sink.events], method)["problems"]
    manager_receipts = [row for row in meter.receipts if row.recipient == "manager"]
    verifier_receipts = [row for row in meter.receipts if row.recipient == "verifier"]
    assert len(manager_receipts) == result.usage.manager_turns
    assert len(verifier_receipts) == result.usage.verifier_calls == 2
    assert all(row.cost.usage.input_tokens == 123 for row in meter.receipts)
    assert all(row.cost.usd_amount is not None for row in meter.receipts)
    assert all(row["requested_model"] == "qwen3.8-max" for (kind, _), row in writes.items()
               if kind == "usage" and row["recipient"] == "verifier")
    assert "cost_receipt" not in json.dumps(source.inputs)
    assert "usd_amount" not in json.dumps(source.inputs)
    for private in ("private-A", "private-model", "private-evaluator", "source_ref",
                    "evaluator_id", "cost_receipt", "usd_amount"):
        assert private not in json.dumps(verifier_source.inputs)
    if method == "B0":
        for feedback in (PROFILE_MESSAGE_PREFIX, "SPENT_COST_LEDGER", "cost_receipt",
                         "usd_amount", "network_class"):
            assert feedback not in json.dumps(source.inputs)
    assert (execution.snapshot_calls > 0) == (method == "B1")


@pytest.mark.asyncio
async def test_native_two_parallel_specialists_and_manager_continuation_are_all_metered() -> None:
    class TwoSpecialists(SyntheticSDKModel):
        def __init__(self) -> None:
            super().__init__()
            self.entered = 0
            self.release = asyncio.Event()
            self.manager_calls = 0

        async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
            items = kwargs["input"]
            self.inputs.append(items)
            assignment = next((json.loads(item["content"])["assignment"] for item in items
                               if item.get("role") == "user"
                               and isinstance(item.get("content"), str)
                               and item["content"].startswith('{"assignment"')), None)
            if assignment is not None:
                self.entered += 1
                if self.entered == 2:
                    self.release.set()
                await asyncio.wait_for(self.release.wait(), timeout=2)
                return ModelResponse(output=[ResponseOutputMessage(
                    id=f"note-{assignment['logical_agent_id']}", type="message",
                    role="assistant", status="completed", content=[ResponseOutputText(
                        type="output_text", text="Synthetic evidence is ready.", annotations=[])]
                )], usage=Usage(requests=1, input_tokens=0, output_tokens=0), response_id=None)
            self.manager_calls += 1
            if self.manager_calls == 1:
                return tool_response(1, [("consult_specialist", {
                    "logical_agent_id": name, "role": "evidence analyst",
                    "objective": "Inspect synthetic evidence.", "input_artifacts": ["source-0"],
                    "instruction": "Inspect the provided synthetic input.",
                }) for name in ("analyst-one", "analyst-two")])
            assert self.entered == 2
            return tool_response(2, [("invoke_model", {"inputs": ["source-0"],
                                                       "arguments": {"prompt": "Return A."}})])

    meter, _ = build_meter()
    task, registry = benchmark_task(), build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    source, verifier_source = TwoSpecialists(), VerifierModel()
    execution = SnapshotPhysical("A")
    gateway = RuntimeActionGateway(SemanticActionValidator(task, registry, operations),
                                   execution)  # type: ignore[arg-type]

    def transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": json.loads(request.content)["model"],
                                        "usage": usage(321)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), event_hooks={
        "request": [meter.request_hook], "response": [meter.response_hook],
    }) as client:
        verifier = OpenAIAgentsBlindVerifier(model=meter.model(
            HTTPMeasuredDelegate(client, verifier_source, "qwen3.8-max"),
            recipient="verifier", agent_name="blind_evidence_verifier",
            requested_model="qwen3.8-max"))
        runtime = OpenAIAgentsNativeRuntime(
            name="manager", instructions="Solve faithfully.",
            model=HTTPMeasuredDelegate(client, source, "deepseek-v4-pro"),
            sdk_module=metered_sdk(agents, meter, manager_model="deepseek-v4-pro"),
            registry=registry, available_operations=operations, blind_verifier=verifier,
            predecision_profiles=True, record_input_provenance=True,
        )
        result = await asyncio.wait_for(runtime.run(task, gateway), timeout=5)
    assert result.final_answer == "A" and result.usage.created_subagents == 2
    assert result.usage.peak_active_subagents == 2
    roles = meter.summary()["roles"]
    assert [roles[role]["calls"] for role in ("manager", "specialist", "verifier")] == [2, 2, 2]
    assert roles["all"]["calls"] == roles["all"]["known_usd_calls"] == 6
    assert all(row.cost.usage.input_tokens == 321 for row in meter.receipts)
    for forbidden in ("usd_amount", "cost_receipt", "private-evaluator", "physical_profile"):
        assert forbidden not in json.dumps(source.inputs)
