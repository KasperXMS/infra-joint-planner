import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_resident_phase2_final_audit as legacy

from infra_joint.control.provenance import provenance_sha256

legacy_prepared = legacy.prepared

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
final = importlib.import_module("large_scale_resident_phase2_derived_final_audit_v1")
ACTUAL_AUDIT_SOURCES = final.audit_sources
ACTUAL_PRIVATE = final.private.audit_phase_two
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two


@pytest.fixture
def prepared(legacy_prepared, monkeypatch):
    value = legacy_prepared
    original = next(a for a in value.ledger.original_attempts if a.run_id == "run-2")
    raw = replace(original, disposition="confounder", reason="raw-field-gate")
    value.ledger.original_attempts = tuple(
        raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts)
    record = value.projection["rows"][2]["attempts"][0]
    record.update(original_disposition="confounder", receipt_sha256="d" * 64)
    proof = {"run_id": raw.run_id, "original_admission_sha256": raw.receipt_sha256,
             "original_execution_sha256": raw.execution_sha256,
             "reviewed_admission_sha256": "d" * 64,
             "derived_field_proof": [{"action_id": "failed-1"}, {"action_id": "failed-2"}]}
    directory = value.root / final.derived.DIRECTORY
    directory.mkdir()
    path = directory / "run-2.json"
    path.write_text(json.dumps(proof), encoding="utf-8")
    value.derived_sidecars = {path.name: final.environment.cadence.digest(path)}
    manifest = json.loads(value.manifest.read_text())
    manifest["derived_field_sidecars"] = value.derived_sidecars
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls = []

    def full_control(control, sidecar, derived_sidecars=None):
        assert control == value.control and sidecar == Path(manifest["sidecar_path"])
        assert derived_sidecars == value.derived_sidecars
        value.routing_calls.append("full_control")
        return manifest["parent"], tuple(f"cell-{i}" for i in range(192))

    def membership(control, cells, sidecar, *, require_dispatch_ready):
        assert control == {**value.control_value, "derived_field_sidecars": value.derived_sidecars}
        assert require_dispatch_ready is True
        value.routing_calls.append("membership")
        return value.ledger

    monkeypatch.setattr(final.environment, "fence", lambda *_: None)
    monkeypatch.setattr(final.environment, "full_control", full_control)
    monkeypatch.setattr(final.environment, "membership", membership)
    monkeypatch.setattr(final.environment, "collect", lambda *_: value.projection)
    monkeypatch.setattr(final.derived, "verify_sidecar", lambda p, _: json.loads(p.read_text()))
    monkeypatch.setattr(final, "audit_sources", lambda: value.sources.copy())

    def diagnostics(*_):
        value.calls.append("private")
        return value.diagnostics

    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    return value


def create(prepared):
    return final.create_bundle(prepared.manifest, "m" * 64,
                               provenance_sha256(prepared.sources), prepared.output)


def test_synthetic_all193_bundle_routes_third_map_preserves_unknowns_and_raws(prepared):
    original = copy.deepcopy(prepared.projection)
    controls = copy.deepcopy(prepared.control_value)
    result = create(prepared)
    record = result["projection"]["rows"][2]["attempts"][0]
    assert result["version"] == final.VERSION
    assert record["confirmed_absent_derived_record_field_failures"] == 2
    assert record["confirmed_absent_record_field_failures"] == 2
    assert record["phase2_derived_field_sidecar_sha256"] == prepared.derived_sidecars["run-2.json"]
    assert record["original_rejection_preserved"] is True
    assert record["telemetry"] is None and record["semantic_primary_cause"] is None
    assert record["original_disposition"] == "confounder"
    assert record["original_receipt_sha256"] == "r" * 64
    assert prepared.projection == original and prepared.control_value == controls
    assert result["derived_field_sidecars"] == prepared.derived_sidecars
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    excluded = result["projection"]["rows"][71]["attempts"][0]
    assert excluded["run_id"] == final.previous.environment.RUN
    for key in ("projection", "recipient_audit", "private_diagnostics"):
        assert result["component_sha256"][key] == provenance_sha256(result[key])
    for key in ("semantic_audit_complete", "manual_audit_complete", "q1_q10_complete",
                "goal_complete", "artifact_bodies_exported", "measured_execution_modified"):
        assert result[key] is False
    assert prepared.routing_calls == ["full_control", "membership"]
    assert prepared.calls == ["private"]
    assert json.loads(prepared.output.read_text()) == result


def test_global_guard_is_first(monkeypatch):
    def live(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", live)
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("source read while live"))
    monkeypatch.setattr(final.environment, "read",
                        lambda *_: pytest.fail("metadata read while live"))
    with pytest.raises(RuntimeError, match="live controller"):
        final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))


@pytest.mark.parametrize("key,value", [
    ("phase2_complete", False), ("attempt_count", 192), ("admitted_cells", 191),
    ("pending_count", 1), ("confounded_attempts", 1), ("operational_excluded_attempts", 2)])
def test_incomplete_inventory_rejects_before_private_scan(prepared, key, value):
    prepared.projection[key] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["overlap", "hash", "run", "original", "execution",
                                   "effective", "empty-proof", "raw-identity", "uncovered"])
def test_derived_review_drift_rejects_before_private_scan(prepared, change):
    path = prepared.root / final.derived.DIRECTORY / "run-2.json"
    proof = json.loads(path.read_text())
    if change == "overlap":
        prepared.control_value["initial_field_sidecars"]["run-2.json"] = "a" * 64
        prepared.control.write_text(json.dumps(prepared.control_value))
    elif change == "hash":
        prepared.derived_sidecars["run-2.json"] = "a" * 64
    elif change == "raw-identity":
        prepared.projection["rows"][2]["attempts"][0]["original_receipt_sha256"] = "drift"
    elif change == "uncovered":
        prepared.derived_sidecars["not-a-run.json"] = "a" * 64
    else:
        key = {"run": "run_id", "original": "original_admission_sha256",
               "execution": "original_execution_sha256", "effective": "reviewed_admission_sha256",
               "empty-proof": "derived_field_proof"}[change]
        proof[key] = [] if change == "empty-proof" else "drift"
        path.write_text(json.dumps(proof))
        prepared.derived_sidecars[path.name] = final.environment.cadence.digest(path)
    manifest = json.loads(prepared.manifest.read_text())
    manifest["derived_field_sidecars"] = prepared.derived_sidecars
    prepared.manifest.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_external_source_pin_rejects_before_metadata_reads(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"extension": "drift"})
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("read before source pin"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)
    assert not prepared.calls


def test_source_drift_after_synthetic_diagnostics_prevents_output(prepared, monkeypatch):
    def changed(*_):
        prepared.sources["wrapper.py"] = "drift"
        return prepared.diagnostics

    monkeypatch.setattr(final, "audit_phase_two", changed)
    with pytest.raises(RuntimeError, match="source/journal changed"):
        create(prepared)
    assert not prepared.output.exists()


def test_private_entrypoint_routes_control_map_and_retains_original_scanner(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    original_private = ACTUAL_PRIVATE
    original_scanner = final.private.previous.private.scan_store
    original_multihop = final.private.previous.audit_multihop
    for row in prepared.projection["rows"]:
        row["condition"]["task"] = {"family": "video_mme", "position": 1}
        for attempt in row["attempts"]:
            attempt["environment_stage"] = "pre-strata"
    # Exercise the actual rebound private entrypoint; unannotated synthetic tasks
    # require no corpus, owning-store body access, or SSH.
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("private scan on synthetic unannotated task"))
    result = create(prepared)
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.routing_calls == ["full_control", "membership", "full_control", "membership"]
    assert final.private.audit_phase_two is original_private
    assert final.private.previous.private.scan_store is original_scanner
    assert original_multihop.__globals__["private"].scan_store is original_scanner


def test_function_copy_preserves_keyword_defaults_without_global_mutation():
    def original(value=2, *, multiplier=3):
        return value * multiplier

    before = dict(original.__globals__)
    bound = final.copied(original, {"adapter_marker": True})
    assert bound() == 6 and bound(4) == 12
    assert bound.__defaults__ == original.__defaults__
    assert bound.__kwdefaults__ == original.__kwdefaults__
    assert bound.__kwdefaults__ is not original.__kwdefaults__
    assert original.__globals__ == before


def test_actual_source_closure_contains_extension_reviewer_and_native_scanner():
    sources = ACTUAL_AUDIT_SOURCES()
    for name in ("large_scale_resident_phase2_derived_final_audit_v1",
                 "large_scale_resident_phase2_derived_environment_v1",
                 "large_scale_resident_phase2_derived_field_review_v1",
                 "large_scale_resident_derived_field_review_v1",
                 "large_scale_resident_phase2_environment_private_v1",
                 "large_scale_resident_phase2_private_evidence_v1",
                 "large_scale_resident_private_evidence_v1",
                 "cost_guidance_private_multihop_audit_v1", "infra_joint.control.provenance"):
        assert name in sources
