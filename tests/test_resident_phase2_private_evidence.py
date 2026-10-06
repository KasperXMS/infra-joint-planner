import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
import test_resident_private_evidence as legacy_tests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_phase2_private_evidence_v1")


@pytest.fixture
def multihop_case(tmp_path, monkeypatch):
    return legacy_tests.multihop_fixture.__wrapped__(tmp_path, monkeypatch)


def test_live_guard_precedes_metadata_and_any_body_read(monkeypatch, tmp_path):
    def active(_):
        raise RuntimeError("live held-out controller")

    monkeypatch.setattr(audit.private, "assert_inactive", active)
    monkeypatch.setattr(audit.sources, "collect", lambda *_: pytest.fail("metadata read"))
    with pytest.raises(RuntimeError, match="live held-out"):
        audit.audit_phase_two(tmp_path)
    with pytest.raises(RuntimeError, match="live held-out"):
        audit.audit_multihop(tmp_path, tmp_path / "corpus", tmp_path / "annotation")
    with pytest.raises(RuntimeError, match="live held-out"):
        audit.scan_request("strong-4090", {})


@pytest.mark.parametrize("defect", ["partial", "pending", "confounder", "excluded"])
def test_nonterminal_block_never_reads_bodies(monkeypatch, tmp_path, defect):
    snapshot = {"phase2_complete": True, "pending_count": 0,
                "confounded_attempts": 0, "operational_excluded_attempts": 0}
    snapshot[{"partial": "phase2_complete", "pending": "pending_count",
              "confounder": "confounded_attempts",
              "excluded": "operational_excluded_attempts"}[defect]] = (
        False if defect == "partial" else 1)
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.sources, "collect", lambda *_: snapshot)
    monkeypatch.setattr(audit, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="completed resolved PhaseII"):
        audit.audit_phase_two(tmp_path)


def request(agent="strong-4090", phase="phase2"):
    run_id = f"{audit.ROOT.name}-{phase}-synthetic-attempt1"
    prefix = "/home/super" if agent == "strong-4090" else "/mnt/ssd"
    return {"namespace": audit.ROOT.name, "run_id": run_id, "supports": [], "artifacts": [],
            "store_root": f"{prefix}/heterogeneous-v1/artifacts/{audit.ROOT.name}/{run_id}/{agent}"}


@pytest.mark.parametrize("defect", ["namespace", "run_id", "store_root", "phase1", "owner"])
def test_scanner_exact_heldout_run_owner_and_namespace(monkeypatch, defect):
    calls = []
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.private, "scan_store", lambda r: calls.append(r) or [])
    value = request()
    assert audit.scan_request("strong-4090", value) == []
    value = copy.deepcopy(value)
    if defect == "phase1":
        value = request(phase="phase1")
    elif defect == "owner":
        value["store_root"] = value["store_root"].replace("/strong-4090", "/A28")
    else:
        value[defect] = "unrelated"
    with pytest.raises(RuntimeError, match="exact PhaseII run/owner"):
        audit.scan_request("strong-4090", value)
    assert len(calls) == 1


def test_remote_scan_preserves_owner_local_transport(monkeypatch):
    captured = []
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)

    def run(args, **kwargs):
        captured.append((args, kwargs))
        return type("Response", (), {"stdout": "[]"})()

    monkeypatch.setattr(audit.subprocess, "run", run)
    value = request("A28")
    assert audit.scan_request("A28", value) == []
    args, kwargs = captured[0]
    assert args[-2] == audit.private.HOSTS["A28"]
    assert "--scan-store" in args[-1] and " -S " in args[-1]
    assert json.loads(kwargs["input"]) == value
    assert kwargs["timeout"] == 60 and kwargs["check"]


def test_reused_scan_code_exports_no_gold_body_or_prompt_and_preserves_unknown(
    multihop_case, monkeypatch,
):
    directory, corpus, source_private, calls = multihop_case
    original_scanner = audit.private.scan_request
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit, "scan_request", original_scanner)
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    value = audit.audit_multihop(directory, corpus, source_private)
    assert len(calls) == 1 and value["model_calls"] == 0
    assert value["semantic_evidence_retention"] is None
    assert all(secret not in json.dumps(value) for secret in (
        "PRIVATE GOLD", "PRIVATE FACT", "PRIVATE PROMPT"))
    assert audit.private.scan_request is original_scanner
    assert all(p.read_bytes() == data for p, data in before.items())


def test_original_source_drift_guards_are_not_bypassed(multihop_case, monkeypatch):
    directory, corpus, source_private, calls = multihop_case
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit, "scan_request", audit.private.scan_request)
    source_private.write_text('{"changed":true}')
    with pytest.raises(RuntimeError, match="annotation drift"):
        audit.audit_multihop(directory, corpus, source_private)
    assert not calls


def test_every_worker_exit_verified_before_first_scan(monkeypatch, tmp_path):
    source_hash = "a" * 64
    rows = []
    for index, exited in ((3, True), (4, False)):
        cell = f"phase2-multihop_rag-{index}-synthetic-p1-fast-B0"
        directory = tmp_path / "evidence" / cell / "attempt1"
        directory.mkdir(parents=True)
        (directory / "worker-shutdown.json").write_text(json.dumps({"verified_exited": exited}))
        rows.append({"condition": {"cell_id": cell, "task": {
            "family": "multihop_rag", "position": index}}, "attempts": [{
            "disposition": "valid", "attempt_index": 1, "execution_sha256": source_hash}]})
    value = {"phase2_complete": True, "pending_count": 0, "confounded_attempts": 0,
             "operational_excluded_attempts": 0, "execution_freeze_sha256": source_hash,
             "scheduled_cells": 2, "rows": rows}
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.sources, "collect", lambda *_: value)
    monkeypatch.setattr(audit, "audit_multihop", lambda *_: pytest.fail("body read"))
    with pytest.raises(RuntimeError, match="exited Workers"):
        audit.audit_phase_two(tmp_path)


def test_completed_unannotated_task_keeps_unknown_without_private_scan(monkeypatch, tmp_path):
    journal = tmp_path / "phase2-attempts.jsonl"
    journal.write_text("synthetic frozen membership")
    directory = tmp_path / "evidence/cell/attempt1"
    directory.mkdir(parents=True)
    (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    source = "a" * 64
    value = {
        "phase2_complete": True, "pending_count": 0, "confounded_attempts": 0,
        "operational_excluded_attempts": 0, "execution_freeze_sha256": source,
        "journal_sha256": audit.private.sha256(journal),
        "control_file_sha256": "b" * 64, "scheduled_cells": 1,
        "rows": [{"condition": {"cell_id": "cell", "task": {
            "family": "longbench_v2", "position": 3}}, "attempts": [{
                "disposition": "valid", "attempt_index": 1, "run_id": "run",
                "execution_sha256": source, "benchmark_score": None}]}],
    }
    monkeypatch.setattr(audit.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(audit.sources, "collect", lambda *_: value)
    monkeypatch.setattr(audit, "audit_multihop", lambda *_: pytest.fail("unannotated scan"))
    result = audit.audit_phase_two(tmp_path)
    row = result["records"][0]
    assert row["coverage"] is None and row["benchmark_score"] is None
    assert row["semantic_primary_cause"] is None and row["unannotated_retention"] is None
    assert not result["semantic_audit_complete"]
    assert result["planner_or_model_calls"] == 0 and not result["artifact_bodies_exported"]
