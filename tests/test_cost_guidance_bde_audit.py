import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("audit_cost_guidance_bde_v1")


def test_optional_card_exposure_must_precede_exact_executed_action() -> None:
    quote = {"quote_id": "q", "consequence": {"model_service": None}}
    action = {"action_id": "proposed", "operator": "bm25_retrieve", "inputs": [], "outputs": []}
    card = {"card_id": "q", "consequence": quote["consequence"], "advisory_only": True}
    events = [
        {"event_type": "logical.cost_quote.created", "payload": {"quote": quote, "action": action}},
        {"event_type": "logical.cost_card.returned", "payload": card},
        {"event_type": "logical.reasoning.input", "payload": {"logical_agent_id": "manager",
            "input_items": [{"type": "function_call_output", "output": json.dumps(card)}]}},
        {"event_type": "logical.action.selected", "payload": {"action_id": "executed"}},
        {"event_type": "logical.cost_card.matched", "payload": {"card_id": "q",
                                                                 "action_id": "executed"}},
        {"event_type": "logical.cost_quote.observed", "payload": {"quote_id": "q",
                                                                   "action_id": "proposed"}},
    ]
    value = audit.feedback_visibility(events)[0]
    assert value["exact_visible_before_action_selection"]
    assert value["matched_actual_action_id"] == "executed"
    # Same-batch or late feedback is not a pre-decision observation.
    events[2], events[3] = events[3], events[2]
    assert not audit.feedback_visibility(events)[0]["exact_visible_before_action_selection"]


def test_comparative_cards_are_proven_inside_real_sdk_function_result() -> None:
    quote = {"quote_id": "q", "consequence": {"model_service": None}}
    action = {"action_id": "proposal", "operator": "invoke_model", "inputs": [], "outputs": []}
    events = [
        {"event_type": "logical.cost_quote.created", "payload": {"quote": quote, "action": action}},
        {"event_type": "logical.reasoning.input", "payload": {"logical_agent_id": "manager",
            "input_items": [{"type": "function_call_output", "output": json.dumps({
                "comparison_id": "g", "candidates": [quote]})}]}},
    ]
    assert audit.feedback_visibility(events)[0]["exact_visible_after_creation"]
    events[1]["payload"]["input_items"][0]["output"] = "q was mentioned in text"
    assert not audit.feedback_visibility(events)[0]["exact_visible_after_creation"]
