import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
final = importlib.import_module("large_scale_resident_phase2_final_audit_v1")
env = final.environment
ACTUAL_AUDIT_SOURCES = final.audit_sources


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(env.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(env.frozen, "require_remote", lambda: None)
    (tmp_path / "analysis").mkdir()
    manifest, control = tmp_path / "manifest.json", tmp_path / "control.json"
    journal = tmp_path / "phase2-attempts.jsonl"
    journal.write_text("preserved journal", encoding="utf-8")
    execution, receipt, reviewed_sha = "e" * 64, "r" * 64, "v" * 64
    raw, rows = [], []
    cells = [f"cell-{i}" for i in range(192)]
    cells[71] = env.CELL
    model_run, field_run = "run-0", "run-1"
    proofs = {}
    for i, cell in enumerate(cells):
        run = f"run-{i}"
        original = "confounder" if i in (0, 1) else "valid"
        raw.append(Attempt(cell, run, 1, execution, original, "reason", receipt))
        record = {"run_id": run, "attempt_index": 1, "execution_sha256": execution,
                  "disposition": "valid", "original_disposition": original,
                  "receipt_sha256": reviewed_sha if original == "confounder" else receipt,
                  "original_receipt_sha256": receipt, "benchmark_score": None if i == 0 else 0,
                  "confirmed_post_inference_json_failures": 0,
                  "post_inference_failed_service_tokens": 0,
                  "confirmed_absent_record_field_failures": 0,
                  "semantic_primary_cause": None, "telemetry": None,
                  "original_rejection_preserved": False}
        if i == 71:
            record["attempt_index"] = 2
            raw[-1] = Attempt(cell, run, 2, execution, "valid", "reason", receipt)
        attempts = [record]
        if i == 71:
            raw.append(Attempt(cell, env.RUN, 1, execution, "confounder", "reason", env.RAW_SHA))
            excluded = copy.deepcopy(record)
            excluded.update(run_id=env.RUN, attempt_index=1, disposition="operational_excluded",
                            original_disposition="confounder", original_receipt_sha256=env.RAW_SHA)
            attempts.insert(0, excluded)
        rows.append({"condition": {"cell_id": cell}, "attempts": attempts, "pending_run_ids": []})
        for attempt in attempts:
            directory = tmp_path / "evidence" / cell / ("attempt" + str(attempt["attempt_index"]))
            directory.mkdir(parents=True)
            (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
        if i in (0, 1):
            proofs[run] = {"run_id": run, "original_admission_sha256": receipt,
                           "original_execution_sha256": execution,
                           "reviewed_admission_sha256": reviewed_sha,
                           "proof" if i == 0 else "field_misuse_proof": [
                               {"action": 1}, {"action": 2}]}
    sidecar_maps = []
    for reviewer, run in ((env.field.core, model_run), (env.field.review, field_run)):
        directory = tmp_path / reviewer.DIRECTORY
        directory.mkdir()
        path = directory / (run + ".json")
        path.write_text(json.dumps(proofs[run]), encoding="utf-8")
        sidecar_maps.append({path.name: env.cadence.digest(path)})
        monkeypatch.setattr(reviewer, "verify_sidecar",
                            lambda path, _: json.loads(path.read_text()))
    control_value = {"model_json_sidecars": sidecar_maps[0],
                     "initial_field_sidecars": sidecar_maps[1]}
    control.write_text(json.dumps(control_value), encoding="utf-8")
    value = {"control_path": str(control), "sidecar_path": str(tmp_path / "exclusion.json"),
             "parent": {"execution_freeze_sha256": execution}}
    manifest.write_text(json.dumps(value), encoding="utf-8")
    projection = {"rows": rows, "scheduled_cells": 192, "admitted_cells": 192,
                  "attempt_count": 193, "phase2_complete": True, "pending_count": 0,
                  "confounded_attempts": 0, "operational_excluded_attempts": 1,
                  "execution_freeze_sha256": execution,
                  "journal_sha256": env.cadence.digest(journal)}
    ledger = SimpleNamespace(original_attempts=tuple(raw), path=journal)
    monkeypatch.setattr(env, "fence", lambda *_: None)
    monkeypatch.setattr(env, "full_control", lambda *_: (value["parent"], tuple(cells)))
    monkeypatch.setattr(env, "membership", lambda *_args, **_kwargs: ledger)
    monkeypatch.setattr(env, "collect", lambda *_: projection)
    monkeypatch.setattr(final.private.previous.private, "assert_inactive", lambda *_: None)
    sources = {"wrapper.py": "a" * 64, "original.py": "b" * 64}
    monkeypatch.setattr(final, "audit_sources", lambda: sources.copy())
    calls = []
    recipients = {"records": [{"run_id": a["run_id"], "effective_disposition": a["disposition"],
                               "original_admission_sha256": a["original_receipt_sha256"],
                               "request_file_sha256": {"request": "q" * 64},
                               "actual_recipient_counts": {"manager": 1, "verifier": 1}}
                              for row in rows for a in row["attempts"]]}
    diagnostics = {"records": [{"run_id": a["run_id"], "coverage": None,
                                "semantic_primary_cause": None}
                               for row in rows for a in row["attempts"]],
                   "journal_sha256": projection["journal_sha256"],
                   "manifest_sha256": "m" * 64, "semantic_audit_complete": False}
    monkeypatch.setattr(env, "audit_wire", lambda *_: recipients)

    def synthetic_private(*_):
        calls.append("private")
        return diagnostics

    monkeypatch.setattr(final.private, "audit_phase_two", synthetic_private)
    return SimpleNamespace(manifest=manifest, control=control, control_value=control_value,
                           projection=projection, ledger=ledger, sources=sources, calls=calls,
                           recipients=recipients, diagnostics=diagnostics, root=tmp_path,
                           output=tmp_path / "analysis/bundle.json")


def create(prepared):
    return final.create_bundle(prepared.manifest, "m" * 64,
                               provenance_sha256(prepared.sources), prepared.output)


def test_synthetic193_success_preserves_originals_unknowns_and_bound_components(prepared):
    original = copy.deepcopy(prepared.projection)
    result = create(prepared)
    assert json.loads(prepared.output.read_text()) == result
    assert prepared.projection == original
    assert len(result["recipient_audit"]["records"]) == 193
    rows = result["projection"]["rows"]
    model, field = rows[0]["attempts"][0], rows[1]["attempts"][0]
    assert model["confirmed_post_inference_json_failures"] == 2
    assert model["post_inference_failed_service_tokens"] is None
    assert field["confirmed_absent_record_field_failures"] == 2
    assert model["original_rejection_preserved"] and field["original_rejection_preserved"]
    assert model["benchmark_score"] is None and model["telemetry"] is None
    assert rows[71]["attempts"][0]["run_id"] == env.RUN
    for key in ("projection", "recipient_audit", "private_diagnostics"):
        assert result["component_sha256"][key] == provenance_sha256(result[key])
    for key in ("semantic_audit_complete", "manual_audit_complete", "q1_q10_complete",
                "goal_complete"):
        assert result[key] is False
    assert prepared.calls == ["private"]


def test_global_live_guard_precedes_source_control_and_output_access(monkeypatch):
    def reject(*_):
        raise RuntimeError("live controller")

    monkeypatch.setattr(final.private.previous.private, "assert_inactive", reject)
    monkeypatch.setattr(final, "audit_sources", lambda: pytest.fail("source read while live"))
    with pytest.raises(RuntimeError, match="live controller"):
        final.create_bundle(Path("absent"), "x", "x", Path("absent-output"))


@pytest.mark.parametrize("field,value", [
    ("phase2_complete", False), ("pending_count", 1), ("confounded_attempts", 1),
    ("attempt_count", 192), ("admitted_cells", 191), ("operational_excluded_attempts", 0)])
def test_partial_pending_or_inventory_counter_rejects_before_scan(prepared, field, value):
    prepared.projection[field] = value
    with pytest.raises(RuntimeError, match="all192"):
        create(prepared)
    assert not prepared.calls and not prepared.output.exists()


@pytest.mark.parametrize("change", ["extra-invalid", "excluded-missing", "excluded-wrong-run",
                                   "pending-row", "duplicate-cell", "worker-live"])
def test_inventory_and_exits_reject_before_scan(prepared, change):
    rows = prepared.projection["rows"]
    if change == "extra-invalid":
        rows[3]["attempts"][0]["disposition"] = "confounder"
    elif change == "excluded-missing":
        rows[71]["attempts"].pop(0)
    elif change == "excluded-wrong-run":
        rows[71]["attempts"][0]["run_id"] = "different-excluded"
    elif change == "pending-row":
        rows[3]["pending_run_ids"] = ["pending"]
    elif change == "duplicate-cell":
        rows[3]["condition"]["cell_id"] = rows[2]["condition"]["cell_id"]
    else:
        path = prepared.root / "evidence/cell-3/attempt1/worker-shutdown.json"
        path.write_text('{"verified_exited":false}')
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls


@pytest.mark.parametrize("change", ["namespace", "hash", "run", "original", "proof"])
def test_exact_sidecar_bindings_reject_before_scan(prepared, change):
    control = copy.deepcopy(prepared.control_value)
    path = prepared.root / env.field.core.DIRECTORY / "run-0.json"
    if change == "namespace":
        control["model_json_sidecars"] = {"../run-0.json": "a" * 64}
    elif change == "hash":
        control["model_json_sidecars"]["run-0.json"] = "a" * 64
    else:
        proof = json.loads(path.read_text())
        key = {"run": "run_id", "original": "original_admission_sha256", "proof": "proof"}[change]
        proof[key] = [] if change == "proof" else "drift"
        path.write_text(json.dumps(proof))
        control["model_json_sidecars"]["run-0.json"] = env.cadence.digest(path)
    prepared.control.write_text(json.dumps(control))
    with pytest.raises(RuntimeError):
        create(prepared)
    assert not prepared.calls


def test_source_pin_rejects_before_evidence_reads(prepared, monkeypatch):
    monkeypatch.setattr(final, "audit_sources", lambda: {"wrapper.py": "changed"})
    monkeypatch.setattr(env, "read",
                        lambda *_: pytest.fail("control read before source verification"))
    with pytest.raises(RuntimeError, match="source drift"):
        create(prepared)


def test_wrapper_source_drift_during_scan_prevents_persistence(prepared, monkeypatch):
    def scan(*_):
        prepared.sources["wrapper.py"] = "changed"
        return prepared.diagnostics

    monkeypatch.setattr(final.private, "audit_phase_two", scan)
    with pytest.raises(RuntimeError, match="source/journal changed"):
        create(prepared)
    assert not prepared.output.exists()


@pytest.mark.parametrize("change", ["missing", "duplicate", "admission", "disposition"])
def test_recipient_inventory_binding_rejects_before_private_scan(prepared, change):
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
    assert not prepared.calls


@pytest.mark.parametrize("change", ["outside", "existing"])
def test_output_owned_exclusive_rejects_before_sources_or_scans(prepared, monkeypatch, change):
    if change == "outside":
        prepared.output = prepared.root / "outside.json"
    else:
        prepared.output.write_text("preserved")
    monkeypatch.setattr(final, "audit_sources",
                        lambda: pytest.fail("source read for rejected output"))
    with pytest.raises((RuntimeError, FileExistsError)):
        create(prepared)
    assert not prepared.calls
    if change == "existing":
        assert prepared.output.read_text() == "preserved"


def test_actual_source_inventory_includes_adapter_guard_and_native_scanner():
    sources = final.audit_sources()
    assert "large_scale_resident_phase2_final_audit_v1" in sources
    assert "large_scale_resident_phase2_private_evidence_v1" in sources
    assert "large_scale_resident_private_evidence_v1" in sources
    assert "cost_guidance_private_multihop_audit_v1" in sources
    assert "infra_joint.control.provenance" in sources


def test_scanner_sources_in_separate_namespaces_are_bound_and_drift_rejects(
        prepared, monkeypatch):
    modules = [final.private.previous, final.private.previous.private,
               sys.modules[final.private.previous.private.scan_store.__module__]]
    for index, module in enumerate(modules):
        directory = prepared.root / f"archived-namespace-{index}" / "scripts"
        directory.mkdir(parents=True)
        path = directory / Path(module.__file__).name
        path.write_bytes(Path(module.__file__).read_bytes())
        monkeypatch.setattr(module, "__file__", str(path))
    monkeypatch.setattr(final, "audit_sources", ACTUAL_AUDIT_SOURCES)
    before = final.audit_sources()
    paths = final.audit_source_paths()
    for module in modules:
        assert module.__name__ in before
        assert paths[module.__name__] == str(Path(module.__file__).resolve())
    wrapper = Path(final.private.previous.__file__)
    wrapper.write_bytes(wrapper.read_bytes() + b"\n# synthetic source drift\n")
    monkeypatch.setattr(env, "read", lambda *_: pytest.fail("evidence read after wrapper drift"))
    with pytest.raises(RuntimeError, match="source drift"):
        final.create_bundle(prepared.manifest, "m" * 64, provenance_sha256(before), prepared.output)
    assert not prepared.calls
