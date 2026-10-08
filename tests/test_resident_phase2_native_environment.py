import importlib
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
native = importlib.import_module("large_scale_resident_phase2_native_environment_v1")
filtered_tests = importlib.import_module("test_resident_phase2_filtered_environment")
history = filtered_tests.history
filtered_history = filtered_tests.filtered_history
save = filtered_tests.renewed_tests.save
original_collect = native.collect
field = native.field


@pytest.fixture
def native_history(filtered_history, monkeypatch):
    prior = filtered_history
    old_value = filtered_tests.extend(prior)
    old = prior.history.root / native.PARENT_NAME
    monkeypatch.setattr(native, "PARENT_SHA", native.cadence.digest(old))
    monkeypatch.setattr(native, "sources", lambda: {"native-env": "source"})
    monkeypatch.setattr(native.native, "sources", lambda: {"native-review": "source"})
    raw = prior.history.raw
    raw.reserve("cell-6", "native105", "b" * 64)
    raw.settle("native105", "confounder", "runtime_error:ModelBehaviorError", "1" * 64)
    path = save(prior.history.root / native.native.DIRECTORY / "native105.json", {
        "run_id": "native105", "reviewed_admission_sha256": "2" * 64,
        "native_argument_proof": [{"action": 1}],
        "reviewed_admission": {"disposition": "valid", "reason": native.native.REASON}})
    original = raw.attempts[-1]
    pair = {"raw": asdict(original), "effective": asdict(replace(
        original, disposition="valid", reason=native.native.REASON, receipt_sha256="2" * 64))}

    def verify(sidecar, attempt):
        proof = native.read(sidecar)
        assert proof["run_id"] == attempt.run_id and attempt.disposition == "confounder"
        prior.history.calls.append("native-proof")
        return proof

    monkeypatch.setattr(native.native, "verify_sidecar", verify)
    monkeypatch.setattr(native, "collect", lambda _value, ledger: {
        "preserved": len(ledger.original_attempts), "admitted": len(ledger.completed_cells)})
    return SimpleNamespace(history=prior.history, old=old, old_value=old_value,
                           path=path, pair=pair, prior=prior)


def extend(state, suffix="001", control="010", parent=None):
    old = state.old if parent is None else parent
    return native.freeze(old, native.cadence.digest(old),
        state.history.root / ("phase2-field-reviewed-control-freeze-" + control + ".json"),
        state.history.root / ("phase2-field-ledger-freeze-" + control + ".json"),
        state.history.root / (native.PREFIX + suffix + ".json"))


def membership_value(value):
    return {**native.read(Path(value["control_path"])),
            **{k: value[k] for k in native.GROUPS[2:]}}


def test_fifth_group_preserves_all_ancestor_bytes_pairs_exclusion_and_inventory(native_history):
    state = native_history
    before = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    value = extend(state)
    path = state.history.root / (native.PREFIX + "001.json")
    native.fence(path, native.cadence.digest(path), value)
    assert (*native.filtered.GROUPS, "native_argument_sidecars") == native.GROUPS
    assert value["historical_reviews"] == [*state.old_value["historical_reviews"], state.pair]
    for key in (*native.filtered.GROUPS, "exclusion", "baseline_run_ids", "parent"):
        assert value[key] == state.old_value[key]
    assert value["new_review_sidecars"] == {**{k: {} for k in native.filtered.GROUPS},
        "native_argument_sidecars": {state.path.name: native.cadence.digest(state.path)}}
    assert value["new_retry_authority"] is False
    assert all(p.read_bytes() == content for p, content in before.items())
    assert ("all-wire", {"preserved": 8, "admitted": 7}) in state.history.calls
    ledger = native.membership(membership_value(value), state.history.cells,
                               state.history.sidecar, require_dispatch_ready=True)
    assert len(ledger.original_attempts) == 8
    assert len(ledger.completed_cells) == 7
    assert ledger.exclusion[1].disposition == "operational_excluded"
    assert sum(a.disposition == "operational_excluded" for a in ledger.attempts) == 1
    with pytest.raises(RuntimeError, match="exhausted"):
        ledger.reserve(native.environment.CELL, "third", "b" * 64)


@pytest.mark.parametrize("damage", ["unproved", "unmatched", "overlap", "pending", "old-proof"])
def test_exact_disjoint_five_map_coverage_has_no_wildcard(native_history, damage):
    state = native_history
    if damage == "unmatched":
        save(state.path.with_name("extra.json"), {})
    elif damage == "overlap":
        save(state.path.with_name("filtered103.json"), {})
    elif damage == "old-proof":
        save(state.history.root / native.field.review.DIRECTORY / "initial.json", {})
    else:
        state.history.raw.reserve("cell-7", "unproved", "b" * 64)
        if damage != "pending":
            state.history.raw.settle("unproved", "confounder", "new-gate", "f" * 64)
    with pytest.raises(RuntimeError):
        extend(state)
    assert not (state.history.root / "phase2-field-reviewed-control-freeze-010.json").exists()
    assert not (state.history.root / (native.PREFIX + "001.json")).exists()


def test_membership_requires_all_five_maps_without_aliasing(native_history):
    state = native_history
    value = {**native.read(Path(state.old_value["control_path"])),
             **native.current_inventory()}
    for key in native.GROUPS:
        incomplete = {k: v for k, v in value.items() if k != key}
        with pytest.raises(RuntimeError, match="all five"):
            native.membership(incomplete, state.history.cells, state.history.sidecar,
                              require_dispatch_ready=True)
    with pytest.raises(RuntimeError, match="all five"):
        native.extension_delta({k: {} for k in native.filtered.GROUPS},
                               native.current_inventory())


def test_matching_sha_does_not_replace_native_independent_source_proof(native_history, monkeypatch):
    def reject(*_):
        raise RuntimeError("native SDK argument source proof failed")

    monkeypatch.setattr(native.native, "verify_sidecar", reject)
    with pytest.raises(RuntimeError, match="source proof failed"):
        extend(native_history)


def test_initial_authority_requires_pinned_filtered001(native_history, monkeypatch):
    monkeypatch.setattr(native, "PARENT_SHA", "0" * 64)
    with pytest.raises(RuntimeError, match="pinned filtered001"):
        extend(native_history)


def test_old_four_map_parent_accepts_separate_native_directory(native_history):
    state = native_history
    assert "native_argument_sidecars" not in state.old_value
    current = native.current_inventory()
    assert native.history_fence(state.old, native.cadence.digest(state.old), current) == (
        state.old_value)
    assert native.historical_control(state.old_value) == (
        native.read(Path(state.old_value["control_path"])))
    claimed = {**state.old_value, "native_argument_sidecars": {}}
    path = save(state.history.root / "phase2-filtered-environment-cadence-freeze-forged.json",
                claimed)
    with pytest.raises(RuntimeError, match="cannot claim native"):
        native.history_fence(path, native.cadence.digest(path), current)


def test_fifth_group_cannot_claim_original71_or_other_groups(native_history):
    value = native_history.old_value
    for name in (native.environment.RUN + ".json", "model.json", "initial.json",
                 "derived81.json", "filtered103.json", "../escape.json", "plain"):
        with pytest.raises(RuntimeError, match="disjoint"):
            native.inventory({**value, "native_argument_sidecars": {name: "a" * 64}})
    with pytest.raises(RuntimeError):
        native.inventory({**value, "native_argument_sidecars": {"x.json": "BAD"}})


@pytest.mark.parametrize("damage", ["source", "ancestor-source", "journal", "metadata", "proof",
                                     "private-guard", "execution", "reference"])
def test_drift_stops_before_any_authority_creation(native_history, monkeypatch, damage):
    state = native_history
    if damage == "source":
        first = extend(state)
        path = state.history.root / (native.PREFIX + "001.json")
        monkeypatch.setattr(native, "sources", lambda: {"changed": "source"})
        with pytest.raises(RuntimeError, match="source/config/metadata drift"):
            native.fence(path, native.cadence.digest(path), first)
        return
    if damage == "ancestor-source":
        monkeypatch.setattr(native.filtered, "sources", lambda: {"changed": "source"})
    elif damage == "journal":
        state.history.raw.path.write_bytes(state.history.raw.path.read_bytes().replace(
            b"excluded-original", b"excluded-modified"))
    elif damage == "metadata":
        save(Path(state.old_value["control_path"]), {"changed": True})
    elif damage == "proof":
        save(state.prior.path, {"changed": True})
    elif damage == "private-guard":
        def reject(*_):
            raise RuntimeError("original global private guard")
        monkeypatch.setattr(native.field.core.previous.gate.evidence.private,
                            "assert_inactive", reject)
    elif damage == "execution":
        monkeypatch.setattr(native.frozen, "verify_freeze", lambda: "f" * 64)
    else:
        monkeypatch.setattr(native.frozen, "reference", lambda: {"changed": True})
    with pytest.raises(RuntimeError):
        extend(state)
    assert not (state.history.root / "phase2-field-reviewed-control-freeze-010.json").exists()


def test_native_current_fence_creator_and_acyclic_history(native_history):
    state = native_history
    value = extend(state)
    path = state.history.root / (native.PREFIX + "001.json")
    with pytest.raises(FileExistsError):
        extend(state)
    with pytest.raises(RuntimeError, match="acyclic"):
        native.history_fence(path, native.cadence.digest(path), native.inventory(value),
                             frozenset({path.resolve()}))
    save(state.path.with_name("unreviewed.json"), {})
    with pytest.raises(RuntimeError, match="current native manifest/inventory drift"):
        native.fence(path, native.cadence.digest(path), value)


def test_future_five_map_renewal_preserves_first_snapshot(native_history):
    state = native_history
    first = extend(state)
    first_path = state.history.root / (native.PREFIX + "001.json")
    immutable = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    state.history.raw.reserve("cell-7", "native106", "b" * 64)
    state.history.raw.settle("native106", "confounder", "runtime_error:ModelBehaviorError",
                             "3" * 64)
    path = save(state.path.with_name("native106.json"), {
        "run_id": "native106", "reviewed_admission_sha256": "4" * 64,
        "native_argument_proof": [{"action": 2}]})
    raw = state.history.raw.attempts[-1]
    pair = {"raw": asdict(raw), "effective": asdict(replace(
        raw, disposition="valid", reason=native.native.REASON, receipt_sha256="4" * 64))}
    second = extend(state, "002", "011", first_path)
    second_path = state.history.root / (native.PREFIX + "002.json")
    native.fence(second_path, native.cadence.digest(second_path), second)
    assert second["historical_reviews"] == [*first["historical_reviews"], pair]
    assert second["new_review_sidecars"] == {**{k: {} for k in native.filtered.GROUPS},
        "native_argument_sidecars": {path.name: native.cadence.digest(path)}}
    assert all(p.read_bytes() == data for p, data in immutable.items()
               if p != state.history.raw.path)
    with pytest.raises(RuntimeError, match="review additions required"):
        extend(state, "003", "012", second_path)


def test_historical_fifth_group_removal_or_hash_change_is_rejected(native_history):
    state = native_history
    old = native.current_inventory()
    for group in native.GROUPS:
        removed = {**old, group: {}}
        if old[group]:
            with pytest.raises(RuntimeError, match="removed or changed"):
                native.extension_delta(old, removed)
    changed = {**old, "native_argument_sidecars": {state.path.name: "0" * 64}}
    with pytest.raises(RuntimeError, match="removed or changed"):
        native.extension_delta(old, changed)


def test_new_delta_and_manifest_pairs_cannot_be_forged(native_history):
    state = native_history
    value = extend(state)
    path = state.history.root / (native.PREFIX + "001.json")
    mutated = {**value, "historical_reviews": [*value["historical_reviews"][:-1],
        {**state.pair, "effective": {**state.pair["effective"], "reason": "invented"}}]}
    save(path, mutated)
    with pytest.raises(RuntimeError, match="raw/effective review pairs changed"):
        native.fence(path, native.cadence.digest(path), mutated)
    mutated = {**value, "new_review_sidecars": {k: {} for k in native.GROUPS}}
    save(path, mutated)
    with pytest.raises(RuntimeError, match="exact nonempty"):
        native.fence(path, native.cadence.digest(path), mutated)


def test_existing_original_control_can_be_reused_byte_identically(native_history):
    state = native_history
    control, receipt = (Path(state.old_value[k]) for k in ("control_path", "ledger_path"))
    before = control.read_bytes(), receipt.read_bytes()
    value = native.freeze(state.old, native.cadence.digest(state.old), control, receipt,
                          state.history.root / (native.PREFIX + "001.json"))
    assert (control.read_bytes(), receipt.read_bytes()) == before
    assert value["control_path"] == str(control)


def test_projection_native_adapter_metadata_retains_original_fields(native_history, monkeypatch):
    state = native_history
    value = {**state.old_value, **native.current_inventory()}
    ledger = native.membership(membership_value(value), state.history.cells,
                               state.history.sidecar, require_dispatch_ready=True)
    record = {"run_id": "native105", "reason": native.native.REASON,
              "receipt_sha256": "2" * 64, "original_disposition": "confounder",
              "evaluation": None, "completion": False, "failed_call_tokens": None}
    routed = []
    monkeypatch.setattr(native.native, "effective_admission",
                        lambda *_: routed.append("native") or {})

    def project(_value, _ledger):
        field.review.effective_admission(state.history.root, ledger.attempts[-1])
        return {"rows": [{"attempts": [record]}]}

    monkeypatch.setattr(native.environment, "collect", project)
    monkeypatch.setattr(native.filtered, "collect", filtered_tests.original_collect)
    result = original_collect(value, ledger)
    assert result["confirmed_native_argument_failures"] == 1
    assert result["native_argument_reviewed_attempts"] == 1
    assert result["native_argument_proof_source_sha256"] == {"native-review": "source"}
    assert record["native_argument_proof_count"] == 1
    assert record["native_argument_sidecar_sha256"] == native.cadence.digest(state.path)
    assert record["evaluation"] is None and record["completion"] is False
    assert record["failed_call_tokens"] is None and record["original_disposition"] == "confounder"
    assert result["new_model_calls"] == 0
    assert routed == ["native"]


def test_original_global_functions_and_source_bytes_never_mutated(native_history):
    modules = (native.filtered, native.filtered.renewed, native.environment,
               native.field, native.field.core.previous)
    before = {Path(m.__file__): Path(m.__file__).read_bytes() for m in modules}
    functions = [m.sources for m in modules if hasattr(m, "sources")]
    original_membership = native.filtered.membership
    original_module = native.environment.run.__globals__["MODULE"]
    original_startup = native.cadence.assert_startup_safe.__globals__["MODULE"]
    extend(native_history)
    assert functions == [m.sources for m in modules if hasattr(m, "sources")]
    assert native.filtered.membership is original_membership
    assert native.environment.run.__globals__["MODULE"] == original_module
    assert native.cadence.assert_startup_safe.__globals__["MODULE"] == original_startup
    assert all(p.read_bytes() == data for p, data in before.items())


def test_original_cadence_and_immediate_stop_are_reused(native_history):
    state = native_history
    value = extend(state)
    ledger = native.membership(membership_value(value), state.history.cells,
                               state.history.sidecar, require_dispatch_ready=True)
    audits = []

    def execute(cell):
        ledger.reserve(cell.cell_id, "newfinding", "b" * 64)
        ledger.settle("newfinding", "confounder", "new-failure", "f" * 64)

    with pytest.raises(RuntimeError, match="pending/new finding"):
        native.environment.run_batches(state.history.cells, ledger, execute,
                                       lambda: None, lambda: audits.append(1))
    assert audits == []
    assert native.cadence.INTERVAL == 16
    assert native.environment.run_batches is native.filtered.environment.run_batches
