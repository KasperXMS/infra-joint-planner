import importlib
import json
import sys
from pathlib import Path

import pytest
import test_resident_phase2_reviewed_queue as fixtures

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
snapshot = importlib.import_module("large_scale_resident_phase2_reviewed_snapshot_v1")
queue = snapshot.queue
rejected_model_json = fixtures.rejected_model_json
heldout_json = fixtures.heldout_json


@pytest.fixture
def reviewed_projection(heldout_json, monkeypatch):
    root, _, ledger, _, parent_path, parent, cells = heldout_json
    queue.create_review("run1", parent_path)
    control = root / "phase2-reviewed-control-freeze-001.json"
    queue.frozen.write_new(control, queue.control_value(parent_path))
    gate = {"schedule": [{"cell_id": c.cell_id} for c in cells],
            "phase2_schedule_sha256": parent["phase2_schedule_sha256"]}
    monkeypatch.setattr(snapshot.previous, "checked_inputs", lambda *_: (parent, gate))
    monkeypatch.setattr(snapshot.previous, "settled", lambda _, a, __: {
        "run_id": a.run_id, "disposition": a.disposition, "reason": a.reason,
        "benchmark_score": 0, "trace_metrics": {"model_service_work_complete_total_ms": None,
                                                  "successful_inference_telemetry_count": 4}})
    return root, ledger, control


def test_reviewed_projection_preserves_rejection_quality_and_missing_work(reviewed_projection):
    root, ledger, control = reviewed_projection
    before = ledger.path.read_bytes()
    value = snapshot.collect(root, control_path=control)
    assert value["admitted_cells"] == 1 and value["attempt_count"] == 1
    assert value["original_confounded_attempts"] == 1 and value["confounded_attempts"] == 0
    row = value["rows"][0]["attempts"][0]
    assert row["adjudicated"] and row["disposition"] == "valid"
    assert row["original_disposition"] == "confounder"
    assert row["benchmark_score"] == 0
    assert row["trace_metrics"]["model_service_work_complete_total_ms"] is None
    assert not value["phase2_complete"] and not value["goal_complete"]
    assert ledger.path.read_bytes() == before


def test_pending_action_not_counted_as_completion(reviewed_projection):
    root, ledger, control = reviewed_projection
    view = queue.ReviewedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    value = snapshot.collect(root, control_path=control)
    assert value["admitted_cells"] == 1 and value["pending_count"] == 1
    assert value["rows"][1]["pending_run_ids"] == ["run2"]
    assert value["rows"][1]["attempts"] == []


@pytest.mark.parametrize("damage", ["source", "parent", "sidecar", "foreign"])
def test_projection_rejects_changed_reviewed_bindings(reviewed_projection, damage):
    root, _, control = reviewed_projection
    if damage == "foreign":
        (root / queue.DIRECTORY / "foreign.json").write_text("{}")
    elif damage == "sidecar":
        path = root / queue.DIRECTORY / "run1.json"
        path.write_text(path.read_text() + "\n")
    else:
        value = json.loads(control.read_text())
        if damage == "source":
            value["source_sha256"][Path(queue.__file__).name] = "0" * 64
        else:
            value["parent_control_file_sha256"] = "0" * 64
        control.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="drift"):
        snapshot.collect(root, control_path=control)


def test_missing_journal_is_never_initialized(reviewed_projection):
    root, ledger, control = reviewed_projection
    ledger.path.unlink()
    with pytest.raises(RuntimeError, match="missing journal"):
        snapshot.collect(root, control_path=control)
    assert not ledger.path.exists()
