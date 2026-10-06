import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_cardinality_private_evidence import prepare_completed_stores

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_resident_E_query_private_evidence_v1")


def complete_snapshot() -> dict:
    return {
        "scheduled_cells": 168, "admitted_cells": 168, "pending_count": 0,
        "phase1_complete": True,
        "execution_freezes": {str(k): v for k, v in audit.sources.EXECUTIONS.items()},
        "collector_source_sha256": {},
        "rows": [{
            "condition": {"cell_id": f"cell-{i}", "task": {
                "family": "longbench_v2", "position": 1}},
            "pending_run_ids": [], "attempts": [{
                "disposition": "valid", "attempt_index": 1, "run_id": f"run-{i}",
                "comparative_sample_eligible": True, "admission_problems": [],
                "execution_sha256": audit.sources.EXECUTIONS[i % 4 + 1],
                "execution_source_epoch": i % 4 + 1, "benchmark_score": None,
            }],
        } for i in range(168)],
    }


def test_all_four_sources_and_excluded_E_original_are_preserved_without_mutation() -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][3]
    row["attempts"].insert(0, dict(row["attempts"][0], run_id="old-E-confounder",
                                  disposition="confounder", comparative_sample_eligible=False,
                                  execution_source_epoch=3,
                                  execution_sha256=audit.sources.EXECUTIONS[3]))
    row["attempts"][1]["attempt_index"] = 2
    before = copy.deepcopy(snapshot)
    selected = audit.source_bound_membership(snapshot)
    assert len(selected) == 168 and selected[3][1]["execution_source_epoch"] == 4
    assert snapshot == before


@pytest.mark.parametrize("defect", ["partial", "pending", "missing_four", "bad_four_hash",
                                     "epoch_source", "string_epoch", "boolean_epoch",
                                     "old_boundary", "two_valid", "excluded_source_drift"])
def test_incomplete_or_epoch_ambiguous_membership_is_rejected(defect: str) -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][3]
    attempt = row["attempts"][0]
    if defect == "partial":
        snapshot["admitted_cells"] = 112
    elif defect == "pending":
        snapshot["pending_count"] = 1
    elif defect == "missing_four":
        del snapshot["execution_freezes"]["4"]
    elif defect == "bad_four_hash":
        snapshot["execution_freezes"]["4"] = "f" * 64
    elif defect == "epoch_source":
        attempt["execution_source_epoch"] = 3
    elif defect == "string_epoch":
        attempt["execution_source_epoch"] = "4"
    elif defect == "boolean_epoch":
        attempt["execution_source_epoch"] = True
    elif defect == "old_boundary":
        del attempt["execution_source_epoch"]
        attempt["execution_source_boundary"] = "input-cardinality-repair-003"
    elif defect == "two_valid":
        row["attempts"].append(dict(attempt, run_id="another-valid"))
    else:
        row["attempts"].insert(0, dict(attempt, run_id="old-confounder",
                                      disposition="confounder", comparative_sample_eligible=False,
                                      execution_source_epoch=3))
    with pytest.raises(RuntimeError, match="private audit"):
        audit.source_bound_membership(snapshot)


def test_live_queue_blocks_before_collecting_metadata_or_reading_bodies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def active(root):
        raise RuntimeError("queue live")

    monkeypatch.setattr(audit.private, "assert_inactive", active)
    monkeypatch.setattr(audit.sources, "collect", lambda *args: pytest.fail("live metadata read"))
    with pytest.raises(RuntimeError, match="queue live"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_partial_four_source_block_never_reads_benchmark_bodies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    snapshot["admitted_cells"] = 112
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("partial block body read"))
    with pytest.raises(RuntimeError, match="completed resolved168"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_late_worker_exit_is_checked_before_any_private_body_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    snapshot["rows"][0]["condition"]["task"]["family"] = "multihop_rag"
    prepare_completed_stores(tmp_path, snapshot)
    (tmp_path / "evidence/cell-167/attempt1/worker-shutdown.json").write_text(
        '{"verified_exited":false}')
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: pytest.fail("premature corpus read"))
    with pytest.raises(RuntimeError, match="every effective Worker exited"):
        audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "unused")


def test_only_effective_E_repair_is_scanned_and_missing_evaluation_remains_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = complete_snapshot()
    row = snapshot["rows"][3]
    row["condition"]["task"]["family"] = "multihop_rag"
    row["attempts"].insert(0, dict(row["attempts"][0], run_id="old-E-confounder",
                                  disposition="confounder", comparative_sample_eligible=False,
                                  execution_source_epoch=3,
                                  execution_sha256=audit.sources.EXECUTIONS[3]))
    row["attempts"][1]["attempt_index"] = 2
    prepare_completed_stores(tmp_path, snapshot)
    calls = []
    monkeypatch.setattr(audit.sources, "collect", lambda *args: snapshot)
    monkeypatch.setattr(audit.private, "audit_multihop",
                        lambda *args: calls.append(args) or {"semantic_evidence_retention": None})
    value = audit.audit_phase_one(tmp_path, tmp_path, tmp_path / "corpus")
    assert len(calls) == 1 and calls[0][0] == tmp_path / "evidence/cell-3/attempt2"
    assert value["version"] == audit.VERSION
    assert value["records"][3]["execution_source_epoch"] == 4
    assert value["excluded_historical_run_ids"] == ["old-E-confounder"]
    assert value["planner_or_model_calls"] == 0 and not value["artifact_bodies_exported"]
    assert not value["semantic_audit_complete"] and not value["phase2_authorized"]
    assert all(r["benchmark_score"] is None for r in value["records"])


@pytest.mark.parametrize("defect", ["restart", "journal_changed"])
def test_four_source_audit_rechecks_queue_and_membership(
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
