import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_cardinality_private_evidence_v1")


def complete_snapshot() -> dict:
    freezes = {"1": audit.sources.resident.EXECUTION_FREEZE_SHA256,
               "2": audit.sources.REPAIR_SHA256, "3": "f" * 64}
    boundaries = list(audit.BOUNDARIES)
    return {
        "scheduled_cells": 168, "admitted_cells": 168, "pending_count": 0,
        "phase1_complete": True, "execution_freezes": freezes,
        "collector_source_sha256": {},
        "rows": [{
            "condition": {"cell_id": f"cell-{i}", "task": {
                "family": "longbench_v2", "position": 1}},
            "pending_run_ids": [], "attempts": [{
                "disposition": "valid", "attempt_index": 1, "run_id": f"run-{i}",
                "comparative_sample_eligible": True, "admission_problems": [],
                "execution_sha256": freezes[str(i % 3 + 1)],
                "execution_source_boundary": boundaries[i % 3], "benchmark_score": None,
            }],
        } for i in range(168)],
    }


def test_three_source_private_membership_preserves_old_confounded_original() -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][2]
    row["attempts"].insert(0, dict(row["attempts"][0], run_id="confounded-old",
                                  disposition="confounder", comparative_sample_eligible=False,
                                  execution_sha256=audit.sources.REPAIR_SHA256,
                                  execution_source_boundary="quote-integrity-repair-002"))
    row["attempts"][1]["attempt_index"] = 2
    before = copy.deepcopy(snapshot)
    selected = audit.source_bound_membership(snapshot)
    assert len(selected) == 168
    assert selected[2][1]["execution_source_boundary"] == "input-cardinality-repair-003"
    assert snapshot == before


@pytest.mark.parametrize("defect", ["partial", "pending", "duplicate_cell", "two_valid",
                                     "source", "boundary", "freeze", "missing_epoch",
                                     "reused_epoch", "historical_drift"])
def test_private_membership_rejects_partial_or_source_ambiguous_population(defect: str) -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][0]
    if defect == "partial":
        snapshot["admitted_cells"] = 167
    elif defect == "pending":
        snapshot["pending_count"] = 1
    elif defect == "duplicate_cell":
        snapshot["rows"][1]["condition"]["cell_id"] = row["condition"]["cell_id"]
    elif defect == "two_valid":
        row["attempts"].append(dict(row["attempts"][0], run_id="another-valid"))
    elif defect == "source":
        row["attempts"][0]["execution_sha256"] = "e" * 64
    elif defect == "boundary":
        row["attempts"][0]["execution_source_boundary"] = "unreviewed"
    elif defect == "freeze":
        snapshot["execution_freezes"]["3"] = "not-a-digest"
    elif defect == "missing_epoch":
        del snapshot["execution_freezes"]["3"]
    elif defect == "reused_epoch":
        snapshot["execution_freezes"]["3"] = snapshot["execution_freezes"]["2"]
    else:
        snapshot["execution_freezes"]["1"] = "e" * 64
    with pytest.raises(RuntimeError, match="private audit"):
        audit.source_bound_membership(snapshot)


def prepare_completed_stores(tmp_path: Path, snapshot: dict) -> None:
    journal = tmp_path / "phase1-attempts.jsonl"
    journal.write_text("immutable", encoding="utf-8")
    snapshot["journal_sha256"] = audit.private.sha256(journal)
    for row in snapshot["rows"]:
        valid = next(a for a in row["attempts"] if a["disposition"] == "valid")
        directory = tmp_path / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(valid["attempt_index"]))
        directory.mkdir(parents=True)
        (directory / "worker-shutdown.json").write_text('{"verified_exited":true}')


def test_partial_three_source_block_never_reads_corpus_or_store_bodies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    snapshot["admitted_cells"] = 110
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("partial block body read"))
    with pytest.raises(RuntimeError, match="completed resolved168"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_any_late_worker_still_live_blocks_all_earlier_body_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    snapshot["rows"][0]["condition"]["task"]["family"] = "multihop_rag"
    prepare_completed_stores(tmp_path, snapshot)
    late = tmp_path / "evidence/cell-167/attempt1/worker-shutdown.json"
    late.write_text('{"verified_exited":false}')
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("body read before all exits verified"))
    with pytest.raises(RuntimeError, match="every effective Worker exited"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_three_source_body_scan_selects_only_repaired_effective_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][2]
    row["condition"]["task"]["family"] = "multihop_rag"
    row["attempts"].insert(0, dict(row["attempts"][0], run_id="excluded-original",
                                  disposition="confounder", comparative_sample_eligible=False,
                                  execution_source_boundary="quote-integrity-repair-002",
                                  execution_sha256=audit.sources.REPAIR_SHA256))
    row["attempts"][1]["attempt_index"] = 2
    prepare_completed_stores(tmp_path, snapshot)
    calls = []
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: calls.append(args) or {"semantic_evidence_retention": None})
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "corpus")
    assert len(calls) == 1 and calls[0][0] == tmp_path / "evidence/cell-2/attempt2"
    assert value["excluded_historical_run_ids"] == ["excluded-original"]
    assert value["execution_freezes"] == snapshot["execution_freezes"]
    assert not value["semantic_audit_complete"] and not value["phase2_authorized"]
    assert value["planner_or_model_calls"] == 0 and not value["artifact_bodies_exported"]
    assert all(r["benchmark_score"] is None for r in value["records"])


@pytest.mark.parametrize("defect", ["restart", "journal_changed"])
def test_private_audit_rechecks_runtime_and_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str,
) -> None:
    snapshot = complete_snapshot()
    prepare_completed_stores(tmp_path, snapshot)
    calls = []

    def inactive(*args):
        calls.append(args)
        if len(calls) == 2:
            if defect == "restart":
                raise RuntimeError("queue restarted")
            (tmp_path / "phase1-attempts.jsonl").write_text(json.dumps({"changed": True}))

    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "assert_inactive", inactive)
    with pytest.raises(RuntimeError, match="queue restarted|membership changed"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")
