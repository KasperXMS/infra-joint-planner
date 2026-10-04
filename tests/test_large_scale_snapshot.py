import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
analysis = importlib.import_module("large_scale_snapshot_v1")


def event(kind: str, **payload: object) -> dict:
    return {"event_type": kind, "payload": payload}


def test_missing_measurement_remains_unknown_not_zero() -> None:
    assert analysis.measured_total([]) == 0
    assert analysis.measured_total([2, 3]) == 5
    assert analysis.measured_total([2, None]) is None
    assert analysis.measured_total([False]) is None


def test_model_preflight_reject_is_not_counted_as_actual_inference() -> None:
    events = [
        event("logical.action.prepared", action={"action_id": "a", "action_type": "model"}),
        event("logical.model.outcome", reached_model_inference=False),
        event("logical.observation", action_id="a", succeeded=False,
              failure_code="context_limit_exceeded"),
    ]
    result = analysis.event_metrics(events)
    assert result["prepared_model_actions"] == 1
    assert result["reported_reached_model_inference"] == 0
    assert result["successful_inference_telemetry_count"] == 0
    assert result["failure_codes"] == {"context_limit_exceeded": 1}


def test_inference_unknown_tokens_are_preserved_and_wrapper_latency_not_added() -> None:
    events = [event("physical.execution", execution={
        "operator": "invoke_model", "operator_latency_ms": 150,
        "model_telemetry": {"service_latency_ms": 100, "input_tokens": None,
                            "output_tokens": 3, "finish_reason": "stop"}})]
    result = analysis.event_metrics(events)
    assert result["model_service_work_ms"] == 100
    assert result["physical_model_input_tokens"] is None
    assert result["physical_model_output_tokens"] == 3
    assert result["successful_tool_executions"] == 0


def test_sdk_history_deduplicates_queries_and_one_candidate_is_not_real_comparison() -> None:
    item = {"type": "function_call", "call_id": "q", "name": "estimate_bm25_retrieve"}
    events = [event("logical.reasoning.input", logical_agent_id="manager", input_items=[item]),
              event("logical.reasoning.input", logical_agent_id="manager", input_items=[item]),
              event("logical.cost_candidates.returned", candidates=[{"opaque": "private"}])]
    result = analysis.event_metrics(events)["method_interface"]
    assert result["optional_query_attempts_lower_bound"] == 1
    assert result["candidate_counts"] == [1]
    assert result["real_multi_candidate_comparisons"] == 0
    assert "private" not in json.dumps(result)


def test_private_prompt_outputs_and_inputs_are_not_exported_by_event_metrics() -> None:
    secret = "PRIVATE-CORPUS-QUESTION-GOLD"
    events = [event("logical.action.prepared", action={
        "action_type": "model", "action_id": "safe-id", "prompt": secret, "inputs": [secret]}),
        event("logical.observation", action_id="safe-id", succeeded=True, output=secret),
        event("logical.reasoning.input", logical_agent_id="manager", input_items=[{
            "type": "message", "content": secret}]),
        event("logical.subagent.start", instruction=secret, objective=secret)]
    assert secret not in json.dumps(analysis.event_metrics(events))


def test_read_only_snapshot_does_not_initialize_missing_ledger(tmp_path: Path) -> None:
    folder = tmp_path / "preparation/task-freeze-002"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps({"phase1_schedule_sha256": "a" * 64}))
    (folder / "phase1-schedule.json").write_text('[{"cell_id":"synthetic"}]')
    with pytest.raises(RuntimeError, match="cannot initialize"):
        analysis.snapshot(tmp_path)
    assert not (tmp_path / "phase1-attempts.jsonl").exists()


def test_settled_result_uses_admissions_canonical_hash_not_formatted_file_hash(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    result = {"execution_completed": True, "final_answer": "synthetic answer", "loop": None,
              "evaluation": {"benchmark_score": 0.0, "format_valid": True}}
    path = run / "result.json"
    path.write_text(json.dumps(result, indent=4))
    (run / "trace.jsonl").write_text("")
    admission = {"disposition": "valid", "result_sha256": provenance_sha256(result)}
    (directory / "admission.json").write_text(json.dumps(admission))
    attempt = SimpleNamespace(attempt_index=1, run_id="run", execution_sha256="a" * 64,
                              receipt_sha256=provenance_sha256(admission),
                              disposition="valid", reason="passed")
    value = analysis.settled_attempt(tmp_path, "cell", attempt)
    assert value["benchmark_score"] == 0.0 and value["execution_completed"]
    assert "synthetic answer" not in json.dumps(value)
    result["final_answer"] = "tampered"
    path.write_text(json.dumps(result))
    with pytest.raises(RuntimeError, match="result/admission drift"):
        analysis.settled_attempt(tmp_path, "cell", attempt)


def test_eligible_decisions_use_ready_frontier_not_all_reasoning_turns() -> None:
    events = [
        event("logical.reasoning.started", logical_agent_id="manager", decision_id="d1"),
        event("logical.batch.validation", logical_agent_id="manager", decision_id="d1",
              status="rejected", all_inputs_materialized=False),
        event("logical.reasoning.started", logical_agent_id="manager", decision_id="d2"),
        event("logical.batch.validation", logical_agent_id="manager", decision_id="d2",
              status="accepted", all_inputs_materialized=True),
        # Multiple ready actions in the same decision count as one opportunity.
        event("logical.batch.validation", logical_agent_id="manager", decision_id="d2",
              status="accepted", all_inputs_materialized=True),
        event("logical.reasoning.started", logical_agent_id="manager", decision_id="d3"),
        event("logical.cost_quote.created", action={"owner_agent_id": "manager"},
              quote={"quote_id": "q1"}),
        event("logical.cost_card.returned", card_id="q1"),
        event("logical.reasoning.started", logical_agent_id="manager", decision_id="finish"),
    ]
    result = analysis.event_metrics(events)["method_interface"]
    assert result["eligible_high_impact_decisions"] == 2
    assert result["valid_optional_query_decisions"] == 1
    assert result["valid_query_adoption_rate"] == 0.5
    assert analysis.event_metrics([])["method_interface"]["valid_query_adoption_rate"] is None


def test_quote_states_and_authorization_are_distinct_from_execution_and_causal_revision() -> None:
    events = [event("logical.cost_quote.commit_authorized", quote_id="q"),
              event("logical.cost_quote.discarded", quote_id="not-chosen"),
              event("logical.cost_quote.run.end", proposal_attempts=4,
                    quote_states={"authorized": 1, "discarded": 1, "pending": 2})]
    result = analysis.event_metrics(events)["method_interface"]
    assert result["commits_authorized"] == 1
    assert result["quotes_observed"] == 0
    assert result["quote_final_states"]["pending"] == 2
    assert result["quote_induced_revision_rate"] is None


def test_raw_function_receipts_capture_last_turn_without_exporting_arguments(
    tmp_path: Path,
) -> None:
    (tmp_path / "id-usage.json").write_text(json.dumps({
        "recipient": "manager", "call_id": "id", "status": 200,
        "started_utc": "2026-10-05T01:00:00+00:00"}))
    (tmp_path / "id-request.json").write_text(json.dumps({"tools": [
        {"function": {"name": "estimate_bm25_retrieve"}}]}))
    (tmp_path / "id-response.json").write_text(json.dumps({"choices": [{"message": {
        "content": "PRIVATE-ANSWER", "tool_calls": [{"function": {
            "name": "estimate_bm25_retrieve", "arguments": "PRIVATE-QUERY"}}]}}]}))
    events = [event("logical.reasoning.started", logical_agent_id="manager", decision_id="d")]
    events[0]["timestamp"] = "2026-10-05T01:00:00Z"
    value = analysis.root_function_receipts(tmp_path, events)
    assert value["optional_query_attempts"] == 1
    assert value["optional_query_decision_ids"] == ["d"]
    assert value["manager_requests_with_optional_query_interface"] == 1
    assert "PRIVATE" not in json.dumps(value)


def test_raw_function_receipts_separate_specialists_and_unknown_manager_responses(
    tmp_path: Path,
) -> None:
    (tmp_path / "s-usage.json").write_text(json.dumps({"recipient": "specialist"}))
    (tmp_path / "m-usage.json").write_text(json.dumps({
        "recipient": "manager", "call_id": "m", "status": 500}))
    value = analysis.root_function_receipts(tmp_path, [])
    assert value["unknown_manager_responses"] == 1
    assert value["optional_query_attempts"] == 0


def test_sdk_failure_receipts_include_nonphysical_specialist_reject_and_deduplicate() -> None:
    item = {"type": "function_call_output", "call_id": "rejected-specialist",
            "output": json.dumps({"succeeded": False, "failure_code": "phase_restricted",
                                  "failure_message": "PRIVATE-INSTRUCTION"})}
    events = [event("logical.reasoning.input", logical_agent_id="manager", input_items=[item]),
              event("logical.reasoning.input", logical_agent_id="manager", input_items=[item])]
    value = analysis.event_metrics(events)
    assert value["sdk_function_failure_receipts_lower_bound"] == {"phase_restricted": 1}
    assert value["prepared_physical_actions"] == 0
    assert value["successful_inference_telemetry_count"] == 0
    assert "PRIVATE" not in json.dumps(value)


def test_sdk_function_failure_analysis_does_not_treat_artifact_body_as_tool_failure() -> None:
    item = {"type": "function_call_output", "call_id": "read",
            "output": json.dumps({"succeeded": True, "output": {
                "succeeded": False, "failure_code": "private-document-text"}})}
    events = [event("logical.reasoning.input", logical_agent_id="manager", input_items=[item])]
    assert analysis.event_metrics(events)["sdk_function_failure_receipts_lower_bound"] == {}


def test_sdk_failure_ids_are_scoped_by_logical_recipient() -> None:
    item = {"type": "function_call_output", "call_id": "same-id",
            "output": '{"succeeded":false,"failure_code":"semantic_validation_failed"}'}
    events = [event("logical.reasoning.input", logical_agent_id=owner, input_items=[item])
              for owner in ("manager", "specialist-1")]
    assert analysis.event_metrics(events)["sdk_function_failure_receipts_lower_bound"] == {
        "semantic_validation_failed": 2}
