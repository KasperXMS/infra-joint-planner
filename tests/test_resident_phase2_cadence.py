import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
cadence = importlib.import_module("large_scale_resident_phase2_cadence_v1")
wire = importlib.import_module("large_scale_resident_feedback_wire_v1")
heldout_field = importlib.import_module("test_resident_phase2_field_review").heldout_field
combined = importlib.import_module("test_resident_phase2_field_queue").combined


def ledger_for(tmp_path, count, initial=0):
    cells = tuple(f"cell-{i}" for i in range(count))
    path = tmp_path / "attempts.jsonl"
    raw = AttemptLedger(path, cells, "a" * 64)
    for cell in cells[:initial]:
        raw.reserve(cell, cell + "-run", "b" * 64)
        raw.settle(cell + "-run", "valid", "wrong_answer", "c" * 64)
    return cells, cadence.BatchLedger(path, cells, "a" * 64, ())


@pytest.mark.parametrize(("count", "initial", "expected"), [
    (35, 0, [16, 32, 35]), (83, 50, [64, 80, 83]), (64, 49, [64]),
    (16, 16, [16]),
])
def test_full_audits_only_at_16_cell_boundaries_and_final_remainder(
    tmp_path, count, initial, expected,
):
    cells, ledger = ledger_for(tmp_path, count, initial)
    executions, audits, fences = [], [], []

    def execute(cell):
        executions.append(cell.cell_id)
        ledger.reserve(cell.cell_id, cell.cell_id + "-new", "b" * 64)
        ledger.settle(cell.cell_id + "-new", "valid", "wrong_answer", "c" * 64)

    cadence.run_batches(tuple(SimpleNamespace(cell_id=c) for c in cells), ledger,
                        execute, lambda: fences.append(True),
                        lambda: audits.append(len(ledger.completed_cells)))
    assert executions == list(cells[initial:])
    assert audits == expected
    assert len(fences) == count - initial + len(expected)


def test_new_finding_stops_before_next_cell_without_waiting_for_16(tmp_path):
    cells, ledger = ledger_for(tmp_path, 20)
    executions, audits = [], []

    def execute(cell):
        executions.append(cell.cell_id)
        ledger.reserve(cell.cell_id, cell.cell_id, "b" * 64)
        ledger.settle(cell.cell_id, "confounder", "privacy_violation", "c" * 64)

    with pytest.raises(RuntimeError, match="new finding"):
        cadence.run_batches(tuple(SimpleNamespace(cell_id=c) for c in cells), ledger,
                            execute, lambda: None, lambda: audits.append(True))
    assert executions == [cells[0]] and audits == []
    assert ledger.original_attempts[0].disposition == "confounder"


def test_batch_audit_failure_blocks_dispatch_of_cell17(tmp_path):
    cells, ledger = ledger_for(tmp_path, 20)
    executions = []

    def execute(cell):
        executions.append(cell.cell_id)
        ledger.reserve(cell.cell_id, cell.cell_id, "b" * 64)
        ledger.settle(cell.cell_id, "valid", "wrong_answer", "c" * 64)

    def audit():
        raise RuntimeError("recipient leakage")

    with pytest.raises(RuntimeError, match="recipient leakage"):
        cadence.run_batches(tuple(SimpleNamespace(cell_id=c) for c in cells), ledger,
                            execute, lambda: None, audit)
    assert executions == list(cells[:16])


def test_historical_exact_review_reused_without_rewriting_raw_journal(tmp_path):
    cells = ("old", "next", "future")
    raw = AttemptLedger(tmp_path / "attempts.jsonl", cells, "a" * 64)
    raw.reserve("old", "old-run", "b" * 64)
    raw.settle("old-run", "confounder", "model_json", "c" * 64)
    original = raw.attempts[0]
    effective = replace(original, disposition="valid", reason="proved_model_json",
                        receipt_sha256="d" * 64)
    before = raw.path.read_bytes()
    ledger = cadence.BatchLedger(raw.path, cells, "a" * 64, ((original, effective),))
    assert ledger.attempts == (effective,)
    assert ledger.original_attempts == (original,) and raw.path.read_bytes() == before
    ledger.reserve("next", "next-run", "b" * 64)
    ledger.settle("next-run", "confounder", "new_unknown", "e" * 64)
    assert ledger.attempts[-1].disposition == "confounder"
    with pytest.raises(RuntimeError, match="confounder"):
        ledger.reserve("future", "future-run", "b" * 64)
    with pytest.raises(RuntimeError, match="changed"):
        cadence.BatchLedger(raw.path, cells, "a" * 64,
                            ((replace(original, reason="changed"), effective),))


def test_same_order_no_retry_and_external_journal_change_rejected(tmp_path):
    cells, ledger = ledger_for(tmp_path, 3)
    with pytest.raises(RuntimeError, match="reordered"):
        ledger.reserve(cells[1], "out-of-order", "b" * 64)
    ledger.reserve(cells[0], "run", "b" * 64)
    ledger.settle("run", "valid", "wrong_answer", "c" * 64)
    with pytest.raises(RuntimeError, match="repeated"):
        ledger.reserve(cells[0], "retry", "b" * 64)
    ledger.path.write_bytes(ledger.path.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="outside"):
        ledger.reserve(cells[1], "next", "b" * 64)


def test_pending_attempt_cannot_be_dispatched_or_declared_complete(tmp_path):
    cells, ledger = ledger_for(tmp_path, 2)
    ledger.reserve(cells[0], "pending", "b" * 64)
    with pytest.raises(RuntimeError, match="pending/unresolved"):
        cadence.run_batches(tuple(SimpleNamespace(cell_id=c) for c in cells), ledger,
                            lambda _: pytest.fail("dispatch"), lambda: None,
                            lambda: pytest.fail("full audit"))


def test_metadata_fence_is_per_cell_and_stops_drift_before_dispatch(tmp_path):
    cells, ledger = ledger_for(tmp_path, 3)
    calls = []

    def fence():
        raise RuntimeError("source drift")

    with pytest.raises(RuntimeError, match="source drift"):
        cadence.run_batches(tuple(SimpleNamespace(cell_id=c) for c in cells), ledger,
                            lambda c: calls.append(c), fence, lambda: None)
    assert calls == []


def test_manifest_hash_drift_fails_before_any_source_or_private_read(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text('{"tampered":true}')
    monkeypatch.setattr(cadence, "source_bindings", lambda: pytest.fail("source read"))
    with pytest.raises(RuntimeError, match="drift"):
        cadence.metadata_fence(path, "0" * 64, {})


def test_controller_own_registration_does_not_relax_private_guard(tmp_path):
    root = tmp_path / "experiment"
    root.mkdir()
    (root / "queue-process-phase2-008.json").write_text('{"pid":71}')
    proc = tmp_path / "proc/71"
    proc.mkdir(parents=True)
    (proc / "cmdline").write_bytes(
        b"python\0-m\0large_scale_resident_phase2_cadence_v1\0experiment\0")
    cadence.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=71)
    with pytest.raises(RuntimeError, match="inactive queue"):
        cadence.field.core.previous.gate.evidence.private.assert_inactive(
            root, proc_root=tmp_path / "proc")
    with pytest.raises(RuntimeError, match="prohibits startup"):
        cadence.assert_startup_safe(root, proc_root=tmp_path / "proc", own_pid=72)


def test_missing_journal_never_initialized_by_batch_ledger(tmp_path):
    path = tmp_path / "missing.jsonl"
    with pytest.raises(RuntimeError, match="initialize"):
        cadence.BatchLedger(path, ("cell",), "a" * 64, ())
    assert not path.exists()


def test_historical_modules_and_original_execute_cell_unchanged():
    assert cadence.field.core.previous.execute_cell is (
        cadence.field.core.previous.previous.execute_cell)
    assert cadence.field.review.FieldReviewedAttemptLedger._check_reservation is (
        cadence.field.review.parent.ReadOnceAttemptLedger._check_reservation)


def test_fresh_original_sidecar_proof_once_per_checkpoint_not_per_ledger_access(
    combined, monkeypatch,
):
    _, raw, _, _, _, control, _, _ = combined
    field = cadence.field
    model_proof, field_proof = field.core.verify_sidecar, field.review.verify_sidecar
    counts = {"model": 0, "field": 0}

    def model_once(*args):
        counts["model"] += 1
        return model_proof(*args)

    def field_once(*args):
        counts["field"] += 1
        return field_proof(*args)

    monkeypatch.setattr(field.core, "verify_sidecar", model_once)
    monkeypatch.setattr(field.review, "verify_sidecar", field_once)
    cells = tuple(SimpleNamespace(cell_id=c) for c in raw.cells)
    value = json.loads(control.read_text())
    view = cadence.fresh_membership(value, cells, require_dispatch_ready=True)
    for _ in range(100):
        assert len(view.attempts) == 2 and len(view.completed_cells) == 2 and not view.pending
    assert counts == {"model": 1, "field": 1}
    before = raw.path.read_bytes()
    assert view.original_attempts[0].disposition == "confounder"
    assert raw.path.read_bytes() == before
    view.reserve("future", "pending", "b" * 64)
    assert counts == {"model": 1, "field": 1}
    with pytest.raises(RuntimeError, match="pending/unresolved"):
        cadence.fresh_membership(value, cells, require_dispatch_ready=True)


def test_full_control_and_projection_reuse_original_logic_without_global_mutation(combined):
    root, raw, _, _, _, control, _, _ = combined
    original_membership = cadence.field.checked_membership
    original_queue = cadence.snapshot.queue
    parent, cells = cadence.full_control(control)
    assert len(cells) == 3 and parent["execution_freeze_sha256"] == "b" * 64
    projection = cadence.full_projection(root, control)
    assert projection["admitted_cells"] == 2 and projection["original_confounded_attempts"] == 2
    assert projection["confounded_attempts"] == 0 and projection["goal_complete"] is False
    assert cadence.field.checked_membership is original_membership
    assert cadence.snapshot.queue is original_queue
    assert len(raw.path.read_text().splitlines()) == 5


def test_wire_request_texts_preserve_nonfeedback_and_typed_blocks():
    assert wire.texts({"messages": [{"content": "a"}, {"content": [
        {"type": "text", "text": "b"}, {"type": "image", "image": "not-exported"},
    ]}]}) == ["a", "b"]
    with pytest.raises(RuntimeError, match="leak"):
        wire._require(False, "recipient leak")
    assert json.loads(json.dumps({"unknown": None}))["unknown"] is None
