"""Source, Worker settings and actual SDK arguments remain exact offline."""

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_resident_phase2_native_field_review as initial_tests

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
wrapper = importlib.import_module("large_scale_resident_phase2_derived_companion_review_v2")
environment = importlib.import_module(
    "large_scale_resident_phase2_derived_companion_environment_v2")
native_history = initial_tests.native_history
history = initial_tests.history
old_wrapper_tests = importlib.import_module("test_resident_phase2_derived_field_wrapper")
heldout_field = old_wrapper_tests.heldout_field
wrapped = old_wrapper_tests.wrapped


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_historical_v1_dispatch_uses_frozen_reviewer_not_new_companion(tmp_path, monkeypatch):
    attempt = SimpleNamespace(run_id="old81")
    path = put(tmp_path / wrapper.DIRECTORY / "old81.json", {"version": wrapper.OLD_VERSION})
    calls = []
    monkeypatch.setattr(wrapper.original, "verify_sidecar", lambda *args: calls.append(args) or {})
    monkeypatch.setattr(wrapper, "proof", lambda *_: pytest.fail("historical reinterpretation"))
    assert wrapper.verify_sidecar(path, attempt) == {}
    assert calls == [(path, attempt)]


def test_persisted_header_is_inner_proof_version_not_outer_phase_wrapper_header(
        wrapped, monkeypatch):
    root, _directory, ledger, parent, old, _, _, _ = wrapped
    monkeypatch.setattr(wrapper.original.derived, "review", lambda *_: {
        "version": "metadata-bound-derived-record-field-proof-v1",
        "derived_field_proof": [{"action_id": "synthetic-field-misuse"}]})
    created = wrapper.original.create_review("run4", parent, old)
    path = Path(created["sidecar_path"])
    before = path.read_bytes()
    proof = wrapper.verify_sidecar(path, ledger.attempts[0])
    assert proof["version"] == "metadata-bound-derived-record-field-proof-v1"
    assert wrapper.OLD_VERSION == "metadata-bound-derived-record-field-proof-v1"
    assert wrapper.ancestor.OLD_VERSION == "phase2-source-propagated-derived-field-review-v1"
    assert proof["reviewer_sources_sha256"] == wrapper.original.sources()
    assert path.read_bytes() == before
    invalid = {**proof, "version": "phase2-source-propagated-derived-field-review-v1"}
    put(path, invalid)
    with pytest.raises(RuntimeError, match="unsupported"):
        wrapper.verify_sidecar(path, ledger.attempts[0])


@pytest.mark.parametrize("version", [None, "invented", "phase2-source-derived-v99",
                                     "phase2-source-propagated-derived-field-review-v1"])
def test_unknown_proof_versions_never_get_a_derived_waiver(tmp_path, version):
    attempt = SimpleNamespace(run_id="unknown")
    path = put(tmp_path / wrapper.DIRECTORY / "unknown.json", {"version": version})
    with pytest.raises(RuntimeError, match="unsupported"):
        wrapper.verify_sidecar(path, attempt)


def test_new_proof_reproduces_exact_candidate_before_acceptance(tmp_path, monkeypatch):
    attempt = SimpleNamespace(run_id="new109")
    proof = {"version": wrapper.VERSION, "parent_control_path": "parent",
             "historical_sidecar_path": "historical", "field": "proof"}
    path = put(tmp_path / wrapper.DIRECTORY / "new109.json", proof)
    monkeypatch.setattr(wrapper, "proof", lambda *_: proof)
    assert wrapper.verify_sidecar(path, attempt) == proof
    altered = {**proof, "field": "unreproduced"}
    put(path, altered)
    with pytest.raises(RuntimeError, match="drift"):
        wrapper.verify_sidecar(path, attempt)


@pytest.fixture
def worker_binding(tmp_path):
    attempt = SimpleNamespace(run_id="run109")
    directory = tmp_path / "evidence"
    put(directory / "worker-pids.json", {"A4": 42, "A28": 43})
    put(directory / "private/worker-state-after.json", {"A4": {}, "A28": {}})
    for agent, pid in (("A4", 42), ("A28", 43)):
        put(directory / "worker-starts" / (agent + ".json"), {"pid": pid})
        put(tmp_path / "worker-configs" / (attempt.run_id + "-" + agent + ".yaml"),
            {"max_read_artifact_bytes": 65536})
    return SimpleNamespace(root=tmp_path, attempt=attempt, directory=directory)


def test_explicit_read_limit_configuration_and_actual_startup_identity_are_bound(worker_binding):
    state = worker_binding
    value = wrapper.read_limit_binding(state.root, state.attempt, state.directory)
    assert value["config_driven_startup_unchanged"] is True
    assert set(value["settings"]) == {"A4", "A28"}
    assert all(item["max_read_artifact_bytes"] == 65536 for item in value["settings"].values())
    assert wrapper.worker_settings.WorkerConfig.model_fields[
        "max_read_artifact_bytes"].default == wrapper.READ_LIMIT


@pytest.mark.parametrize("damage", ["omitted", "override", "pids", "starts", "state", "empty"])
def test_read_limit_never_inferred_from_an_unbound_default(worker_binding, damage):
    state = worker_binding
    path = state.root / "worker-configs" / "run109-A4.yaml"
    if damage == "omitted":
        put(path, {})
    elif damage == "override":
        put(path, {"max_read_artifact_bytes": 1_000_000})
    elif damage == "pids":
        put(state.directory / "worker-pids.json", {"A4": True, "A28": 43})
    elif damage == "starts":
        put(state.directory / "worker-starts/A4.json", {"pid": 99})
    elif damage == "state":
        put(state.directory / "private/worker-state-after.json", {"A4": {}})
    else:
        put(state.directory / "worker-pids.json", {})
    with pytest.raises(RuntimeError):
        wrapper.read_limit_binding(state.root, state.attempt, state.directory)


@pytest.fixture
def wire(tmp_path):
    owner = "specialist-0001"
    args = {"inputs": ["derived"], "arguments": {"query": "public-query", "text_field": "text"}}
    selected = {"action_id": owner + ":tc1", "logical_agent_id": owner,
                "decision_id": owner + ":native-turn:1",
                "operator": "bm25_retrieve", "selected_tool_arguments": args}
    text = json.dumps({"assignment": {"logical_agent_id": owner}})
    items = [{"role": "user", "content": text}]
    events = [{"event_type": "logical.reasoning.input", "payload": {
        "decision_id": selected["decision_id"], "logical_agent_id": owner,
        "input_items": items, "input_sha256": provenance_sha256(items)}},
        {"event_type": "logical.action.selected", "payload": selected}]
    usage = {"call_id": "request1", "recipient": "specialist",
             "agent_name": "bounded_specialist", "status": 200}
    request = {"tools": [{"function": {"name": "bm25_retrieve", "parameters": {}}}],
               "messages": [{"role": "user", "content": text}]}
    response = {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [
        {"id": "tc1", "function": {"name": "bm25_retrieve", "arguments": json.dumps(args)}}]}}]}
    for suffix, value in (("usage", usage), ("request", request), ("response", response)):
        put(tmp_path / ("request1-" + suffix + ".json"), value)
    proof = {"derived_field_proof": [{"action_id": owner + ":tc1"}],
             "context_preflight_proof": [], "read_artifact_limit_proof": [],
             "output_collision_proof": []}
    return SimpleNamespace(root=tmp_path, events=events, proof=proof, args=args,
                           usage=usage, request=request, response=response)


def test_actual_sdk_tool_arguments_match_exact_selected_event_without_content_export(wire):
    before = copy.deepcopy((wire.events, wire.proof))
    result = wrapper.sdk_selected_tool_proof(wire.root, wire.events, wire.proof)
    assert len(result) == 1
    assert result[0]["owner_agent_id"] == "specialist-0001"
    assert result[0]["arguments_sha256"] == provenance_sha256(json.dumps(wire.args))
    assert "public-query" not in json.dumps(result)
    assert (wire.events, wire.proof) == before


@pytest.mark.parametrize("damage", ["owner", "action-owner-prefix", "decision-owner-prefix",
                                   "assignment", "input-hash", "actual-input",
                                   "arguments", "operator", "status", "finish",
                                   "schema", "missing-response", "missing-selected",
                                   "duplicate-selected", "duplicate-tool", "invalid-json",
                                   "extra-target"])
def test_actual_sdk_wire_drift_fails_closed(wire, damage):
    call = wire.response["choices"][0]["message"]["tool_calls"][0]
    if damage == "owner":
        wire.usage["recipient"] = "manager"
    elif damage == "action-owner-prefix":
        wire.events[-1]["payload"]["action_id"] = "wrong:tc1"
        wire.proof["derived_field_proof"] = [{"action_id": "wrong:tc1"}]
    elif damage == "decision-owner-prefix":
        wire.events[-1]["payload"]["decision_id"] = "wrong:native-turn:1"
        wire.events[0]["payload"]["decision_id"] = "wrong:native-turn:1"
    elif damage == "assignment":
        item = wire.events[0]["payload"]["input_items"][0]
        item["content"] = json.dumps({"assignment": {"logical_agent_id": "wrong"}})
        wire.request["messages"][0]["content"] = item["content"]
        wire.events[0]["payload"]["input_sha256"] = provenance_sha256(
            wire.events[0]["payload"]["input_items"])
    elif damage == "input-hash":
        wire.events[0]["payload"]["input_sha256"] = "f" * 64
    elif damage == "actual-input":
        wire.request["messages"][0]["content"] = "other-input"
    elif damage == "arguments":
        call["function"]["arguments"] = json.dumps({**wire.args, "inputs": ["wrong"]})
    elif damage == "operator":
        call["function"]["name"] = "read_artifact"
    elif damage == "status":
        wire.usage["status"] = 500
    elif damage == "finish":
        wire.response["choices"][0]["finish_reason"] = "length"
    elif damage == "schema":
        wire.request["tools"] = []
    elif damage == "missing-response":
        wire.response["choices"][0]["message"]["tool_calls"] = []
    elif damage == "missing-selected":
        wire.events.clear()
    elif damage == "duplicate-selected":
        wire.events.append(copy.deepcopy(wire.events[-1]))
    elif damage == "duplicate-tool":
        wire.response["choices"][0]["message"]["tool_calls"].append(copy.deepcopy(call))
    elif damage == "invalid-json":
        call["function"]["arguments"] = "{"
    else:
        wire.proof["read_artifact_limit_proof"] = [{"action_id": "missing:call"}]
    for suffix in ("usage", "request", "response"):
        put(wire.root / ("request1-" + suffix + ".json"), getattr(wire, suffix))
    with pytest.raises(RuntimeError):
        wrapper.sdk_selected_tool_proof(wire.root, wire.events, wire.proof)


def test_collision_prior_and_rejected_calls_both_require_actual_sdk_wire(wire):
    wire.proof["output_collision_proof"] = [{"action_id": "specialist-0001:tc2",
                                           "reserved_action_id": "specialist-0001:tc1"}]
    selected = copy.deepcopy(wire.events[-1]["payload"])
    selected["action_id"] = "specialist-0001:tc2"
    wire.events.append({"event_type": "logical.action.selected", "payload": selected})
    with pytest.raises(RuntimeError, match="actual SDK wire"):
        wrapper.sdk_selected_tool_proof(wire.root, wire.events, wire.proof)
    call = copy.deepcopy(wire.response["choices"][0]["message"]["tool_calls"][0])
    call["id"] = "tc2"
    wire.response["choices"][0]["message"]["tool_calls"].append(call)
    put(wire.root / "request1-response.json", wire.response)
    assert len(wrapper.sdk_selected_tool_proof(wire.root, wire.events, wire.proof)) == 2


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
    historical = put(root / "historical.json", {})
    monkeypatch.setattr(environment, "PARENT_SHA", "a" * 64)
    monkeypatch.setattr(wrapper.previous.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(wrapper.previous, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(wrapper.previous.environment, "require_strata_stopped",
                        lambda: calls.append("strata"))
    monkeypatch.setattr(wrapper.original.core.previous.gate.evidence.private, "assert_inactive",
                        lambda *_, **kw: calls.append("own-lease" if kw else "inactive"))
    monkeypatch.setattr(wrapper.original.core.previous, "cells_from_gate", lambda *_: history.cells)
    candidate = {"derived_field_proof": [1], "read_artifact_limit_proof": [1],
                 "output_collision_proof": [1], "actual_manager_schema_wire_proof": [1],
                 "reviewed_admission_sha256": "8" * 64}
    monkeypatch.setattr(wrapper, "proof", lambda *_: candidate)
    monkeypatch.setattr(wrapper, "verify_sidecar", lambda *_: calls.append("verified"))
    monkeypatch.setattr(wrapper, "_preflight", lambda *_: calls.append("full-gate-all-five"))
    output = root / wrapper.DIRECTORY / (history.target + ".json")
    expected = environment.inventory(history.value)

    def current():
        addition = {output.name: environment.cadence.digest(output)} if output.exists() else {}
        return {**expected, "derived_field_sidecars": {
            **expected["derived_field_sidecars"], **addition}}

    monkeypatch.setattr(environment, "current_inventory", current)
    return SimpleNamespace(history=history, manifest=manifest, historical=historical,
                           output=output, candidate=candidate, calls=calls)


def create(state):
    return wrapper.create_review(state.manifest, "a" * 64, state.history.target, state.historical)


def test_creator_runs_full_preflight_and_adds_only_one_same_group_proof_once(creation):
    state = creation
    before = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    result = create(state)
    assert json.loads(state.output.read_text()) == state.candidate
    assert result["new_model_calls"] == 0 and result["retry"] is False
    assert result["confirmed_read_limit_failures"] == 1
    assert result["confirmed_output_collision_failures"] == 1
    assert state.calls.index("full-gate-all-five") < state.calls.index("verified")
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not (state.history.root / "queue-lease.json").exists()
    with pytest.raises(RuntimeError):
        create(state)


@pytest.mark.parametrize("damage", ["live", "strata", "proof", "full-gate", "manifest",
                                   "journal", "inventory"])
def test_every_creator_guard_precedes_write_and_releases_lease(creation, monkeypatch, damage):
    state = creation

    def reject(*_args, **_kwargs):
        raise RuntimeError("unsafe proof environment")

    if damage == "live":
        monkeypatch.setattr(wrapper.original.core.previous.gate.evidence.private,
                            "assert_inactive", reject)
    elif damage == "strata":
        monkeypatch.setattr(wrapper.previous.environment, "require_strata_stopped", reject)
    elif damage == "proof":
        monkeypatch.setattr(wrapper, "proof", reject)
    elif damage == "full-gate":
        monkeypatch.setattr(wrapper, "_preflight", reject)
    elif damage == "manifest":
        monkeypatch.setattr(wrapper.previous, "fence", reject)
    elif damage == "journal":
        def advance(*_args):
            state.history.raw.path.write_bytes(state.history.raw.path.read_bytes() + b"\n")
        monkeypatch.setattr(wrapper, "_preflight", advance)
    else:
        expected = environment.inventory(state.history.value)
        monkeypatch.setattr(environment, "current_inventory", lambda: {
            **expected, "native_argument_sidecars": {}})
    with pytest.raises((RuntimeError, ValueError)):
        create(state)
    assert not state.output.exists() and not (state.history.root / "queue-lease.json").exists()


@pytest.mark.parametrize("damage", [None, "native-proof", "old-pair", "parent", "schedule"])
def test_actual_preflight_reproduces_all_five_reviewers_without_global_mutation(
        history, monkeypatch, damage):
    value = history.value
    value["control_path"] = str(history.root / "control.json")
    calls = []
    ancestor = environment.previous.previous
    reviewers = (environment.field.core, environment.field.review, wrapper.original,
                 ancestor.filtered.filtered, ancestor.native)
    for index, reviewer in enumerate(reviewers):
        def verify(_path, _attempt, index=index):
            calls.append(index)
            if damage == "native-proof" and index == 4:
                raise RuntimeError("historical native argument proof changed")
            return {"reviewed_admission_sha256": "9" * 64 if index == 4 else "e" * 64}
        monkeypatch.setattr(reviewer, "verify_sidecar", verify)
    # This is the exact durable cell81 header. Exercise the real v2 dispatcher
    # inside the complete candidate gate, not a stub replacing its dispatch.
    old_path = history.root / wrapper.DIRECTORY / next(iter(value["derived_field_sidecars"]))
    old_proof = json.loads(old_path.read_text())
    old_proof["version"] = "metadata-bound-derived-record-field-proof-v1"
    put(old_path, old_proof)
    value["derived_field_sidecars"][old_path.name] = environment.cadence.digest(old_path)
    monkeypatch.setattr(environment.environment, "verify_exclusion",
                        lambda *_: calls.append("excluded"))

    def full_gate(_control):
        checked_membership({"phase2_schedule_sha256": "a" * 64}, history.cells,  # noqa: F821
                           require_dispatch_ready=True)
        parent = {"changed": True} if damage == "parent" else value["parent"]
        cells = history.cells[:-1] if damage == "schedule" else history.cells
        return parent, cells

    monkeypatch.setattr(environment.field, "checked_control", full_gate)
    target = history.raw.attempts[-1]
    path = history.root / wrapper.DIRECTORY / (target.run_id + ".json")
    candidate = {"reviewed_admission_sha256": "8" * 64}
    if damage == "old-pair":
        value["historical_reviews"][-1]["effective"]["receipt_sha256"] = "0" * 64
    functions = (environment.previous.membership, environment.previous.full_control,
                 environment._review_pairs, environment.membership, environment.full_control,
                 environment.field.checked_control)
    before = [dict(function.__globals__) for function in functions]
    if damage is None:
        wrapper._preflight(value, environment.inventory(value), path, target, candidate,
                           history.cells)
        assert set(calls) == {0, 1, 2, 3, 4, "excluded"}
        assert calls.count(2) == 1
    else:
        with pytest.raises(RuntimeError):
            wrapper._preflight(value, environment.inventory(value), path, target, candidate,
                               history.cells)
    assert not path.exists()
    assert json.loads(old_path.read_text())["version"] == (
        "metadata-bound-derived-record-field-proof-v1")
    assert all(function.__globals__ == namespace for function, namespace in zip(
        functions, before, strict=True))
