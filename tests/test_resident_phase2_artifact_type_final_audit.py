"""The successor final adapter keeps strict final guards and every ancestor."""

import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_resident_phase2_native_renewed_final_audit as previous_tests

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
final = importlib.import_module("large_scale_resident_phase2_artifact_type_final_audit_v1")
legacy_prepared = previous_tests.legacy_prepared
filtered_prepared = previous_tests.filtered_prepared
native_prepared = previous_tests.native_prepared
renewed_prepared = previous_tests.prepared
ACTUAL_SOURCES = final.audit_sources
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two


@pytest.fixture
def prepared(renewed_prepared, monkeypatch):
    value = renewed_prepared
    raw = next(a for a in value.ledger.original_attempts if a.run_id == "run-109")
    raw = replace(raw, disposition="confounder", reason=final.environment.field.review.field.GATE)
    effective = replace(
        raw, disposition="valid", reason=final.derived.REASON, receipt_sha256="k" * 64
    )
    value.ledger.original_attempts = tuple(
        raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts
    )
    value.ledger.attempts = tuple(
        effective if a.run_id == raw.run_id else a for a in value.ledger.attempts
    )
    value.projection["rows"][109]["attempts"][0].update(
        original_disposition=raw.disposition,
        original_reason=raw.reason,
        disposition=effective.disposition,
        reason=effective.reason,
        receipt_sha256=effective.receipt_sha256,
        execution_completed=True,
        artifact_type_misuse_count=1,
        artifact_context_preflight_count=1,
    )
    proof = {
        "version": final.derived.VERSION,
        "run_id": raw.run_id,
        "original_admission_sha256": raw.receipt_sha256,
        "original_execution_sha256": raw.execution_sha256,
        "reviewed_admission_sha256": effective.receipt_sha256,
        "artifact_type_misuse_proof": [{"action_id": "bad"}],
        "context_preflight_proof": [{"action_id": "context"}],
        "model_output_materialization_proof": [{"action_id": "producer"}],
    }
    path = value.root / final.derived.DIRECTORY / (raw.run_id + ".json")
    path.write_text(json.dumps(proof), encoding="utf-8")
    value.derived_sidecars[path.name] = final.environment.cadence.digest(path)
    value.control_value["derived_field_sidecars"] = value.derived_sidecars
    value.control.write_text(json.dumps(value.control_value), encoding="utf-8")
    manifest = json.loads(value.manifest.read_text())
    manifest.update(
        extension_version=final.environment.VERSION, derived_field_sidecars=value.derived_sidecars
    )
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls.clear()

    def fence(path, sha, checked):
        assert path == value.manifest and sha == "m" * 64
        assert checked["extension_version"] == final.environment.VERSION
        value.routing_calls.append("versioned-fence")

    for name in ("full_control", "membership", "collect"):
        monkeypatch.setattr(
            final.environment, name, getattr(final.ancestor.previous.environment, name)
        )
    monkeypatch.setattr(final.environment, "fence", fence)
    monkeypatch.setattr(final, "audit_sources", lambda: value.sources.copy())
    monkeypatch.setattr(final, "audit_phase_two", final.ancestor.previous.audit_phase_two)
    old_verify = final.derived.original.verify_sidecar

    def verify(path, attempt):
        if path.name == "run-109.json":
            return json.loads(path.read_text())
        return old_verify(path, attempt)

    monkeypatch.setattr(final.derived, "verify_sidecar", verify)
    return value


def create(state):
    return final.create_bundle(
        state.manifest, "m" * 64, provenance_sha256(state.sources), state.output
    )


def test_all193_with_new_derived_companions_preserve_old_pairs_unknowns_and_globals(prepared):
    functions = (
        final.ancestor.base.reconcile,
        final.ancestor.base.create_bundle,
        final.ancestor.previous.SOURCE_MODULES,
        final.ancestor.previous.ENVIRONMENT_VIEW,
    )
    globals_before = [dict(function.__globals__) for function in functions]
    before = copy.deepcopy(prepared.projection)
    result = create(prepared)
    assert result["version"] == final.VERSION
    rows = result["projection"]["rows"]
    assert rows[109]["attempts"][0]["artifact_type_misuse_count"] == 1
    assert rows[109]["attempts"][0]["artifact_context_preflight_count"] == 1
    assert "confirmed_absent_derived_record_field_failures" not in rows[109]["attempts"][0]
    assert rows[81]["attempts"][0]["confirmed_absent_derived_record_field_failures"] == 2
    assert rows[107]["attempts"][0]["confirmed_absent_record_field_failures"] == 3
    assert rows[105]["attempts"][0]["execution_completed"] is False
    assert rows[105]["attempts"][0]["benchmark_score"] is None
    assert rows[71]["attempts"][0]["disposition"] == "operational_excluded"
    assert sum(len(row["attempts"]) for row in rows) == 193
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.projection == before
    assert result["goal_complete"] is result["semantic_audit_complete"] is False
    assert result["manual_audit_complete"] is result["q1_q10_complete"] is False
    assert result["planner_or_model_calls"] == 0
    assert result["score_aggregation"] == "not performed"
    assert all(
        function.__globals__ == before
        for function, before in zip(functions, globals_before, strict=True)
    )


@pytest.mark.parametrize("entry", ["bundle", "private"])
def test_live_guard_precedes_source_metadata_or_private_body(monkeypatch, entry):
    def reject(*_):
        raise RuntimeError("owned queue still live")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", reject)
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("live metadata"))
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("live source"))
    with pytest.raises(RuntimeError, match="still live"):
        if entry == "bundle":
            final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))
        else:
            ACTUAL_ADAPTER_PRIVATE(Path("absent"), "x", {}, {}, {})


@pytest.mark.parametrize(
    "key,value",
    [
        ("phase2_complete", False),
        ("attempt_count", 192),
        ("scheduled_cells", 191),
        ("admitted_cells", 191),
        ("pending_count", 1),
        ("confounded_attempts", 1),
        ("operational_excluded_attempts", 2),
    ],
)
def test_all192_all193_required_before_private_scan(prepared, key, value):
    prepared.projection[key] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize(
    "damage", ["missing", "hash", "raw", "effective", "empty", "extra-group", "native", "old71"]
)
def test_new_and_historical_exact_binding_fails_before_private_body(prepared, damage):
    path = prepared.root / final.derived.DIRECTORY / "run-109.json"
    if damage == "missing":
        prepared.derived_sidecars.pop(path.name)
    elif damage == "hash":
        prepared.derived_sidecars[path.name] = "f" * 64
    elif damage == "raw":
        prepared.projection["rows"][109]["attempts"][0]["original_reason"] = "drift"
    elif damage == "effective":
        prepared.ledger.attempts = tuple(
            replace(a, receipt_sha256="drift") if a.run_id == "run-109" else a
            for a in prepared.ledger.attempts
        )
    elif damage == "empty":
        proof = json.loads(path.read_text())
        proof["artifact_type_misuse_proof"] = []
        path.write_text(json.dumps(proof))
        prepared.derived_sidecars[path.name] = final.environment.cadence.digest(path)
    elif damage == "extra-group":
        prepared.native_sidecars.update(prepared.derived_sidecars)
    elif damage == "native":
        prepared.native_sidecars.clear()
    else:
        prepared.projection["rows"][71]["attempts"].pop(0)
    prepared.control.write_text(json.dumps(prepared.control_value))
    manifest = json.loads(prepared.manifest.read_text())
    manifest.update(
        derived_field_sidecars=prepared.derived_sidecars,
        native_argument_sidecars=prepared.native_sidecars,
    )
    prepared.manifest.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_actual_import_closure_retains_every_current_ancestor_and_new_pure_reviewer():
    actual = ACTUAL_SOURCES()
    old = final.ancestor.audit_sources()
    assert all(actual.get(name) == sha for name, sha in old.items())
    assert "large_scale_resident_phase2_derived_companion_review_v1" in actual
    assert "large_scale_resident_phase2_derived_companion_environment_v1" in actual
    assert "large_scale_resident_phase2_derived_companion_final_audit_v1" in actual
    for module in (
        final,
        final.environment,
        final.derived,
        final.derived.pure,
        final.derived.native_agents,
        final.private.previous.private,
        sys.modules[final.private.previous.private.scan_store.__module__],
    ):
        assert module.__name__ in actual
        assert final.audit_source_paths()[module.__name__] == str(Path(module.__file__).resolve())


def test_no_exclusive_final_output_overwrite(prepared):
    create(prepared)
    before = prepared.output.read_bytes()
    with pytest.raises(FileExistsError):
        create(prepared)
    assert prepared.output.read_bytes() == before
