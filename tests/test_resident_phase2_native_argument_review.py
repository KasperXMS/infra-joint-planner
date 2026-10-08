"""Offline native JSON wrapper: no SDK changes, retries or evidence rewrites."""

import copy
import importlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
wrapper = importlib.import_module("large_scale_resident_phase2_native_argument_review_v1")
environment = importlib.import_module("large_scale_resident_phase2_native_environment_v1")
sdk_tests = importlib.import_module("test_resident_sdk_argument_review")
source = sdk_tests.source
field_tests = importlib.import_module("test_resident_phase2_field_review")
heldout_field = field_tests.heldout_field
SyntheticRawHistory = importlib.import_module(
    "test_resident_phase2_renewed_field_review").SyntheticRawHistory


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def wrapped(heldout_field, source, monkeypatch):
    root, directory, ledger, parent, _old, _, _, _ = heldout_field
    api, original, events, request, response = source
    for path in (directory / "private/api").glob("*"):
        path.unlink()
    for path in api.glob("*"):
        put(directory / "private/api" / path.name, json.loads(path.read_text()))
    put(directory / "admission.json", original)
    trace = directory / "runs/run4/trace.jsonl"
    trace.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    put(directory / "tc-attestation.json", {
        "cleanup_error": None, "original_qdisc": {}, "restored_qdisc": {}})
    execution = {"owned_native_sha256": {"app/src/native.py": "a" * 64},
                 "installed_sdk_sources": {"agent": {
                     "import_path": "lexical/agents/agent.py",
                     "resolved_path": "shared/agents/agent.py", "sha256": "b" * 64}}}
    old = root / wrapper.sdk.SEMANTIC_DIRECTORY / (root.name + "-phase1-native.json")
    historical = {"execution_sources": copy.deepcopy(execution)}
    put(old, historical)
    monkeypatch.setattr(wrapper, "HISTORICAL_NAME", old.name)
    monkeypatch.setattr(wrapper, "HISTORICAL_SHA", wrapper.core.legacy.sha256(old))
    monkeypatch.setattr(wrapper.sdk, "verify_sidecar", lambda *_: copy.deepcopy(historical))
    monkeypatch.setattr(wrapper.sdk, "execution_sources", lambda _: copy.deepcopy(execution))
    monkeypatch.setattr(wrapper.previous.previous.previous, "historical_attempt", lambda *_: "old")
    monkeypatch.setattr(wrapper.core.previous.previous, "admission", lambda *_: original)
    attempt = replace(ledger.attempts[0], reason=wrapper.sdk.GATE,
                      receipt_sha256=provenance_sha256(original))
    return SimpleNamespace(root=root, directory=directory, parent=parent, old=old,
                           attempt=attempt, original=original, events=events,
                           request=request, response=response, execution=execution,
                           historical=historical)


def prove(state):
    return wrapper.proof(state.root, state.attempt, state.parent, state.old)


def test_source_bound_native_proof_preserves_original_and_all_raw_bytes(wrapped):
    state = wrapped
    before = {p: p.read_bytes() for p in state.directory.rglob("*") if p.is_file()}
    value = prove(state)
    assert len(value["native_argument_proof"]) == 2
    assert value["execution_sources"] == state.historical["execution_sources"]
    assert value["reviewer_sources_sha256"] == wrapper.sources()
    assert Path(wrapper.sdk.__file__).name in wrapper.sources()
    admission = value["reviewed_admission"]
    assert admission["original_evaluation"] is None
    assert admission["execution_completed"] is False
    assert admission["terminal_failure"] == state.original["terminal_failure"]
    assert value["new_model_calls"] == 0
    assert value["replacement_authorized"] is value["formal_execution_changed"] is False
    assert all(p.read_bytes() == contents for p, contents in before.items())
    assert wrapper.DIRECTORY != wrapper.sdk.SEMANTIC_DIRECTORY


@pytest.mark.parametrize("damage", ["provider", "schema", "later", "truncation", "other-finding",
    "privacy", "history-bytes", "historical-proof", "native", "sdk-hash", "sdk-import",
    "sdk-resolved", "parent", "exit", "shutdown", "residency", "cleanup"])
def test_wrapper_cannot_waive_source_provider_or_unrelated_findings(wrapped, monkeypatch, damage):
    state = wrapped
    api = state.directory / "private/api"
    if damage == "provider":
        usage = json.loads((api / "last-usage.json").read_text())
        usage["status"] = 503
        put(api / "last-usage.json", usage)
    elif damage == "schema":
        state.request["tools"][0]["function"]["parameters"] = {}
        put(api / "last-request.json", state.request)
    elif damage == "later":
        put(api / "late-usage.json", {"call_id": "late", "recipient": "verifier", "status": 200,
                                    "finished_utc": "2026-10-06T13:00:01+00:00"})
    elif damage == "truncation":
        state.response["choices"][0]["finish_reason"] = "length"
        put(api / "last-response.json", state.response)
    elif damage in {"other-finding", "privacy"}:
        if damage == "privacy":
            state.original["api_audit"]["problems"] = ["privacy"]
        else:
            state.original["problems"].append("another-finding")
        put(state.directory / "admission.json", state.original)
        state.attempt = replace(state.attempt, receipt_sha256=provenance_sha256(state.original))
    elif damage == "history-bytes":
        state.old.write_text("{}")
    elif damage == "historical-proof":
        def reject(*_):
            raise RuntimeError("full historical proof drift")
        monkeypatch.setattr(wrapper.sdk, "verify_sidecar", reject)
    elif damage in {"native", "sdk-hash", "sdk-import", "sdk-resolved"}:
        if damage == "native":
            state.execution["owned_native_sha256"]["app/src/native.py"] = "c" * 64
        else:
            key = {"sdk-hash": "sha256", "sdk-import": "import_path",
                   "sdk-resolved": "resolved_path"}[damage]
            state.execution["installed_sdk_sources"]["agent"][key] = "changed"
    elif damage == "parent":
        parent = json.loads(state.parent.read_text())
        parent["source_sha256"] = {}
        put(state.parent, parent)
    else:
        name, key, replacement = {
            "exit": ("process-exit.json", "returncode", 1),
            "shutdown": ("worker-shutdown.json", "verified_exited", False),
            "residency": ("private/residency-validation.json", "passed", False),
            "cleanup": ("tc-attestation.json", "cleanup_error", "failed")}[damage]
        value = json.loads((state.directory / name).read_text())
        value[key] = replacement
        put(state.directory / name, value)
    with pytest.raises(RuntimeError):
        prove(state)


def test_sidecar_reproduction_and_effective_receipt_fail_closed(wrapped):
    state = wrapped
    value = prove(state)
    path = state.root / wrapper.DIRECTORY / (state.attempt.run_id + ".json")
    put(path, value)
    assert wrapper.verify_sidecar(path, state.attempt) == value
    effective = replace(state.attempt, disposition="valid", reason=wrapper.REASON,
                        receipt_sha256=value["reviewed_admission_sha256"])
    assert wrapper.effective_admission(state.root, effective) == value["reviewed_admission"]
    value["reviewed_admission"]["replacement_authorized"] = True
    put(path, value)
    with pytest.raises(RuntimeError):
        wrapper.verify_sidecar(path, state.attempt)
    with pytest.raises(RuntimeError):
        wrapper.effective_admission(state.root, effective)


@pytest.fixture
def history(tmp_path, monkeypatch):
    monkeypatch.setattr(environment.environment, "CELL", "cell0")
    monkeypatch.setattr(environment.environment, "RUN", "excluded")
    monkeypatch.setattr(environment.frozen, "ROOT", tmp_path)
    cells = tuple(SimpleNamespace(cell_id=f"cell{i}") for i in range(8))
    raw = SyntheticRawHistory(tmp_path / "phase2-attempts.jsonl",
                              tuple(c.cell_id for c in cells), "a" * 64)
    raw.reserve("cell0", "excluded", "b" * 64)
    raw.settle("excluded", "confounder", "environment", environment.environment.RAW_SHA)
    excluded = raw.attempts[-1]
    raw.reserve("cell0", "replacement", "b" * 64)
    raw.settle("replacement", "valid", "semantic_failure", "c" * 64)
    reviews = []
    groups = {group: {} for group in environment.GROUPS}
    for i, (group, directory) in enumerate(zip(environment.GROUPS[:-1],
                                               environment._directories()[:-1], strict=True), 1):
        run = group.removesuffix("_sidecars")
        raw.reserve(f"cell{i}", run, "b" * 64)
        raw.settle(run, "confounder", "original-finding", "d" * 64)
        attempt = raw.attempts[-1]
        proof_path = tmp_path / directory / (run + ".json")
        put(proof_path, {})
        groups[group][proof_path.name] = environment.cadence.digest(proof_path)
        reason = (wrapper.core.legacy.REVIEW_REASON, environment.field.review.field.REASON,
                  environment.filtered.renewed.previous.derived.REASON,
                  wrapper.previous.REASON)[i - 1]
        reviews.append({"raw": asdict(attempt), "effective": asdict(replace(
            attempt, disposition="valid", reason=reason, receipt_sha256="e" * 64))})
    target = tmp_path.name + "-phase2-target105"
    raw.reserve("cell5", target, "b" * 64)
    raw.settle(target, "confounder", wrapper.sdk.GATE, "f" * 64)
    sidecar = tmp_path / "exclusion.json"
    put(sidecar, {})
    value = {"parent": {"phase2_schedule_sha256": "a" * 64}, **groups,
             "sidecar_path": str(sidecar), "historical_reviews": reviews,
             "exclusion": {"raw": asdict(excluded), "effective": asdict(replace(
                 excluded, disposition="operational_excluded",
                 reason=environment.environment.REASON,
                 receipt_sha256=environment.cadence.digest(sidecar)))}}
    return SimpleNamespace(raw=raw, root=tmp_path, cells=cells, target=target, value=value)


def test_native_last_target_replay_preserves_all_four_reviews_and_exclusion(history):
    before = history.raw.path.read_bytes()
    ledger, target = wrapper.pending_ledger(history.value, history.cells,
                                            history.raw.path, history.target)
    assert target == history.raw.attempts[-1]
    assert len(ledger.completed_cells) == 5
    assert len(ledger.original_attempts) == 7
    assert history.raw.path.read_bytes() == before
    history.value["historical_reviews"].pop()
    with pytest.raises(RuntimeError):
        wrapper.pending_ledger(history.value, history.cells, history.raw.path, history.target)


def test_native_replay_rejects_initial_field_gate_without_mutating_reviewer(history):
    raw = SyntheticRawHistory(history.root / "wrong-gate.jsonl",
                              tuple(c.cell_id for c in history.cells), "a" * 64)
    for attempt in history.raw.attempts:
        raw.reserve(attempt.cell_id, attempt.run_id, attempt.execution_sha256)
        reason = (wrapper.previous.creator.review.field.GATE
                  if attempt.run_id == history.target else attempt.reason)
        raw.settle(attempt.run_id, attempt.disposition, reason, attempt.receipt_sha256)
    gate = wrapper.previous.creator.review.field.GATE
    with pytest.raises(RuntimeError, match="only the exact target"):
        wrapper.pending_ledger(history.value, history.cells, raw.path, history.target)
    assert gate == wrapper.previous.creator.review.field.GATE


@pytest.fixture
def creation(history, monkeypatch):
    root = history.root
    calls = []
    manifest = root / environment.PARENT_NAME
    control, gate = root / "control.json", root / "gate.json"
    history.value["control_path"] = str(control)
    history.value["parent"]["gate_path"] = str(gate)
    put(manifest, history.value)
    put(control, {"parent_control_path": str(root / "phase2-control-freeze-001.json")})
    put(gate, {})
    monkeypatch.setattr(environment, "PARENT_SHA", "a" * 64)
    monkeypatch.setattr(wrapper, "INITIAL_JOURNAL_SHA",
                        environment.cadence.digest(history.raw.path))
    monkeypatch.setattr(wrapper.core.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(environment.filtered, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(wrapper.renewed.environment, "require_strata_stopped",
                        lambda: calls.append("strata"))
    monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive",
                        lambda *_, **kw: calls.append("own-lease" if kw else "inactive"))
    monkeypatch.setattr(wrapper.core.previous, "cells_from_gate", lambda *_: history.cells)
    candidate = {"native_argument_proof": [1], "run_id": history.target,
                 "reviewed_admission_sha256": "9" * 64}
    monkeypatch.setattr(wrapper, "proof", lambda *_: candidate)
    monkeypatch.setattr(wrapper, "verify_sidecar", lambda *_: calls.append("verified"))
    monkeypatch.setattr(wrapper, "_preflight", lambda *_: calls.append("full-gate-all-five"))
    output = root / wrapper.DIRECTORY / (history.target + ".json")
    expected = environment.inventory(history.value)

    def current():
        return {**expected, "native_argument_sidecars": {
            output.name: environment.cadence.digest(output)} if output.exists() else {}}

    monkeypatch.setattr(environment, "current_inventory", current)
    return SimpleNamespace(history=history, manifest=manifest, output=output,
                           candidate=candidate, calls=calls)


def create(state):
    return wrapper.create_review(state.manifest, "a" * 64, state.history.target,
                                 state.history.root / "historical.json")


def test_creator_adds_only_new_group_retains_journal_and_releases_lease(creation):
    state = creation
    before = state.history.raw.path.read_bytes()
    result = create(state)
    assert json.loads(state.output.read_text()) == state.candidate
    assert state.history.raw.path.read_bytes() == before
    assert not (state.history.root / "queue-lease.json").exists()
    assert state.calls.index("full-gate-all-five") < state.calls.index("verified")
    assert result["confirmed_native_argument_failures"] == 1
    assert result["new_model_calls"] == 0 and result["retry"] is False
    original = state.output.read_bytes()
    with pytest.raises(RuntimeError):
        create(state)
    assert state.output.read_bytes() == original


@pytest.mark.parametrize("damage", ["active", "strata", "proof", "full-gate", "journal",
                                   "inventory", "manifest", "wrong-journal-pin"])
def test_creator_rejects_unproven_state_before_write_and_releases_lease(creation, monkeypatch,
                                                                     damage):
    state = creation

    def reject(*_args, **_kwargs):
        raise RuntimeError("unsafe state")

    if damage == "active":
        monkeypatch.setattr(wrapper.core.previous.gate.evidence.private, "assert_inactive", reject)
    elif damage == "strata":
        monkeypatch.setattr(wrapper.renewed.environment, "require_strata_stopped", reject)
    elif damage == "proof":
        monkeypatch.setattr(wrapper, "proof", reject)
    elif damage == "full-gate":
        monkeypatch.setattr(wrapper, "_preflight", reject)
    elif damage == "manifest":
        monkeypatch.setattr(environment.filtered, "fence", reject)
    elif damage == "wrong-journal-pin":
        monkeypatch.setattr(wrapper, "INITIAL_JOURNAL_SHA", "0" * 64)
    elif damage == "inventory":
        monkeypatch.setattr(environment, "current_inventory", lambda: {
            **environment.inventory(state.history.value), "native_argument_sidecars": {
                "unexpected.json": "1" * 64}})
    else:
        def advance(*_):
            state.history.raw.path.write_bytes(state.history.raw.path.read_bytes() + b"\n")
        monkeypatch.setattr(wrapper, "_preflight", advance)
    with pytest.raises((RuntimeError, ValueError)):
        create(state)
    assert not state.output.exists()
    assert not (state.history.root / "queue-lease.json").exists()


def test_creator_rejects_any_additional_postwrite_inventory_delta(creation, monkeypatch):
    state = creation
    expected = environment.inventory(state.history.value)

    def current():
        if not state.output.exists():
            return expected
        return {**expected, "native_argument_sidecars": {
            state.output.name: environment.cadence.digest(state.output)},
            "model_json_sidecars": {**expected["model_json_sidecars"],
                                    "unexpected.json": "1" * 64}}

    monkeypatch.setattr(environment, "current_inventory", current)
    before = state.history.raw.path.read_bytes()
    with pytest.raises(RuntimeError, match="only the exact target native"):
        create(state)
    assert state.history.raw.path.read_bytes() == before
    assert not (state.history.root / "queue-lease.json").exists()


def test_preflight_runs_real_five_group_membership_without_global_mutation(history, monkeypatch):
    value = history.value
    control = history.root / "control.json"
    value["control_path"] = str(control)
    reviewers = (wrapper.core, environment.field.review,
                 environment.filtered.renewed.previous.derived, wrapper.previous)
    for reviewer in reviewers:
        monkeypatch.setattr(reviewer, "verify_sidecar", lambda *_: {
            "reviewed_admission_sha256": "e" * 64})
    monkeypatch.setattr(environment.environment, "verify_exclusion", lambda *_: None)

    def full_gate(_control):
        checked_membership({"phase2_schedule_sha256": "a" * 64}, history.cells,  # noqa: F821
                           require_dispatch_ready=True)
        return value["parent"], history.cells

    monkeypatch.setattr(environment.field, "checked_control", full_gate)
    target = history.raw.attempts[-1]
    path = history.root / wrapper.DIRECTORY / (target.run_id + ".json")
    candidate = {"reviewed_admission_sha256": "9" * 64}
    functions = (environment.membership, environment._review_pairs, environment.full_control,
                 environment.field.checked_control)
    before = [dict(fn.__globals__) for fn in functions]
    wrapper._preflight(environment, value, environment.inventory(value), path, target,
                       candidate, history.cells)
    assert not path.exists()
    assert all(fn.__globals__ == globals_before for fn, globals_before in zip(
        functions, before, strict=True))
    value["historical_reviews"][0]["effective"]["receipt_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="historical raw/effective"):
        wrapper._preflight(environment, value, environment.inventory(value), path, target,
                           candidate, history.cells)
