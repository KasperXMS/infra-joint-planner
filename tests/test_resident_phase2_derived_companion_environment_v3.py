"""Versioned derived proof keeps the existing exact five-group authority."""

import importlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_resident_phase2_derived_companion_environment_v2 as previous_tests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
environment = importlib.import_module(
    "large_scale_resident_phase2_derived_companion_environment_v3")
history = previous_tests.history
filtered_history = previous_tests.filtered_history
native_history = previous_tests.native_history
renewal_history = previous_tests.renewal_history
legacy_prepared = previous_tests.prepared
save = previous_tests.previous_tests.save


@pytest.fixture
def prepared(legacy_prepared, monkeypatch):
    state = legacy_prepared
    previous_tests.add(state)
    value = previous_tests.extend(state)
    parent = state.history.root / environment.PARENT_NAME
    monkeypatch.setattr(environment, "PARENT_SHA", environment.cadence.digest(parent))
    monkeypatch.setattr(environment, "sources", lambda: {"derived-companion": "source"})
    monkeypatch.setattr(environment, "collect", lambda _value, ledger: {
        "preserved": len(ledger.original_attempts), "admitted": len(ledger.completed_cells)})
    old_reviewer = environment.derived.ancestor.verify_sidecar

    def verify(path, attempt):
        proof = json.loads(path.read_text())
        if proof.get("version") == environment.derived.VERSION:
            if proof["run_id"] != attempt.run_id or proof.get("proof_valid") is not True:
                raise RuntimeError("independent derived companion reproduction failed")
            return proof
        return old_reviewer(path, attempt)

    monkeypatch.setattr(environment.derived, "verify_sidecar", verify)
    return SimpleNamespace(history=state.history, previous=state, old=parent, old_value=value)


def add(state, run="derived126", cell="cell-9"):
    state.history.raw.reserve(cell, run, "b" * 64)
    state.history.raw.settle(run, "confounder", environment.field.review.field.GATE, "3" * 64)
    raw = state.history.raw.attempts[-1]
    proof = {"version": environment.derived.VERSION, "run_id": run,
             "reviewed_admission_sha256": "4" * 64, "proof_valid": True,
             "derived_field_proof": [{"field": "text"}],
             "read_artifact_limit_proof": [{"action": "large-read"}],
             "output_collision_proof": [{"action": "reuse-output"}]}
    path = save(state.history.root / environment.derived.DIRECTORY /
                               (run + ".json"), proof)
    pair = {"raw": asdict(raw), "effective": asdict(replace(raw, disposition="valid",
             reason=environment.derived.REASON, receipt_sha256="4" * 64))}
    return path, pair


def extend(state, suffix="001", control="013", parent=None):
    old = state.old if parent is None else parent
    return environment.freeze(old, environment.cadence.digest(old),
        state.history.root / ("phase2-field-reviewed-control-freeze-" + control + ".json"),
        state.history.root / ("phase2-field-ledger-freeze-" + control + ".json"),
        state.history.root / (environment.PREFIX + suffix + ".json"))


def test_new_derived_proof_joins_same_group_and_all_ancestors_remain_exact(prepared):
    path, pair = add(prepared)
    immutable = {p: p.read_bytes() for p in prepared.history.root.rglob("*") if p.is_file()}
    methods = (environment.previous.membership, environment.previous.full_control,
               environment.previous.collect, environment.derived.original.verify_sidecar)
    namespaces = [dict(method.__globals__) for method in methods]
    value = extend(prepared)
    manifest = prepared.history.root / (environment.PREFIX + "001.json")
    environment.fence(manifest, environment.cadence.digest(manifest), value)
    assert environment.GROUPS is environment.previous.GROUPS and len(environment.GROUPS) == 5
    assert value["historical_reviews"] == [*prepared.old_value["historical_reviews"], pair]
    assert value["new_review_sidecars"] == {**{key: {} for key in environment.GROUPS},
        "derived_field_sidecars": {path.name: environment.cadence.digest(path)}}
    assert value["derived_field_sidecars"].items() >= (
        prepared.old_value["derived_field_sidecars"].items())
    for key in ("parent", "exclusion", "baseline_run_ids", "native_argument_sidecars"):
        assert value[key] == prepared.old_value[key]
    assert all(p.read_bytes() == before for p, before in immutable.items())
    assert all(method.__globals__ == before for method, before in zip(
        methods, namespaces, strict=True))


def test_future_renewal_requires_exact_nonempty_addition_not_new_proof_group(prepared):
    add(prepared)
    first = extend(prepared)
    first_path = prepared.history.root / (environment.PREFIX + "001.json")
    path, pair = add(prepared, "derived127", "cell-10")
    second = extend(prepared, "002", "014", first_path)
    assert second["historical_reviews"] == [*first["historical_reviews"], pair]
    assert second["new_review_sidecars"]["derived_field_sidecars"] == {
        path.name: environment.cadence.digest(path)}
    with pytest.raises(RuntimeError, match="nonempty"):
        extend(prepared, "003", "015", prepared.history.root / (environment.PREFIX + "002.json"))


@pytest.mark.parametrize("damage", ["new-proof", "old-proof", "raw-pair", "unproved",
                                   "pending", "overlap", "old-source", "metadata",
                                   "journal", "execution", "live", "wire", "full-gate"])
def test_every_finding_and_drift_fails_before_new_authority_write(prepared, monkeypatch, damage):
    path, _pair = add(prepared)
    if damage == "new-proof":
        proof = json.loads(path.read_text())
        proof["proof_valid"] = False
        save(path, proof)
    elif damage == "old-proof":
        name = next(iter(prepared.old_value["derived_field_sidecars"]))
        save(path.with_name(name), {"changed": True})
    elif damage == "raw-pair":
        parent = json.loads(prepared.old.read_text())
        parent["historical_reviews"][-1]["effective"]["receipt_sha256"] = "f" * 64
        save(prepared.old, parent)
        monkeypatch.setattr(environment, "PARENT_SHA", environment.cadence.digest(prepared.old))
    elif damage in ("unproved", "pending"):
        prepared.history.raw.reserve("cell-9", "unknown", "b" * 64)
        if damage == "unproved":
            prepared.history.raw.settle("unknown", "confounder", "other-defect", "f" * 64)
    elif damage == "overlap":
        save(path.with_name("native105.json"), {})
    elif damage == "old-source":
        monkeypatch.setattr(environment.previous, "sources", lambda: {"drift": "source"})
    elif damage == "metadata":
        save(Path(prepared.old_value["control_path"]), {"drift": True})
    elif damage == "journal":
        prepared.history.raw.path.write_bytes(prepared.history.raw.path.read_bytes().replace(
            b"excluded-original", b"excluded-changed"))
    elif damage == "execution":
        monkeypatch.setattr(environment.frozen, "verify_freeze", lambda: "f" * 64)
    else:
        def reject(*_args, **_kwargs):
            raise RuntimeError("closed generic guard")
        if damage == "live":
            monkeypatch.setattr(environment.field.core.previous.gate.evidence.private,
                                "assert_inactive", reject)
        elif damage == "wire":
            monkeypatch.setattr(environment.environment, "audit_wire", reject)
        else:
            monkeypatch.setattr(environment, "full_control", reject)
    with pytest.raises((RuntimeError, KeyError)):
        extend(prepared)
    assert not (prepared.history.root / "phase2-field-reviewed-control-freeze-013.json").exists()
    assert not (prepared.history.root / "phase2-field-ledger-freeze-013.json").exists()
    assert not (prepared.history.root / (environment.PREFIX + "001.json")).exists()


@pytest.mark.parametrize("target", ["control", "ledger", "manifest"])
def test_exclusive_targets_never_overwrite_existing_evidence(prepared, target):
    add(prepared)
    names = {"control": "phase2-field-reviewed-control-freeze-013.json",
             "ledger": "phase2-field-ledger-freeze-013.json",
             "manifest": environment.PREFIX + "001.json"}
    path = save(prepared.history.root / names[target], {"preserve": True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        extend(prepared)
    assert path.read_bytes() == before


def test_unpinned_parent_and_historical_review_reason_change_are_rejected(prepared, monkeypatch):
    add(prepared)
    monkeypatch.setattr(environment, "PARENT_SHA", "0" * 64)
    with pytest.raises(RuntimeError, match="pinned derived companion v2"):
        extend(prepared)


def test_unchanged_runtime_cadence_and_group_directories():
    assert environment.cadence.INTERVAL == 16
    assert environment.current_inventory is environment.previous.current_inventory
    assert environment.environment.run_batches is environment.previous.environment.run_batches
    assert environment.derived.DIRECTORY == environment.derived.original.DIRECTORY
    assert environment.derived.REASON == environment.derived.original.REASON


def test_projection_retains_v2_companion_version_and_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(environment.frozen, "ROOT", tmp_path)
    records = []
    hashes = {}
    for run, version in (("old109", environment.derived.ANCESTOR_VERSION),
                         ("new126", environment.derived.VERSION)):
        path = save(tmp_path / environment.derived.DIRECTORY / (run + ".json"), {
            "version": version, "reviewed_admission_sha256": run,
            "read_artifact_limit_proof": [1], "output_collision_proof": [1]})
        hashes[path.name] = environment.cadence.digest(path)
        records.append({"reason": environment.derived.REASON,
                        "run_id": run, "receipt_sha256": run})
    monkeypatch.setattr(environment.previous, "collect", lambda *_: {
        "rows": [{"attempts": records}]})
    result = environment.collect({"derived_field_sidecars": hashes}, None)
    assert result["derived_companion_reviewed_attempts"] == 2
    assert records[0]["derived_companion_review_version"] == environment.derived.ANCESTOR_VERSION
    assert records[1]["derived_companion_review_version"] == environment.derived.VERSION
    assert all(record["read_artifact_limit_proof_count"] == 1 for record in records)
    assert all(record["output_collision_proof_count"] == 1 for record in records)
