import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from cost_guidance_cell_analysis_v1 import (  # noqa: E402
    analyze,
    measured_sum,
    model_evidence_audit,
    profile_error,
    quote_decision_audit,
)


def test_usage_unknown_is_not_measured_zero_and_profiles_do_not_extrapolate() -> None:
    assert measured_sum([{"tokens": None}, {"tokens": 3}], "tokens") == {
        "observed_sum": 3, "measured_receipts": 1, "unknown_receipts": 1,
        "complete_total": None,
    }
    assert profile_error({"source": "unknown"}, 30)["p50_error_ms"] is None
    assert profile_error({"source": "empirical", "sample_count": 3,
                          "p50_ms": 20, "p90_ms": 25}, 30)["p50_error_ms"] == 10


def test_quote_accuracy_compares_work_not_joint_quantiles_or_wall_time() -> None:
    profile = {"source": "empirical", "sample_count": 3, "p50_ms": 20, "p90_ms": 30}
    consequence = {"operator": "invoke_model", "movement": {
        "configured_serialization_ms": 2, "empirical_transfer_receipts": [profile]},
        "model_service": profile, "context": {"envelope_fits": True}}
    events = [{"event_type": "logical.cost_quote.created", "payload": {
        "quote": {"quote_id": "q", "action_sha256": "h"}, "action": {}}},
        {"event_type": "logical.cost_quote.observed", "payload": {
            "quote_id": "q", "action_id": "a", "succeeded": True,
            "predicted_consequence": consequence, "predicted_transfer_bytes": 10,
            "actual_transfer_bytes": 10, "transfer_bytes_error": 0,
            "actual_transfer_work_ms": 22, "actual_model_service_ms": 40}},
        {"event_type": "physical.execution", "payload": {
            "action_id": "a", "execution": {"transfers": [
                {"duration_ms": 22, "bytes_transferred": 10}]}}}]
    result = analyze(events)["estimated_vs_observed"][0]
    assert result["transfer_p50_work_error_ms"] == 2
    assert result["model_service_error"]["p50_error_ms"] == 20
    assert result["context_preflight_prediction_match"] is True
    assert result["transfer_estimate_is_joint_quantile_or_wall_time"] is False
    events[-1]["payload"]["execution"]["transfers"] = []
    result = analyze(events)["estimated_vs_observed"][0]
    assert result["transfer_p50_work_error_ms"] is None
    assert result["transfer_prediction_error_unknown_reason"] is not None


def test_exact_quote_visibility_precedes_commit_without_exporting_semantic_bodies() -> None:
    import json

    quote = {"quote_id": "q", "action_sha256": "h", "consequence": {
        "operator": "invoke_model", "physical_selection_succeeded": False,
        "selection_failure_code": "context_limit_exceeded"}}
    action = {"action_id": "a", "action_type": "model", "prompt": "PRIVATE BODY",
              "inputs": ["evidence"], "outputs": [], "requirements": {
                  "min_context_tokens": 40000}}
    events = [
        {"event_type": "logical.cost_quote.created", "payload": {
            "quote": quote, "action": action}},
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": "manager", "decision_id": "turn2", "input_sha256": "inputh",
            "input_items": [{"type": "function_call_output", "output": json.dumps(quote)}]}},
        {"event_type": "logical.cost_quote.commit_authorized", "payload": {
            "quote_id": "q", "age_ms": 2}},
        {"event_type": "logical.cost_quote.observed", "payload": {
            "quote_id": "q", "succeeded": False, "failure_code": "context_limit_exceeded"}},
    ]
    row = quote_decision_audit(events)[0]
    assert row["exact_card_visible_before_decision"] is True
    assert row["manager_inputs_before_first_commit_or_discard"][0]["input_sha256"] == "inputh"
    assert row["committed_despite_known_selection_failure"] is True
    assert row["state"] == "consumed"  # Consumption is not inference success.
    assert row["execution_succeeded"] is False
    assert row["visibility_proves_causal_use"] is False
    assert row["action"]["prompt_bytes"] == 12
    assert "PRIVATE BODY" not in repr(row)


def test_quote_id_mentions_altered_cards_children_and_late_inputs_do_not_prove_visibility() -> None:
    import json

    quote = {"quote_id": "q", "action_sha256": "h", "consequence": {"movement": 100}}
    created = {"event_type": "logical.cost_quote.created", "payload": {
        "quote": quote, "action": {}}}
    inputs = [
        ("manager", {"role": "assistant", "content": "quote q"}),
        ("manager", {"type": "function_call_output", "output": json.dumps({"quote_id": "q"})}),
        ("manager", {"type": "function_call_output", "output": json.dumps({
            **quote, "consequence": {"movement": 0}})}),
        ("specialist", {"type": "function_call_output", "output": json.dumps(quote)}),
    ]
    events = [created] + [
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": owner, "input_items": [item]}} for owner, item in inputs]
    events += [
        {"event_type": "logical.cost_quote.discarded", "payload": {"quote_id": "q"}},
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": "manager", "input_items": [
                {"type": "function_call_output", "output": json.dumps(quote)}]}},
    ]
    row = quote_decision_audit(events)[0]
    assert row["state"] == "discarded"
    assert row["exact_card_visible_before_decision"] is False
    assert row["manager_inputs_before_first_commit_or_discard"] == []


def test_uncommitted_quote_remains_pending_and_duplicate_receipts_fail_closed() -> None:
    import pytest

    event = {"event_type": "logical.cost_quote.created", "payload": {
        "quote": {"quote_id": "q", "action_sha256": "h"}, "action": {}}}
    row = quote_decision_audit([event])[0]
    assert row["state"] == "pending"
    assert row["execution_succeeded"] is None
    with pytest.raises(ValueError, match="duplicate created quote"):
        quote_decision_audit([event, event])
    with pytest.raises(ValueError, match="no creation receipt"):
        quote_decision_audit([{
            "event_type": "logical.cost_quote.discarded", "payload": {"quote_id": "q"}}])


def test_prompt_only_terminal_is_not_called_artifact_reduction_or_grounded_quality() -> None:
    events = [
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "retrieval", "operator": "bm25_retrieve", "inputs": ["corpus"],
            "outputs": [{"artifact_id": "evidence"}]}}},
        {"event_type": "logical.observation", "payload": {
            "action_id": "retrieval", "succeeded": True}},
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "model", "action_type": "model", "prompt": "PRIVATE QUESTION",
            "inputs": [], "outputs": []}}},
        {"event_type": "logical.model.outcome", "payload": {
            "action_id": "model", "reached_model_inference": True}},
        {"event_type": "logical.observation", "payload": {
            "action_id": "model", "succeeded": True}},
        {"event_type": "logical.terminal.candidate_selected", "payload": {
            "source_action_id": "model"}},
    ]
    result = model_evidence_audit(events)
    assert result["terminal_model_has_artifact_inputs"] is False
    assert result["successful_inference_artifact_input_count"] == 0
    assert result["successful_read_artifact_action_ids"] == []
    assert result["counts_establish_semantic_adequacy"] is False
    assert "PRIVATE QUESTION" not in repr(result)
    events[2]["payload"]["action"]["inputs"] = ["evidence"]
    result = model_evidence_audit(events)
    assert result["terminal_model_has_artifact_inputs"] is True
    assert result["successful_inference_artifact_input_count"] == 1
    events = [e for e in events if e["event_type"] != "logical.model.outcome"]
    result = model_evidence_audit(events)
    assert result["successful_inference_artifact_input_count"] is None
    assert result["successful_inferences_missing_outcome_receipts"] == ["model"]


def test_failed_context_attempt_is_not_successful_evidence_inference() -> None:
    events = [
        {"event_type": "logical.action.prepared", "payload": {"action": {
            "action_id": "rejected", "action_type": "model", "inputs": ["corpus"]}}},
        {"event_type": "logical.model.outcome", "payload": {
            "action_id": "rejected", "reached_model_inference": False}},
        {"event_type": "logical.observation", "payload": {
            "action_id": "rejected", "succeeded": False}},
    ]
    result = model_evidence_audit(events)
    assert result["successful_inferences"] == []
    assert result["terminal_model_has_artifact_inputs"] is None
