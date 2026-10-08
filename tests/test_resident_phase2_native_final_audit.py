import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_resident_phase2_filtered_final_audit as filtered_tests

from infra_joint.control.provenance import provenance_sha256

legacy_prepared = filtered_tests.legacy_prepared
filtered_prepared = filtered_tests.prepared
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
final = importlib.import_module("large_scale_resident_phase2_native_final_audit_v1")
ACTUAL_SOURCES = final.audit_sources
ACTUAL_PRIVATE = final.private.audit_phase_two
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two
ACTUAL_GUARD = final.private.previous.private.assert_inactive


@pytest.fixture
def prepared(filtered_prepared, monkeypatch):
    value = filtered_prepared
    old = next(a for a in value.ledger.original_attempts if a.run_id == "run-105")
    raw = replace(old, disposition="confounder", reason=final.native.sdk.GATE)
    value.ledger.original_attempts = tuple(
        raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts)
    record = value.projection["rows"][105]["attempts"][0]
    record.update(original_disposition="confounder", receipt_sha256="n" * 64,
                  telemetry=None, benchmark_score=None, original_evaluation=None,
                  execution_completed=False, post_inference_failed_service_tokens=None)
    proof = {"run_id": raw.run_id, "original_admission_sha256": raw.receipt_sha256,
             "original_execution_sha256": raw.execution_sha256,
             "reviewed_admission_sha256": "n" * 64,
             "reviewer_sources_sha256": {"native-review.py": "a" * 64},
             "execution_sources": {
                 "owned_native_sha256": {"native.py": "b" * 64},
                 "installed_sdk_sources": {"tool_execution": {
                     "import_path": "lexical/sdk.py", "resolved_path": "actual/sdk.py",
                     "sha256": "c" * 64}}},
             "native_argument_proof": [{"arguments_bytes": 1262, "failure_type": "json_invalid"}],
             "reviewed_admission": {"disposition": "valid", "reason": final.native.REASON,
                                    "execution_completed": False, "original_evaluation": None,
                                    "replacement_authorized": False}}
    directory = value.root / final.native.DIRECTORY
    directory.mkdir()
    path = directory / "run-105.json"
    path.write_text(json.dumps(proof), encoding="utf-8")
    value.native_sidecars = {path.name: final.environment.cadence.digest(path)}
    monkeypatch.setattr(final.native, "verify_sidecar", lambda p, _: json.loads(p.read_text()))
    raw_by_run = {a.run_id: a for a in value.ledger.original_attempts}
    effective = []
    for row in value.projection["rows"]:
        for attempt in row["attempts"]:
            saved = raw_by_run[attempt["run_id"]]
            reason = final.native.REASON if saved.run_id == raw.run_id else saved.reason
            attempt.update(original_reason=saved.reason, reason=reason)
            effective.append(replace(saved, disposition=attempt["disposition"], reason=reason,
                                     receipt_sha256=attempt["receipt_sha256"]))
    value.ledger.attempts = tuple(effective)
    manifest = json.loads(value.manifest.read_text())
    manifest.update(extension_version=final.environment.VERSION,
                    native_argument_sidecars=value.native_sidecars)
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls.clear()

    def full_control(control, sidecar, derived, filtered, native):
        assert control == value.control and sidecar == Path(manifest["sidecar_path"])
        assert (derived, filtered, native) == (
            value.derived_sidecars, value.filtered_sidecars, value.native_sidecars)
        value.routing_calls.append("native-full-control")
        return manifest["parent"], tuple(f"cell-{i}" for i in range(192))

    def membership(control, cells, sidecar, *, require_dispatch_ready):
        assert control == {**value.control_value, "derived_field_sidecars": value.derived_sidecars,
                           "filtered_field_sidecars": value.filtered_sidecars,
                           "native_argument_sidecars": value.native_sidecars}
        assert require_dispatch_ready is True
        value.routing_calls.append("native-membership")
        return value.ledger

    def fence(path, sha, checked):
        assert path == value.manifest and sha == "m" * 64
        assert checked["extension_version"] == final.environment.VERSION
        value.routing_calls.append("native-fence")

    def collect(*_):
        value.routing_calls.append("native-collect")
        return value.projection

    def diagnostics(manifest, sha, derived, filtered, native):
        assert manifest == value.manifest and sha == "m" * 64
        assert (derived, filtered, native) == (
            value.derived_sidecars, value.filtered_sidecars, value.native_sidecars)
        value.calls.append("private")
        return value.diagnostics

    monkeypatch.setattr(final.environment, "full_control", full_control)
    monkeypatch.setattr(final.environment, "membership", membership)
    monkeypatch.setattr(final.environment, "fence", fence)
    monkeypatch.setattr(final.environment, "collect", collect)
    monkeypatch.setattr(final, "audit_sources", lambda: value.sources.copy())
    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    monkeypatch.setattr(final.previous.environment, "fence",
                        lambda *_: pytest.fail("historical fence route"))
    return value


def create(value):
    return final.create_bundle(value.manifest, "m" * 64,
                               provenance_sha256(value.sources), value.output)


def direct(value):
    return ACTUAL_ADAPTER_PRIVATE(value.manifest, "m" * 64, value.derived_sidecars,
                                  value.filtered_sidecars, value.native_sidecars)


def test_all193_five_groups_preserve_old_fields_unknowns_and_globals(prepared):
    projection, control = copy.deepcopy(prepared.projection), copy.deepcopy(prepared.control_value)
    functions = (final.original.reconcile, vars(final.original)["_inventory"], ACTUAL_PRIVATE,
                 final.previous.previous.SOURCE_MODULES)
    namespaces = [dict(function.__globals__) for function in functions]
    result = create(prepared)
    rows = result["projection"]["rows"]
    record = rows[105]["attempts"][0]
    assert record["native_argument_proof_count"] == 1
    assert record["confirmed_native_argument_failures"] == 1
    assert record["native_argument_sidecar_sha256"] == prepared.native_sidecars["run-105.json"]
    assert record["original_reason"] == final.native.sdk.GATE
    assert record["reason"] == final.native.REASON
    assert record["original_rejection_preserved"] is True
    assert record["original_disposition"] == "confounder"
    assert record["native_argument_original_admission_sha256"] == "r" * 64
    assert record["native_argument_reviewed_admission_sha256"] == "n" * 64
    assert record["native_argument_execution_sources"]["installed_sdk_sources"][
        "tool_execution"]["resolved_path"] == "actual/sdk.py"
    for key in ("telemetry", "benchmark_score", "original_evaluation",
                "post_inference_failed_service_tokens", "semantic_primary_cause"):
        assert record[key] is None
    assert record["execution_completed"] is False
    assert rows[0]["attempts"][0]["confirmed_post_inference_json_failures"] == 2
    assert rows[1]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    assert rows[81]["attempts"][0]["confirmed_absent_derived_record_field_failures"] == 2
    assert rows[84]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    assert rows[103]["attempts"][0]["confirmed_absent_filtered_record_field_failures"] == 2
    assert rows[103]["attempts"][0]["filtered_field_transformation_source_sha256"] == {
        "transform.py": "t" * 64}
    assert rows[71]["attempts"][0]["run_id"] == final.original.environment.RUN
    assert rows[71]["attempts"][0]["disposition"] == "operational_excluded"
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    assert result["native_argument_sidecars"] == prepared.native_sidecars
    assert prepared.projection == projection and prepared.control_value == control
    assert prepared.calls == ["private"]
    assert json.loads(prepared.output.read_text()) == result
    for key in ("projection", "recipient_audit", "private_diagnostics"):
        assert result["component_sha256"][key] == provenance_sha256(result[key])
    for key in ("semantic_audit_complete", "manual_audit_complete", "q1_q10_complete",
                "goal_complete", "artifact_bodies_exported", "measured_execution_modified",
                "excluded_attempt_omitted"):
        assert result[key] is False
    assert result["planner_or_model_calls"] == 0
    assert result["score_aggregation"] == "not performed"
    for function, namespace in zip(functions, namespaces, strict=True):
        assert function.__globals__ == namespace


def test_actual_private_scanner_route_visits_all193_including_original71(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    monkeypatch.setattr(final.private.previous.private, "assert_inactive", ACTUAL_GUARD)
    scanner = final.private.previous.private.scan_store
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
    assert prepared.root / "evidence" / final.original.environment.CELL / "attempt1" in visits
    assert len(result["private_diagnostics"]["records"]) == 193
    assert final.private.previous.private.scan_store is scanner
    assert final.private.previous.private.assert_inactive is ACTUAL_GUARD
    assert final.private.audit_phase_two is ACTUAL_PRIVATE


@pytest.mark.parametrize("entry", ["bundle", "direct"])
def test_live_guard_before_sources_metadata_or_output(monkeypatch, entry):
    def live(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", live)
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("live source read"))
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("live metadata read"))
    with pytest.raises(RuntimeError, match="live controller"):
        if entry == "bundle":
            final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))
        else:
            ACTUAL_ADAPTER_PRIVATE(Path("absent"), "x", {}, {}, {})


@pytest.mark.parametrize("key,value", [
    ("phase2_complete", False), ("attempt_count", 192), ("scheduled_cells", 191),
    ("admitted_cells", 191), ("pending_count", 1), ("confounded_attempts", 1),
    ("operational_excluded_attempts", 2)])
def test_incomplete_before_private_body(prepared, key, value):
    prepared.projection[key] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["attempt_count", "late-row", "native-proof", "effective-pair"])
def test_actual_direct_private_guard_includes_late_inventory_and_proof(
        prepared, monkeypatch, change):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("private body before metadata guard"))
    if change == "attempt_count":
        prepared.projection["attempt_count"] = 192
    elif change == "late-row":
        prepared.projection["rows"][-1]["pending_run_ids"] = ["pending-last"]
    elif change == "native-proof":
        prepared.native_sidecars["run-105.json"] = "a" * 64
    else:
        prepared.ledger.attempts = tuple(
            replace(a, receipt_sha256="drift") if a.run_id == "run-191" else a
            for a in prepared.ledger.attempts)
    with pytest.raises(RuntimeError):
        direct(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_controller_becomes_live_before_first_body_scan(prepared, monkeypatch):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final, "audit_phase_two", ACTUAL_ADAPTER_PRIVATE)
    checks = 0

    def guard(*_):
        nonlocal checks
        checks += 1
        if checks == 3:
            raise RuntimeError("controller became live")

    for row in prepared.projection["rows"]:
        row["condition"]["task"] = {"family": "multihop_rag", "position": 1}
        for attempt in row["attempts"]:
            attempt["environment_stage"] = "pre-strata"
    monkeypatch.setattr(final.private.previous.private, "assert_inactive", guard)
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("private body after controller became live"))
    with pytest.raises(RuntimeError, match="became live"):
        create(prepared)
    assert checks == 3 and not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing", "overlap", "hash", "raw", "raw-reason", "run",
                                   "execution", "effective", "empty", "old71", "late-pair",
                                   "initial-missing", "model-missing", "derived-missing",
                                   "filtered-missing", "control-map"])
def test_exact_five_group_and_raw_effective_drift_rejects_before_scan(prepared, change):
    path = prepared.root / final.native.DIRECTORY / "run-105.json"
    proof = json.loads(path.read_text())
    if change == "missing":
        prepared.native_sidecars.clear()
    elif change == "overlap":
        prepared.control_value["initial_field_sidecars"].update(prepared.native_sidecars)
    elif change == "hash":
        prepared.native_sidecars[path.name] = "a" * 64
    elif change in ("raw", "raw-reason"):
        key = "original_receipt_sha256" if change == "raw" else "original_reason"
        prepared.projection["rows"][105]["attempts"][0][key] = "drift"
    elif change == "old71":
        prepared.projection["rows"][71]["attempts"].pop(0)
    elif change == "late-pair":
        prepared.ledger.attempts = tuple(
            replace(a, receipt_sha256="drift") if a.run_id == "run-191" else a
            for a in prepared.ledger.attempts)
    elif change in ("initial-missing", "model-missing"):
        key = "initial_field_sidecars" if change == "initial-missing" else "model_json_sidecars"
        prepared.control_value[key].clear()
    elif change in ("derived-missing", "filtered-missing"):
        getattr(prepared, change.split("-")[0] + "_sidecars").clear()
    elif change == "control-map":
        prepared.control_value["native_argument_sidecars"] = {"drift.json": "d" * 64}
    else:
        key = {"run": "run_id", "execution": "original_execution_sha256",
               "effective": "reviewed_admission_sha256", "empty": "native_argument_proof"}[change]
        proof[key] = [] if change == "empty" else "drift"
        path.write_text(json.dumps(proof))
        prepared.native_sidecars[path.name] = final.environment.cadence.digest(path)
    prepared.control.write_text(json.dumps(prepared.control_value))
    manifest = json.loads(prepared.manifest.read_text())
    manifest.update(derived_field_sidecars=prepared.derived_sidecars,
                    filtered_field_sidecars=prepared.filtered_sidecars,
                    native_argument_sidecars=prepared.native_sidecars)
    prepared.manifest.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


def test_source_pin_before_metadata(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"native": "drift"})
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata before pin"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)


@pytest.mark.parametrize("change", ["missing", "duplicate", "admission", "disposition"])
def test_all_attempt_recipient_binding_before_private_scan(prepared, change):
    records = prepared.recipients["records"]
    if change == "missing":
        records.pop()
    elif change == "duplicate":
        records[-1] = records[0]
    else:
        key = "original_admission_sha256" if change == "admission" else "effective_disposition"
        records[0][key] = "drift"
    with pytest.raises(RuntimeError, match="recipient"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing", "duplicate", "journal", "manifest", "semantic"])
def test_private_diagnostic_binding_prevents_write(prepared, change):
    if change == "missing":
        prepared.diagnostics["records"].pop()
    elif change == "duplicate":
        prepared.diagnostics["records"][-1] = prepared.diagnostics["records"][0]
    else:
        key = {"journal": "journal_sha256", "manifest": "manifest_sha256",
               "semantic": "semantic_audit_complete"}[change]
        prepared.diagnostics[key] = True if change == "semantic" else "drift"
    with pytest.raises(RuntimeError, match="diagnostic"):
        create(prepared)
    assert not prepared.output.exists()


@pytest.mark.parametrize("change", ["source", "path", "journal", "metadata"])
def test_drift_during_scan_prevents_write(prepared, monkeypatch, change):
    actual_paths = final.audit_source_paths()
    paths = dict(actual_paths)
    monkeypatch.setattr(final, "audit_source_paths", lambda: paths.copy())
    fences = 0

    def fence(*_):
        nonlocal fences
        fences += 1
        if change == "metadata" and fences > 1:
            raise RuntimeError("metadata drift")

    def diagnostics(*_):
        if change == "source":
            prepared.sources["wrapper.py"] = "drift"
        elif change == "path":
            paths["wrapper.py"] = "drift"
        elif change == "journal":
            prepared.ledger.path.write_text("journal drift")
        return prepared.diagnostics

    monkeypatch.setattr(final.environment, "fence", fence)
    monkeypatch.setattr(final, "audit_phase_two", diagnostics)
    with pytest.raises(RuntimeError, match="changed|drift"):
        create(prepared)
    assert not prepared.output.exists()


def test_exclusive_output_preserves_original(prepared):
    create(prepared)
    before = prepared.output.read_bytes()
    with pytest.raises(FileExistsError):
        create(prepared)
    assert prepared.output.read_bytes() == before and prepared.calls == ["private"]


def test_actual_import_closure_preserves_all_old_sources_and_adds_actual_native_modules():
    actual, old = ACTUAL_SOURCES(), final.previous.audit_sources()
    assert all(actual.get(name) == sha for name, sha in old.items())
    paths = final.audit_source_paths()
    for module in (final, final.environment, final.native, final.native.sdk,
                   final.private.previous.private,
                   sys.modules[final.private.previous.private.scan_store.__module__]):
        assert module.__name__ in actual
        assert paths[module.__name__] == str(Path(module.__file__).resolve())


def test_actual_installed_namespace_source_is_pinned(prepared, monkeypatch):
    directory = prepared.root / "actual-installed-namespace"
    directory.mkdir()
    source = directory / Path(final.native.__file__).name
    source.write_bytes(Path(final.native.__file__).read_bytes())
    monkeypatch.setattr(final.native, "__file__", str(source))
    monkeypatch.setattr(final, "audit_sources", ACTUAL_SOURCES)
    before = final.audit_sources()
    assert final.audit_source_paths()[final.native.__name__] == str(source.resolve())
    source.write_bytes(source.read_bytes() + b"\n# source drift\n")
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata after drift"))
    with pytest.raises(RuntimeError, match="source drift"):
        final.create_bundle(prepared.manifest, "m" * 64, provenance_sha256(before), prepared.output)


def test_cli_keeps_external_pins(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(final, "create_bundle", lambda *args: calls.append(args))
    final.main(["--manifest", "native.json", "--manifest-sha256", "m" * 64,
                "--audit-source-sha256", "s" * 64, "--output", "bundle.json"])
    assert calls == [(Path("native.json"), "m" * 64, "s" * 64, Path("bundle.json"))]
    assert json.loads(capsys.readouterr().out) == {
        "preserved_attempts": 193, "model_calls": 0, "goal_complete": False}
