import importlib
import json
import sys
from pathlib import Path

import pytest

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
