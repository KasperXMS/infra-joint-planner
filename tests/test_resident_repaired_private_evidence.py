import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_repaired_private_evidence_v1")


def complete_snapshot() -> dict:
    return {
        "scheduled_cells": 168, "admitted_cells": 168, "pending_count": 0,
        "phase1_complete": True, "confounded_attempts": 2,
        "execution_freezes": {"1": "original", "2": "repair"},
        "collector_source_sha256": {},
        "rows": [{
            "condition": {"cell_id": f"cell-{i}", "task": {
                "family": "longbench_v2", "position": 1}},
            "pending_run_ids": [], "attempts": [{
                "disposition": "valid", "attempt_index": 1, "run_id": f"run-{i}",
                "comparative_sample_eligible": True, "admission_problems": [],
                "execution_sha256": "original", "execution_source_boundary": "original",
                "benchmark_score": None,
            }],
        } for i in range(168)],
    }


def test_repaired_private_membership_keeps_history_but_selects_effective_attempt():
    snapshot = complete_snapshot()
    row = snapshot["rows"][0]
    old = dict(row["attempts"][0], disposition="confounder", comparative_sample_eligible=False)
    row["attempts"].insert(0, old)
    row["attempts"][1].update(run_id="repaired-run", attempt_index=2,
                              execution_sha256="repair", execution_source_boundary="repair")
    before = copy.deepcopy(snapshot)
    selected = audit.resolved_membership(snapshot)
    assert len(selected) == 168
    assert selected[0][1]["run_id"] == "repaired-run"
    assert snapshot == before


@pytest.mark.parametrize("defect", [
    "partial", "pending", "missing_row", "duplicate_cell", "duplicate_run",
    "no_valid", "two_valid", "unknown_disposition", "ineligible", "problem", "row_pending",
])
def test_repaired_private_membership_rejects_unresolved_or_ambiguous_population(defect):
    snapshot = complete_snapshot()
    row = snapshot["rows"][0]
    if defect == "partial":
        snapshot["admitted_cells"] = 167
    elif defect == "pending":
        snapshot["pending_count"] = 1
    elif defect == "missing_row":
        snapshot["rows"].pop()
    elif defect == "duplicate_cell":
        snapshot["rows"][1]["condition"]["cell_id"] = row["condition"]["cell_id"]
    elif defect == "duplicate_run":
        snapshot["rows"][1]["attempts"][0]["run_id"] = row["attempts"][0]["run_id"]
    elif defect == "no_valid":
        row["attempts"][0]["disposition"] = "confounder"
    elif defect == "two_valid":
        row["attempts"].append(dict(row["attempts"][0], run_id="another-valid-run"))
    elif defect == "unknown_disposition":
        row["attempts"].append(dict(row["attempts"][0], disposition="unknown"))
    elif defect == "ineligible":
        row["attempts"][0]["comparative_sample_eligible"] = False
    elif defect == "problem":
        row["attempts"][0]["admission_problems"] = ["unresolved"]
    else:
        row["pending_run_ids"] = ["pending"]
    with pytest.raises(RuntimeError, match="private audit"):
        audit.resolved_membership(snapshot)


def test_repaired_private_audit_cannot_scan_partial_block(tmp_path, monkeypatch):
    snapshot = complete_snapshot()
    snapshot["admitted_cells"] = 85
    monkeypatch.setattr(audit.repaired, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("partial block must not read bodies"))
    with pytest.raises(RuntimeError, match="completed resolved168"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_repaired_private_audit_preserves_unknown_quality_and_excluded_history(
    tmp_path, monkeypatch,
):
    snapshot = complete_snapshot()
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("frozen-journal")
    snapshot["journal_sha256"] = audit.private.sha256(journal)
    row = snapshot["rows"][0]
    row["attempts"].insert(0, dict(row["attempts"][0], disposition="confounder",
                                  comparative_sample_eligible=False, run_id="excluded-old"))
    for item in snapshot["rows"]:
        directory = tmp_path / "evidence" / item["condition"]["cell_id"] / "attempt1"
        directory.mkdir(parents=True)
        (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    monkeypatch.setattr(audit.repaired, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("unannotated body scan"))
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")
    assert len(value["records"]) == 168
    assert value["excluded_historical_run_ids"] == ["excluded-old"]
    assert value["execution_freezes"] == {"1": "original", "2": "repair"}
    assert all(r["benchmark_score"] is None and r["coverage"] is None for r in value["records"])
    assert not value["semantic_audit_complete"] and not value["phase2_authorized"]
    assert value["planner_or_model_calls"] == 0
    assert "excluded-old" not in json.dumps(value["records"])


def test_private_body_scans_only_effective_repaired_attempt_not_confounded_original(
    tmp_path, monkeypatch,
):
    snapshot = complete_snapshot()
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("frozen-journal")
    snapshot["journal_sha256"] = audit.private.sha256(journal)
    row = snapshot["rows"][0]
    row["condition"]["task"]["family"] = "multihop_rag"
    row["attempts"].insert(0, dict(row["attempts"][0], disposition="confounder",
                                  comparative_sample_eligible=False, run_id="excluded-old"))
    row["attempts"][1].update(attempt_index=2, run_id="repair", execution_sha256="repair",
                              execution_source_boundary="repair")
    for item in snapshot["rows"]:
        index = next(a["attempt_index"] for a in item["attempts"] if a["disposition"] == "valid")
        directory = tmp_path / "evidence" / item["condition"]["cell_id"] / f"attempt{index}"
        directory.mkdir(parents=True)
        (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')
    old = tmp_path / "evidence/cell-0/attempt1"
    old.mkdir()
    (old / "worker-shutdown.json").write_text('{"verified_exited":false}')
    calls = []
    monkeypatch.setattr(audit.repaired, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: calls.append(args) or {"semantic_evidence_retention": None})
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "corpus")
    assert len(calls) == 1
    assert calls[0] == (tmp_path / "evidence/cell-0/attempt2", tmp_path / "corpus",
                        tmp_path / "preparation/task-freeze-002/multihop_rag-1/"
                        "private-evaluation.json")
    assert value["records"][0]["run_id"] == "repair"
    assert value["records"][0]["execution_sha256"] == "repair"
    assert value["excluded_historical_run_ids"] == ["excluded-old"]


@pytest.mark.parametrize("defect", ["worker_live", "restart", "journal_changed"])
def test_repaired_private_audit_rechecks_exit_inactivity_and_membership(
    tmp_path, monkeypatch, defect,
):
    snapshot = complete_snapshot()
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("frozen-journal")
    snapshot["journal_sha256"] = audit.private.sha256(journal)
    for item in snapshot["rows"]:
        directory = tmp_path / "evidence" / item["condition"]["cell_id"] / "attempt1"
        directory.mkdir(parents=True)
        (directory / "worker-shutdown.json").write_text(json.dumps({
            "verified_exited": defect != "worker_live"}))
    calls = []

    def inactive(*args):
        calls.append(args)
        if defect == "restart" and len(calls) == 2:
            raise RuntimeError("inactive queue and atomic required")
        if defect == "journal_changed" and len(calls) == 2:
            journal.write_text("changed-journal")

    monkeypatch.setattr(audit.repaired, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "assert_inactive", inactive)
    with pytest.raises(RuntimeError, match="Worker exits|inactive queue|membership changed"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")
