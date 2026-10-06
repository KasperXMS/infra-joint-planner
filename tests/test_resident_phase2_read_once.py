import importlib
import json
import sys
from pathlib import Path

import pytest
import test_resident_phase2_reviewed_queue as fixtures

from infra_joint.experiments.attempt_ledger import Attempt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
adapter = importlib.import_module("large_scale_resident_phase2_read_once_v1")
rejected_model_json = fixtures.rejected_model_json
heldout_json = fixtures.heldout_json


def test_completed_cells_revalidates_once_not_once_per_scheduled_cell():
    class CountingLedger(adapter.ReadOnceAttemptLedger):
        calls = 0

        @property
        def attempts(self):
            self.calls += 1
            return (Attempt("cell1", "run1", 1, "a" * 64, "valid"),)

    ledger = object.__new__(CountingLedger)
    ledger.cells = tuple(f"cell{i}" for i in range(1, 193))
    assert ledger.completed_cells == ("cell1",) and ledger.calls == 1
    assert ledger.completed_cells == ("cell1",) and ledger.calls == 2


def test_read_once_continues_exact_original_run_without_global_mutation(
    heldout_json, monkeypatch,
):
    root, _, _, _, parent, saved, cells = heldout_json
    previous = adapter.previous
    previous.create_review("run1", parent)
    control = root / "phase2-reviewed-control-freeze-001.json"
    previous.frozen.write_new(control, previous.control_value(parent))
    receipt = root / "phase2-ledger-read-once-freeze-001.json"
    previous.frozen.write_new(receipt, adapter.freeze_value(control))
    monkeypatch.setattr(previous, "checked_control", lambda _: (saved, cells))
    calls = []

    def execute(cell, ledger, _):
        assert isinstance(ledger, adapter.ReadOnceAttemptLedger)
        calls.append(cell.cell_id)
        ledger.reserve(cell.cell_id, "run2", "b" * 64)
        ledger.settle("run2", "valid", "wrong_answer", "c" * 64)

    monkeypatch.setattr(previous.previous, "execute_cell", execute)
    original_class = previous.ReviewedAttemptLedger
    adapter.run(control, receipt)
    assert calls == ["cell2"]
    assert previous.ReviewedAttemptLedger is original_class
    assert json.loads((root / "phase2-queue-completed.json").read_text())["goal_complete"] is False


def test_adapter_drift_stops_before_any_ledger_or_execution(heldout_json, monkeypatch):
    root, _, _, _, parent, _, _ = heldout_json
    previous = adapter.previous
    previous.create_review("run1", parent)
    control = root / "phase2-reviewed-control-freeze-001.json"
    previous.frozen.write_new(control, previous.control_value(parent))
    receipt = root / "phase2-ledger-read-once-freeze-001.json"
    value = adapter.freeze_value(control)
    value["source_sha256"] = "0" * 64
    previous.frozen.write_new(receipt, value)
    monkeypatch.setattr(previous, "checked_control", lambda _: pytest.fail("execution"))
    with pytest.raises(RuntimeError, match="drift"):
        adapter.run(control, receipt)
