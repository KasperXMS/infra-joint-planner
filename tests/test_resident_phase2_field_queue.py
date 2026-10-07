import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_phase2_field_queue_v1")
snapshot = importlib.import_module("large_scale_resident_phase2_field_snapshot_v1")
private = importlib.import_module("large_scale_resident_phase2_field_private_v1")
heldout_field = importlib.import_module("test_resident_phase2_field_review").heldout_field


@pytest.fixture
def combined(heldout_field, monkeypatch):
    root, _, raw, parent, historical, _, original, _ = heldout_field
    queue.review.create_review("run4", parent, historical)
    view = queue.review.FieldReviewedAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    view.reserve("next", "run-model", "b" * 64)
    view.settle("run-model", "confounder", queue.core.legacy.GATE_PROBLEM, "e" * 64)
    model_value = {"reviewed_admission_sha256": "f" * 64,
                   "reviewed_admission": {"disposition": "valid", "benchmark_score": 0}}
    model_path = root / queue.core.DIRECTORY / "run-model.json"
    model_path.parent.mkdir()
    model_path.write_text(json.dumps(model_value))

    def model_proof(path, attempt):
        assert path == model_path and attempt.run_id == "run-model"
        assert attempt.disposition == "confounder"
        return json.loads(path.read_text())

    # Model-JSON proof internals have their separate real-evidence tests. This
    # fixture isolates composition of the two independently verified views.
    monkeypatch.setattr(queue.core, "verify_sidecar", model_proof)
    saved = json.loads(parent.read_text())
    old = root / "phase2-reviewed-control-freeze-002.json"
    old.write_text(json.dumps({
        "version": "resident-phase2-exact-model-json-continuation-v1",
        "parent_control_path": str(parent),
        "parent_control_file_sha256": queue.core.legacy.sha256(parent),
        "sidecars": {model_path.name: queue.core.legacy.sha256(model_path)},
        "source_sha256": {Path(p).name: queue.core.legacy.sha256(Path(p)) for p in (
            queue.core.__file__, queue.core.legacy.__file__, queue.core.bindings.__file__)},
        "execution_freeze_sha256": saved["execution_freeze_sha256"],
        "phase2_schedule_sha256": saved["phase2_schedule_sha256"],
        "nominal_cells": saved["nominal_cells"], "no_retry": True,
        "semantic_tuning": False, "prior_results_modified": False}))
    old_receipt = root / "phase2-ledger-read-once-freeze-003.json"
    old_receipt.write_text(json.dumps(queue.review.parent.freeze_value(old)))
    control = root / "phase2-field-reviewed-control-freeze-001.json"
    control.write_text(json.dumps(queue.control_value(parent, old, old_receipt)))
    receipt = root / "phase2-field-ledger-freeze-001.json"
    receipt.write_text(json.dumps(queue.freeze_value(control)))
    gate = {"schedule": [{"cell_id": c} for c in raw.cells],
            "phase2_schedule_sha256": saved["phase2_schedule_sha256"]}
    monkeypatch.setattr(queue.base, "checked_inputs", lambda *_: (saved, gate))
    monkeypatch.setattr(queue.core.previous, "cells_from_gate",
                        lambda _: tuple(type("Cell", (), {"cell_id": c})() for c in raw.cells))

    def settled(_, attempt, execution):
        return {"run_id": attempt.run_id, "attempt_index": attempt.attempt_index,
                "execution_sha256": execution, "disposition": attempt.disposition,
                "benchmark_score": 0, "unknown_failed_traffic": None}

    monkeypatch.setattr(queue.base, "settled", settled)
    return root, raw, parent, old, old_receipt, control, receipt, original


def test_combined_control_preserves_old_controls_raw_findings_and_unknowns(combined):
    root, raw, parent, old, old_receipt, control, receipt, _ = combined
    before = {p: p.read_bytes() for p in (raw.path, parent, old, old_receipt)}
    queue.validate(control, receipt)
    value = snapshot.collect(root, control_path=control)
    assert value["admitted_cells"] == 2 and value["attempt_count"] == 2
    assert value["original_confounded_attempts"] == 2 and value["confounded_attempts"] == 0
    assert not value["phase2_complete"] and not value["goal_complete"]
    for row in value["rows"][:2]:
        attempt = row["attempts"][0]
        assert attempt["original_disposition"] == "confounder"
        assert attempt["disposition"] == "valid" and attempt["benchmark_score"] == 0
        assert attempt["unknown_failed_traffic"] is None
    assert all(p.read_bytes() == contents for p, contents in before.items())


def test_original_executor_only_runs_unstarted_cell_and_no_module_mutation(combined, monkeypatch):
    root, raw, _, _, _, control, receipt, _ = combined
    calls = []
    original_guard = queue.core.previous.gate.evidence.private.assert_inactive
    original_ledger = queue.core.ReviewedAttemptLedger

    def execute(cell, ledger, saved):
        assert isinstance(ledger, queue.review.FieldReviewedAttemptLedger)
        assert saved["execution_freeze_sha256"] == "b" * 64
        calls.append(cell.cell_id)
        ledger.reserve("future", "run-future", "b" * 64)
        ledger.settle("run-future", "valid", "wrong_answer", "c" * 64)

    monkeypatch.setattr(queue.core.previous, "execute_cell", execute)
    queue.run(control, receipt)
    assert calls == ["future"]
    assert queue.core.previous.gate.evidence.private.assert_inactive is original_guard
    assert queue.core.ReviewedAttemptLedger is original_ledger
    assert len(raw.path.read_text().splitlines()) == 7
    assert json.loads((root / "phase2-queue-completed.json").read_text())["goal_complete"] is False


@pytest.mark.parametrize("damage", ["control", "source", "old_control", "old_receipt",
                                  "field_sidecar", "foreign", "overlap", "missing"])
def test_drift_or_unowned_review_cannot_unlock_continuation(combined, damage):
    root, _, _, old, old_receipt, control, receipt, _ = combined
    if damage in {"control", "source"}:
        path = control if damage == "control" else receipt
        value = json.loads(path.read_text())
        value["source_sha256"][Path(queue.__file__).name] = "0" * 64
        path.write_text(json.dumps(value))
    elif damage in {"old_control", "old_receipt"}:
        path = old if damage == "old_control" else old_receipt
        path.write_text(path.read_text() + "\n")
    elif damage == "field_sidecar":
        (root / queue.review.DIRECTORY / "run4.json").write_text("{}")
    elif damage == "foreign":
        (root / queue.review.DIRECTORY / "foreign.json").write_text("{}")
    elif damage == "overlap":
        (root / queue.core.DIRECTORY / "run4.json").write_text("{}")
    else:
        (root / queue.review.DIRECTORY / "run4.json").unlink()
    with pytest.raises((RuntimeError, KeyError)):
        queue.validate(control, receipt)
        queue.checked_control(control)


def test_pending_batch_allowed_in_projection_but_never_dispatch_or_completion(combined):
    root, raw, _, _, _, control, _, _ = combined
    view = queue.review.FieldReviewedAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    view.reserve("future", "pending", "b" * 64)
    value = snapshot.collect(root, control_path=control)
    assert value["admitted_cells"] == 2 and value["pending_count"] == 1
    assert value["rows"][2]["attempts"] == []
    assert value["rows"][2]["pending_run_ids"] == ["pending"]
    with pytest.raises(RuntimeError, match="pending/unresolved"):
        queue.checked_control(control)


def test_private_audit_live_guard_precedes_any_metadata_or_body_read(tmp_path, monkeypatch):
    def active(_):
        raise RuntimeError("live queue")

    monkeypatch.setattr(private.previous.private, "assert_inactive", active)
    monkeypatch.setattr(queue, "validate", lambda *_: pytest.fail("metadata read"))
    with pytest.raises(RuntimeError, match="live queue"):
        private.audit_phase_two(tmp_path / "control", tmp_path / "receipt", root=tmp_path)


def test_partial_combined_block_cannot_scan_private_bodies(combined, monkeypatch):
    root, raw, _, _, _, control, receipt, _ = combined
    monkeypatch.setattr(private.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    before = raw.path.read_bytes()
    with pytest.raises(RuntimeError, match="completed resolved PhaseII"):
        private.audit_phase_two(control, receipt, root=root)
    assert raw.path.read_bytes() == before


def test_full_combined_private_membership_preserves_quality_unknowns_and_guards(
    combined, monkeypatch,
):
    root, raw, _, _, _, control, receipt, _ = combined
    view = queue.review.FieldReviewedAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    view.reserve("future", "run-future", "b" * 64)
    view.settle("run-future", "valid", "wrong_answer", "c" * 64)
    directory = root / "evidence/future/attempt1"
    directory.mkdir(parents=True)
    (directory / "admission.json").write_text('{"disposition":"valid"}')
    for cell in raw.cells:
        directory = root / "evidence" / cell / "attempt1"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    original_inputs = queue.base.checked_inputs

    def inputs(*args):
        parent, gate = original_inputs(*args)
        for row in gate["schedule"]:
            row["task"] = {"family": "longbench_v2", "position": 3}
        return parent, gate

    monkeypatch.setattr(queue.base, "checked_inputs", inputs)
    monkeypatch.setattr(private.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    old_collect = private.previous.sources.collect
    old_guard = private.previous.private.assert_inactive
    journal = raw.path.read_bytes()
    value = private.audit_phase_two(control, receipt, root=root)
    assert len(value["records"]) == 3
    assert all(r["benchmark_score"] == 0 and r["coverage"] is None
               and r["semantic_primary_cause"] is None for r in value["records"])
    assert not value["semantic_audit_complete"] and not value["artifact_bodies_exported"]
    assert not value["raw_journal_rewritten"] and not value["original_private_guard_changed"]
    assert private.previous.sources.collect is old_collect
    assert private.previous.private.assert_inactive is old_guard
    assert raw.path.read_bytes() == journal


def test_missing_journal_projection_cannot_initialize_or_admit(combined):
    root, raw, _, _, _, control, _, _ = combined
    raw.path.unlink()
    with pytest.raises(RuntimeError, match="missing journal"):
        snapshot.collect(root, control_path=control)
    assert not raw.path.exists()


def test_registered_controller_can_start_but_original_private_guard_rejects(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    (root / "queue-process-phase2-005.json").write_text('{"pid":71}')
    proc = tmp_path / "proc/71"
    proc.mkdir(parents=True)
    (proc / "cmdline").write_bytes(
        b"python\0-m\0large_scale_resident_phase2_field_queue_v1\0experiment\0")
    queue.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=71)
    with pytest.raises(RuntimeError, match="inactive queue"):
        queue.core.previous.gate.evidence.private.assert_inactive(root, proc_root=tmp_path / "proc")


@pytest.mark.parametrize("handle", ["queue-process-other.json", "queue-lease.json",
                                    "evidence/cell/attempt1/process.json"])
def test_other_live_process_or_lease_blocks_startup(tmp_path, handle):
    root = tmp_path / "experiment"
    path = root / handle
    path.parent.mkdir(parents=True)
    path.write_text('{"pid":72}')
    proc = tmp_path / "proc/72"
    proc.mkdir(parents=True)
    (proc / "cmdline").write_bytes(b"python\0experiment\0")
    with pytest.raises(RuntimeError, match="prohibits startup"):
        queue.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=71)


def test_reviewer_and_original_atomic_executor_are_unchanged():
    assert queue.core.previous.execute_cell is queue.core.previous.previous.execute_cell
    assert queue.review.FieldReviewedAttemptLedger._check_reservation is (
        queue.review.parent.ReadOnceAttemptLedger._check_reservation)
