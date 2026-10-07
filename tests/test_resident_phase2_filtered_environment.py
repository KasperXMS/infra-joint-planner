import importlib
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
filtered = importlib.import_module("large_scale_resident_phase2_filtered_environment_v1")
renewed_tests = importlib.import_module("test_resident_phase2_renewed_environment")
history = renewed_tests.history
original_collect = filtered.collect


@pytest.fixture
def filtered_history(history, monkeypatch):
    old = history.root / filtered.PARENT_NAME
    old_value = filtered.renewed.freeze(
        history.derived_manifest, filtered.cadence.digest(history.derived_manifest),
        history.root / "phase2-field-reviewed-control-freeze-008.json",
        history.root / "phase2-field-ledger-freeze-008.json", old)
    monkeypatch.setattr(filtered, "PARENT_SHA", filtered.cadence.digest(old))
    monkeypatch.setattr(filtered, "sources", lambda: {"filtered-env": "source"})
    history.raw.reserve("cell-5", "filtered103", "b" * 64)
    history.raw.settle("filtered103", "confounder", "exact-field-gate", "f" * 64)
    path = renewed_tests.save(history.root / filtered.filtered.DIRECTORY / "filtered103.json", {
        "run_id": "filtered103", "reviewed_admission_sha256": "9" * 64,
        "derived_field_proof": [{"action": 1}, {"action": 2}]})
    raw = history.raw.attempts[-1]
    pair = {"raw": asdict(raw), "effective": asdict(replace(
        raw, disposition="valid", reason=filtered.filtered.REASON, receipt_sha256="9" * 64))}

    def verify(sidecar, attempt):
        assert sidecar == path and attempt == raw
        history.calls.append("filtered-proof")
        return filtered.read(sidecar)

    monkeypatch.setattr(filtered.filtered, "verify_sidecar", verify)
    monkeypatch.setattr(filtered, "collect", lambda _value, ledger: {
        "preserved": len(ledger.original_attempts), "admitted": len(ledger.completed_cells)})
    return SimpleNamespace(history=history, old=old, old_value=old_value,
                           path=path, pair=pair)


def extend(state, suffix="001", control="009", parent=None):
    old = state.old if parent is None else parent
    return filtered.freeze(old, filtered.cadence.digest(old),
        state.history.root / ("phase2-field-reviewed-control-freeze-" + control + ".json"),
        state.history.root / ("phase2-field-ledger-freeze-" + control + ".json"),
        state.history.root / (filtered.PREFIX + suffix + ".json"))


def test_filtered_extension_preserves_all_old_groups_71_and_raw_evidence(filtered_history):
    state = filtered_history
    before = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    result = extend(state)
    output = state.history.root / (filtered.PREFIX + "001.json")
    filtered.fence(output, filtered.cadence.digest(output), result)
    assert result["historical_reviews"] == [*state.old_value["historical_reviews"], state.pair]
    assert result["exclusion"] == state.old_value["exclusion"]
    assert result["baseline_run_ids"] == state.old_value["baseline_run_ids"]
    assert result["new_review_sidecars"] == {
        **{k: {} for k in filtered.renewed.GROUPS},
        "filtered_field_sidecars": {state.path.name: filtered.cadence.digest(state.path)}}
    assert all(p.read_bytes() == data for p, data in before.items())
    assert "filtered-proof" in state.history.calls
    assert ("all-wire", {"preserved": 7, "admitted": 6}) in state.history.calls
    ledger = filtered.membership({**filtered.read(Path(result["control_path"])),
        "derived_field_sidecars": result["derived_field_sidecars"],
        "filtered_field_sidecars": result["filtered_field_sidecars"]},
        state.history.cells, state.history.sidecar, require_dispatch_ready=True)
    assert len(ledger.completed_cells) == 6
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(filtered.environment.CELL, "third", "b" * 64)


@pytest.mark.parametrize("damage", ["unproved", "unmatched", "overlap", "pending", "old-proof"])
def test_filtered_extension_has_exact_membership_and_no_wildcard(filtered_history, damage):
    state = filtered_history
    if damage == "unmatched":
        renewed_tests.save(state.path.with_name("extra.json"), {})
    elif damage == "overlap":
        renewed_tests.save(state.path.with_name("initial.json"), {})
    elif damage == "old-proof":
        renewed_tests.save(state.history.root / filtered.field.review.DIRECTORY / "initial.json",
                           {})
    else:
        state.history.raw.reserve("cell-6", "unproved", "b" * 64)
        if damage != "pending":
            state.history.raw.settle("unproved", "confounder", "new-gate", "f" * 64)
    with pytest.raises(RuntimeError):
        extend(state)
    assert not (state.history.root / "phase2-field-reviewed-control-freeze-009.json").exists()
    assert not (state.history.root / (filtered.PREFIX + "001.json")).exists()


def test_matching_hash_cannot_replace_filtered_source_proof(filtered_history, monkeypatch):
    def reject(*_):
        raise RuntimeError("filtered source proof failed")

    monkeypatch.setattr(filtered.filtered, "verify_sidecar", reject)
    with pytest.raises(RuntimeError, match="source proof failed"):
        extend(filtered_history)


def test_exact_base_authority_required_not_an_unpinned_similar_name(filtered_history, monkeypatch):
    monkeypatch.setattr(filtered, "PARENT_SHA", "0" * 64)
    with pytest.raises(RuntimeError, match="pinned renewed003"):
        extend(filtered_history)


def test_filtered_manifest_fences_fourth_group_and_never_repeats_creator(filtered_history):
    state = filtered_history
    result = extend(state)
    path = state.history.root / (filtered.PREFIX + "001.json")
    with pytest.raises(FileExistsError):
        extend(state)
    renewed_tests.save(state.path.with_name("new.json"), {})
    with pytest.raises(RuntimeError, match="current filtered manifest/inventory drift"):
        filtered.fence(path, filtered.cadence.digest(path), result)


def test_old_v1_sources_functions_and_inventory_helpers_never_mutated(filtered_history):
    old_membership = filtered.renewed.membership
    old_groups = filtered.renewed.GROUPS
    old_proof = filtered.filtered.previous.proof
    before = {Path(m.__file__): Path(m.__file__).read_bytes() for m in (
        filtered.renewed, filtered.renewed.previous, filtered.filtered.previous)}
    extend(filtered_history)
    assert filtered.renewed.membership is old_membership
    assert old_groups == filtered.renewed.GROUPS
    assert filtered.filtered.previous.proof is old_proof
    assert all(p.read_bytes() == data for p, data in before.items())


def test_fourth_group_cannot_represent_environmental_exclusion(filtered_history):
    value = {**filtered_history.old_value,
             "filtered_field_sidecars": {filtered.environment.RUN + ".json": "0" * 64}}
    with pytest.raises(RuntimeError, match="disjoint"):
        filtered.inventory(value)


def test_existing_control_can_be_reused_without_modification(filtered_history):
    state = filtered_history
    old_control, old_receipt = (Path(state.old_value[k]) for k in ("control_path", "ledger_path"))
    before = old_control.read_bytes(), old_receipt.read_bytes()
    output = state.history.root / (filtered.PREFIX + "001.json")
    value = filtered.freeze(state.old, filtered.cadence.digest(state.old),
                            old_control, old_receipt, output)
    assert (old_control.read_bytes(), old_receipt.read_bytes()) == before
    assert value["control_path"] == str(old_control)


def test_environment_cadence_and_new_finding_stop_remain_original():
    assert filtered.cadence.INTERVAL == 16
    assert filtered.environment.run_batches is filtered.renewed.environment.run_batches


def test_inventory_rejects_bad_path_hash_and_removed_old_group(filtered_history):
    old = filtered.inventory(filtered_history.old_value)
    for name in ("../escape.json", "plain", filtered.environment.RUN + ".json"):
        with pytest.raises(RuntimeError):
            filtered.inventory({**filtered_history.old_value, "filtered_field_sidecars": {
                name: "a" * 64}})
    with pytest.raises(RuntimeError):
        filtered.inventory({**filtered_history.old_value,
                            "filtered_field_sidecars": {"x.json": "bad"}})
    removed = {**old, "derived_field_sidecars": {}}
    with pytest.raises(RuntimeError, match="removed or changed"):
        filtered.extension_delta(old, removed)


def test_projection_uses_filtered_admission_adapter_and_counts_exact_proof(
        filtered_history, monkeypatch):
    state = filtered_history
    value = {**state.old_value, **filtered.current_inventory()}
    ledger = filtered.membership({**filtered.read(Path(value["control_path"])),
        "derived_field_sidecars": value["derived_field_sidecars"],
        "filtered_field_sidecars": value["filtered_field_sidecars"]},
        state.history.cells, state.history.sidecar, require_dispatch_ready=True)
    record = {"run_id": "filtered103", "reason": filtered.filtered.REASON,
              "receipt_sha256": "9" * 64}

    def project(_value, _ledger):
        return {"rows": [{"attempts": [record]}]}

    monkeypatch.setattr(filtered.environment, "collect", project)
    result = original_collect(value, ledger)
    assert result["confirmed_filtered_absent_record_field_failures"] == 2
    assert record["filtered_record_field_proof_count"] == 2
    assert result["new_model_calls"] == 0
    assert result["new_store_or_corpus_body_decoded"] is False
