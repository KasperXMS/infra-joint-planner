import importlib
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
creator = importlib.import_module("large_scale_resident_phase2_renewed_field_review_v1")
environment = creator.environment
original_inactive = creator.review.core.previous.gate.evidence.private.assert_inactive


class SyntheticRawHistory(AttemptLedger):
    def _check_reservation(self, cell_id):
        pass


@pytest.fixture
def history(tmp_path, monkeypatch):
    monkeypatch.setattr(environment.environment, "CELL", "cell0")
    monkeypatch.setattr(environment.environment, "RUN", "excluded")
    cells = tuple(SimpleNamespace(cell_id=f"cell{i}") for i in range(8))
    raw = SyntheticRawHistory(tmp_path / "phase2-attempts.jsonl",
                              tuple(c.cell_id for c in cells), "a" * 64)
    raw.reserve("cell0", "excluded", "b" * 64)
    raw.settle("excluded", "confounder", "environment", environment.environment.RAW_SHA)
    excluded = raw.attempts[-1]
    raw.reserve("cell0", "replacement", "b" * 64)
    raw.settle("replacement", "valid", "semantic_failure", "c" * 64)
    reviews = []
    for i, name in enumerate(("model", "initial", "derived81"), start=1):
        raw.reserve(f"cell{i}", name, "b" * 64)
        raw.settle(name, "confounder", "exact-historical-finding", "d" * 64)
        attempt = raw.attempts[-1]
        reviews.append({"raw": asdict(attempt), "effective": asdict(replace(
            attempt, disposition="valid", reason="proved", receipt_sha256="e" * 64))})
    target = tmp_path.name + "-phase2-target95"
    raw.reserve("cell4", target, "b" * 64)
    raw.settle(target, "confounder", creator.review.field.GATE, "f" * 64)
    value = {"parent": {"phase2_schedule_sha256": "a" * 64},
             "historical_reviews": reviews, "exclusion": {"raw": asdict(excluded),
             "effective": asdict(replace(excluded, disposition="operational_excluded",
                 reason=environment.environment.REASON, receipt_sha256="1" * 64))}}
    return SimpleNamespace(raw=raw, value=value, cells=cells, root=tmp_path, target=target)


def test_replay_preserves_derived_review_and_single_environment_replacement(history):
    before = history.raw.path.read_bytes()
    ledger, target = creator.pending_ledger(history.value, history.cells,
                                            history.raw.path, history.target)
    assert target == history.raw.attempts[-1]
    assert ledger.completed_cells == ("cell0", "cell1", "cell2", "cell3")
    assert len(ledger.original_attempts) == 6
    assert len([a for a in ledger.attempts if a.disposition == "operational_excluded"]) == 1
    assert next(a for a in ledger.attempts if a.run_id == "derived81").disposition == "valid"
    assert history.raw.path.read_bytes() == before


def test_missing_derived_review_reproduces_historical_replay_rejection(history):
    history.value["historical_reviews"] = history.value["historical_reviews"][:-1]
    with pytest.raises(RuntimeError, match="unresolved system confounder"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_missing_environment_exclusion_is_not_waived(history):
    history.value["exclusion"]["effective"]["disposition"] = "valid"
    with pytest.raises(RuntimeError, match="only the exact authorized environmental pair"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_target_must_be_unique_and_unresolved(history):
    with pytest.raises(RuntimeError, match="one original target"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, "absent")
    with pytest.raises(RuntimeError, match="only the exact target"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, "model")


def test_other_new_finding_is_not_waived(history):
    history.raw.reserve("cell5", "new-other-finding", "b" * 64)
    history.raw.settle("new-other-finding", "confounder", "other-defect", "2" * 64)
    with pytest.raises(RuntimeError, match="unresolved system confounder"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_pending_action_prohibits_creation(history):
    # Remove only the synthetic final settlement: the hash-linked prefix now
    # contains a genuinely pending target, with no later illegal reservation.
    lines = history.raw.path.read_bytes().splitlines()
    history.raw.path.write_bytes(b"\n".join(lines[:-1]) + b"\n")
    with pytest.raises(RuntimeError, match="only the exact target"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_changed_raw_historical_pair_fails_closed(history):
    history.value["historical_reviews"][2]["raw"]["receipt_sha256"] = "3" * 64
    with pytest.raises(RuntimeError, match="proved historical raw attempt changed"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_creator_checks_global_inactivity_before_reading_or_writing(monkeypatch, tmp_path):
    monkeypatch.setattr(environment.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(environment.frozen, "ROOT", tmp_path)

    def reject(_root):
        raise RuntimeError("actual live queue")

    monkeypatch.setattr(creator.review.core.previous.gate.evidence.private,
                        "assert_inactive", reject)
    with pytest.raises(RuntimeError, match="actual live queue"):
        creator.create_review(tmp_path / "missing.json", "a" * 64, "target", tmp_path / "old")
    assert not list(tmp_path.iterdir())


def test_hash_linked_journal_tamper_is_not_accepted(history):
    rows = [json.loads(line) for line in history.raw.path.read_text().splitlines()]
    rows[-1]["reason"] = "changed"
    history.raw.path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises((RuntimeError, ValueError)):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


@pytest.fixture
def creation(history, monkeypatch):
    calls = []
    root = history.root
    manifest, control, gate = (root / name for name in ("manifest.json", "control.json",
                                                      "gate.json"))
    history.value["control_path"] = str(control)
    history.value["parent"]["gate_path"] = str(gate)
    manifest.write_text(json.dumps(history.value))
    control.write_text(json.dumps({"parent_control_path": str(root / "parent.json")}))
    gate.write_text("{}")
    monkeypatch.setattr(environment.frozen, "ROOT", root)
    monkeypatch.setattr(environment.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(environment, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(environment.environment, "require_strata_stopped",
                        lambda: calls.append("strata"))
    monkeypatch.setattr(creator.review.core.previous.gate.evidence.private,
                        "assert_inactive", lambda *_, **kw: calls.append(
                            "inactive-own-lease" if kw.get("allow_current_audit_lease")
                            else "inactive"))
    monkeypatch.setattr(creator.review.core.previous, "cells_from_gate", lambda *_: history.cells)

    def parent(_path):
        calls.append("full-parent")
        return history.value["parent"], history.cells

    monkeypatch.setattr(creator.review.core.previous, "checked_control", parent)
    proof = {"field_misuse_proof": [1, 2, 3], "actual_manager_schema_wire_proof": [1, 2],
             "sentinel": "unchanged original proof"}

    def prove(_root, target, _parent, _historical):
        assert target == history.raw.attempts[-1]
        calls.append("original-proof")
        return proof

    monkeypatch.setattr(creator.review, "proof", prove)

    def verify(path, target):
        assert json.loads(path.read_text()) == proof
        assert target == history.raw.attempts[-1]
        calls.append("original-verify")
        return proof

    monkeypatch.setattr(creator.review, "verify_sidecar", verify)
    inventory = {group: {} for group in environment.GROUPS}
    monkeypatch.setattr(environment, "inventory", lambda *_: inventory)
    output = root / creator.review.DIRECTORY / (history.target + ".json")
    monkeypatch.setattr(environment, "current_inventory", lambda: {
        **inventory, "initial_field_sidecars": {output.name: environment.cadence.digest(output)}})
    return SimpleNamespace(history=history, manifest=manifest, output=output, calls=calls,
                           proof=proof, historical=root / "historical.json")


def create(creation):
    return creator.create_review(creation.manifest, "a" * 64, creation.history.target,
                                 creation.historical)


def test_creation_keeps_full_gate_original_proof_and_exact_view(creation):
    before = creation.history.raw.path.read_bytes()
    result = create(creation)
    assert creation.history.raw.path.read_bytes() == before
    assert json.loads(creation.output.read_text()) == creation.proof
    assert creation.calls == ["remote", "inactive", "fence", "strata", "full-parent",
                              "original-proof", "fence", "strata", "inactive-own-lease",
                              "original-verify"]
    assert result["confirmed_field_failures"] == 3
    assert result["retry"] is False
    assert result["atomic_execution_changed"] is False


def test_creator_cannot_repeat_or_overwrite(creation):
    create(creation)
    before = creation.output.read_bytes()
    with pytest.raises(RuntimeError, match="owned exclusive"):
        create(creation)
    assert creation.output.read_bytes() == before


def test_full_parent_drift_fails_before_original_proof_or_write(creation, monkeypatch):
    monkeypatch.setattr(creator.review.core.previous, "checked_control",
                        lambda *_: ({"changed": True}, creation.history.cells))
    with pytest.raises(RuntimeError, match="full original parent/schedule changed"):
        create(creation)
    assert "original-proof" not in creation.calls
    assert not creation.output.exists()


def test_original_proof_failure_is_not_waived(creation, monkeypatch):
    def reject(*_):
        raise RuntimeError("not exact field misuse")

    monkeypatch.setattr(creator.review, "proof", reject)
    with pytest.raises(RuntimeError, match="not exact field misuse"):
        create(creation)
    assert not creation.output.exists()


def test_manifest_drift_during_proof_fails_before_write(creation, monkeypatch):
    count = 0

    def fence(*_):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("source/config/metadata drift")

    monkeypatch.setattr(environment, "fence", fence)
    with pytest.raises(RuntimeError, match="source/config/metadata drift"):
        create(creation)
    assert not creation.output.exists()


def test_unchanged_guard_exempts_only_current_audit_lease(tmp_path):
    proc = tmp_path / "proc"
    own, foreign = os.getpid(), os.getpid() + 1
    for pid in (own, foreign):
        directory = proc / str(pid)
        directory.mkdir(parents=True)
        (directory / "cmdline").write_bytes(tmp_path.name.encode() + b"\0python\0")
    (tmp_path / "queue-lease.json").write_text(json.dumps({"pid": own}))
    with pytest.raises(RuntimeError, match="inactive queue and atomic actions"):
        original_inactive(tmp_path, proc_root=proc)
    original_inactive(tmp_path, proc_root=proc, allow_current_audit_lease=True)
    (tmp_path / "queue-process-foreign.json").write_text(json.dumps({"pid": foreign}))
    with pytest.raises(RuntimeError, match="inactive queue and atomic actions"):
        original_inactive(tmp_path, proc_root=proc, allow_current_audit_lease=True)


def test_target_must_be_the_last_original_attempt_even_after_generic_repair(history):
    history.raw.authorize_generic_repair(
        history.target, original_admission_sha256="f" * 64,
        repair_audit_sha256="5" * 64, new_execution_sha256="4" * 64)
    history.raw.reserve("cell4", "later-valid-run", "4" * 64)
    history.raw.settle("later-valid-run", "valid", "completed", "6" * 64)
    with pytest.raises(RuntimeError, match="only the exact target"):
        creator.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_extra_inventory_addition_is_rejected_without_journal_rewrite(creation, monkeypatch):
    before = creation.history.raw.path.read_bytes()
    monkeypatch.setattr(environment, "current_inventory", lambda: {
        "model_json_sidecars": {"unexpected.json": "7" * 64},
        "initial_field_sidecars": {
            creation.output.name: environment.cadence.digest(creation.output)},
        "derived_field_sidecars": {}})
    with pytest.raises(RuntimeError, match="only the exact target initial-field sidecar"):
        create(creation)
    assert creation.history.raw.path.read_bytes() == before
    assert json.loads(creation.output.read_text()) == creation.proof
