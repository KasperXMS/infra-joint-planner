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


def test_failed_run_costs_use_persisted_receipts_not_timestamp_difference() -> None:
    events = [event("task.start", private="PRIVATE-TASK"),
              event("artifact.materialize.end", bytes_transferred=50, duration_ms=3),
              event("logical.action.prepared", action={"action_id": "ok"}),
              event("logical.action.prepared", action={"action_id": "reject"}),
              event("physical.execution", action_id="ok", execution={
                  "operator_latency_ms": 7, "output": "PRIVATE-BODY", "transfers": []}),
              event("physical.execution", action_id="reject", failure={"stage": "selection"}),
              event("run.failed", e2e_latency_ms=123, failure="PRIVATE-ERROR")]
    value = analysis.trace_cost_receipts(events)
    assert value["recorded_e2e_latency_ms"] == 123
    assert value["initial_completed_bytes"] == 50
    assert value["initial_completed_transfer_work_ms"] == 3
    assert value["action_transfer_complete_bytes"] == 0
    assert value["operator_successful_receipts_work_ms"] == 7
    assert not value["original_result_modified"]
    assert "PRIVATE" not in json.dumps(value)


@pytest.mark.parametrize("stage", ["execution", "unknown"])
def test_failed_execution_movement_is_unknown_not_successful_subtotal(stage: str) -> None:
    events = [event("physical.execution", action_id="ok", execution={
        "operator_latency_ms": 7, "transfers": [{"bytes_transferred": 100, "duration_ms": 8}]}),
        event("physical.execution", action_id="failed", failure={"stage": stage})]
    value = analysis.trace_cost_receipts(events)
    assert value["recorded_e2e_latency_ms"] is None
    assert value["action_transfer_successful_receipts_bytes"] == 100
    assert value["action_transfer_complete_bytes"] is None
    assert value["action_transfer_complete_work_ms"] is None


def test_missing_action_receipt_makes_complete_movement_unknown() -> None:
    value = analysis.trace_cost_receipts([
        event("logical.action.prepared", action={"action_id": "missing"})])
    assert value["prepared_without_physical_receipt"] == 1
    assert value["action_transfer_complete_bytes"] is None
    assert value["recorded_e2e_latency_ms"] is None


@pytest.mark.parametrize("bad", [None, True, -1, float("inf"), "123"])
def test_unmeasured_or_invalid_cost_receipts_are_unknown(bad: object) -> None:
    value = analysis.trace_cost_receipts([
        event("run.failed", e2e_latency_ms=bad),
        event("artifact.materialize.end", bytes_transferred=bad, duration_ms=bad)])
    assert value["recorded_e2e_latency_ms"] is None
    assert value["initial_completed_bytes"] is None
    assert value["initial_completed_transfer_work_ms"] is None


def test_multiple_endings_cannot_silently_select_a_favorable_timing() -> None:
    with pytest.raises(RuntimeError, match="multiple run endings"):
        analysis.trace_cost_receipts([event("run.end", e2e_latency_ms=100),
                                      event("run.failed", e2e_latency_ms=200)])


def test_duplicate_physical_receipt_is_not_double_charged() -> None:
    receipt = event("physical.execution", action_id="same", execution={"transfers": []})
    with pytest.raises(RuntimeError, match="duplicate physical receipt"):
        analysis.trace_cost_receipts([receipt, receipt])


def test_physical_receipt_without_execution_or_failure_is_unknown() -> None:
    value = analysis.trace_cost_receipts([event("physical.execution", action_id="missing-outcome")])
    assert value["unmeasured_execution_failures"] == 1
    assert value["action_transfer_complete_bytes"] is None


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


def test_classified_provider_failure_keeps_quality_usage_and_cost_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    result = {"execution_completed": False, "final_answer": None, "loop": None,
              "evaluation": None, "telemetry": None,
              "failure": {"code": "logical_loop_failed", "exception_type": "AgentLoopError"}}
    (run / "result.json").write_text(json.dumps(result))
    (run / "trace.jsonl").write_text("")
    (directory / "api-accounting.json").write_text(json.dumps({"roles": {
        "all": {"known_usd_subtotal": "0.1", "complete_usd_total": None}}}))
    admission = {"disposition": "valid", "result_sha256": provenance_sha256(result),
                 "failure_class": "provider_input_policy", "problems": []}
    monkeypatch.setattr(analysis, "effective_admission", lambda root, attempt: admission)
    attempt = SimpleNamespace(run_id="run", attempt_index=1, execution_sha256="b" * 64,
                              receipt_sha256=provenance_sha256(admission), disposition="valid",
                              reason="audited_provider_input_policy_failure")
    value = analysis.settled_attempt(tmp_path, "cell", attempt)
    assert value["provider_policy_failure"]
    assert value["benchmark_score"] is None and value["format_valid"] is None
    assert value["terminal_answer_sha256"] is None
    assert value["loop_usage"] is None and value["telemetry"] is None
    assert value["api_accounting"]["roles"]["all"]["complete_usd_total"] is None


def test_completion_membership_verifies_once_per_calculation_not_per_168_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = object.__new__(analysis.SnapshotAttemptLedger)
    ledger.cells = tuple(f"cell{i}" for i in range(168))
    reads = []
    valid = True

    def checked_attempts(self: object) -> tuple:
        reads.append(self)
        return (SimpleNamespace(cell_id="cell0", disposition="valid" if valid else None),)

    monkeypatch.setattr(analysis.ClassifiedAttemptLedger, "attempts", property(checked_attempts))
    assert ledger.completed_cells == ("cell0",)
    assert len(reads) == 1
    valid = False
    assert ledger.completed_cells == ()
    assert len(reads) == 2  # No persistent cache hides a changed admission.

    def failed_verification(self: object) -> tuple:
        raise RuntimeError("original adjudicated evidence drift")

    monkeypatch.setattr(analysis.ClassifiedAttemptLedger, "attempts",
                        property(failed_verification))
    with pytest.raises(RuntimeError, match="evidence drift"):
        _ = ledger.completed_cells


def test_snapshot_counts_use_one_verified_attempt_population(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = tmp_path / "preparation/task-freeze-002"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps({"phase1_schedule_sha256": "a" * 64}))
    (folder / "phase1-schedule.json").write_text(json.dumps([
        {"cell_id": f"cell{i}"} for i in range(168)]))
    (tmp_path / "phase1-attempts.jsonl").write_text("synthetic journal placeholder\n")
    attempts = tuple(SimpleNamespace(cell_id=f"cell{i}", run_id=f"run{i}",
                                     disposition=status, reason=reason)
                     for i, status, reason in [
                         (0, "valid", "audited_post_inference_model_json_failure"),
                         (1, "valid", "completed_or_valid_semantic_failure"),
                         (2, "confounder", "preserved"), (3, None, None)])
    reads = []

    class OnePopulation:
        def __init__(self, *args: object) -> None:
            pass

        @property
        def attempts(self) -> tuple:
            reads.append("effective")
            return attempts

        @property
        def original_attempts(self) -> tuple:
            reads.append("original")
            return (SimpleNamespace(disposition="confounder"),
                    SimpleNamespace(disposition="confounder"),
                    SimpleNamespace(disposition="valid"), SimpleNamespace(disposition=None))

    monkeypatch.setattr(analysis, "SnapshotAttemptLedger", OnePopulation)
    monkeypatch.setattr(analysis, "settled_attempt", lambda root, cell, attempt: {
        "run_id": attempt.run_id, "disposition": attempt.disposition})
    result = analysis.snapshot(tmp_path)
    assert reads == ["effective", "original"]
    assert result["scheduled_cells"] == 168
    assert result["admitted_cells"] == 2
    assert result["pending_count"] == result["confounded_attempts"] == 1
    assert result["original_confounded_attempts"] == 2
    assert result["adjudicated_attempts"] == 1
    assert result["provider_policy_adjudicated_attempts"] == 0
    assert not result["phase1_complete"] and not result["method_pruning_authorized"]


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
    attempt = SimpleNamespace(cell_id="cell", attempt_index=1, run_id="run",
                              execution_sha256="a" * 64,
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


@pytest.mark.parametrize(("code", "unknown"), [
    ("validation_failed", True), ("context_limit_exceeded", False),
])
def test_failed_model_work_is_unknown_unless_failure_proves_preflight(
    code: str, unknown: bool,
) -> None:
    events = [event("logical.model.outcome", succeeded=False,
                    physical_selection_succeeded=True, reached_model_inference=False,
                    failure_code=code),
              event("physical.execution", failure={"stage": "execution", "duration_ms": 25})]
    value = analysis.event_metrics(events)
    assert value["reported_reached_model_inference"] == 0
    assert not value["inference_flag_is_complete_measurement"]
    assert value["unmeasured_failed_model_outcomes"] == int(unknown)
    assert value["model_service_work_complete_total_ms"] == (None if unknown else 0)
    assert value["failed_physical_execution_work_ms"] == 25


@pytest.mark.parametrize("code", ["physical_execution_failed", "action_cancelled"])
def test_interrupted_model_without_physical_receipt_keeps_service_total_unknown(code: str) -> None:
    events = [event("logical.action.prepared", action={
        "action_id": "missing", "action_type": "model", "prompt": "PRIVATE-PROMPT"}),
        event("logical.observation", action_id="missing", succeeded=False,
              failure_code=code, failure_message="PRIVATE-ENDPOINT"),
        event("physical.execution", action_id="ok", execution={
            "operator": "invoke_model", "model_telemetry": {
                "service_latency_ms": 100, "input_tokens": 10, "output_tokens": 2}})]
    value = analysis.event_metrics(events)
    assert value["successful_inference_telemetry_count"] == 1
    assert value["model_service_work_ms"] == 100
    assert value["unmeasured_failed_model_outcomes"] == 1
    assert value["model_service_work_complete_total_ms"] is None
    assert "PRIVATE" not in json.dumps(value)


def test_model_failure_seen_in_both_outcome_and_observation_is_counted_once() -> None:
    events = [event("logical.action.prepared", action={
        "action_id": "failed", "action_type": "model"}),
        event("logical.model.outcome", action_id="failed", succeeded=False,
              physical_selection_succeeded=True, reached_model_inference=False,
              failure_code="validation_failed"),
        event("logical.observation", action_id="failed", succeeded=False,
              failure_code="validation_failed"),
        event("physical.execution", action_id="failed", failure={
            "stage": "execution", "duration_ms": 25})]
    value = analysis.event_metrics(events)
    assert value["unmeasured_failed_model_outcomes"] == 1
    assert value["model_service_work_complete_total_ms"] is None


@pytest.mark.parametrize("code", ["context_limit_exceeded", "unsupported_modality",
                                 "deployment_required"])
def test_missing_preflight_receipt_does_not_invent_inference_work(code: str) -> None:
    events = [event("logical.action.prepared", action={
        "action_id": "preflight", "action_type": "model"}),
        event("logical.observation", action_id="preflight", succeeded=False, failure_code=code)]
    value = analysis.event_metrics(events)
    assert value["unmeasured_failed_model_outcomes"] == 0
    assert value["model_service_work_complete_total_ms"] == 0


def test_selection_only_failure_proves_no_inference_without_model_outcome() -> None:
    events = [event("logical.action.prepared", action={
        "action_id": "selection", "action_type": "model"}),
        event("logical.observation", action_id="selection", succeeded=False,
              failure_code="physical_feasibility_failed"),
        event("physical.execution", action_id="selection", failure={
            "stage": "selection", "duration_ms": 1})]
    assert analysis.event_metrics(events)["model_service_work_complete_total_ms"] == 0


def test_tool_transport_failure_does_not_invent_unknown_model_work() -> None:
    events = [event("logical.action.prepared", action={
        "action_id": "tool", "action_type": "tool", "operator": "read_artifact"}),
        event("logical.observation", action_id="tool", succeeded=False,
              failure_code="physical_execution_failed")]
    assert analysis.event_metrics(events)["unmeasured_failed_model_outcomes"] == 0


def test_prepared_model_without_any_outcome_cannot_prove_zero_service_work() -> None:
    value = analysis.event_metrics([event("logical.action.prepared", action={
        "action_id": "unobserved", "action_type": "model"})])
    assert value["model_service_work_complete_total_ms"] is None
