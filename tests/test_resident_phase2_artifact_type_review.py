"""Version dispatch, explicit context envelope and actual semantic wire proof."""

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
wrapper = importlib.import_module("large_scale_resident_phase2_artifact_type_review_v1")
environment = importlib.import_module("large_scale_resident_phase2_artifact_type_environment_v1")
history = initial_tests.history
native_history = initial_tests.native_history


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize("version", sorted(wrapper.OLD_VERSIONS))
def test_historical_exact_version_routes_to_unchanged_v3(tmp_path, monkeypatch, version):
    attempt = SimpleNamespace(run_id="old")
    path = put(tmp_path / wrapper.DIRECTORY / "old.json", {"version": version})
    calls = []
    monkeypatch.setattr(wrapper.ancestor, "verify_sidecar", lambda *args: calls.append(args) or {})
    monkeypatch.setattr(wrapper, "proof", lambda *_: pytest.fail("historical reinterpretation"))
    assert wrapper.verify_sidecar(path, attempt) == {}
    assert calls == [(path, attempt)]


@pytest.mark.parametrize(
    "version", [None, "invented", "phase2-source-propagated-derived-field-review-v1"]
)
def test_unknown_version_cannot_receive_artifact_or_field_waiver(tmp_path, version):
    path = put(tmp_path / wrapper.DIRECTORY / "new.json", {"version": version})
    with pytest.raises(RuntimeError, match="unsupported"):
        wrapper.verify_sidecar(path, SimpleNamespace(run_id="new"))


def test_new_version_reproduces_only_exact_artifact_type_proof(tmp_path, monkeypatch):
    value = {
        "version": wrapper.VERSION,
        "parent_control_path": "parent",
        "artifact_type_misuse_proof": [1],
    }
    path = put(tmp_path / wrapper.DIRECTORY / "new.json", value)
    monkeypatch.setattr(wrapper, "proof", lambda *_: value)
    assert wrapper.verify_sidecar(path, SimpleNamespace(run_id="new")) == value
    put(path, {**value, "artifact_type_misuse_proof": [2]})
    with pytest.raises(RuntimeError, match="drift"):
        wrapper.verify_sidecar(path, SimpleNamespace(run_id="new"))


@pytest.fixture
def contexts(tmp_path, monkeypatch):
    model = {
        "model_id": "qwen",
        "modalities": ["image", "text"],
        "context_window": 32768,
        "reserved_output_tokens": 2048,
        "image_token_cost": 4096,
    }
    formal = {**model, "deployment_id": "dep", "agent_id": "A4"}
    pool = put(tmp_path / "pool.yaml", {"environment": {"deployments": [formal]}})
    monkeypatch.setattr(wrapper.previous.frozen, "POOL_CONFIG", pool)
    directory = tmp_path / "evidence"
    put(directory / "worker-pids.json", {"A4": 42})
    state = {"A4": {"deployments": [{**model, "deployment_id": "dep"}]}}
    put(directory / "private/worker-state-after.json", state)
    put(directory / "worker-starts/A4.json", {"pid": 42})
    worker = put(tmp_path / "worker-configs/run-A4.yaml", {"deployments": {"dep": model}})
    return SimpleNamespace(
        root=tmp_path,
        directory=directory,
        worker=worker,
        pool=pool,
        model=model,
        state=state,
        attempt=SimpleNamespace(run_id="run"),
    )


def test_explicit_context_image_and_output_config_state_agree(contexts):
    value = wrapper.context_binding(contexts.root, contexts.attempt, contexts.directory)
    assert value["image_context_tokens"] == 4096
    assert value["settings"]["A4"]["deployments"]["dep"] == {
        "context_window": 32768,
        "reserved_output_tokens": 2048,
        "image_token_cost": 4096,
    }
    assert "artifact_root" not in json.dumps(value)


@pytest.mark.parametrize(
    "damage",
    [
        "unknown-image",
        "unknown-context",
        "unknown-reserve",
        "drift",
        "model",
        "modality",
        "owner",
        "starts",
        "pids",
        "missing-state",
        "extra-state",
        "missing-config",
    ],
)
def test_no_default_guessing_or_context_binding_waiver(contexts, damage):
    state = contexts
    model = state.model.copy()
    if damage.startswith("unknown-"):
        model.pop(
            {
                "unknown-image": "image_token_cost",
                "unknown-context": "context_window",
                "unknown-reserve": "reserved_output_tokens",
            }[damage]
        )
    elif damage == "drift":
        model["image_token_cost"] = 2048
    elif damage == "model":
        model["model_id"] = "wrong"
    elif damage == "modality":
        model["modalities"] = ["text"]
    elif damage == "owner":
        value = json.loads(state.pool.read_text())
        value["environment"]["deployments"][0]["agent_id"] = "other"
        put(state.pool, value)
    elif damage == "starts":
        put(state.directory / "worker-starts/A4.json", {"pid": 99})
    elif damage == "pids":
        put(state.directory / "worker-pids.json", {"A4": True})
    elif damage == "missing-state":
        state.state["A4"]["deployments"] = []
    elif damage == "extra-state":
        state.state["A4"]["deployments"].append(state.state["A4"]["deployments"][0].copy())
    else:
        state.worker.unlink()
    if damage != "missing-config":
        put(state.worker, {"deployments": {"dep": model}})
    put(state.directory / "private/worker-state-after.json", state.state)
    with pytest.raises((RuntimeError, FileNotFoundError)):
        wrapper.context_binding(state.root, state.attempt, state.directory)


@pytest.fixture
def semantic_wire(tmp_path):
    spec = next(
        item
        for item in wrapper.structured_operator_specs()
        if item.operator_id == "aggregate_artifacts"
    )
    function = {
        "name": spec.operator_id,
        "description": spec.description,
        "parameters": vars(wrapper.native_agents)["_native_tool_schema"](spec),
        "strict": False,
    }
    observations = [
        {
            "action_id": "specialist:p" + str(i),
            "owner_agent_id": "specialist",
            "succeeded": True,
            "output": {"text": "synthetic-note"},
            "produced_information": [
                {"artifact_id": "note" + str(i), "media_type": "text/plain", "size_bytes": 12}
            ],
        }
        for i in range(3)
    ]
    request = {
        "tools": [{"type": "function", "function": function}],
        "messages": [{"role": "tool", "content": json.dumps(item)} for item in observations],
    }
    put(tmp_path / "request1-request.json", request)
    verified = {
        "artifact_type_misuse_proof": [{"action_id": "specialist:bad"}],
        "model_output_materialization_proof": [
            {"action_id": item["action_id"]} for item in observations
        ],
    }
    events = [{"event_type": "logical.observation", "payload": item} for item in observations]
    wires = [{"action_id": "specialist:bad", "provider_call_id": "request1"}]
    return SimpleNamespace(
        root=tmp_path, request=request, verified=verified, events=events, wires=wires
    )


def test_actual_failed_agent_knows_json_schema_and_prior_plain_text_outputs(semantic_wire):
    state = semantic_wire
    before = copy.deepcopy((state.events, state.request))
    proof = wrapper.capability_wire_proof(state.root, state.events, state.verified, state.wires)
    assert len(proof[0]["visible_model_outputs"]) == 3
    assert "synthetic-note" not in json.dumps(proof)
    assert (state.events, state.request) == before


@pytest.mark.parametrize(
    "damage",
    [
        "description",
        "schema",
        "strict",
        "missing-result",
        "metadata",
        "output",
        "owner",
        "duplicate",
        "failed",
    ],
)
def test_static_capability_visibility_must_be_actual_not_source_only(semantic_wire, damage):
    state = semantic_wire
    function = state.request["tools"][0]["function"]
    if damage == "description":
        function["description"] = "combine anything"
    elif damage == "schema":
        function["parameters"] = {}
    elif damage == "strict":
        function["strict"] = True
    elif damage == "missing-result":
        state.request["messages"].pop()
    elif damage == "duplicate":
        state.request["messages"].append(state.request["messages"][0])
    elif damage == "failed":
        state.events[0]["payload"]["succeeded"] = False
    else:
        content = json.loads(state.request["messages"][0]["content"])
        if damage == "metadata":
            content["produced_information"][0]["media_type"] = "application/json"
        elif damage == "owner":
            content["owner_agent_id"] = "wrong"
        else:
            content["output"] = {}
        state.request["messages"][0]["content"] = json.dumps(content)
    put(state.root / "request1-request.json", state.request)
    with pytest.raises(RuntimeError):
        wrapper.capability_wire_proof(state.root, state.events, state.verified, state.wires)


@pytest.fixture
def creation(history, monkeypatch):
    root = history.root
    calls = []
    manifest = put(root / environment.PARENT_NAME, history.value)
    control, gate = root / "control.json", root / "gate.json"
    history.value["control_path"] = str(control)
    history.value["parent"]["gate_path"] = str(gate)
    put(manifest, history.value)
    put(control, {"parent_control_path": str(root / "phase2-control-freeze-001.json")})
    put(gate, {})
    monkeypatch.setattr(environment, "PARENT_SHA", "a" * 64)
    monkeypatch.setattr(wrapper.previous.frozen, "require_remote", lambda: calls.append("remote"))
    monkeypatch.setattr(environment.ancestor, "fence", lambda *_: calls.append("fence"))
    monkeypatch.setattr(
        wrapper.previous.environment, "require_strata_stopped", lambda: calls.append("strata")
    )
    monkeypatch.setattr(
        wrapper.original.core.previous.gate.evidence.private,
        "assert_inactive",
        lambda *_, **kw: calls.append("own-lease" if kw else "inactive"),
    )
    monkeypatch.setattr(wrapper.original.core.previous, "cells_from_gate", lambda *_: history.cells)
    candidate = {
        "artifact_type_misuse_proof": [1],
        "context_preflight_proof": [1],
        "actual_manager_schema_wire_proof": [1],
        "reviewed_admission_sha256": "8" * 64,
    }
    monkeypatch.setattr(wrapper, "proof", lambda *_: candidate)
    monkeypatch.setattr(wrapper, "verify_sidecar", lambda *_: calls.append("verified"))
    monkeypatch.setattr(wrapper, "_preflight", lambda *_: calls.append("full-gate-all-five"))
    output = root / wrapper.DIRECTORY / (history.target + ".json")
    expected = environment.inventory(history.value)

    def current():
        addition = {output.name: environment.cadence.digest(output)} if output.exists() else {}
        return {
            **expected,
            "derived_field_sidecars": {**expected["derived_field_sidecars"], **addition},
        }

    monkeypatch.setattr(environment, "current_inventory", current)
    return SimpleNamespace(
        history=history, manifest=manifest, output=output, candidate=candidate, calls=calls
    )


def create(state):
    return wrapper.create_review(state.manifest, "a" * 64, state.history.target)


def test_creator_full_preflight_precedes_exclusive_single_addition(creation):
    state = creation
    before = {p: p.read_bytes() for p in state.history.root.rglob("*") if p.is_file()}
    result = create(state)
    assert json.loads(state.output.read_text()) == state.candidate
    assert result["new_model_calls"] == 0 and result["retry"] is False
    assert result["confirmed_artifact_type_misuse_failures"] == 1
    assert state.calls.index("full-gate-all-five") < state.calls.index("verified")
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not (state.history.root / "queue-lease.json").exists()
    with pytest.raises(RuntimeError):
        create(state)


@pytest.mark.parametrize(
    "damage", ["live", "strata", "proof", "full-gate", "manifest", "journal", "inventory"]
)
def test_every_creator_guard_runs_before_write(creation, monkeypatch, damage):
    state = creation

    def reject(*_args, **_kwargs):
        raise RuntimeError("unsafe proof environment")

    if damage == "live":
        monkeypatch.setattr(
            wrapper.original.core.previous.gate.evidence.private, "assert_inactive", reject
        )
    elif damage == "strata":
        monkeypatch.setattr(wrapper.previous.environment, "require_strata_stopped", reject)
    elif damage == "proof":
        monkeypatch.setattr(wrapper, "proof", reject)
    elif damage == "full-gate":
        monkeypatch.setattr(wrapper, "_preflight", reject)
    elif damage == "manifest":
        monkeypatch.setattr(environment.ancestor, "fence", reject)
    elif damage == "journal":

        def advance(*_args):
            state.history.raw.path.write_bytes(state.history.raw.path.read_bytes() + b"\n")

        monkeypatch.setattr(wrapper, "_preflight", advance)
    else:
        expected = environment.inventory(state.history.value)
        monkeypatch.setattr(
            environment, "current_inventory", lambda: {**expected, "native_argument_sidecars": {}}
        )
    with pytest.raises((RuntimeError, ValueError)):
        create(state)
    assert not state.output.exists() and not (state.history.root / "queue-lease.json").exists()


def test_actual_preflight_preserves_five_reviewers_without_fake_field_proof(history, monkeypatch):
    value = history.value
    value["control_path"] = str(history.root / "control.json")
    calls = []
    ancestors = environment.previous.previous
    reviewers = (
        environment.field.core,
        environment.field.review,
        wrapper.original,
        ancestors.filtered.filtered,
        ancestors.native,
    )
    for index, reviewer in enumerate(reviewers):
        monkeypatch.setattr(
            reviewer,
            "verify_sidecar",
            lambda _p, _a, i=index: (
                calls.append(i) or {"reviewed_admission_sha256": "9" * 64 if i == 4 else "e" * 64}
            ),
        )
    old = history.root / wrapper.DIRECTORY / next(iter(value["derived_field_sidecars"]))
    prior = json.loads(old.read_text())
    prior["version"] = wrapper.ancestor.OLD_VERSION
    put(old, prior)
    value["derived_field_sidecars"][old.name] = environment.cadence.digest(old)
    monkeypatch.setattr(
        environment.environment, "verify_exclusion", lambda *_: calls.append("excluded")
    )

    def full_gate(_control):
        checked_membership(  # noqa: F821
            {"phase2_schedule_sha256": "a" * 64},
            history.cells,
            require_dispatch_ready=True,
        )
        return value["parent"], history.cells

    monkeypatch.setattr(environment.field, "checked_control", full_gate)
    target = history.raw.attempts[-1]
    path = history.root / wrapper.DIRECTORY / (target.run_id + ".json")
    candidate = {
        "version": wrapper.VERSION,
        "artifact_type_misuse_proof": [1],
        "reviewed_admission_sha256": "8" * 64,
    }
    before = dict(environment._review_pairs.__globals__)
    wrapper._preflight(value, environment.inventory(value), path, target, candidate, history.cells)
    assert set(calls) == {0, 1, 2, 3, 4, "excluded"}
    assert "derived_field_proof" not in candidate
    assert environment._review_pairs.__globals__ == before and not path.exists()


def test_context_unknown_may_not_default_to_4096():
    assert wrapper.DIRECTORY == wrapper.ancestor.DIRECTORY
    assert wrapper.REASON == wrapper.ancestor.REASON
    assert wrapper.VERSION not in wrapper.OLD_VERSIONS
    assert provenance_sha256(wrapper.sources())


@pytest.mark.parametrize("damage", [None, "window", "reserve", "image", "nonuniform"])
def test_reported_context_arithmetic_requires_bound_actual_envelope(contexts, damage):
    binding = wrapper.context_binding(contexts.root, contexts.attempt, contexts.directory)
    verified = {
        "context_preflight_proof": [
            {"context_window": 32768, "reserved_output": 2048, "image_context_tokens": 4096}
        ]
    }
    if damage == "nonuniform":
        binding["settings"]["A4"]["deployments"]["other"] = {
            "context_window": 16384,
            "reserved_output_tokens": 2048,
            "image_token_cost": 4096,
        }
    elif damage:
        key = {
            "window": "context_window",
            "reserve": "reserved_output",
            "image": "image_context_tokens",
        }[damage]
        verified["context_preflight_proof"][0][key] = 1
    if damage:
        with pytest.raises(RuntimeError):
            wrapper.validate_context_proof(binding, verified)
    else:
        wrapper.validate_context_proof(binding, verified)
