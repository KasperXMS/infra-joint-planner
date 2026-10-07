import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
wrapper = importlib.import_module("large_scale_resident_phase2_filtered_field_review_v1")
environment = importlib.import_module("large_scale_resident_phase2_filtered_environment_v1")
heldout_field = importlib.import_module("test_resident_phase2_field_review").heldout_field
history = importlib.import_module("test_resident_phase2_renewed_field_review").history


@pytest.fixture
def wrapped(heldout_field, monkeypatch):
    root, directory, ledger, parent, old, historical, original, task = heldout_field
    paths = (*wrapper.bindings.records.SOURCE_PATHS, wrapper.core.SOURCES[0])
    monkeypatch.setattr(wrapper.filtered, "SOURCE_PATHS", paths)
    app = root / "app-input-cardinality-repair-003"
    monkeypatch.setattr(wrapper.previous, "import_module", lambda name: SimpleNamespace(
        __file__=str(app / ("src/" + name.replace(".", "/") + ".py"))))
    monkeypatch.setattr(wrapper.filtered, "review", lambda *_: {
        "derived_field_proof": [{"action_id": "failed",
                                 "source_preserving_filter_ancestors": ["filter"]}]})
    (directory / "tc-attestation.json").write_text(json.dumps({
        "cleanup_error": None, "original_qdisc": {}, "restored_qdisc": {}}))
    (directory / "runs/run4/result.json").write_text(json.dumps({
        "execution_completed": True, "evaluation": {"format_valid": True, "score": 1.0}}))
    return SimpleNamespace(root=root, directory=directory, ledger=ledger,
                           parent=parent, old=old, original=original)


def test_filtered_proof_reuses_complete_original_sources_without_mutating_v1(wrapped):
    state = wrapped
    before = {p: p.read_bytes() for p in state.directory.rglob("*") if p.is_file()}
    original_proof = wrapper.previous.proof
    value = wrapper.proof(state.root, state.ledger.attempts[0], state.parent, state.old)
    assert value["reviewed_admission"]["reason"] == wrapper.REASON
    assert (value["reviewed_admission"]["original_evaluation"]
            == state.original["original_evaluation"])
    assert value["reviewer_sources_sha256"] == wrapper.sources()
    assert Path(wrapper.filtered.__file__).name in value["reviewer_sources_sha256"]
    assert Path(wrapper.previous.__file__).name in value["reviewer_sources_sha256"]
    assert value["new_store_or_corpus_body_decoded"] is False
    assert value["formal_execution_changed"] is value["replacement_authorized"] is False
    assert wrapper.previous.proof is original_proof
    assert all(p.read_bytes() == data for p, data in before.items())
    assert "PRIVATE" not in json.dumps(value)


@pytest.mark.parametrize("damage", ["historical", "worker", "imports", "network", "shutdown",
                                  "residency", "admission", "no-filter", "irrelevant-filter"])
def test_filtered_proof_cannot_waive_source_cleanup_or_nonfiltered_failure(wrapped, monkeypatch,
                                                                         damage):
    state = wrapped
    if damage == "historical":
        def reject(*_):
            raise RuntimeError("historical drift")

        monkeypatch.setattr(wrapper.bindings, "verify_record", reject)
    elif damage == "worker":
        worker_file = (state.root / "app-input-cardinality-repair-003"
                       / wrapper.filtered.SOURCE_PATHS[0])
        worker_file.write_text("modified")
    elif damage == "imports":
        file = state.root / "different.py"
        file.write_text("different implementation")
        monkeypatch.setattr(wrapper.previous, "import_module",
                            lambda _: SimpleNamespace(__file__=str(file)))
    elif damage in {"no-filter", "irrelevant-filter"}:
        monkeypatch.setattr(wrapper.filtered, "review", lambda *_: {
            "derived_field_proof": [{"action_id": "failed"}],
            "inferred_record_contracts": {"unrelated": {"producer_operator": "filter_records"}}})
    else:
        name, key, replacement = {
            "network": ("tc-attestation.json", "cleanup_error", "failed"),
            "shutdown": ("worker-shutdown.json", "verified_exited", False),
            "residency": ("private/residency-validation.json", "passed", False),
            "admission": ("admission.json", "problems", ["new-unrelated-finding"])}[damage]
        path = state.directory / name
        value = json.loads(path.read_text())
        value[key] = replacement
        path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        wrapper.proof(state.root, state.ledger.attempts[0], state.parent, state.old)


def test_filtered_sidecar_requires_reproduced_sources_and_exact_effective_receipt(wrapped):
    state = wrapped
    original = state.ledger.attempts[0]
    value = wrapper.proof(state.root, original, state.parent, state.old)
    path = state.root / wrapper.DIRECTORY / (original.run_id + ".json")
    path.parent.mkdir()
    path.write_text(json.dumps(value))
    wrapper.verify_sidecar(path, original)
    effective = replace(original, disposition="valid", reason=wrapper.REASON,
                        receipt_sha256=provenance_sha256(value["reviewed_admission"]))
    assert wrapper.effective_admission(state.root, effective) == value["reviewed_admission"]
    value["reviewed_admission"]["disposition"] = "confounder"
    path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        wrapper.effective_admission(state.root, effective)
    with pytest.raises(RuntimeError):
        wrapper.verify_sidecar(path, original)
    assert original.disposition == "confounder"


@pytest.fixture
def creation(history, monkeypatch):
    root = history.root
    calls = []
    manifest = root / environment.PARENT_NAME
    control, gate = root / "control.json", root / "gate.json"
    history.value.update(control_path=str(control), **{k: {} for k in environment.GROUPS})
    history.value["parent"]["gate_path"] = str(gate)
    manifest.write_text(json.dumps(history.value))
    control.write_text(json.dumps({"parent_control_path": str(root / "parent.json")}))
    gate.write_text("{}")
    monkeypatch.setattr(environment, "PARENT_SHA", "a" * 64)
    monkeypatch.setattr(wrapper.core.frozen, "ROOT", root)
    monkeypatch.setattr(wrapper.core.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(wrapper.renewed, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(wrapper.renewed.environment, "require_strata_stopped",
                        lambda: calls.append("strata"))
    monkeypatch.setattr(wrapper.core.previous.gate.evidence.private,
                        "assert_inactive", lambda *_, **kw: calls.append(
                            "inactive-own-lease" if kw.get("allow_current_audit_lease")
                            else "inactive"))
    monkeypatch.setattr(wrapper.core.previous, "cells_from_gate", lambda *_: history.cells)
    monkeypatch.setattr(wrapper.core.previous, "checked_control",
                        lambda *_: (history.value["parent"], history.cells))
    value = {"derived_field_proof": [1, 2], "actual_manager_schema_wire_proof": [1, 2, 3]}

    def prove(_root, target, _parent, _historical):
        assert target == history.raw.attempts[-1]
        calls.append("source-proof")
        return value

    monkeypatch.setattr(wrapper, "proof", prove)
    monkeypatch.setattr(wrapper, "verify_sidecar", lambda *_: calls.append("verified"))
    before_inventory = {k: {} for k in environment.GROUPS}
    output = root / wrapper.DIRECTORY / (history.target + ".json")

    def current():
        return {**before_inventory, "filtered_field_sidecars": {
            output.name: environment.cadence.digest(output)} if output.exists() else {}}

    monkeypatch.setattr(environment, "current_inventory", current)
    return SimpleNamespace(history=history, manifest=manifest, output=output,
                           value=value, calls=calls)


def create(state):
    return wrapper.create_review(state.manifest, "a" * 64, state.history.target,
                                 state.history.root / "historical.json")


def test_creator_preserves_all_old_reviews_and_exact_journal_creates_once(creation):
    state = creation
    before = state.history.raw.path.read_bytes()
    result = create(state)
    assert state.history.raw.path.read_bytes() == before
    assert json.loads(state.output.read_text()) == state.value
    assert result["confirmed_field_failures"] == 2
    assert result["actual_manager_requests"] == 3
    assert result["retry"] is False
    assert result["atomic_execution_changed"] is False
    assert state.calls[-1] == "inactive"
    with pytest.raises(RuntimeError):
        create(state)
    assert json.loads(state.output.read_text()) == state.value


@pytest.mark.parametrize("damage", ["active", "strata", "parent", "proof", "extra-inventory"])
def test_creator_stops_before_write_on_new_or_unproven_state(creation, monkeypatch, damage):
    state = creation

    def reject(*_args, **_kwargs):
        raise RuntimeError("reject unsafe state")

    if damage == "active":
        monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive", reject)
    elif damage == "strata":
        monkeypatch.setattr(wrapper.renewed.environment, "require_strata_stopped", reject)
    elif damage == "parent":
        monkeypatch.setattr(wrapper.core.previous, "checked_control",
                            lambda *_: ({"different": True}, state.history.cells))
    elif damage == "proof":
        monkeypatch.setattr(wrapper, "proof", reject)
    else:
        monkeypatch.setattr(environment, "current_inventory", lambda: {
            **{k: {} for k in environment.GROUPS},
            "filtered_field_sidecars": {"unmatched.json": "b" * 64}})
    before = state.history.raw.path.read_bytes()
    with pytest.raises(RuntimeError):
        create(state)
    assert not state.output.exists()
    assert state.history.raw.path.read_bytes() == before


def test_lasttarget_and_existing_review_replay_use_unchanged_fail_closed_helper(history):
    value = history.value
    before = history.raw.path.read_bytes()
    ledger, target = wrapper.creator.pending_ledger(value, history.cells,
                                                    history.raw.path, history.target)
    assert target == history.raw.attempts[-1]
    assert len(ledger.completed_cells) == 4
    assert history.raw.path.read_bytes() == before
    value["historical_reviews"].pop()
    with pytest.raises(RuntimeError):
        wrapper.creator.pending_ledger(value, history.cells, history.raw.path, history.target)
