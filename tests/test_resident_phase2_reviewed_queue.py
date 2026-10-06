import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
import test_resident_adjudicated_queue as fixtures
from test_resident_phase2_queue import simulated_queue

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_phase2_reviewed_queue_v1")
rejected_model_json = fixtures.rejected_model_json


@pytest.fixture
def heldout_json(rejected_model_json, monkeypatch):
    root, directory, old_ledger, receipt = rejected_model_json
    run = directory / "runs/run1"
    (directory / "process-exit.json").write_text('{"pid":9999999,"returncode":0}')
    source = ('completion = await deployment.backend.invoke(model_request)\n'
              'json.loads(completion.text)\n'
              'raise ValueError("model output is not valid JSON")\n')
    paths = {}
    for app in ("app", "app-input-cardinality-repair-003"):
        for relative in queue.SOURCES:
            path = root / app / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source if relative.endswith("server.py") else "inference = None\n")
            paths[relative] = queue.legacy.sha256(path)
    (root / "execution-freeze-003.json").write_text(json.dumps({"source_sha256": paths}))
    monkeypatch.setattr(queue.bindings, "frozen_sources", lambda *_: copy.deepcopy(paths))
    receipt["original_evaluation"]["benchmark_score"] = 0
    (directory / "admission.json").write_text(json.dumps(receipt))
    ledger = AttemptLedger(root / "phase2-attempts.jsonl", old_ledger.cells, "a" * 64)
    ledger.reserve("cell1", "run1", "b" * 64)
    ledger.settle("run1", "confounder", queue.legacy.GATE_PROBLEM, provenance_sha256(receipt))
    parent = root / "phase2-control-freeze-001.json"
    parent.write_text('{"original":"preserved"}')
    saved = {"execution_freeze_sha256": "b" * 64, "phase2_schedule_sha256": "a" * 64,
             "pricing_path": str(root / "prices"), "nominal_cells": 2}
    cells = (type("Cell", (), {"cell_id": "cell1"})(),
             type("Cell", (), {"cell_id": "cell2"})())
    monkeypatch.setattr(queue.previous, "checked_control", lambda _: (saved, cells))
    monkeypatch.setattr(queue.previous.previous, "admission", lambda *_: receipt)
    events = [json.loads(line) for line in (run / "trace.jsonl").open()]
    events[0]["payload"]["action"]["prompt"] += "\u2028PRIVATE_AFTER_SEPARATOR"
    (run / "trace.jsonl").write_text("".join(
        json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")
    return root, directory, ledger, receipt, parent, saved, cells


def test_exact_review_preserves_history_wrong_score_and_unknown_cost(heldout_json):
    root, directory, ledger, receipt, parent, _, _ = heldout_json
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    journal = ledger.path.read_bytes()
    result = queue.create_review("run1", parent)
    assert result["confirmed_model_parse_failures"] == 1 and result["retry"] is False
    sidecar = json.loads(Path(result["sidecar_path"]).read_text())
    assert sidecar["reviewed_admission"]["original_evaluation"] == receipt["original_evaluation"]
    assert sidecar["reviewed_admission"]["original_evaluation"]["benchmark_score"] == 0
    assert sidecar["proof"][0]["model_service_tokens_unknown"] is True
    assert sidecar["replacement_authorized"] is False
    assert "PRIVATE" not in json.dumps(sidecar)
    assert ledger.path.read_bytes() == journal
    assert all(p.read_bytes() == content for p, content in before.items())
    view = queue.ReviewedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert view.original_attempts[0].disposition == "confounder"
    assert view.attempts[0].disposition == "valid"
    assert queue.effective_admission(root, view.attempts[0]) == sidecar["reviewed_admission"]
    with pytest.raises(RuntimeError, match="must not be repeated"):
        view.reserve("cell1", "forbidden-retry", "b" * 64)
    with pytest.raises(FileExistsError):
        queue.create_review("run1", parent)


@pytest.mark.parametrize("damage", [
    "source", "residency", "worker_exit", "wrapper_exit", "schema_error", "duplicate",
    "privacy", "physical_stage", "wrong_media", "operational",
])
def test_review_cannot_waive_unrelated_findings(heldout_json, damage):
    root, directory, ledger, receipt, parent, _, _ = heldout_json
    if damage == "source":
        (root / "app-input-cardinality-repair-003" / queue.SOURCES[0]).write_text("changed")
    elif damage in {"residency", "worker_exit", "wrapper_exit"}:
        relative, value = {
            "residency": ("private/residency-validation.json", {"passed": False}),
            "worker_exit": ("worker-shutdown.json", {"verified_exited": False}),
            "wrapper_exit": ("process-exit.json", {"returncode": 1}),
        }[damage]
        (directory / relative).write_text(json.dumps(value))
    elif damage in {"privacy", "operational"}:
        receipt["problems"].append("privacy_violation" if damage == "privacy" else "outage")
    else:
        trace = directory / "runs/run1/trace.jsonl"
        events = [json.loads(line) for line in trace.open(encoding="utf-8")]
        if damage == "duplicate":
            events.append(events[-1])
        elif damage == "schema_error":
            events[1]["payload"]["failure_message"] = "schema mismatch"
        elif damage == "physical_stage":
            events[-1]["payload"]["failure"]["stage"] = "selection"
        else:
            events[0]["payload"]["action"]["outputs"][0]["media_type"] = "text/plain"
        trace.write_text("".join(json.dumps(e) + "\n" for e in events))
    before = ledger.path.read_bytes()
    with pytest.raises(RuntimeError):
        queue.create_review("run1", parent)
    assert not (root / queue.DIRECTORY / "run1.json").exists()
    assert ledger.path.read_bytes() == before


def test_live_guard_runs_before_review_or_queue_reads(heldout_json, monkeypatch):
    root, _, _, _, parent, _, _ = heldout_json

    def active(_):
        raise RuntimeError("live queue")

    monkeypatch.setattr(queue.previous.gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(queue.previous, "checked_control", lambda _: pytest.fail("read control"))
    with pytest.raises(RuntimeError, match="live queue"):
        queue.create_review("run1", parent)
    with pytest.raises(RuntimeError, match="live queue"):
        queue.run(root / "phase2-reviewed-control-freeze-001.json")


@pytest.mark.parametrize("damage", ["sidecar", "evidence", "worker_source", "parent"])
def test_existing_sidecar_requires_exact_unchanged_proof(heldout_json, damage):
    root, directory, ledger, _, parent, _, _ = heldout_json
    queue.create_review("run1", parent)
    if damage == "sidecar":
        p = root / queue.DIRECTORY / "run1.json"
        value = json.loads(p.read_text())
        value["replacement_authorized"] = True
        p.write_text(json.dumps(value))
    elif damage == "evidence":
        (directory / "new-unbound-file.json").write_text("{}")
    elif damage == "worker_source":
        (root / "app-input-cardinality-repair-003" / queue.SOURCES[1]).write_text("changed")
    else:
        parent.write_text('{"original":"changed"}')
    with pytest.raises(RuntimeError):
        _ = queue.ReviewedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256).attempts


def test_continuation_uses_same_atomic_executor_without_retries_or_monkeypatch(
    heldout_json, monkeypatch,
):
    root, _, ledger, _, parent, saved, cells = heldout_json
    queue.create_review("run1", parent)
    control = root / "phase2-reviewed-control-freeze-001.json"
    queue.frozen.write_new(control, queue.control_value(parent))
    monkeypatch.setattr(queue, "checked_control", lambda _: (saved, cells))
    calls = []

    def execute(cell, view, value):
        assert value is saved
        calls.append(cell.cell_id)
        view.reserve(cell.cell_id, "run2", "b" * 64)
        view.settle("run2", "valid", "quality_failure", "c" * 64)

    original_class = queue.previous.previous.quote.reviewer.QuoteRepairAttemptLedger
    monkeypatch.setattr(queue.previous, "execute_cell", execute)
    queue.run(control)
    assert calls == ["cell2"]
    assert queue.previous.previous.quote.reviewer.QuoteRepairAttemptLedger is original_class
    view = queue.ReviewedAttemptLedger(ledger.path, ledger.cells, ledger.schedule_sha256)
    assert len(view.original_attempts) == 2 and view.completed_cells == ("cell1", "cell2")
    assert json.loads((root / "phase2-queue-completed.json").read_text())["goal_complete"] is False


def test_execution_boundary_is_the_original_atomic_entrypoint():
    assert queue.previous.execute_cell is queue.previous.previous.execute_cell
    assert queue.previous.execute_cell.__module__ == "large_scale_resident_phase2_queue_v1"


def test_review_control_rejects_unreviewed_or_foreign_sidecars(heldout_json):
    root, _, _, _, parent, _, _ = heldout_json
    with pytest.raises(RuntimeError, match="actual exact sidecars"):
        queue.control_value(parent)
    queue.create_review("run1", parent)
    (root / queue.DIRECTORY / "foreign.json").write_text("{}")
    with pytest.raises(RuntimeError, match="unresolved or unowned"):
        queue.control_value(parent)


def test_reviewed_execution_keeps_existing_fail_closed_behavior(monkeypatch, tmp_path):
    _, calls, cells = simulated_queue(monkeypatch, tmp_path, disposition="confounder")
    saved = {"phase2_schedule_sha256": queue.previous.previous.schedule_sha256(cells),
             "global_cap": 420, "execution_freeze_sha256": "c" * 64,
             "atomic_execution_entrypoint": str(queue.frozen.APP /
                                                "scripts/large_scale_resident_queue_v1.py"),
             "pricing_path": str(tmp_path / "prices")}
    path = tmp_path / "phase2-reviewed-control-freeze-001.json"
    path.write_text("{}")
    monkeypatch.setattr(queue, "checked_control", lambda _: (saved, cells))
    with pytest.raises(RuntimeError, match="actual audit"):
        queue.run(path)
    assert len(calls) == 1
    assert not (tmp_path / "evidence" / cells[1].cell_id).exists()
    assert "audit-tools" not in calls[0]["env"]["PYTHONPATH"]
