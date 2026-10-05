import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
analysis = importlib.import_module("large_scale_snapshot_v1")


def prepared(aid: str, kind: str) -> dict:
    return {"event_type": "logical.action.prepared", "payload": {
        "action": {"action_id": aid, "action_type": kind}}}


def execution(aid: str, latency: int) -> dict:
    return {"event_type": "physical.execution", "payload": {
        "action_id": aid, "execution": {"operator_latency_ms": latency, "transfers": []}}}


def test_operator_receipt_scope_separates_model_calls_without_e2e_subtraction():
    value = analysis.trace_cost_receipts([prepared("tool", "tool"), prepared("model", "model"),
        execution("tool", 7), execution("model", 150)])
    assert value["operator_successful_receipts_work_ms"] == 157  # Original scope preserved.
    assert value["successful_tool_execution_work_ms"] == 7
    assert value["complete_tool_execution_work_ms"] == 7
    assert value["successful_model_action_execution_work_ms"] == 150
    assert value["recorded_e2e_latency_ms"] is None


def test_unknown_execution_kind_does_not_become_complete_zero_tool_work():
    value = analysis.trace_cost_receipts([execution("unclassified", 150)])
    assert value["execution_kind_unknown_receipts"] == 1
    assert value["complete_tool_execution_work_ms"] is None


def test_failed_tool_execution_keeps_complete_operator_work_unknown():
    value = analysis.trace_cost_receipts([prepared("tool", "tool"),
        {"event_type": "physical.execution", "payload": {"action_id": "tool", "failure": {
            "stage": "execution", "duration_ms": 100}}}])
    assert value["successful_tool_execution_work_ms"] == 0
    assert value["complete_tool_execution_work_ms"] is None


def test_tool_selection_reject_and_model_failure_do_not_add_fabricated_operator_work():
    value = analysis.trace_cost_receipts([prepared("tool", "tool"), prepared("model", "model"),
        {"event_type": "physical.execution", "payload": {"action_id": "tool",
            "failure": {"stage": "selection"}}},
        {"event_type": "physical.execution", "payload": {"action_id": "model",
            "failure": {"stage": "execution", "duration_ms": 100}}}])
    assert value["complete_tool_execution_work_ms"] == 0
    assert value["successful_model_action_execution_work_ms"] == 0
    assert value["action_transfer_complete_bytes"] is None
