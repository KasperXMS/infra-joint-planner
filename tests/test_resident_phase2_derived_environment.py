import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
extension = importlib.import_module("large_scale_resident_phase2_derived_environment_v1")
environment = extension.environment


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class SyntheticHistory(AttemptLedger):
    """Produce history previously admitted by successive historical reviewers."""

    def _check_reservation(self, cell_id):
        pass


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    monkeypatch.setattr(extension.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(environment, "CELL", "cell-0")
    monkeypatch.setattr(environment, "RUN", "excluded-original")
    cells = tuple(SimpleNamespace(cell_id=f"cell-{i}") for i in range(6))
    journal = tmp_path / "phase2-attempts.jsonl"
    raw = SyntheticHistory(journal, tuple(c.cell_id for c in cells), "a" * 64)
    raw.reserve("cell-0", environment.RUN, "b" * 64)
    raw.settle(environment.RUN, "confounder", "admission_unverifiable", environment.RAW_SHA)
    raw.reserve("cell-0", "replacement", "b" * 64)
    raw.settle("replacement", "valid", "wrong_answer", "c" * 64)
    groups = (("model_json_sidecars", extension.field.core.DIRECTORY,
               extension.field.core, "model"),
              ("initial_field_sidecars", extension.field.review.DIRECTORY,
               extension.field.review, "initial"),
              ("derived_field_sidecars", extension.derived.DIRECTORY,
               extension.derived, "derived"))
    value = {"phase2_schedule_sha256": "a" * 64}
    called = []
    for i, (key, directory, reviewer, run) in enumerate(groups, 1):
        raw.reserve(f"cell-{i}", run, "b" * 64)
        raw.settle(run, "confounder", "field-or-model-gate", "d" * 64)
        proof = {"reviewed_admission_sha256": "e" * 64,
                 "reviewed_admission": {"disposition": "valid", "reason": run},
                 "derived_field_proof": [{"action_id": "one"}, {"action_id": "two"}]}
        path = save(tmp_path / directory / (run + ".json"), proof)
        value[key] = {path.name: extension.cadence.digest(path)}

        def verify(path, attempt, expected=run):
            assert attempt.run_id == expected and attempt.disposition == "confounder"
            called.append(expected)
            return extension.read(path)

        monkeypatch.setattr(reviewer, "verify_sidecar", verify)
    sidecar = save(tmp_path / environment.DIRECTORY / (environment.RUN + ".json"), {})

    def exclusion(path, attempt):
        assert path == sidecar and attempt == raw.attempts[0]
        called.append("excluded")
        return {}

    monkeypatch.setattr(environment, "verify_exclusion", exclusion)
    return SimpleNamespace(root=tmp_path, raw=raw, cells=cells, value=value,
                           sidecar=sidecar, called=called)


def view(fixture, ready=True):
    return extension.membership(fixture.value, fixture.cells, fixture.sidecar,
                                require_dispatch_ready=ready)


def test_every_disjoint_review_is_reproved_without_changing_raw_journal(reviewed):
    before = reviewed.raw.path.read_bytes()
    ledger = view(reviewed)
    assert reviewed.called == ["model", "initial", "derived", "excluded"]
    assert ledger.original_attempts == reviewed.raw.attempts
    assert len(ledger.completed_cells) == 4
    assert ledger.attempts[0].disposition == "operational_excluded"
    assert ledger.attempts[-1].reason == extension.derived.REASON
    assert reviewed.raw.path.read_bytes() == before
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(environment.CELL, "third", "b" * 64)


@pytest.mark.parametrize("damage", ["missing", "overlap", "extra", "exclude_overlap"])
def test_missing_overlapping_or_unmatched_findings_cannot_be_waived(reviewed, damage):
    new = reviewed.value["derived_field_sidecars"]
    if damage == "missing":
        new.clear()
    elif damage == "overlap":
        new.update(reviewed.value["model_json_sidecars"])
    elif damage == "extra":
        new["unknown.json"] = "f" * 64
    else:
        new[environment.RUN + ".json"] = "f" * 64
    with pytest.raises(RuntimeError, match="disjoint exact"):
        view(reviewed)
    assert reviewed.called == []


def test_matching_sidecar_hash_never_replaces_full_proof(reviewed, monkeypatch):
    def reject(*_):
        raise RuntimeError("actual transformation drift")

    monkeypatch.setattr(extension.derived, "verify_sidecar", reject)
    with pytest.raises(RuntimeError, match="transformation drift"):
        view(reviewed)


def test_sidecar_drift_rejected_before_derived_proof(reviewed):
    save(reviewed.root / extension.derived.DIRECTORY / "derived.json", {})
    with pytest.raises(RuntimeError, match="sidecar drift"):
        view(reviewed)
    assert "derived" not in reviewed.called


def test_new_findings_stop_original_batch_before_next_cell(reviewed):
    ledger = view(reviewed)
    executed = []

    def execute(cell):
        executed.append(cell.cell_id)
        ledger.reserve(cell.cell_id, "new-unreviewed", "b" * 64)
        ledger.settle("new-unreviewed", "confounder", "new-gate", "f" * 64)

    with pytest.raises(RuntimeError, match="finding"):
        environment.run_batches(reviewed.cells, ledger, execute, lambda: None, lambda: None)
    assert executed == ["cell-4"]


def test_full_control_binds_only_membership_and_preserves_defaults(reviewed, monkeypatch):
    namespace = {"checked_membership": lambda *_: None}
    exec("def checked(path, default='retained', *, keyword='also-retained'):\n"
         "    return default, keyword, checked_membership(path, (), "
         "require_dispatch_ready=True)\n", namespace)
    original = namespace["checked"]
    monkeypatch.setattr(extension.field, "checked_control", original)
    monkeypatch.setattr(extension, "membership", lambda value, *_args, **_kwargs: value)
    result = extension.full_control({"old": True}, reviewed.sidecar,
                                    reviewed.value["derived_field_sidecars"])
    assert result == ("retained", "also-retained", {
        "old": True, "derived_field_sidecars": reviewed.value["derived_field_sidecars"]})
    assert original.__globals__["checked_membership"] is namespace["checked_membership"]


def test_projection_routes_exact_reason_and_reports_all_failures(reviewed, monkeypatch):
    ledger = view(reviewed)
    gate = save(reviewed.root / "gate.json", {"schedule": [
        {"cell_id": cell.cell_id} for cell in reviewed.cells]})
    control = save(reviewed.root / "control.json", reviewed.value)
    value = {**reviewed.value, "parent": {"gate_path": str(gate),
             "execution_freeze_sha256": "b" * 64, "phase2_schedule_sha256": "a" * 64},
             "control_path": str(control), "baseline_run_ids": [environment.RUN]}
    routed = []

    def old_admission(_root, attempt):
        routed.append(attempt.run_id)
        return {"disposition": "valid", "old": True}

    def new_admission(_root, attempt):
        routed.append("derived-only:" + attempt.run_id)
        return {"disposition": "valid", "derived": True}

    monkeypatch.setattr(extension.field.review, "effective_admission", old_admission)
    monkeypatch.setattr(extension.derived, "effective_admission", new_admission)
    monkeypatch.setattr(extension.field.base, "settled", lambda _root, attempt, _sha: {
        "run_id": attempt.run_id})
    result = extension.collect(value, ledger)
    assert routed == ["replacement", "model", "initial", "derived-only:derived"]
    assert extension.field.review.effective_admission is old_admission
    assert result["derived_field_reviewed_attempts"] == 1
    assert result["confirmed_derived_absent_record_field_failures"] == 2
    record = result["rows"][3]["attempts"][0]
    assert record["confirmed_absent_record_field_failures"] == 2
    assert record["original_disposition"] == "confounder"
    assert record["environment_stage"] == "post-strata"
    assert result["rows"][0]["attempts"][0]["effective_admission"]["disposition"] == (
        "operational_excluded")


def test_real_run_keeps_startup_defaults_and_original_globals(tmp_path, monkeypatch):
    monkeypatch.setattr(extension.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(extension.frozen, "require_remote", lambda: None)
    old_module = environment.run.__globals__["MODULE"]
    old_startup = extension.cadence.assert_startup_safe.__globals__["MODULE"]
    with pytest.raises(RuntimeError, match="owned launch-pinned"):
        extension.run(tmp_path / "invalid.json", "a" * 64)
    assert environment.run.__globals__["MODULE"] == old_module
    assert extension.cadence.assert_startup_safe.__globals__["MODULE"] == old_startup


def test_freeze_inactive_guard_precedes_any_input(tmp_path, monkeypatch):
    monkeypatch.setattr(extension.frozen, "require_remote", lambda: None)

    def reject(*_):
        raise RuntimeError("live original controller")

    monkeypatch.setattr(extension.field.core.previous.gate.evidence.private,
                        "assert_inactive", reject)
    with pytest.raises(RuntimeError, match="live original controller"):
        extension.freeze(tmp_path / "absent.json", "a" * 64, tmp_path / "output.json")


@pytest.mark.parametrize("changed", [False, True])
def test_parent_manifest_pin_preserves_original_journal_prefix(reviewed, monkeypatch, changed):
    before = reviewed.raw.path.read_bytes()
    value = {"version": "resident-phase2-user-authorized-environment-continuation-v1",
             "baseline_journal_bytes": len(before),
             "baseline_journal_sha256": extension.cadence.digest(reviewed.raw.path)}
    path = save(reviewed.root / (environment.PREFIX + "001.json"), value)
    checked = []
    monkeypatch.setattr(environment, "fence", lambda *args: checked.append(args))
    if changed:
        reviewed.raw.path.write_bytes(before.replace(b"excluded-original", b"excluded-changed"))
        with pytest.raises(RuntimeError, match="original environment journal prefix changed"):
            extension.parent_fence(path, extension.cadence.digest(path))
    else:
        assert extension.parent_fence(path, extension.cadence.digest(path)) == value
    assert len(checked) == 1 and checked[0][2] == value


def test_freeze_preserves_ancestor_order_and_adds_new_proofs(reviewed, monkeypatch):
    ledger = view(reviewed)
    original = {a.run_id: a for a in ledger.original_attempts}
    pairs = [{"raw": asdict(original[a.run_id]), "effective": asdict(a)}
             for a in ledger.attempts if a.run_id in {"model", "initial"}]
    control = save(reviewed.root / "control.json", reviewed.value)
    receipt = save(reviewed.root / "receipt.json", {})
    old_path = reviewed.root / (environment.PREFIX + "001.json")
    parent = {"phase2_schedule_sha256": "a" * 64, "execution_freeze_sha256": "b" * 64}
    old = {"version": "resident-phase2-user-authorized-environment-continuation-v1",
           "parent": parent, "control_path": str(control), "ledger_path": str(receipt),
           "sidecar_path": str(reviewed.sidecar), "historical_reviews": list(reversed(pairs)),
           "exclusion": {"raw": asdict(ledger.exclusion[0]),
                         "effective": asdict(ledger.exclusion[1])},
           "baseline_run_ids": [environment.RUN],
           "bound_metadata_files": {str(control): extension.cadence.digest(control),
                                    str(receipt): extension.cadence.digest(receipt)},
           "model_json_sidecars": reviewed.value["model_json_sidecars"],
           "initial_field_sidecars": reviewed.value["initial_field_sidecars"]}
    save(old_path, old)
    before = reviewed.raw.path.read_bytes()
    calls = []
    monkeypatch.setattr(extension.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(extension, "parent_fence", lambda *_: old)
    monkeypatch.setattr(environment, "require_strata_stopped", lambda: None)
    monkeypatch.setattr(extension.field.core.previous.gate.evidence.private, "assert_inactive",
                        lambda *_: calls.append("inactive"))
    monkeypatch.setattr(extension.field, "validate", lambda *_: calls.append("old-control"))
    monkeypatch.setattr(extension, "full_control", lambda *_: (parent, reviewed.cells))
    monkeypatch.setattr(extension, "sources", lambda: {"extension": "sha"})
    monkeypatch.setattr(extension, "collect", lambda *_: {"all_attempts": len(ledger.attempts)})
    monkeypatch.setattr(environment, "audit_wire", lambda value, _: calls.append(value))
    output = reviewed.root / (extension.PREFIX + "001.json")
    result = extension.freeze(old_path, extension.cadence.digest(old_path), output)
    assert result["historical_reviews"][:2] == old["historical_reviews"]
    assert result["historical_reviews"][2]["raw"]["run_id"] == "derived"
    assert result["baseline_run_ids"] == [environment.RUN]
    assert result["continuation_baseline_run_ids"] == list(original)
    assert result["baseline_journal_bytes"] == len(before)
    assert result["parent_environment_manifest_sha256"] == extension.cadence.digest(old_path)
    assert str(reviewed.root / extension.derived.DIRECTORY / "derived.json") in result[
        "bound_metadata_files"]
    assert reviewed.raw.path.read_bytes() == before
    assert "old-control" in calls and {"all_attempts": 5} in calls
    assert calls.count("inactive") == 2
    assert extension.read(output) == result
    with pytest.raises(FileExistsError):
        extension.freeze(old_path, extension.cadence.digest(old_path), output)


@pytest.mark.parametrize("damage", ["source", "derived", "metadata", "reference", "execution"])
def test_fence_checks_new_and_old_authority(reviewed, monkeypatch, damage):
    metadata = save(reviewed.root / "metadata.json", {})
    value = {**reviewed.value, "extension_version": extension.VERSION,
             "source_sha256": {"source": "correct"},
             "bound_metadata_files": {str(metadata): extension.cadence.digest(metadata)},
             "parent": {"execution_freeze_sha256": "b" * 64},
             "reference_sha256": extension.provenance_sha256({}),
             "parent_environment_manifest_path": str(reviewed.root / "old.json"),
             "parent_environment_manifest_sha256": "c" * 64}
    path = save(reviewed.root / (extension.PREFIX + "001.json"), value)
    monkeypatch.setattr(extension, "sources", lambda: {"source": (
        "wrong" if damage == "source" else "correct")})
    monkeypatch.setattr(extension.frozen, "reference", lambda: (
        {"changed": True} if damage == "reference" else {}))
    monkeypatch.setattr(extension.frozen, "verify_freeze", lambda: (
        "wrong" if damage == "execution" else "b" * 64))
    if damage == "metadata":
        save(metadata, {"changed": True})
    elif damage == "derived":
        save(reviewed.root / extension.derived.DIRECTORY / "new.json", {})
    monkeypatch.setattr(extension, "parent_fence", lambda *_: pytest.fail(
        "mutated extension must fail before checking ancestor"))
    with pytest.raises(RuntimeError, match="immutable source/evidence drift"):
        extension.fence(path, extension.cadence.digest(path), value)
