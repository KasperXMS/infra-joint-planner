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
final = importlib.import_module("large_scale_resident_phase2_renewed_final_audit_v1")
ACTUAL_SOURCES = final.audit_sources
ACTUAL_PRIVATE = final.private.audit_phase_two
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two
ACTUAL_GUARD = final.private.previous.private.assert_inactive


@pytest.fixture
def prepared(legacy_prepared, monkeypatch):
    value = legacy_prepared
    for index, reviewer, key, receipt in (
            (81, final.derived, "derived_field_proof", "d" * 64),
            (84, final.previous.previous.environment.field.review, "field_misuse_proof", "i" * 64)):
        original = next(a for a in value.ledger.original_attempts if a.run_id == f"run-{index}")
        raw = replace(original, disposition="confounder", reason="raw-field-gate")
        value.ledger.original_attempts = tuple(
            raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts)
        value.projection["rows"][index]["attempts"][0].update(
            original_disposition="confounder", receipt_sha256=receipt,
            telemetry=None, benchmark_score=None)
        proof = {"run_id": raw.run_id, "original_admission_sha256": raw.receipt_sha256,
                 "original_execution_sha256": raw.execution_sha256,
                 "reviewed_admission_sha256": receipt,
                 key: [{"action_id": f"failed-{index}-1"}, {"action_id": f"failed-{index}-2"}]}
        directory = value.root / reviewer.DIRECTORY
        directory.mkdir(exist_ok=True)
        path = directory / (raw.run_id + ".json")
        path.write_text(json.dumps(proof), encoding="utf-8")
        sidecars = {path.name: final.environment.cadence.digest(path)}
        if index == 81:
            value.derived_sidecars = sidecars
        else:
            value.control_value["initial_field_sidecars"].update(sidecars)
    value.control.write_text(json.dumps(value.control_value), encoding="utf-8")
    manifest = json.loads(value.manifest.read_text())
    manifest.update(extension_version=final.environment.VERSION,
                    derived_field_sidecars=value.derived_sidecars, **value.control_value)
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls = []

    def full_control(control, sidecar, derived_sidecars=None):
        assert control == value.control and sidecar == Path(manifest["sidecar_path"])
        assert derived_sidecars == value.derived_sidecars
        value.routing_calls.append("renewed-full-control")
        return manifest["parent"], tuple(f"cell-{i}" for i in range(192))

    def membership(control, cells, sidecar, *, require_dispatch_ready):
        assert control == {**value.control_value, "derived_field_sidecars": value.derived_sidecars}
        assert require_dispatch_ready is True
        value.routing_calls.append("renewed-membership")
        return value.ledger

    def fence(path, sha, checked):
        assert path == value.manifest and sha == "m" * 64
        assert checked["extension_version"] == final.environment.VERSION
        value.routing_calls.append("renewed-fence")

    def collect(*_):
        value.routing_calls.append("renewed-collect")
        return value.projection

    def diagnostics(manifest, sha, maps):
        assert manifest == value.manifest and sha == "m" * 64 and maps == value.derived_sidecars
        value.calls.append("private")
        return value.diagnostics

    monkeypatch.setattr(final.environment, "fence", fence)
    monkeypatch.setattr(final.environment, "full_control", full_control)
    monkeypatch.setattr(final.environment, "membership", membership)
    monkeypatch.setattr(final.environment, "collect", collect)
    monkeypatch.setattr(final.derived, "verify_sidecar",
                        lambda path, _: json.loads(path.read_text()))
    monkeypatch.setattr(final, "audit_sources", lambda: value.sources.copy())
    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    monkeypatch.setattr(final.previous.environment, "fence",
                        lambda *_: pytest.fail("hidden old derived environment fence"))
    return value


def create(prepared):
    return final.create_bundle(prepared.manifest, "m" * 64,
                               provenance_sha256(prepared.sources), prepared.output)


def test_renewed_manifest_all193_routes_three_maps_and_preserves_unknowns(prepared):
    original_projection = copy.deepcopy(prepared.projection)
    original_control = copy.deepcopy(prepared.control_value)
    original_namespaces = [dict(function.__globals__) for function in (
        final.CREATE_BUNDLE, final.RECONCILE, final.AUDIT_PHASE_TWO, final.ENVIRONMENT_VIEW)]
    result = create(prepared)
    assert result["version"] == final.VERSION
    assert json.loads(prepared.output.read_text()) == result
    rows = result["projection"]["rows"]
    derived, initial = rows[81]["attempts"][0], rows[84]["attempts"][0]
    assert derived["confirmed_absent_derived_record_field_failures"] == 2
    assert derived["confirmed_absent_record_field_failures"] == 2
    assert initial["confirmed_absent_record_field_failures"] == 2
    assert initial["phase2_field_sidecar_sha256"] == (
        prepared.control_value["initial_field_sidecars"]["run-84.json"])
    assert derived["phase2_derived_field_sidecar_sha256"] == (
        prepared.derived_sidecars["run-81.json"])
    for record in (derived, initial):
        assert record["original_rejection_preserved"] is True
        assert record["original_disposition"] == "confounder"
        assert record["original_receipt_sha256"] == "r" * 64
        assert record["benchmark_score"] is None and record["telemetry"] is None
        assert record["semantic_primary_cause"] is None
    assert rows[0]["attempts"][0]["confirmed_post_inference_json_failures"] == 2
    assert rows[0]["attempts"][0]["post_inference_failed_service_tokens"] is None
    assert rows[1]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    excluded = rows[71]["attempts"][0]
    assert excluded["run_id"] == final.previous.previous.environment.RUN
    assert excluded["disposition"] == "operational_excluded"
    assert sum(len(row["attempts"]) for row in rows) == 193
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.projection == original_projection and prepared.control_value == original_control
    assert prepared.routing_calls == ["renewed-fence", "renewed-full-control",
                                      "renewed-membership", "renewed-collect", "renewed-fence"]
    for component in ("projection", "recipient_audit", "private_diagnostics"):
        assert result["component_sha256"][component] == provenance_sha256(result[component])
    for key in ("semantic_audit_complete", "manual_audit_complete", "q1_q10_complete",
                "goal_complete", "artifact_bodies_exported", "measured_execution_modified"):
        assert result[key] is False
    for function, namespace in zip((final.CREATE_BUNDLE, final.RECONCILE,
                                    final.AUDIT_PHASE_TWO, final.ENVIRONMENT_VIEW),
                                   original_namespaces, strict=True):
        assert function.__globals__ == namespace


def test_private_route_uses_renewed_control_fence_and_same_original_scanner(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    monkeypatch.setattr(final.private.previous.private, "assert_inactive", ACTUAL_GUARD)
    original_scanner = final.private.previous.private.scan_store
    original_guard = final.private.previous.private.assert_inactive
    for row in prepared.projection["rows"]:
        row["condition"]["task"] = {"family": "video_mme", "position": 1}
        for attempt in row["attempts"]:
            attempt["environment_stage"] = "pre-strata"
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("unexpected synthetic private body scan"))
    result = create(prepared)
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.routing_calls.count("renewed-fence") == 4
    assert prepared.routing_calls.count("renewed-full-control") == 2
    assert prepared.routing_calls.count("renewed-membership") == 2
    assert final.private.previous.private.scan_store is original_scanner
    assert final.private.previous.private.assert_inactive is original_guard
    assert final.private.audit_phase_two is ACTUAL_PRIVATE


def test_live_guard_precedes_sources_control_and_output(monkeypatch):
    def live(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", live)
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("source read while live"))
    monkeypatch.setattr(final.environment, "read",
                        lambda *_: pytest.fail("metadata read while live"))
    with pytest.raises(RuntimeError, match="live controller"):
        final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))


@pytest.mark.parametrize("key,value", [
    ("phase2_complete", False), ("attempt_count", 192), ("scheduled_cells", 191),
    ("admitted_cells", 191), ("pending_count", 1), ("confounded_attempts", 1),
    ("operational_excluded_attempts", 2)])
def test_incomplete_or_partial_inventory_rejects_before_private_scan(prepared, key, value):
    prepared.projection[key] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing-current-initial-proof", "initial-hash-drift",
                                   "original-identity", "derived-overlap", "old71-missing"])
def test_current_proof_inventory_and_raw_identity_fail_closed(prepared, change):
    if change == "missing-current-initial-proof":
        prepared.control_value["initial_field_sidecars"].pop("run-84.json")
    elif change == "initial-hash-drift":
        prepared.control_value["initial_field_sidecars"]["run-84.json"] = "a" * 64
    elif change == "original-identity":
        prepared.projection["rows"][84]["attempts"][0]["original_receipt_sha256"] = "drift"
    elif change == "derived-overlap":
        prepared.control_value["initial_field_sidecars"].update(prepared.derived_sidecars)
    else:
        prepared.projection["rows"][71]["attempts"].pop(0)
    prepared.control.write_text(json.dumps(prepared.control_value))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_external_source_pin_precedes_metadata_reads(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"renewed-source": "drift"})
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("read before source pin"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)
    assert not prepared.calls


def test_source_drift_after_diagnostics_prevents_exclusive_write(prepared, monkeypatch):
    def diagnostics(*_):
        prepared.sources["wrapper.py"] = "drift"
        return prepared.diagnostics

    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    with pytest.raises(RuntimeError, match="source/journal changed"):
        create(prepared)
    assert not prepared.output.exists()


def test_exclusive_bundle_cannot_overwrite_existing_output(prepared):
    create(prepared)
    original = prepared.output.read_bytes()
    with pytest.raises(FileExistsError):
        create(prepared)
    assert prepared.output.read_bytes() == original
    assert prepared.calls == ["private"]


def test_actual_source_closure_and_paths_include_renewed_control_and_same_scanner():
    sources = ACTUAL_SOURCES()
    paths = final.audit_source_paths()
    for name in ("large_scale_resident_phase2_renewed_final_audit_v1",
                 "large_scale_resident_phase2_renewed_environment_v1",
                 "large_scale_resident_phase2_derived_final_audit_v1",
                 "large_scale_resident_phase2_derived_field_review_v1",
                 "large_scale_resident_phase2_field_review_v1",
                 "large_scale_resident_private_evidence_v1",
                 "cost_guidance_private_multihop_audit_v1"):
        assert name in sources
        assert paths[name] == str(Path(sys.modules[name].__file__).resolve())


def test_actual_renewed_module_namespace_is_pinned_and_source_drift_rejects(prepared, monkeypatch):
    archived = prepared.root / "different-installed-namespace"
    archived.mkdir()
    source = archived / Path(final.environment.__file__).name
    source.write_bytes(Path(final.environment.__file__).read_bytes())
    monkeypatch.setattr(final.environment, "__file__", str(source))
    monkeypatch.setattr(final, "audit_sources", ACTUAL_SOURCES)
    before = final.audit_sources()
    assert final.audit_source_paths()[final.environment.__name__] == str(source.resolve())
    source.write_bytes(source.read_bytes() + b"\n# synthetic source drift\n")
    monkeypatch.setattr(final.environment, "read",
                        lambda *_: pytest.fail("read after source drift"))
    with pytest.raises(RuntimeError, match="source drift"):
        final.create_bundle(prepared.manifest, "m" * 64, provenance_sha256(before), prepared.output)
    assert not prepared.calls and not prepared.output.exists()


def test_cli_preserves_launch_pins_output_and_incomplete_status(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(final, "create_bundle", lambda *args: calls.append(args))
    final.main(["--manifest", "renewed.json", "--manifest-sha256", "m" * 64,
                "--audit-source-sha256", "s" * 64, "--output", "bundle.json"])
    assert calls == [(Path("renewed.json"), "m" * 64, "s" * 64, Path("bundle.json"))]
    assert json.loads(capsys.readouterr().out) == {
        "preserved_attempts": 193, "model_calls": 0, "goal_complete": False}
