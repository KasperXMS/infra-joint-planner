import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_resident_phase2_native_final_audit as native_tests

from infra_joint.control.provenance import provenance_sha256

legacy_prepared = native_tests.legacy_prepared
filtered_prepared = native_tests.filtered_prepared
native_prepared = native_tests.prepared
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
final = importlib.import_module("large_scale_resident_phase2_native_renewed_final_audit_v1")
ACTUAL_SOURCES = final.audit_sources
ACTUAL_PRIVATE = final.private.audit_phase_two
ACTUAL_ADAPTER_PRIVATE = final.audit_phase_two
ACTUAL_GUARD = final.private.previous.private.assert_inactive


@pytest.fixture
def prepared(native_prepared, monkeypatch):
    value = native_prepared
    reviewer = final.environment.field.review
    old = next(a for a in value.ledger.original_attempts if a.run_id == "run-107")
    raw = replace(old, disposition="confounder", reason=reviewer.field.GATE)
    value.ledger.original_attempts = tuple(
        raw if a.run_id == raw.run_id else a for a in value.ledger.original_attempts)
    effective = replace(raw, disposition="valid", reason=reviewer.field.REASON,
                        receipt_sha256="j" * 64)
    value.ledger.attempts = tuple(
        effective if a.run_id == raw.run_id else a for a in value.ledger.attempts)
    value.projection["rows"][107]["attempts"][0].update(
        original_disposition=raw.disposition, original_reason=raw.reason,
        disposition=effective.disposition, reason=effective.reason,
        receipt_sha256=effective.receipt_sha256, original_evaluation={"score": 0.125},
        benchmark_score=0.125, execution_completed=True)
    proof = {"run_id": raw.run_id, "original_admission_sha256": raw.receipt_sha256,
             "original_execution_sha256": raw.execution_sha256,
             "reviewed_admission_sha256": effective.receipt_sha256,
             "field_misuse_proof": [{"action_id": f"typed-failure-{i}"} for i in range(3)]}
    path = value.root / reviewer.DIRECTORY / "run-107.json"
    path.write_text(json.dumps(proof), encoding="utf-8")
    value.control_value["initial_field_sidecars"][path.name] = (
        final.environment.cadence.digest(path))
    value.control.write_text(json.dumps(value.control_value), encoding="utf-8")
    manifest = json.loads(value.manifest.read_text())
    manifest.update(extension_version=final.environment.VERSION, **value.control_value)
    value.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    value.routing_calls.clear()

    def full_control(control, sidecar, derived, filtered, native):
        assert control == value.control and sidecar == Path(manifest["sidecar_path"])
        assert (derived, filtered, native) == (
            value.derived_sidecars, value.filtered_sidecars, value.native_sidecars)
        value.routing_calls.append("renewed-full-control")
        return manifest["parent"], tuple(f"cell-{i}" for i in range(192))

    def membership(control, cells, sidecar, *, require_dispatch_ready):
        assert control == {**value.control_value, "derived_field_sidecars": value.derived_sidecars,
                           "filtered_field_sidecars": value.filtered_sidecars,
                           "native_argument_sidecars": value.native_sidecars}
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
                        lambda *_: pytest.fail("frozen native environment fence route"))
    return value


def create(value):
    return final.create_bundle(value.manifest, "m" * 64,
                               provenance_sha256(value.sources), value.output)


def direct(value):
    return ACTUAL_ADAPTER_PRIVATE(value.manifest, "m" * 64, value.derived_sidecars,
                                  value.filtered_sidecars, value.native_sidecars)


def test_renewed_five_groups_all193_preserve_native_unknowns_initial107_and_globals(prepared):
    projection, control = copy.deepcopy(prepared.projection), copy.deepcopy(prepared.control_value)
    functions = (final.SOURCE_MODULES, final.ENVIRONMENT_VIEW, final.RECONCILE,
                 final.AUDIT_PHASE_TWO, final.CREATE_BUNDLE, ACTUAL_PRIVATE,
                 final.original.reconcile, vars(final.original)["_inventory"])
    namespaces = [dict(function.__globals__) for function in functions]
    result = create(prepared)
    assert result["version"] == final.VERSION
    assert json.loads(prepared.output.read_text()) == result
    rows = result["projection"]["rows"]
    native, initial = rows[105]["attempts"][0], rows[107]["attempts"][0]
    assert native["confirmed_native_argument_failures"] == 1
    assert native["native_argument_sidecar_sha256"] == prepared.native_sidecars["run-105.json"]
    assert native["native_argument_original_admission_sha256"] == "r" * 64
    assert native["native_argument_reviewed_admission_sha256"] == "n" * 64
    for key in ("benchmark_score", "telemetry", "original_evaluation",
                "semantic_primary_cause", "post_inference_failed_service_tokens"):
        assert native[key] is None
    assert native["execution_completed"] is False
    assert native["original_reason"] == final.native.sdk.GATE
    assert initial["confirmed_absent_record_field_failures"] == 3
    assert initial["phase2_field_sidecar_sha256"] == (
        prepared.control_value["initial_field_sidecars"]["run-107.json"])
    assert initial["original_disposition"] == "confounder"
    assert initial["original_receipt_sha256"] == "r" * 64
    assert initial["receipt_sha256"] == "j" * 64
    assert initial["original_rejection_preserved"] is True
    assert initial["execution_completed"] is True
    assert initial["original_evaluation"] == {"score": 0.125}
    assert initial["benchmark_score"] == 0.125
    assert rows[0]["attempts"][0]["confirmed_post_inference_json_failures"] == 2
    assert rows[1]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    assert rows[81]["attempts"][0]["confirmed_absent_derived_record_field_failures"] == 2
    assert rows[84]["attempts"][0]["confirmed_absent_record_field_failures"] == 2
    assert rows[103]["attempts"][0]["confirmed_absent_filtered_record_field_failures"] == 2
    assert rows[71]["attempts"][0]["run_id"] == final.original.environment.RUN
    assert rows[71]["attempts"][0]["disposition"] == "operational_excluded"
    assert sum(len(row["attempts"]) for row in rows) == 193
    assert len(result["recipient_audit"]["records"]) == 193
    assert len(result["private_diagnostics"]["records"]) == 193
    assert prepared.projection == projection and prepared.control_value == control
    assert prepared.routing_calls == ["renewed-fence", "renewed-full-control",
                                      "renewed-membership", "renewed-collect", "renewed-fence"]
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


def test_actual_private_route_renewed_environment_all193_and_unchanged_guard_scanner(
        prepared, monkeypatch):
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
    assert prepared.routing_calls.count("renewed-fence") == 4
    assert prepared.routing_calls.count("renewed-full-control") == 2
    assert prepared.routing_calls.count("renewed-membership") == 2
    assert final.private.previous.private.scan_store is scanner
    assert final.private.previous.private.assert_inactive is ACTUAL_GUARD
    assert final.private.audit_phase_two is ACTUAL_PRIVATE


@pytest.mark.parametrize("entry", ["bundle", "direct"])
def test_live_guard_before_any_source_metadata_or_output(monkeypatch, entry):
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


@pytest.mark.parametrize("change", ["late-row", "initial-proof", "late-effective"])
def test_actual_direct_private_metadata_guard_before_body(prepared, monkeypatch, change):
    monkeypatch.setattr(final.private, "audit_phase_two", ACTUAL_PRIVATE)
    monkeypatch.setattr(final.private.previous, "audit_multihop",
                        lambda *_: pytest.fail("private body before final metadata guard"))
    if change == "late-row":
        prepared.projection["rows"][-1]["pending_run_ids"] = ["late-pending"]
    elif change == "initial-proof":
        prepared.control_value["initial_field_sidecars"].pop("run-107.json")
        prepared.control.write_text(json.dumps(prepared.control_value))
    else:
        prepared.ledger.attempts = tuple(
            replace(a, receipt_sha256="drift") if a.run_id == "run-191" else a
            for a in prepared.ledger.attempts)
    with pytest.raises(RuntimeError):
        direct(prepared)
    assert not prepared.output.exists()


def test_late_live_guard_before_first_private_body(prepared, monkeypatch):
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


@pytest.mark.parametrize("change", ["missing", "hash", "original", "execution", "run",
                                   "empty", "effective-proof", "raw-pair", "effective-pair",
                                   "overlap", "old71", "native-missing", "model-missing",
                                   "derived-missing", "filtered-missing"])
def test_initial107_and_preserved_five_group_pairs_fail_closed(prepared, change):
    path = prepared.root / final.environment.field.review.DIRECTORY / "run-107.json"
    proof = json.loads(path.read_text())
    if change == "missing":
        prepared.control_value["initial_field_sidecars"].pop(path.name)
    elif change == "hash":
        prepared.control_value["initial_field_sidecars"][path.name] = "a" * 64
    elif change == "raw-pair":
        prepared.projection["rows"][107]["attempts"][0]["original_reason"] = "drift"
    elif change == "effective-pair":
        prepared.ledger.attempts = tuple(
            replace(a, receipt_sha256="drift") if a.run_id == "run-107" else a
            for a in prepared.ledger.attempts)
    elif change == "overlap":
        prepared.control_value["initial_field_sidecars"].update(prepared.native_sidecars)
    elif change == "old71":
        prepared.projection["rows"][71]["attempts"].pop(0)
    elif change == "model-missing":
        prepared.control_value["model_json_sidecars"].clear()
    elif change in ("native-missing", "derived-missing", "filtered-missing"):
        getattr(prepared, change.split("-")[0] + "_sidecars").clear()
    else:
        key = {"original": "original_admission_sha256", "execution": "original_execution_sha256",
               "run": "run_id", "empty": "field_misuse_proof",
               "effective-proof": "reviewed_admission_sha256"}[change]
        proof[key] = [] if change == "empty" else "drift"
        path.write_text(json.dumps(proof))
        prepared.control_value["initial_field_sidecars"][path.name] = (
            final.environment.cadence.digest(path))
    prepared.control.write_text(json.dumps(prepared.control_value))
    manifest = json.loads(prepared.manifest.read_text())
    manifest.update(derived_field_sidecars=prepared.derived_sidecars,
                    filtered_field_sidecars=prepared.filtered_sidecars,
                    native_argument_sidecars=prepared.native_sidecars)
    prepared.manifest.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing", "duplicate", "admission", "disposition"])
def test_recipient_context_binding_before_private_scan(prepared, change):
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


@pytest.mark.parametrize("change", ["missing", "duplicate", "manifest", "journal", "semantic"])
def test_missing_all193_diagnostics_and_bound_metadata_fail_closed(prepared, change):
    if change == "missing":
        prepared.diagnostics["records"].pop()
    elif change == "duplicate":
        prepared.diagnostics["records"][-1] = prepared.diagnostics["records"][0]
    else:
        key = {"manifest": "manifest_sha256", "journal": "journal_sha256",
               "semantic": "semantic_audit_complete"}[change]
        prepared.diagnostics[key] = True if change == "semantic" else "drift"
    with pytest.raises(RuntimeError, match="diagnostic"):
        create(prepared)
    assert not prepared.output.exists()


def test_external_source_pin_before_metadata(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"renewed": "drift"})
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata before pin"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)


@pytest.mark.parametrize("change", ["source", "path", "journal", "metadata"])
def test_drift_during_scan_prevents_exclusive_write(prepared, monkeypatch, change):
    paths = final.audit_source_paths()
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


def test_exclusive_output_preserved(prepared):
    create(prepared)
    before = prepared.output.read_bytes()
    with pytest.raises(FileExistsError):
        create(prepared)
    assert prepared.output.read_bytes() == before and prepared.calls == ["private"]


def test_actual_source_closure_retains_every_ancestor_and_actual_paths():
    actual, old = ACTUAL_SOURCES(), final.previous.audit_sources()
    assert all(actual.get(name) == sha for name, sha in old.items())
    paths = final.audit_source_paths()
    for module in (final, final.environment, final.previous, final.native,
                   final.private.previous.private,
                   sys.modules[final.private.previous.private.scan_store.__module__]):
        assert module.__name__ in actual
        assert paths[module.__name__] == str(Path(module.__file__).resolve())
    assert "large_scale_resident_phase2_native_field_review_v1" in actual


def test_actual_installed_environment_namespace_source_pin(prepared, monkeypatch):
    directory = prepared.root / "actual-installed-namespace"
    directory.mkdir()
    source = directory / Path(final.environment.__file__).name
    source.write_bytes(Path(final.environment.__file__).read_bytes())
    monkeypatch.setattr(final.environment, "__file__", str(source))
    monkeypatch.setattr(final, "audit_sources", ACTUAL_SOURCES)
    before = final.audit_sources()
    assert final.audit_source_paths()[final.environment.__name__] == str(source.resolve())
    source.write_bytes(source.read_bytes() + b"\n# synthetic source drift\n")
    monkeypatch.setattr(final.environment, "read", lambda *_: pytest.fail("metadata after drift"))
    with pytest.raises(RuntimeError, match="source drift"):
        final.create_bundle(prepared.manifest, "m" * 64, provenance_sha256(before), prepared.output)


def test_cli_preserves_manifest_and_launch_pins(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(final, "create_bundle", lambda *args: calls.append(args))
    final.main(["--manifest", "renewed.json", "--manifest-sha256", "m" * 64,
                "--audit-source-sha256", "s" * 64, "--output", "bundle.json"])
    assert calls == [(Path("renewed.json"), "m" * 64, "s" * 64, Path("bundle.json"))]
    assert json.loads(capsys.readouterr().out) == {
        "preserved_attempts": 193, "model_calls": 0, "goal_complete": False}
