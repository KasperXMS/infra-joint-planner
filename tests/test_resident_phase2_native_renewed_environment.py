import importlib
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
renewed = importlib.import_module("large_scale_resident_phase2_native_renewed_environment_v1")
native_tests = importlib.import_module("test_resident_phase2_native_environment")
history = native_tests.history
filtered_history = native_tests.filtered_history
native_history = native_tests.native_history
save = native_tests.save


@pytest.fixture
def renewal_history(native_history, monkeypatch):
    value = native_tests.extend(native_history)
    path = native_history.history.root / renewed.PARENT_NAME
    monkeypatch.setattr(renewed, "PARENT_SHA", renewed.cadence.digest(path))
    monkeypatch.setattr(renewed, "sources", lambda: {"five-group-renewal": "source"})
    monkeypatch.setattr(renewed, "collect", lambda _value, ledger: {
        "preserved": len(ledger.original_attempts), "admitted": len(ledger.completed_cells)})
    return SimpleNamespace(history=native_history.history, old=path, old_value=value,
                           native=native_history)


def extend(state, suffix="001", control="011", parent=None):
    old = state.old if parent is None else parent
    return renewed.freeze(old, renewed.cadence.digest(old),
        state.history.root / ("phase2-field-reviewed-control-freeze-" + control + ".json"),
        state.history.root / ("phase2-field-ledger-freeze-" + control + ".json"),
        state.history.root / (renewed.PREFIX + suffix + ".json"))


def new_field(state, run="initial107", cell="cell-7"):
    return state.history.add(run, cell, 1)


def test_initial_only_renewal_keeps_five_maps_native105_exclusion_and_all_old_bytes(
        renewal_history):
    state = renewal_history
    proof, pair = new_field(state)
    immutable = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    functions = (renewed.previous.membership, renewed.previous.full_control,
                 renewed.previous.collect, renewed.field.review.verify_sidecar)
    result = extend(state)
    path = state.history.root / (renewed.PREFIX + "001.json")
    renewed.fence(path, renewed.cadence.digest(path), result)
    assert renewed.GROUPS is renewed.previous.GROUPS
    assert result["native_argument_sidecars"] == state.old_value["native_argument_sidecars"]
    assert result["historical_reviews"] == [*state.old_value["historical_reviews"], pair]
    assert state.native.pair in result["historical_reviews"]
    assert result["new_review_sidecars"] == {**{k: {} for k in renewed.GROUPS},
        "initial_field_sidecars": {proof.name: renewed.cadence.digest(proof)}}
    for key in ("exclusion", "baseline_run_ids", "parent"):
        assert result[key] == state.old_value[key]
    assert all(p.read_bytes() == data for p, data in immutable.items())
    assert functions == (renewed.membership, renewed.full_control,
                         renewed.previous.collect, renewed.field.review.verify_sidecar)
    assert ("all-wire", {"preserved": 9, "admitted": 8}) in state.history.calls
    ledger = renewed.membership(native_tests.membership_value(result), state.history.cells,
                                state.history.sidecar, require_dispatch_ready=True)
    assert len(ledger.completed_cells) == 8 and len(ledger.original_attempts) == 9
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(renewed.environment.CELL, "third", "b" * 64)


@pytest.mark.parametrize("group", [0, 1, 2])
def test_any_original_group_can_renew_without_native_addition(renewal_history, group):
    state = renewal_history
    proof, pair = state.history.add("new-original-group", "cell-7", group)
    result = extend(state)
    assert result["historical_reviews"][-1] == pair
    assert result["new_review_sidecars"][renewed.GROUPS[group]] == {
        proof.name: renewed.cadence.digest(proof)}
    assert result["new_review_sidecars"]["native_argument_sidecars"] == {}


def test_mixed_original_and_native_delta_and_future_own_renewal(renewal_history):
    state = renewal_history
    original_proof, original_pair = new_field(state)
    state.history.raw.reserve("cell-8", "native108", "b" * 64)
    state.history.raw.settle("native108", "confounder", "runtime_error:ModelBehaviorError",
                             "3" * 64)
    proof = save(state.native.path.with_name("native108.json"), {
        "run_id": "native108", "reviewed_admission_sha256": "4" * 64,
        "native_argument_proof": [{"action": 2}]})
    raw = state.history.raw.attempts[-1]
    pair = {"raw": asdict(raw), "effective": asdict(replace(
        raw, disposition="valid", reason=renewed.previous.native.REASON,
        receipt_sha256="4" * 64))}
    first = extend(state)
    first_path = state.history.root / (renewed.PREFIX + "001.json")
    assert first["historical_reviews"] == [*state.old_value["historical_reviews"],
                                           original_pair, pair]
    assert first["new_review_sidecars"]["initial_field_sidecars"] == {
        original_proof.name: renewed.cadence.digest(original_proof)}
    assert first["new_review_sidecars"]["native_argument_sidecars"] == {
        proof.name: renewed.cadence.digest(proof)}
    immutable = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    new_proof, new_pair = new_field(state, "initial109", "cell-9")
    second = extend(state, "002", "012", first_path)
    second_path = state.history.root / (renewed.PREFIX + "002.json")
    renewed.fence(second_path, renewed.cadence.digest(second_path), second)
    assert second["historical_reviews"] == [*first["historical_reviews"], new_pair]
    assert second["new_review_sidecars"]["initial_field_sidecars"] == {
        new_proof.name: renewed.cadence.digest(new_proof)}
    assert second["native_argument_sidecars"] == first["native_argument_sidecars"]
    assert all(p.read_bytes() == data for p, data in immutable.items()
               if p != state.history.raw.path)
    with pytest.raises(RuntimeError, match="nonempty"):
        extend(state, "003", "013", second_path)


def test_empty_delta_and_unpinned_initial_parent_are_rejected(renewal_history, monkeypatch):
    state = renewal_history
    with pytest.raises(RuntimeError, match="nonempty"):
        extend(state)
    new_field(state)
    monkeypatch.setattr(renewed, "PARENT_SHA", "0" * 64)
    with pytest.raises(RuntimeError, match="pinned native001"):
        extend(state)


@pytest.mark.parametrize("target", ["control", "receipt", "output"])
def test_every_creator_target_must_be_fresh_and_never_overwritten(renewal_history, target):
    state = renewal_history
    new_field(state)
    names = {"control": "phase2-field-reviewed-control-freeze-011.json",
             "receipt": "phase2-field-ledger-freeze-011.json",
             "output": renewed.PREFIX + "001.json"}
    path = save(state.history.root / names[target], {"preserve": True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError, match="all three targets absent"):
        extend(state)
    assert path.read_bytes() == before


@pytest.mark.parametrize("damage", ["unproved", "pending", "unmatched", "overlap",
                                     "old-proof", "new-proof", "old-source", "metadata",
                                     "journal", "execution", "reference", "private-live",
                                     "full-gate", "wire-audit", "inventory-growth"])
def test_all_fail_closed_checks_precede_every_new_authority_write(
        renewal_history, monkeypatch, damage):
    state = renewal_history
    proof, _pair = new_field(state)
    if damage in ("unproved", "pending"):
        state.history.raw.reserve("cell-8", "unknown", "b" * 64)
        if damage == "unproved":
            state.history.raw.settle("unknown", "confounder", "new-error", "f" * 64)
    elif damage == "unmatched":
        save(proof.with_name("absent-raw.json"), {})
    elif damage == "overlap":
        save(proof.with_name("native105.json"), {})
    elif damage == "old-proof":
        save(state.native.path, {"changed": True})
    elif damage == "new-proof":
        def reject(path, attempt):
            if attempt.run_id == "initial107":
                raise RuntimeError("independent original field proof failed")
            return renewed.read(path)
        monkeypatch.setattr(renewed.field.review, "verify_sidecar", reject)
    elif damage == "old-source":
        monkeypatch.setattr(renewed.previous, "sources", lambda: {"changed": "source"})
    elif damage == "metadata":
        save(Path(state.old_value["control_path"]), {"changed": True})
    elif damage == "journal":
        state.history.raw.path.write_bytes(state.history.raw.path.read_bytes().replace(
            b"excluded-original", b"excluded-modified"))
    elif damage == "execution":
        monkeypatch.setattr(renewed.frozen, "verify_freeze", lambda: "f" * 64)
    elif damage == "reference":
        monkeypatch.setattr(renewed.frozen, "reference", lambda: {"changed": True})
    elif damage == "private-live":
        def reject(*_args):
            raise RuntimeError("original global private guard rejects live process")
        monkeypatch.setattr(renewed.field.core.previous.gate.evidence.private,
                            "assert_inactive", reject)
    elif damage == "full-gate":
        monkeypatch.setattr(renewed, "full_control", lambda *_args: ({"changed": True}, ()))
    elif damage == "wire-audit":
        def reject(*_args):
            raise RuntimeError("wire audit rejects original recipients")
        monkeypatch.setattr(renewed.environment, "audit_wire", reject)
    else:
        def grow(*_args):
            save(proof.with_name("drift.json"), {})
            return {}
        monkeypatch.setattr(renewed.environment, "audit_wire", grow)
    with pytest.raises((RuntimeError, KeyError)):
        extend(state)
    assert not (state.history.root / "phase2-field-reviewed-control-freeze-011.json").exists()
    assert not (state.history.root / "phase2-field-ledger-freeze-011.json").exists()
    assert not (state.history.root / (renewed.PREFIX + "001.json")).exists()


def test_fence_pins_sources_pairs_delta_current_population_and_acyclic_history(
        renewal_history, monkeypatch):
    state = renewal_history
    new_field(state)
    value = extend(state)
    path = state.history.root / (renewed.PREFIX + "001.json")
    with pytest.raises(RuntimeError, match="acyclic"):
        renewed.history_fence(path, renewed.cadence.digest(path), renewed.inventory(value),
                              frozenset({path.resolve()}))
    mutated = {**value, "new_review_sidecars": {k: {} for k in renewed.GROUPS}}
    save(path, mutated)
    with pytest.raises(RuntimeError, match="exact nonempty"):
        renewed.fence(path, renewed.cadence.digest(path), mutated)
    last = value["historical_reviews"][-1]
    mutated = {**value, "historical_reviews": [*value["historical_reviews"][:-1],
        {**last, "effective": {**last["effective"], "reason": "invented"}}]}
    save(path, mutated)
    with pytest.raises(RuntimeError, match="raw/effective review pairs changed"):
        renewed.fence(path, renewed.cadence.digest(path), mutated)
    save(path, value)
    monkeypatch.setattr(renewed, "sources", lambda: {"changed": "source"})
    with pytest.raises(RuntimeError, match="source/config/metadata drift"):
        renewed.fence(path, renewed.cadence.digest(path), value)


def test_same_five_group_api_and_original_execution_cadence_stop_are_reused():
    assert renewed.membership is renewed.previous.membership
    assert renewed.full_control is renewed.previous.full_control
    assert renewed.collect is renewed.previous.collect
    assert renewed.inventory is renewed.previous.inventory
    assert renewed.extension_delta is renewed.previous.extension_delta
    assert renewed.cadence.INTERVAL == 16
    assert renewed.environment.run_batches is renewed.previous.environment.run_batches
    assert renewed.environment.run.__globals__["MODULE"] == renewed.previous.environment.MODULE
