import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from infra_joint.control.provenance import provenance_sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
collector = importlib.import_module("large_scale_resident_snapshot_v1")
base = collector.base


@pytest.fixture
def projection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    root, old = tmp_path / "new", tmp_path / "old"
    selection = old / "preparation/task-freeze-002"
    selection.mkdir(parents=True)
    root.mkdir()
    (selection / "manifest.json").write_text(json.dumps({"phase1_schedule_sha256": "schedule"}))
    (old / "phase1-attempts.jsonl").write_text("old immutable journal\n")
    (root / "phase1-attempts.jsonl").write_text("new immutable journal\n")
    task_hash = collector.sha256(selection / "manifest.json")
    old_hash = collector.sha256(old / "phase1-attempts.jsonl")
    freeze = {"task_selection_sha256": task_hash, "old_journal_sha256": old_hash,
              "phase1_schedule_sha256": "schedule"}
    (root / "execution-freeze-001.json").write_text(json.dumps(freeze))
    monkeypatch.setattr(collector, "TASK_FREEZE_SHA256", task_hash)
    monkeypatch.setattr(collector, "OLD_JOURNAL_SHA256", old_hash)
    monkeypatch.setattr(collector, "EXECUTION_FREEZE_SHA256", provenance_sha256(freeze))
    value = {"scheduled_cells": 168, "rows": [], "method_pruning_authorized": False,
             "score_aggregation": "not performed", "phase1_complete": True}

    def checked_snapshot(path: Path, *, selection_root: Path) -> dict:
        assert path == root and selection_root == selection
        return value

    monkeypatch.setattr(base, "snapshot", checked_snapshot)
    return root, old, value, freeze


def test_resident_projection_does_not_pool_or_authorize_pruning(projection: tuple) -> None:
    root, old, _, _ = projection
    before = {p: p.read_bytes() for folder in (root, old) for p in folder.rglob("*") if p.is_file()}
    result = collector.collect(root, old)
    assert result["phase1_complete"]
    assert not result["old_and_new_results_pooled"]
    assert result["predecessor_admissions_kept_separate"] == 42
    assert not result["method_pruning_authorized"] and not result["phase2_authorized"]
    assert not result["all_nominal_private_evidence_audited"]
    assert result["score_aggregation"] == "not performed"
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize("target", ["task", "old_journal", "execution", "missing_journal"])
def test_resident_projection_rejects_drift_without_modifying_ledger(
    projection: tuple, target: str,
) -> None:
    root, old, _, _ = projection
    if target == "task":
        path = old / "preparation/task-freeze-002/manifest.json"
    elif target == "old_journal":
        path = old / "phase1-attempts.jsonl"
    elif target == "execution":
        path = root / "execution-freeze-001.json"
    else:
        path = root / "phase1-attempts.jsonl"
        path.unlink()
    if target != "missing_journal":
        path.write_text('{"changed":true}')
    with pytest.raises(RuntimeError):
        collector.collect(root, old)
    if target == "missing_journal":
        assert not path.exists()


def test_resident_projection_rejects_journal_advance(projection: tuple, monkeypatch) -> None:
    root, old, value, _ = projection

    def advanced_snapshot(path: Path, *, selection_root: Path) -> dict:
        (path / "phase1-attempts.jsonl").write_text("advanced by queue\n")
        return value

    monkeypatch.setattr(base, "snapshot", advanced_snapshot)
    with pytest.raises(RuntimeError, match="journal advanced"):
        collector.collect(root, old)
    assert (root / "phase1-attempts.jsonl").read_text() == "advanced by queue\n"


def test_resident_projection_bounded_exports_and_unknowns(projection: tuple, monkeypatch) -> None:
    root, old, value, freeze = projection
    attempt = {"execution_sha256": provenance_sha256(freeze), "attempt_index": 1,
               "run_id": "run", "benchmark_score": None}
    value["rows"] = [{"condition": {"cell_id": "cell"}, "attempts": [attempt]}]
    directory = root / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    private_text = "PRIVATE_PROMPT\u2028PRIVATE_QUERY\u0085PRIVATE_GOLD"
    (run / "trace.jsonl").write_text(json.dumps({"event_type": "diagnostic", "payload": {
        "text": private_text}}, ensure_ascii=False) + "\n", encoding="utf-8")
    (directory / "admission.json").write_text(json.dumps({"api_audit": {"contexts": [{}, {}]}}))
    monkeypatch.setattr(collector, "graph_audit", lambda events: {"available": False})
    monkeypatch.setattr(collector, "quote_decision_audit", lambda events: {})
    monkeypatch.setattr(collector, "model_evidence_audit", lambda events: {})
    monkeypatch.setattr(collector, "analyze", lambda events: {
        "estimated_vs_observed": {"unknown": None}, "quote_protocol_rejections": private_text})
    result = collector.collect(root, old)
    assert private_text not in json.dumps(result, ensure_ascii=False)
    assert attempt["benchmark_score"] is None
    assert attempt["residency_validation"] is None
    assert attempt["actual_recipient_contexts_audited"] == 2
    assert attempt["estimated_vs_observed"]["unknown"] is None
    attempt["execution_sha256"] = "wrong execution"
    with pytest.raises(RuntimeError, match="different execution"):
        collector.collect(root, old)


def test_settled_jsonl_uses_physical_lines_not_unicode_separators(tmp_path: Path) -> None:
    directory = tmp_path / "evidence/cell/attempt1"
    run = directory / "runs/run"
    run.mkdir(parents=True)
    result = {"execution_completed": False, "final_answer": None, "evaluation": None}
    (run / "result.json").write_text(json.dumps(result))
    (run / "trace.jsonl").write_text(json.dumps({"event_type": "diagnostic", "payload": {
        "text": "PRIVATE\u2028PROMPT\u0085QUERY"}}, ensure_ascii=False) + "\n", encoding="utf-8")
    admission = {"disposition": "valid", "result_sha256": provenance_sha256(result)}
    (directory / "admission.json").write_text(json.dumps(admission))
    attempt = SimpleNamespace(cell_id="cell", attempt_index=1, run_id="run",
                              execution_sha256="a" * 64,
                              receipt_sha256=provenance_sha256(admission),
                              disposition="valid", reason="semantic_failure")
    projected = base.settled_attempt(tmp_path, "cell", attempt)
    assert projected["benchmark_score"] is None
    assert "PRIVATE" not in json.dumps(projected)


def test_external_selection_loads_only_new_result_namespace(tmp_path: Path, monkeypatch) -> None:
    root, selection = tmp_path / "new", tmp_path / "old/preparation/task-freeze-002"
    root.mkdir()
    selection.mkdir(parents=True)
    (selection / "manifest.json").write_text(json.dumps({"phase1_schedule_sha256": "schedule"}))
    (selection / "phase1-schedule.json").write_text('[{"cell_id":"cell"}]')
    (root / "phase1-attempts.jsonl").write_text("new journal\n")

    class NewLedger:
        attempts = (SimpleNamespace(cell_id="cell", run_id="new-run", disposition="valid",
                                    reason="completed_or_valid_semantic_failure"),)
        original_attempts = attempts

        def __init__(self, journal: Path, cells: tuple, schedule_hash: str) -> None:
            assert journal == root / "phase1-attempts.jsonl"
            assert cells == ("cell",) and schedule_hash == "schedule"

    monkeypatch.setattr(base, "SnapshotAttemptLedger", NewLedger)

    def new_settled(path: Path, cell: str, attempt: SimpleNamespace) -> dict:
        assert path == root and attempt.run_id == "new-run"
        return {"run_id": attempt.run_id}

    monkeypatch.setattr(base, "settled_attempt", new_settled)
    result = base.snapshot(root, selection_root=selection)
    assert result["admitted_cells"] == 1
    assert result["rows"][0]["attempts"] == [{"run_id": "new-run"}]
