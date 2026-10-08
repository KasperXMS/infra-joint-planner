"""Five-group initial-field creator preserves frozen reviewers and journals."""

import copy
import importlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
wrapper = importlib.import_module("large_scale_resident_phase2_native_field_review_v1")
native_tests = importlib.import_module("test_resident_phase2_native_argument_review")
native_history = native_tests.history
heldout_field = importlib.import_module("test_resident_phase2_field_review").heldout_field
previous = wrapper.previous


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def history(native_history):
    state = native_history
    old_native = state.raw.attempts[-1]
    reviewed = replace(old_native, disposition="valid", reason=previous.native.REASON,
                       receipt_sha256="9" * 64)
    state.value["historical_reviews"].append({"raw": asdict(old_native),
                                              "effective": asdict(reviewed)})
    native_path = state.root / previous.native.DIRECTORY / (old_native.run_id + ".json")
    put(native_path, {"reviewed_admission_sha256": reviewed.receipt_sha256})
    state.value["native_argument_sidecars"][native_path.name] = previous.cadence.digest(native_path)
    state.target = state.root.name + "-phase2-target107"
    state.raw.reserve("cell6", state.target, "b" * 64)
    state.raw.settle(state.target, "confounder", wrapper.review.field.GATE, "f" * 64)
    return state


def test_pending_replay_preserves_every_group_native_review_and_original_exclusion(history):
    before = history.raw.path.read_bytes()
    ledger, target = wrapper.pending_ledger(history.value, history.cells,
                                            history.raw.path, history.target)
    assert target == history.raw.attempts[-1]
    assert len(ledger.completed_cells) == 6
    assert len(ledger.original_attempts) == 8
    assert ledger.attempts[-2].reason == previous.native.REASON
    assert ledger.attempts[-2].disposition == "valid"
    assert history.raw.path.read_bytes() == before


def test_pending_replay_does_not_accept_a_native_sdk_terminal_gate(native_history):
    state = native_history
    with pytest.raises(RuntimeError, match="only the exact target"):
        wrapper.pending_ledger(state.value, state.cells, state.raw.path, state.target)


@pytest.mark.parametrize("damage", ["model", "initial", "derived", "filtered", "native",
                                   "raw-pair", "exclusion", "pending", "other-finding"])
def test_pending_replay_fails_closed_on_any_historical_or_new_finding(history, damage):
    if damage in {"model", "initial", "derived", "filtered", "native"}:
        index = ("model", "initial", "derived", "filtered", "native").index(damage)
        history.value["historical_reviews"].pop(index)
    elif damage == "raw-pair":
        history.value["historical_reviews"][-1]["raw"]["receipt_sha256"] = "0" * 64
    elif damage == "exclusion":
        history.value["exclusion"]["effective"]["disposition"] = "valid"
    elif damage == "pending":
        lines = history.raw.path.read_bytes().splitlines()
        history.raw.path.write_bytes(b"\n".join(lines[:-1]) + b"\n")
    else:
        history.raw.reserve("cell7", "another-finding", "b" * 64)
        history.raw.settle("another-finding", "confounder", "different-defect", "2" * 64)
    with pytest.raises(RuntimeError):
        wrapper.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_unchanged_proof_retains_evaluation_and_source_schema_bindings(heldout_field):
    root, directory, ledger, parent, old, _, original, _ = heldout_field
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    proof = wrapper.review.proof(root, ledger.attempts[0], parent, old)
    assert proof["reviewed_admission"]["original_evaluation"] == original["original_evaluation"]
    assert proof["reviewed_admission"]["replacement_authorized"] is False
    assert proof["reviewer_sources_sha256"] == wrapper.review.sources()
    assert wrapper.review is wrapper.original.review
    assert all(p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("damage", ["schema", "provider", "source", "other-finding"])
def test_original_proof_is_unchanged_and_fail_closed(heldout_field, monkeypatch, damage):
    root, directory, ledger, parent, old, _, original, _ = heldout_field
    if damage == "schema":
        put(directory / "private/api/call1-request.json", {"messages": []})
    elif damage == "source":
        (root / "app-input-cardinality-repair-003" / wrapper.core.SOURCES[0]).write_text("drift")
    elif damage == "provider":
        reproduced = copy.deepcopy(original)
        reproduced["api_audit"] = {"problems": ["provider_http_failure"]}
        monkeypatch.setattr(wrapper.core.previous.previous, "admission", lambda *_: reproduced)
    else:
        value = copy.deepcopy(original)
        value["problems"].append("another-finding")
        put(directory / "admission.json", value)
    with pytest.raises(RuntimeError):
        wrapper.review.proof(root, ledger.attempts[0], parent, old)


@pytest.fixture
def creation(history, monkeypatch):
    environment = importlib.import_module(
        "large_scale_resident_phase2_native_renewed_environment_v1")
    root = history.root
    calls = []
    manifest = root / environment.PARENT_NAME
    control, gate = root / "control.json", root / "gate.json"
    history.value["control_path"] = str(control)
    history.value["parent"]["gate_path"] = str(gate)
    put(manifest, history.value)
    put(control, {"parent_control_path": str(root / "phase2-control-freeze-001.json")})
    put(gate, {})
    historical = root / "historical-shape.json"
    put(historical, {})
    monkeypatch.setattr(environment, "PARENT_SHA", "a" * 64)
    monkeypatch.setattr(wrapper, "INITIAL_JOURNAL_SHA", previous.cadence.digest(history.raw.path))
    monkeypatch.setattr(wrapper, "HISTORICAL_NAME", historical.name)
    monkeypatch.setattr(wrapper, "HISTORICAL_SHA", previous.cadence.digest(historical))
    monkeypatch.setattr(previous.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(previous, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(previous.environment, "require_strata_stopped",
                        lambda: calls.append("strata"))
    monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive",
                        lambda *_, **kw: calls.append("own-lease" if kw else "inactive"))
    monkeypatch.setattr(wrapper.core.previous, "cells_from_gate", lambda *_: history.cells)
    candidate = {"field_misuse_proof": [1, 2, 3],
                 "actual_manager_schema_wire_proof": list(range(9)),
                 "reviewed_admission_sha256": "8" * 64}
    monkeypatch.setattr(wrapper.review, "proof", lambda *_: candidate)
    monkeypatch.setattr(wrapper.review, "verify_sidecar", lambda *_: calls.append("verified"))
    monkeypatch.setattr(wrapper, "_preflight", lambda *_: calls.append("full-gate-all-five"))
    output = root / wrapper.DIRECTORY / (history.target + ".json")
    expected = environment.inventory(history.value)

    def current():
        return {**expected, "initial_field_sidecars": {
            **expected["initial_field_sidecars"], **({output.name: previous.cadence.digest(output)}
                                                   if output.exists() else {})}}

    monkeypatch.setattr(environment, "current_inventory", current)
    return SimpleNamespace(history=history, environment=environment, manifest=manifest,
                           historical=historical, output=output, candidate=candidate, calls=calls)


def create(state):
    return wrapper.create_review(state.manifest, "a" * 64, state.history.target, state.historical)


def test_creator_preserves_all_previous_bytes_and_writes_original_proof_once(creation):
    state = creation
    before = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    result = create(state)
    assert json.loads(state.output.read_text()) == state.candidate
    assert all(p.read_bytes() == data for p, data in before.items())
    assert result["confirmed_field_failures"] == 3
    assert result["actual_manager_requests"] == 9
    assert result["retry"] is result["atomic_execution_changed"] is False
    assert result["new_model_calls"] == 0
    assert not (state.history.root / "queue-lease.json").exists()
    assert state.calls.index("full-gate-all-five") < state.calls.index("verified")
    with pytest.raises(RuntimeError):
        create(state)


def test_creator_accepts_a_current_renewed_authority_without_reusing_initial_pins(
        creation, monkeypatch):
    state = creation
    state.history.value["extension_version"] = state.environment.VERSION
    state.manifest = state.history.root / (state.environment.PREFIX + "002.json")
    put(state.manifest, state.history.value)
    monkeypatch.setattr(wrapper, "INITIAL_JOURNAL_SHA", "0" * 64)
    monkeypatch.setattr(wrapper, "HISTORICAL_SHA", "0" * 64)
    monkeypatch.setattr(state.environment, "fence", lambda *_: state.calls.append("renewed-fence"))
    create(state)
    assert state.calls.count("renewed-fence") == 2
    assert "fence" not in state.calls


@pytest.mark.parametrize("damage", ["live", "strata", "proof", "full-gate", "manifest",
                                   "journal", "journal-pin", "historical-pin", "inventory"])
def test_creator_rejects_before_write_and_releases_lease(creation, monkeypatch, damage):
    state = creation

    def reject(*_args, **_kwargs):
        raise RuntimeError("unsafe state")

    if damage == "live":
        monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive", reject)
    elif damage == "strata":
        monkeypatch.setattr(previous.environment, "require_strata_stopped", reject)
    elif damage == "proof":
        monkeypatch.setattr(wrapper.review, "proof", reject)
    elif damage == "full-gate":
        monkeypatch.setattr(wrapper, "_preflight", reject)
    elif damage == "manifest":
        monkeypatch.setattr(previous, "fence", reject)
    elif damage == "journal-pin":
        monkeypatch.setattr(wrapper, "INITIAL_JOURNAL_SHA", "0" * 64)
    elif damage == "historical-pin":
        state.historical.write_text("changed")
    elif damage == "inventory":
        expected = state.environment.inventory(state.history.value)
        monkeypatch.setattr(state.environment, "current_inventory", lambda: {
            **expected, "native_argument_sidecars": {}})
    else:
        def advance(*_):
            state.history.raw.path.write_bytes(state.history.raw.path.read_bytes() + b"\n")
        monkeypatch.setattr(wrapper, "_preflight", advance)
    with pytest.raises((RuntimeError, ValueError)):
        create(state)
    assert not state.output.exists()
    assert not (state.history.root / "queue-lease.json").exists()


def test_creator_exact_delta_rejects_a_second_new_review(creation, monkeypatch):
    state = creation
    expected = state.environment.inventory(state.history.value)

    def current():
        if not state.output.exists():
            return expected
        return {**expected, "initial_field_sidecars": {
            **expected["initial_field_sidecars"],
            state.output.name: previous.cadence.digest(state.output)},
            "native_argument_sidecars": {**expected["native_argument_sidecars"],
                                        "unexpected.json": "1" * 64}}

    monkeypatch.setattr(state.environment, "current_inventory", current)
    before = state.history.raw.path.read_bytes()
    with pytest.raises(RuntimeError, match="only the exact target initial-field"):
        create(state)
    assert state.history.raw.path.read_bytes() == before
    assert not (state.history.root / "queue-lease.json").exists()


@pytest.mark.parametrize("damage", [None, "native-proof", "old-pair", "parent", "schedule"])
def test_preflight_runs_all_five_unchanged_reviewers_with_private_candidate_binding(
        history, monkeypatch, damage):
    value = history.value
    value["control_path"] = str(history.root / "control.json")
    calls = []
    reviewers = (wrapper.core, previous.field.review,
                 previous.filtered.renewed.previous.derived, previous.filtered.filtered,
                 previous.native)
    for index, reviewer in enumerate(reviewers):
        def verify(_path, _attempt, index=index):
            calls.append(index)
            if damage == "native-proof" and index == 4:
                raise RuntimeError("native historical source proof drift")
            return {"reviewed_admission_sha256": "9" * 64 if index == 4 else "e" * 64}
        monkeypatch.setattr(reviewer, "verify_sidecar", verify)
    monkeypatch.setattr(previous.environment, "verify_exclusion",
                        lambda *_: calls.append("excluded"))

    def full_gate(_control):
        checked_membership({"phase2_schedule_sha256": "a" * 64}, history.cells,  # noqa: F821
                           require_dispatch_ready=True)
        saved = {"different": True} if damage == "parent" else value["parent"]
        cells = history.cells[:-1] if damage == "schedule" else history.cells
        return saved, cells

    monkeypatch.setattr(previous.field, "checked_control", full_gate)
    target = history.raw.attempts[-1]
    path = history.root / wrapper.DIRECTORY / (target.run_id + ".json")
    candidate = {"reviewed_admission_sha256": "8" * 64}
    if damage == "old-pair":
        value["historical_reviews"][-1]["effective"]["receipt_sha256"] = "0" * 64
    functions = (previous.membership, previous._review_pairs, previous.full_control,
                 previous.field.checked_control)
    before = [dict(fn.__globals__) for fn in functions]
    if damage is None:
        wrapper._preflight(value, previous.inventory(value), path, target, candidate, history.cells)
        assert set(calls) == {0, 1, 2, 3, 4, "excluded"}
        assert calls.count(1) == 1
    else:
        with pytest.raises(RuntimeError):
            wrapper._preflight(value, previous.inventory(value), path, target,
                               candidate, history.cells)
    assert not path.exists()
    assert all(fn.__globals__ == globals_before for fn, globals_before in zip(
        functions, before, strict=True))
