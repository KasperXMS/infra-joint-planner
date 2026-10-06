import importlib
import json
import sys
from pathlib import Path

import pytest
import test_resident_phase2_reviewed_snapshot as fixtures

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_phase2_reviewed_private_v1")
rejected_model_json = fixtures.rejected_model_json
heldout_json = fixtures.heldout_json
reviewed_projection = fixtures.reviewed_projection


@pytest.fixture
def reviewed_audit(reviewed_projection):
    root, raw, control = reviewed_projection
    receipt = root / "phase2-ledger-read-once-freeze-002.json"
    audit.reviewed.queue.frozen.write_new(receipt, audit.ledger.freeze_value(control))
    return root, raw, control, receipt


def test_original_live_guard_precedes_control_metadata_and_private_reads(monkeypatch, tmp_path):
    def active(_):
        raise RuntimeError("live held-out controller")

    monkeypatch.setattr(audit.previous.private, "assert_inactive", active)
    monkeypatch.setattr(audit.ledger, "validate", lambda *_: pytest.fail("control read"))
    monkeypatch.setattr(audit, "projection", lambda *_: pytest.fail("metadata read"))
    monkeypatch.setattr(audit.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="live held-out"):
        audit.audit_phase_two(tmp_path / "control", tmp_path / "receipt", root=tmp_path)


def test_partial_reviewed_block_never_scans_private_bodies(reviewed_audit, monkeypatch):
    root, raw, control, receipt = reviewed_audit
    before = raw.path.read_bytes()
    monkeypatch.setattr(audit.previous.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="completed resolved PhaseII"):
        audit.audit_phase_two(control, receipt, root=root)
    assert raw.path.read_bytes() == before


def test_complete_reviewed_view_preserves_wrong_answer_and_unknown_without_mutation(
    reviewed_audit, monkeypatch,
):
    root, raw, control, receipt = reviewed_audit
    view = audit.ledger.ReadOnceAttemptLedger(raw.path, raw.cells, raw.schedule_sha256)
    view.reserve("cell2", "run2", "b" * 64)
    view.settle("run2", "valid", "wrong_answer", "c" * 64)
    for cell in ("cell1", "cell2"):
        directory = root / "evidence" / cell / "attempt1"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    (root / "evidence/cell2/attempt1/admission.json").write_text('{"disposition":"valid"}')
    original_settled = audit.reviewed.previous.settled

    def settled(current_root, attempt, source):
        return {**original_settled(current_root, attempt, source),
                "attempt_index": attempt.attempt_index, "execution_sha256": source}

    monkeypatch.setattr(audit.reviewed.previous, "settled", settled)
    # Synthetic unannotated tasks: preserve unknown rather than invent coverage.
    checked = audit.reviewed.previous.checked_inputs

    def inputs(*args):
        parent, gate = checked(*args)
        for row in gate["schedule"]:
            row["task"] = {"family": "longbench_v2", "position": 3}
        return parent, gate

    monkeypatch.setattr(audit.reviewed.previous, "checked_inputs", inputs)
    monkeypatch.setattr(audit.previous.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    original_collect = audit.previous.sources.collect
    original_class = audit.reviewed.queue.ReviewedAttemptLedger
    before = raw.path.read_bytes()
    result = audit.audit_phase_two(control, receipt, root=root)
    assert len(result["records"]) == 2
    assert all(row["benchmark_score"] == 0 and row["coverage"] is None
               and row["semantic_primary_cause"] is None for row in result["records"])
    assert not result["semantic_audit_complete"] and not result["artifact_bodies_exported"]
    assert result["planner_or_model_calls"] == 0 and not result["raw_journal_rewritten"]
    assert raw.path.read_bytes() == before
    assert audit.previous.sources.collect is original_collect
    assert audit.reviewed.queue.ReviewedAttemptLedger is original_class
    assert not result["original_private_guard_changed"]


@pytest.mark.parametrize("damage", ["adapter", "reviewed_control"])
def test_changed_source_bound_receipt_blocks_before_private_read(
    reviewed_audit, monkeypatch, damage,
):
    root, _, control, receipt = reviewed_audit
    monkeypatch.setattr(audit.previous.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.previous, "audit_multihop", lambda *_: pytest.fail("body read"))
    if damage == "adapter":
        value = json.loads(receipt.read_text())
        value["source_sha256"] = "0" * 64
        receipt.write_text(json.dumps(value))
    else:
        control.write_text(control.read_text() + "\n")
    with pytest.raises(RuntimeError, match="drift"):
        audit.audit_phase_two(control, receipt, root=root)
