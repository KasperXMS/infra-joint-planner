import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from large_scale_optional_card_adoption_audit_v1 import (  # noqa: E402
    optional_card_adoption_audit,
    semantic_payload,
)

from infra_joint.control.provenance import provenance_sha256


def event(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"event_type": kind, "payload": payload}


def trajectory(*, succeeded: bool = True) -> list[dict[str, Any]]:
    action = {"action_id": "manager:estimate-call", "owner_agent_id": "manager",
              "operator": "aggregate_artifacts", "inputs": ["a", "b"],
              "arguments": {"query": "PRIVATE QUERY"}, "prompt": "PRIVATE PROMPT"}
    consequence = {"physical_selection_succeeded": True,
                   "transfer": {"source": "unknown", "latency_ms": None}}
    quote = {"quote_id": "card", "consequence": consequence}
    card = {"card_id": "card", "consequence": consequence, "advisory_only": True,
            "query_latency_ms": 1, "next_step": "PRIVATE MESSAGE"}
    executed = {**action, "action_id": "manager:execution-call"}
    return [
        event("logical.cost_quote.created", {"quote": quote, "action": action}),
        event("logical.cost_card.returned", card),
        event("logical.reasoning.input", {"logical_agent_id": "manager", "input_items": [
            {"type": "function_call_output", "call_id": "estimate-call",
             "output": json.dumps(card)}]}),
        event("logical.action.prepared", {"action": executed}),
        event("logical.cost_card.matched", {"card_id": "card", "action_id": executed["action_id"],
              "exact_semantic_fingerprint": provenance_sha256(semantic_payload(executed))}),
        # The legacy quote outcome references the proposal, not the executed SDK ID.
        event("logical.cost_quote.observed", {"quote_id": "card",
              "action_id": action["action_id"], "succeeded": succeeded}),
        event("logical.observation", {"action_id": executed["action_id"],
              "succeeded": succeeded}),
        # Real runtime emits physical completion metadata after the match event.
        event("physical.execution", {"action_id": executed["action_id"],
              "execution": {} if succeeded else None,
              "failure": None if succeeded else {"failure_code": "context_limit_exceeded"}}),
    ]


def test_different_proposal_execution_ids_link_through_actual_match() -> None:
    result = optional_card_adoption_audit(trajectory())
    assert result["valid_returned_cards"] == result["cards_visible_before_execution"] == 1
    assert result["exact_execution_matches"] == result["successful_matched_executions"] == 1
    assert result["rows"][0]["proposal_action_id"] != result["rows"][0]["execution_action_id"]
    assert not result["unknown_profiles_imputed"] and not result["causal_benefit_proven"]
    assert "PRIVATE" not in json.dumps(result)


def test_visible_unexecuted_card_is_not_action_adoption_or_quality_improvement() -> None:
    result = optional_card_adoption_audit(trajectory()[:3])
    assert result["valid_returned_cards"] == result["cards_visible_before_execution"] == 1
    assert result["exact_execution_matches"] == 0
    assert result["rows"][0]["matched_execution_succeeded"] is None


def test_failed_matched_execution_does_not_become_success() -> None:
    result = optional_card_adoption_audit(trajectory(succeeded=False))
    assert result["exact_execution_matches"] == 1
    assert result["successful_matched_executions"] == 0
    assert result["rows"][0]["matched_execution_succeeded"] is False


@pytest.mark.parametrize("visibility", ["specialist", "wrong_call", "modified", "mention",
                                        "late", "unstructured"])
def test_visibility_requires_exact_root_result_before_action(visibility: str) -> None:
    events = trajectory()
    seen = events[2]["payload"]
    if visibility == "specialist":
        seen["logical_agent_id"] = "specialist"
    elif visibility == "wrong_call":
        seen["input_items"][0]["call_id"] = "other"
    elif visibility == "modified":
        seen["input_items"][0]["output"] = json.dumps({"card_id": "card"})
    elif visibility == "mention":
        seen["input_items"][0]["type"] = "message"
    elif visibility == "unstructured":
        seen["input_items"][0]["output"] = "card"
    else:
        events.append(events.pop(2))
    result = optional_card_adoption_audit(events)
    assert result["cards_visible_before_execution"] == 0
    assert result["exact_execution_matches"] == 1


@pytest.mark.parametrize("defect", ["duplicate_card", "duplicate_match", "orphan_card",
                                    "orphan_match", "fingerprint", "changed_action",
                                    "wrong_outcome_id", "wrong_success", "missing_physical",
                                    "missing_logical", "unknown_success", "unmatched_outcome",
                                    "non_advisory", "forged_consequence", "order"])
def test_inconsistent_proof_fails_closed(defect: str) -> None:
    events = deepcopy(trajectory())
    if defect == "duplicate_card":
        events.append(events[1])
    elif defect == "duplicate_match":
        events.append(events[4])
    elif defect == "orphan_card":
        events.pop(0)
    elif defect == "orphan_match":
        events.pop(1)
    elif defect == "fingerprint":
        events[4]["payload"]["exact_semantic_fingerprint"] = "wrong"
    elif defect == "changed_action":
        events[3]["payload"]["action"]["inputs"].reverse()
    elif defect == "wrong_outcome_id":
        events[5]["payload"]["action_id"] = "manager:execution-call"
    elif defect == "wrong_success":
        events[5]["payload"]["succeeded"] = False
    elif defect == "missing_physical":
        events.pop(7)
    elif defect == "missing_logical":
        events.pop(6)
    elif defect == "unknown_success":
        events[5]["payload"]["succeeded"] = events[6]["payload"]["succeeded"] = None
    elif defect == "unmatched_outcome":
        events.pop(4)
    elif defect == "non_advisory":
        events[1]["payload"]["advisory_only"] = False
    elif defect == "forged_consequence":
        events[1]["payload"]["consequence"] = {"physical_selection_succeeded": False}
    else:
        events[0], events[1] = events[1], events[0]
    with pytest.raises(ValueError):
        optional_card_adoption_audit(events)


def test_no_optional_cards_does_not_invent_queries() -> None:
    result = optional_card_adoption_audit([])
    assert result["valid_returned_cards"] == result["exact_execution_matches"] == 0
    assert not result["raw_query_attempts_counted_here"]
