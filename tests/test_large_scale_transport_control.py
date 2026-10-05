import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
control = importlib.import_module("large_scale_transport_control_v1")


def proof_events() -> list[dict]:
    return [{"event_type": "logical.action.prepared", "payload": {"action": {
        "action_id": "failed-model", "action_type": "model", "prompt": "PRIVATE-PROMPT"}}},
        {"event_type": "logical.observation", "payload": {"action_id": "failed-model",
            "succeeded": False, "failure_code": "physical_execution_failed",
            "failure_message": "unrecoverable physical execution error: ReadTimeout"}},
        {"event_type": "action.completed", "payload": {
            "action_id": "failed-model", "succeeded": False}},
        {"event_type": "workflow.graph.snapshot", "payload": {
            "nodes": [{"action_id": "failed-model", "status": "failed"}]}}]


def test_exact_transport_proof_exports_only_closed_action_metadata() -> None:
    value = control.interrupted_model_proof(proof_events())
    assert value["interrupted_model_actions"] == ["failed-model"]
    assert value["missing_physical_receipts"] == 1
    assert value["inference_status"] == "unknown"
    assert "PRIVATE" not in json.dumps(value)


@pytest.mark.parametrize("mutation", ["not_model", "has_receipt", "wrong_error", "no_closure",
                                     "running_graph", "duplicate_failure", "no_failure"])
def test_transport_proof_cannot_waive_unrelated_or_unclosed_actions(mutation: str) -> None:
    events = proof_events()
    if mutation == "not_model":
        events[0]["payload"]["action"]["action_type"] = "tool"
    elif mutation == "has_receipt":
        events.append({"event_type": "physical.execution",
                       "payload": {"action_id": "failed-model"}})
    elif mutation == "wrong_error":
        events[1]["payload"]["failure_message"] = "PRIVATE-endpoint failure"
    elif mutation == "no_closure":
        events.pop(2)
    elif mutation == "running_graph":
        events[3]["payload"]["nodes"][0]["status"] = "running"
    elif mutation == "duplicate_failure":
        events.append(events[1])
    else:
        events.pop(1)
    with pytest.raises(RuntimeError):
        control.interrupted_model_proof(events)


def test_transport_controller_uses_original_queue_only_after_exact_control_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "queue-control-freeze-005.json"
    path.write_text('{"verified":"separate-control"}')
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control.queue, "require_remote", lambda root: None)
    monkeypatch.setattr(control, "control_value", lambda: {"verified": "separate-control"})
    monkeypatch.setattr(control, "require_stopped", lambda *args, **kwargs: None)
    calls = []
    monkeypatch.setattr(control.queue, "run_queue", lambda execution: calls.append(execution))
    monkeypatch.setattr(control.queue, "AttemptLedger", control.queue.AttemptLedger)
    control.run(path)
    assert calls == [tmp_path / "execution-freeze-003.json"]
    assert control.queue.AttemptLedger is control.ClassifiedQueueView
    path.write_text('{"verified":"tampered"}')
    with pytest.raises(RuntimeError, match="control provenance drift"):
        control.run(path)
    assert len(calls) == 1
