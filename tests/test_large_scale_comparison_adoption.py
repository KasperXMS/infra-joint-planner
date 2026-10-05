import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from large_scale_comparison_adoption_audit_v1 import comparison_adoption_audit  # noqa: E402


def event(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"event_type": kind, "payload": payload}


def card(identifier: str, *, feasible: bool = True) -> dict[str, Any]:
    return {"quote_id": identifier, "action_sha256": "h", "consequence": {
        "physical_selection_succeeded": feasible, "model_service": {"source": "unknown"}}}


def response(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {"comparison_id": "c", "candidates": candidates, "selected_by_system": None,
            "quality_estimated": False, "next_step": "PRIVATE TASK TEXT"}


def visible(value: object, owner: str = "manager") -> dict[str, Any]:
    return event("logical.reasoning.input", {
        "logical_agent_id": owner, "input_items": [
            {"type": "function_call_output", "output": json.dumps(value)}]})


def quoted(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event("logical.cost_quote.created", {
        "quote": q, "action": {"prompt": "SECRET PROMPT", "arguments": {"query": "GOLD"}}})
        for q in candidates if "quote_id" in q]


def test_all_rejected_three_candidate_set_is_not_consequence_comparison() -> None:
    failure = {"succeeded": False, "failure_code": "phase_restricted", "message": "PRIVATE"}
    value = response([failure, failure, failure])
    audit = comparison_adoption_audit([
        event("logical.cost_candidates.returned", value), visible(value)])
    assert audit["submitted_candidate_counts"] == [3]
    assert audit["submitted_multi_candidate_sets"] == 1
    assert audit["multi_quote_consequence_comparisons"] == 0
    assert audit["multi_feasible_quote_comparisons"] == 0
    assert audit["sets_visible_before_choice"] == 1
    assert audit["executed_selected_quotes"] == 0
    assert audit["rows"][0]["returned_typed_failure_count"] == 3
    assert "PRIVATE" not in json.dumps(audit)


def test_nested_cards_visible_before_actual_selected_authorized_execution() -> None:
    candidates = [card("q1"), card("q2")]
    value = response(candidates)
    events = [*quoted(candidates), event("logical.cost_candidates.returned", value),
              visible(value), event("logical.cost_candidates.selected", {
                  "comparison_id": "c", "quote_id": "q2"}),
              event("logical.cost_quote.commit_authorized", {"quote_id": "q2"}),
              event("logical.cost_quote.observed", {"quote_id": "q2", "succeeded": True})]
    audit = comparison_adoption_audit(events)
    assert audit["multi_quote_consequence_comparisons"] == 1
    assert audit["multi_feasible_quote_comparisons"] == 1
    assert audit["sets_visible_before_choice"] == 1
    assert audit["executed_selected_quotes"] == audit["successful_selected_quotes"] == 1
    assert not audit["causal_benefit_proven"] and not audit["execution_or_admission_changed"]
    assert all(secret not in json.dumps(audit) for secret in ("PRIVATE", "SECRET", "GOLD"))


def test_single_valid_card_and_two_failures_is_not_multi_quote_comparison() -> None:
    candidates = [card("q"), {"succeeded": False}, {"succeeded": False}]
    audit = comparison_adoption_audit([
        *quoted(candidates), event("logical.cost_candidates.returned", response(candidates))])
    assert audit["submitted_multi_candidate_sets"] == 1
    assert audit["multi_quote_consequence_comparisons"] == 0
    assert audit["rows"][0]["exact_created_quote_card_count"] == 1


def test_two_selection_failure_cards_are_consequences_not_feasible_alternatives() -> None:
    candidates = [card("q1", feasible=False), card("q2", feasible=False)]
    audit = comparison_adoption_audit([
        *quoted(candidates), event("logical.cost_candidates.returned", response(candidates))])
    assert audit["multi_quote_consequence_comparisons"] == 1
    assert audit["multi_feasible_quote_comparisons"] == 0


def test_unknown_consequence_cards_do_not_become_costed_comparison() -> None:
    candidates = [{"quote_id": "q1", "consequence": None},
                  {"quote_id": "q2", "consequence": None}]
    audit = comparison_adoption_audit([
        *quoted(candidates), event("logical.cost_candidates.returned", response(candidates))])
    assert audit["rows"][0]["exact_created_quote_card_count"] == 2
    assert audit["rows"][0]["unknown_consequence_card_count"] == 2
    assert audit["multi_quote_consequence_comparisons"] == 0


@pytest.mark.parametrize("exposure", ["specialist", "after_choice", "modified", "mention"])
def test_visibility_requires_exact_root_tool_result_before_choice(exposure: str) -> None:
    candidates = [card("q1"), card("q2")]
    value = response(candidates)
    choice = event("logical.cost_candidates.selected", {"comparison_id": "c", "quote_id": "q1"})
    seen = visible(value)
    if exposure == "specialist":
        seen = visible(value, "specialist-1")
    elif exposure == "modified":
        seen = visible({**value, "next_step": "changed"})
    elif exposure == "mention":
        seen = visible("c")
    ending = [choice, seen] if exposure == "after_choice" else [seen, choice]
    audit = comparison_adoption_audit([
        *quoted(candidates), event("logical.cost_candidates.returned", value), *ending])
    assert audit["sets_visible_before_choice"] == 0
    assert audit["selected_member_quotes"] == 1
    assert audit["executed_selected_quotes"] == 0
    assert audit["rows"][0]["selected_quote_succeeded"] is None


def test_failed_execution_is_not_successful_adoption_and_absent_outcome_is_unknown() -> None:
    candidates = [card("q1"), card("q2")]
    events = [*quoted(candidates), event("logical.cost_candidates.returned", response(candidates)),
              event("logical.cost_candidates.selected", {"comparison_id": "c", "quote_id": "q1"}),
              event("logical.cost_quote.commit_authorized", {"quote_id": "q1"})]
    assert comparison_adoption_audit(events)["rows"][0]["selected_quote_succeeded"] is None
    events.append(event("logical.cost_quote.observed", {"quote_id": "q1", "succeeded": False}))
    audit = comparison_adoption_audit(events)
    assert audit["executed_selected_quotes"] == 1 and audit["successful_selected_quotes"] == 0


@pytest.mark.parametrize("defect", ["forged", "duplicate_card", "foreign_choice",
                                    "duplicate_response", "unordered_execution", "auto_winner",
                                    "quality_estimated", "orphan_observation"])
def test_corrupt_or_out_of_contract_comparison_receipts_fail_closed(defect: str) -> None:
    candidates = [card("q1"), card("q2")]
    value = deepcopy(response(candidates))
    events = quoted(candidates)
    if defect == "forged":
        value["candidates"][0]["action_sha256"] = "forged"
    elif defect == "duplicate_card":
        value["candidates"] = [candidates[0], candidates[0]]
    elif defect == "auto_winner":
        value["selected_by_system"] = "q1"
    elif defect == "quality_estimated":
        value["quality_estimated"] = True
    events.append(event("logical.cost_candidates.returned", value))
    if defect == "duplicate_response":
        events.append(event("logical.cost_candidates.returned", value))
    elif defect == "foreign_choice":
        events.append(event("logical.cost_candidates.selected", {
            "comparison_id": "c", "quote_id": "foreign"}))
    elif defect == "orphan_observation":
        events.append(event("logical.cost_quote.observed", {
            "quote_id": "foreign", "succeeded": True}))
    elif defect == "unordered_execution":
        events.extend([event("logical.cost_quote.commit_authorized", {"quote_id": "q1"}),
                       event("logical.cost_candidates.selected", {
                           "comparison_id": "c", "quote_id": "q1"}),
                       event("logical.cost_quote.observed", {
                           "quote_id": "q1", "succeeded": True})])
    with pytest.raises(ValueError):
        comparison_adoption_audit(events)
