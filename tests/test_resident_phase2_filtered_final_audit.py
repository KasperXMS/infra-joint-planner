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
final = importlib.import_module("large_scale_resident_phase2_filtered_final_audit_v1")
ACTUAL_SOURCES = final.audit_sources
ACTUAL_PRIVATE = final.private.audit_phase_two
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two
ACTUAL_GUARD = final.private.previous.private.assert_inactive


@pytest.fixture
def prepared(legacy_prepared, monkeypatch):
    value = legacy_prepared
    for index, reviewer, key, receipt in (
            (81, final.derived, "derived_field_proof", "d" * 64),
            (84, final.environment.field.review, "field_misuse_proof", "i" * 64),
            (103, final.filtered, "derived_field_proof", "f" * 64)):
        old = next(a for a in value.ledger.original_attempts if a.run_id == f"run-{index}")
        raw = replace(old, disposition="confounder", reason="raw-field-gate")
        value.ledger.original_attempts = tuple(
            raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts)
        value.projection["rows"][index]["attempts"][0].update(
            original_disposition="confounder", receipt_sha256=receipt,
            telemetry=None, benchmark_score=None)
        proof = {"run_id": raw.run_id, "original_admission_sha256": raw.receipt_sha256,
                 "original_execution_sha256": raw.execution_sha256,
                 "reviewed_admission_sha256": receipt,
                 "reviewer_sources_sha256": {"proof.py": "s" * 64},
                 "execution_sources_sha256": {"worker.py": "w" * 64},
                 "tested_transformation_sources_sha256": {"transform.py": "t" * 64},
                 key: [{"action_id": f"failed-{index}-1"}, {"action_id": f"failed-{index}-2"}]}
        directory = value.root / reviewer.DIRECTORY
        directory.mkdir(exist_ok=True)
        path = directory / (raw.run_id + ".json")
        path.write_text(json.dumps(proof), encoding="utf-8")
        sidecars = {path.name: final.environment.cadence.digest(path)}
        if index == 81:
            value.derived_sidecars = sidecars
        elif index == 103:
            value.filtered_sidecars = sidecars
        else:
            value.control_value["initial_field_sidecars"].update(sidecars)
        monkeypatch.setattr(reviewer, "verify_sidecar", lambda p, _: json.loads(p.read_text()))
    value.control.write_text(json.dumps(value.control_value), encoding="utf-8")
    manifest = json.loads(value.manifest.read_text())
    manifest.update(extension_version=final.environment.VERSION,
                    derived_field_sidecars=value.derived_sidecars,
                    filtered_field_sidecars=value.filtered_sidecars, **value.control_value)
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls = []

    def full_control(control, sidecar, derived_sidecars=None, filtered_sidecars=None):
        assert control == value.control and sidecar == Path(manifest["sidecar_path"])
        assert derived_sidecars == value.derived_sidecars
        assert filtered_sidecars == value.filtered_sidecars
        value.routing_calls.append("filtered-full-control")
        return manifest["parent"], tuple(f"cell-{i}" for i in range(192))

    def membership(control, cells, sidecar, *, require_dispatch_ready):
        assert control == {**value.control_value, "derived_field_sidecars": value.derived_sidecars,
                           "filtered_field_sidecars": value.filtered_sidecars}
        assert require_dispatch_ready is True
        value.routing_calls.append("filtered-membership")
        return value.ledger

    def fence(path, sha, checked):
        assert path == value.manifest and sha == "m" * 64
        assert checked["extension_version"] == final.environment.VERSION
        value.routing_calls.append("filtered-fence")

    def collect(*_):
        value.routing_calls.append("filtered-collect")
        return value.projection

    def diagnostics(manifest, sha, derived, filtered):
        assert manifest == value.manifest and sha == "m" * 64
        assert derived == value.derived_sidecars and filtered == value.filtered_sidecars
        value.calls.append("private")
        return value.diagnostics

    monkeypatch.setattr(final.environment, "fence", fence)
    monkeypatch.setattr(final.environment, "full_control", full_control)
    monkeypatch.setattr(final.environment, "membership", membership)
    monkeypatch.setattr(final.environment, "collect", collect)
    monkeypatch.setattr(final, "audit_sources", lambda: value.sources.copy())
    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    for old_environment in (final.previous.environment, final.previous.previous.environment):
        monkeypatch.setattr(old_environment, "fence",
                            lambda *_: pytest.fail("hidden historical environment fence"))
    return value


def create(prepared):
    return final.create_bundle(prepared.manifest, "m" * 64,
                               provenance_sha256(prepared.sources), prepared.output)


def test_all193_four_maps_unknowns_originals_and_no_global_mutation(prepared):
    original_projection = copy.deepcopy(prepared.projection)
    original_control = copy.deepcopy(prepared.control_value)
    functions = (final.original.reconcile, vars(final.original)["_inventory"],
                 ACTUAL_PRIVATE, final.previous.SOURCE_MODULES)
    namespaces = [dict(function.__globals__) for function in functions]
    result = create(prepared)
    rows = result["projection"]["rows"]
    record = rows[103]["attempts"][0]
    assert record["confirmed_absent_filtered_record_field_failures"] == 2
    assert record["confirmed_absent_record_field_failures"] == 2
    assert record["phase2_filtered_field_sidecar_sha256"] == (
        prepared.filtered_sidecars["run-103.json"])
    assert record["filtered_field_review_source_sha256"] == {"proof.py": "s" * 64}
    assert record["filtered_field_execution_source_sha256"] == {"worker.py": "w" * 64}
    assert record["filtered_field_transformation_source_sha256"] == {"transform.py": "t" * 64}
    assert record["filtered_field_original_admission_sha256"] == "r" * 64
    assert record["filtered_field_reviewed_admission_sha256"] == "f" * 64
    for index in (81, 84, 103):
        reviewed = rows[index]["attempts"][0]
        assert reviewed["original_rejection_preserved"] is True
        assert reviewed["original_disposition"] == "confounder"
        assert reviewed["original_receipt_sha256"] == "r" * 64
        assert reviewed["semantic_primary_cause"] is None
        assert reviewed["benchmark_score"] is None and reviewed["telemetry"] is None
    assert rows[81]["attempts"][0]["confirmed_absent_derived_record_field_failures"] == 2
    assert rows[0]["attempts"][0]["confirmed_post_inference_json_failures"] == 2
    assert rows[1]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    assert rows[71]["attempts"][0]["run_id"] == final.original.environment.RUN
    assert rows[71]["attempts"][0]["disposition"] == "operational_excluded"
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    assert result["filtered_field_sidecars"] == prepared.filtered_sidecars
    assert prepared.projection == original_projection and prepared.control_value == original_control
    assert prepared.routing_calls == ["filtered-fence", "filtered-full-control",
                                      "filtered-membership", "filtered-collect", "filtered-fence"]
    assert prepared.calls == ["private"]
    assert json.loads(prepared.output.read_text()) == result
    for key in ("projection", "recipient_audit", "private_diagnostics"):
        assert result["component_sha256"][key] == provenance_sha256(result[key])
    for key in ("semantic_audit_complete", "manual_audit_complete", "q1_q10_complete",
                "goal_complete", "artifact_bodies_exported", "measured_execution_modified"):
        assert result[key] is False
    for function, namespace in zip(functions, namespaces, strict=True):
        assert function.__globals__ == namespace


def test_same_native_private_route_scanner_guard_and_all193(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    monkeypatch.setattr(final.private.previous.private, "assert_inactive", ACTUAL_GUARD)
    scanner = final.private.previous.private.scan_store
    guard = final.private.previous.private.assert_inactive
    for row in prepared.projection["rows"]:
        row["condition"]["task"] = {"family": "video_mme", "position": 1}
        for attempt in row["attempts"]:
            attempt["environment_stage"] = "pre-strata"
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("synthetic private body scan"))
    result = create(prepared)
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.routing_calls.count("filtered-fence") == 4
    assert prepared.routing_calls.count("filtered-full-control") == 2
    assert prepared.routing_calls.count("filtered-membership") == 2
    assert final.private.previous.private.scan_store is scanner
    assert final.private.previous.private.assert_inactive is guard
    assert final.private.audit_phase_two is ACTUAL_PRIVATE


def test_actual_private_entrypoint_visits_every193_including_excluded_original(
        prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    visits = []
    for row in prepared.projection["rows"]:
        row["condition"]["task"] = {"family": "multihop_rag", "position": 1}
        for attempt in row["attempts"]:
            attempt["environment_stage"] = "pre-strata"

    def body_scan(directory, *_):
        visits.append(directory)
        return {"retention": None}

    monkeypatch.setattr(final.private.previous, "audit_multihop", body_scan)
    result = create(prepared)
    assert len(visits) == len(set(visits)) == 193
    assert (prepared.root / "evidence" / final.original.environment.CELL / "attempt1") in visits
    assert len(result["private_diagnostics"]["records"]) == 193


def test_direct_private_entrypoint_incomplete_guard_before_any_body_scan(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("private body before all192/all193 gate"))
    prepared.projection["attempt_count"] = 192
    with pytest.raises(RuntimeError, match="all192"):
        ACTUAL_ADAPTER_PRIVATE(prepared.manifest, "m" * 64,
                               prepared.derived_sidecars, prepared.filtered_sidecars)
    assert not prepared.output.exists()


def test_live_guard_first_before_sources_control_and_output(monkeypatch):
    def live(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", live)
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("live source read"))
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("live metadata read"))
    with pytest.raises(RuntimeError, match="live controller"):
        final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))


@pytest.mark.parametrize("key,value", [
    ("phase2_complete", False), ("attempt_count", 192), ("scheduled_cells", 191),
    ("admitted_cells", 191), ("pending_count", 1), ("confounded_attempts", 1),
    ("operational_excluded_attempts", 2)])
def test_incomplete_guards_before_private_body(prepared, key, value):
    prepared.projection[key] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing", "overlap", "hash", "raw", "run", "execution",
                                   "effective", "empty", "old71", "replacement-extra",
                                   "initial-missing", "model-missing", "derived-missing"])
def test_filtered_and_original_inventory_fail_closed(prepared, change):
    path = prepared.root / final.filtered.DIRECTORY / "run-103.json"
    proof = json.loads(path.read_text())
    if change == "missing":
        prepared.filtered_sidecars.clear()
    elif change == "overlap":
        prepared.control_value["initial_field_sidecars"].update(prepared.filtered_sidecars)
        prepared.control.write_text(json.dumps(prepared.control_value))
    elif change == "hash":
        prepared.filtered_sidecars[path.name] = "a" * 64
    elif change == "raw":
        prepared.projection["rows"][103]["attempts"][0]["original_receipt_sha256"] = "drift"
    elif change == "old71":
        prepared.projection["rows"][71]["attempts"].pop(0)
    elif change == "replacement-extra":
        prepared.projection["rows"][71]["attempts"].append(
            copy.deepcopy(prepared.projection["rows"][71]["attempts"][1]))
    elif change in ("initial-missing", "model-missing"):
        key = "initial_field_sidecars" if change == "initial-missing" else "model_json_sidecars"
        prepared.control_value[key].clear()
        prepared.control.write_text(json.dumps(prepared.control_value))
    elif change == "derived-missing":
        prepared.derived_sidecars.clear()
    else:
        key = {"run": "run_id", "execution": "original_execution_sha256",
               "effective": "reviewed_admission_sha256", "empty": "derived_field_proof"}[change]
        proof[key] = [] if change == "empty" else "drift"
        path.write_text(json.dumps(proof))
        prepared.filtered_sidecars[path.name] = final.environment.cadence.digest(path)
    value = json.loads(prepared.manifest.read_text())
    value["filtered_field_sidecars"] = prepared.filtered_sidecars
    value["derived_field_sidecars"] = prepared.derived_sidecars
    prepared.manifest.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_source_pin_before_metadata(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"filtered": "drift"})
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata before pin"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)
    assert not prepared.calls


def test_during_scan_source_drift_prevents_exclusive_write(prepared, monkeypatch):
    def diagnostics(*_):
        prepared.sources["wrapper.py"] = "drift"
        return prepared.diagnostics

    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    with pytest.raises(RuntimeError, match="source/journal changed"):
        create(prepared)
    assert not prepared.output.exists()


def test_exclusive_output_preserves_original(prepared):
    create(prepared)
    before = prepared.output.read_bytes()
    with pytest.raises(FileExistsError):
        create(prepared)
    assert prepared.output.read_bytes() == before and prepared.calls == ["private"]


def test_actual_import_source_closure_keeps_every_old_pin_and_adds_new_modules():
    actual = ACTUAL_SOURCES()
    old = final.previous.audit_sources()
    assert all(actual.get(name) == sha for name, sha in old.items())
    paths = final.audit_source_paths()
    for name in ("large_scale_resident_phase2_filtered_final_audit_v1",
                 "large_scale_resident_phase2_filtered_environment_v1",
                 "large_scale_resident_phase2_filtered_field_review_v1",
                 "large_scale_resident_derived_field_review_v2",
                 "large_scale_resident_private_evidence_v1",
                 "cost_guidance_private_multihop_audit_v1"):
        assert name in actual
        assert paths[name] == str(Path(sys.modules[name].__file__).resolve())


def test_actual_imported_namespace_not_assumed_archive_is_source_pinned(prepared, monkeypatch):
    archive = prepared.root / "actual-installed-namespace"
    archive.mkdir()
    source = archive / Path(final.filtered.__file__).name
    source.write_bytes(Path(final.filtered.__file__).read_bytes())
    monkeypatch.setattr(final.filtered, "__file__", str(source))
    monkeypatch.setattr(final, "audit_sources", ACTUAL_SOURCES)
    before = final.audit_sources()
    assert final.audit_source_paths()[final.filtered.__name__] == str(source.resolve())
    source.write_bytes(source.read_bytes() + b"\n# synthetic source drift\n")
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata after drift"))
    with pytest.raises(RuntimeError, match="source drift"):
        final.create_bundle(prepared.manifest, "m" * 64, provenance_sha256(before), prepared.output)
    assert not prepared.calls and not prepared.output.exists()


def test_cli_preserves_launch_source_and_manifest_pins(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(final, "create_bundle", lambda *args: calls.append(args))
    final.main(["--manifest", "filtered.json", "--manifest-sha256", "m" * 64,
                "--audit-source-sha256", "s" * 64, "--output", "bundle.json"])
    assert calls == [(Path("filtered.json"), "m" * 64, "s" * 64, Path("bundle.json"))]
    assert json.loads(capsys.readouterr().out) == {
        "preserved_attempts": 193, "model_calls": 0, "goal_complete": False}
