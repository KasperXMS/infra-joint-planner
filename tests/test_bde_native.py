import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from agents.items import ModelResponse
from test_action_consequence import environment
from test_control_plane import FrozenSelectionExecutor
from test_cost_quotes import ReadyQuoteObserver, tool_response
from test_native_agents import (
    FakePhysicalService,
    FakeVerifier,
    MemorySink,
    benchmark_task,
    complete_verdict,
    ready_verdict,
)
from test_native_predecision import SyntheticSDKModel

from infra_joint.control.bde_native import RULE_PREFIX, BDENativeRuntime, contains_bde_feedback
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.consequence_profiles import CostHistory
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.cost_rules import CostRuleSet, anonymized_cost_trace, validate_rule_set
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.loop import AgentLoopError
from infra_joint.control.physical import PhysicalExecutionService
from infra_joint.control.provenance import semantic_input_items
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder


def rules() -> dict[str, Any]:
    return {"rules": [{"rule_id": "bounded-cost", "principle": "Query uncertain movement costs.",
                      "scope": "Only materialized inputs", "support_examples": ["a"],
                      "counterexamples": ["b"], "overfit_risk": "Unknown semantic adequacy"}]}


class BDEModel(SyntheticSDKModel):
    def __init__(self, route: str, query: bool = True) -> None:
        super().__init__()
        self.route, self.query = route, query

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        items = semantic_input_items(kwargs.get("input", args[1] if len(args) > 1 else []))
        self.inputs.append(items)
        index = len(self.inputs)
        outputs = [json.loads(i["output"]) for i in items
                   if i.get("type") == "function_call_output"]
        request = {"inputs": ["source-0"], "arguments": {"query": "evidence", "top_k": 1,
                   "output_artifact_id": "evidence"}}
        if self.route == "D":
            if index == 1:
                calls = [("compare_ready_actions", {"candidates": [
                    {"operator": "bm25_retrieve", "payload": request},
                    {"operator": "bm25_retrieve", "payload": {
                        **request, "arguments": {**request["arguments"], "top_k": 2,
                                                 "output_artifact_id": "alternative"}}}]})]
            elif index == 2:
                comparison = outputs[-1]
                assert comparison["selected_by_system"] is None
                calls = [("commit_quote", {"quote_id": comparison["candidates"][0]["quote_id"]})]
            elif index == 3:
                evidence = outputs[-1]["produced_information"][0]["artifact_id"]
                calls = [("invoke_model", {"inputs": [evidence],
                                           "arguments": {"prompt": "Return A."}})]
            else:
                calls = [("commit_quote", {"quote_id": outputs[-1]["quote_id"]})]
        else:
            if self.route == "E":
                assert any(RULE_PREFIX in str(i) for i in items)
            if index == 1 and self.query:
                calls = [("estimate_bm25_retrieve", request)]
            elif index == 1 or (index == 2 and self.query):
                calls = [("bm25_retrieve", request)]
            else:
                evidence = outputs[-1]["produced_information"][0]["artifact_id"]
                calls = [("invoke_model", {"inputs": [evidence],
                                           "arguments": {"prompt": "Return A."}})]
        return tool_response(index, calls)


@pytest.mark.asyncio
@pytest.mark.parametrize(("route", "query"), [("B", False), ("B", True), ("D", True),
                                             ("E", True)])
async def test_bde_actual_sdk_execution_and_cost_isolation(route: str, query: bool) -> None:
    task, registry = benchmark_task(), build_operator_catalog()
    operations = ("bm25_retrieve", "invoke_model")
    execution = FakePhysicalService()
    validator = SemanticActionValidator(task, registry, operations)
    gateway = RuntimeActionGateway(validator, execution)  # type: ignore[arg-type]
    unused = FrozenSelectionExecutor()
    physical = PhysicalExecutionService(registry, environment(),
                                        ReadyQuoteObserver(validator, execution),
                                        unused)  # type: ignore[arg-type]
    sink, model = MemorySink(), BDEModel(route, query)
    verifier = FakeVerifier((ready_verdict(), complete_verdict()))
    runtime = BDENativeRuntime(
        route=route, rules=rules() if route == "E" else None,
        physical=physical, environment=environment(), cost_history=CostHistory(),
        network_category="fast", reachable_workers=frozenset({"private-A"}),
        name="manager", instructions="Solve faithfully.", model=model, registry=registry,
        available_operations=operations, blind_verifier=verifier, record_input_provenance=True,
    )
    result = await asyncio.wait_for(runtime.run(
        task, gateway, static_capabilities=build_static_capability_contract(
            environment(), registry, operations), trace=WorkflowTraceRecorder("bde-sdk", sink),
        profile_visibility=ProfileVisibility.BLIND), timeout=5)
    assert result.final_answer == "A" and len(execution.actions) == 2
    assert unused.decisions == [] and result.usage.verifier_calls == 2
    assert result.usage.tool_model_calls == 2
    assert result.usage.manager_turns == (4 if route == "D" else 2 + int(query))
    for forbidden in ("private-A", "private-model", "private-evaluator", "source_ref"):
        assert forbidden not in json.dumps(model.inputs)
    assert not contains_bde_feedback([v.model_dump(mode="json") for v in verifier.contexts])
    if route in {"B", "E"}:
        matched = [e for e in sink.events if e.event_type == "logical.cost_card.matched"]
        assert len(matched) == int(query)
        assert not any(e.event_type == "logical.cost_quote.commit_authorized" for e in sink.events)
    else:
        assert len([e for e in sink.events if e.event_type == "logical.cost_quote.discarded"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("candidates", [[], [{}] * 4, [
    {"operator": "bm25_retrieve", "payload": {"inputs": ["source-0"], "arguments": {}}},
    {"operator": "invoke_model", "payload": {"inputs": ["not-materialized"], "arguments": {}}},
]])
async def test_comparison_rejects_invalid_count_or_dependency_before_any_quote(
    candidates: list[dict[str, Any]],
) -> None:
    runtime = BDENativeRuntime(route="D", environment=environment(), cost_history=CostHistory(),
                              network_category="fast", reachable_workers=frozenset(),
                              name="manager", instructions="Frozen", model=None,
                              registry=build_operator_catalog(),
                              available_operations=("bm25_retrieve", "invoke_model"))
    state = SimpleNamespace(root_agent=SimpleNamespace(logical_agent_id="manager"),
                            accessible={"manager": {"source-0"}}, emit=lambda *args: None)
    value = json.loads(await runtime._compare(  # type: ignore[arg-type]  # noqa: SLF001
        state, SimpleNamespace(tool_call_id="compare"), json.dumps({"candidates": candidates})))
    assert value["failure_code"] == "invalid_ready_candidates"


@pytest.mark.asyncio
@pytest.mark.parametrize("feedback", [{"card_id": "x", "consequence": {}},
                                      {"comparison_id": "x", "candidates": []}, RULE_PREFIX])
async def test_bde_child_input_cost_feedback_failclosed(feedback: object) -> None:
    sdk = SimpleNamespace(RunConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    state = SimpleNamespace(visibility=ProfileVisibility.BLIND,
                            root_agent=SimpleNamespace(logical_agent_id="manager"))
    config = BDENativeRuntime._predecision_run_config(sdk, state)  # type: ignore[arg-type]
    data = SimpleNamespace(agent=SimpleNamespace(name="bounded_specialist"),
                           model_data=SimpleNamespace(input=[{"type": "function_call_output",
                                                            "output": json.dumps(feedback)}],
                                                      instructions="Frozen"))
    with pytest.raises(AgentLoopError, match="isolation"):
        await config.call_model_input_filter(data)


def test_rule_support_counterexample_and_private_metadata_contract() -> None:
    parsed = CostRuleSet.model_validate(rules())
    validate_rule_set(parsed, [{"example_id": "a"}, {"example_id": "b"}])
    with pytest.raises(ValueError, match="unavailable"):
        validate_rule_set(parsed, [{"example_id": "a"}])
    private = parsed.model_copy(update={"rules": (parsed.rules[0].model_copy(
        update={"principle": "Use A28 for MultiHop."}),)})
    with pytest.raises(ValueError, match="identifiers"):
        validate_rule_set(private, [{"example_id": "a"}, {"example_id": "b"}])


def test_distillation_allowlist_does_not_export_task_queries_answers_or_locations() -> None:
    events = [{"event_type": "logical.action.prepared", "payload": {"action": {
        "action_id": "secret", "operator": "bm25_retrieve", "inputs": ["corpus"],
        "outputs": [], "arguments": {"query": "private question"}}}},
        {"event_type": "physical.execution", "payload": {"action_id": "secret", "execution": {
            "agent_ids": ["private-worker"], "operator_latency_ms": 2,
            "answer": "private answer", "transfers": []}}}]
    result = anonymized_cost_trace(events, "private-task-id")
    assert result["events"][0]["operator"] == "bm25_retrieve"
    assert "private" not in json.dumps(result)
