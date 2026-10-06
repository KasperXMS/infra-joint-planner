import importlib
import json
import shutil
import sys
from pathlib import Path

import pytest
import test_resident_phase2_reviewed_queue as fixtures

from infra_joint.control.provenance import provenance_sha256
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


def test_one_reservation_check_reads_one_view_and_next_check_revalidates():
    class CountingLedger(adapter.ReadOnceAttemptLedger):
        calls = 0

        @property
        def attempts(self):
            self.calls += 1
            return (Attempt("cell1", "run1", 1, "a" * 64, "valid"),)

    ledger = object.__new__(CountingLedger)
    ledger.cells = tuple(f"cell{i}" for i in range(1, 193))
    ledger._repairs = {}
    ledger._check_reservation("cell2")
    assert ledger.calls == 1
    ledger._check_reservation("cell2")
    assert ledger.calls == 2


@pytest.mark.parametrize("case", ["ready", "unknown", "pending", "confounder",
                                  "already_valid", "out_of_order", "excluded_twice",
                                  "excluded_once", "repaired", "unapproved_prior"])
def test_reservation_view_preserves_exact_original_invariants_and_errors(case):
    def attempt(disposition, reason=None):
        return Attempt("cell1", "run1", 1, "a" * 64, disposition, reason)

    attempts = {
        "ready": (), "unknown": (), "pending": (attempt(None),),
        "confounder": (attempt("confounder"),),
        "already_valid": (attempt("valid"),), "out_of_order": (),
        "excluded_once": (attempt("operational_excluded", "provider_outage"),),
        "excluded_twice": (attempt("operational_excluded", "provider_outage"),
                           Attempt("cell1", "run2", 2, "a" * 64,
                                   "operational_excluded", "provider_outage")),
        "repaired": (attempt("confounder"),), "unapproved_prior": (attempt("valid"),),
    }[case]
    cell = "other" if case == "unknown" else "cell2" if case == "out_of_order" else "cell1"
    repairs = {"run1": "b" * 64} if case == "repaired" else {}

    class FixedLedger(adapter.ReadOnceAttemptLedger):
        @property
        def attempts(self):
            return attempts

    ledger = object.__new__(FixedLedger)
    ledger.cells, ledger._repairs = ("cell1", "cell2"), repairs
    original = object.__new__(adapter.previous.AttemptLedger)
    original.cells, original._repairs = ledger.cells, dict(repairs)
    original._attempts = {a.run_id: a for a in attempts}

    def outcome(check):
        try:
            check(cell)
            return None
        except (RuntimeError, ValueError) as exc:
            return type(exc), str(exc)

    assert outcome(ledger._check_reservation) == outcome(original._check_reservation)


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


def test_second_exact_review_replays_prior_review_without_rewriting_history(heldout_json):
    root, directory, raw, original_receipt, parent, _, _ = heldout_json
    original_class = adapter.previous.AttemptLedger
    adapter.create_review("run1", parent)
    second = root / "evidence/cell2/attempt1"
    second.parent.mkdir(parents=True)
    shutil.copytree(directory, second)
    (second / "runs/run1").rename(second / "runs/run2")
    view = adapter.ReadOnceAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    view.settle("run2", "confounder", adapter.previous.legacy.GATE_PROBLEM,
                provenance_sha256(original_receipt))
    journal = raw.path.read_bytes()
    with pytest.raises(RuntimeError, match="unresolved system confounder"):
        adapter.previous.create_review("run2", parent)
    result = adapter.create_review("run2", parent)
    assert result["retry"] is False and result["confirmed_model_parse_failures"] == 1
    final = adapter.ReadOnceAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    assert [a.disposition for a in final.original_attempts] == ["confounder", "confounder"]
    assert [a.disposition for a in final.attempts] == ["valid", "valid"]
    assert final.completed_cells == ("cell1", "cell2")
    assert raw.path.read_bytes() == journal
    assert adapter.previous.AttemptLedger is original_class
    with pytest.raises(RuntimeError, match="must not be repeated"):
        final.reserve("cell2", "forbidden-repeat", "b" * 64)


def test_review_wrapper_keeps_original_live_guard_before_any_parent_read(
    heldout_json, monkeypatch,
):
    _, _, _, _, parent, _, _ = heldout_json

    def active(_):
        raise RuntimeError("live queue before review")

    monkeypatch.setattr(adapter.previous.previous.gate.evidence.private,
                        "assert_inactive", active)
    monkeypatch.setattr(adapter.previous.previous, "checked_control",
                        lambda *_: pytest.fail("parent read"))
    with pytest.raises(RuntimeError, match="live queue before review"):
        adapter.create_review("run1", parent)


def test_registered_self_can_start_but_original_private_guard_still_rejects(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    proc = tmp_path / "proc/71"
    proc.mkdir(parents=True)
    (proc / "cmdline").write_bytes(
        b"python\0-m\0large_scale_resident_phase2_read_once_v1\0experiment\0")
    (root / "queue-process-phase2-003.json").write_text('{"pid":71}')
    original_guard = adapter.previous.previous.gate.evidence.private.assert_inactive
    adapter.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=71)
    with pytest.raises(RuntimeError, match="inactive queue"):
        original_guard(root, proc_root=tmp_path / "proc")
    assert adapter.previous.previous.gate.evidence.private.assert_inactive is original_guard


@pytest.mark.parametrize("handle", ["queue-process-other.json", "queue-lease.json",
                                    "evidence/cell/attempt1/process.json"])
def test_other_live_owner_or_atomic_or_lease_blocks_startup(tmp_path, handle):
    root = tmp_path / "experiment"
    path = root / handle
    path.parent.mkdir(parents=True)
    path.write_text('{"pid":72}')
    proc = tmp_path / "proc/72"
    proc.mkdir(parents=True)
    (proc / "cmdline").write_bytes(b"python\0experiment\0")
    with pytest.raises(RuntimeError, match="prohibits startup"):
        adapter.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=71)
