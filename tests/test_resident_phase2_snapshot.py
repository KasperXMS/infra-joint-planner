import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from test_resident_phase2_queue import synthetic_gate

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
snapshot = importlib.import_module("large_scale_resident_phase2_snapshot_v1")


def inputs(monkeypatch, tmp_path):
    gate = synthetic_gate()
    control = {
        "execution_freeze_sha256": gate["phase2_execution_sha256"],
        "phase2_schedule_sha256": gate["phase2_schedule_sha256"],
        "methods": gate["methods"], "nominal_cells": gate["phase2_cells"],
        "source_sha256": {"source.py": "a" * 64},
    }
    gate_path = tmp_path / "analysis/gate.json"
    gate_path.parent.mkdir()
    gate_path.write_text(json.dumps(gate))
    phase1 = tmp_path / "phase1-attempts.jsonl"
    phase1.write_text("immutable phase1\n")
    control.update(gate_path=str(gate_path),
                   gate_file_sha256=snapshot.queue.frozen.sha256(gate_path),
                   phase1_journal_sha256=snapshot.queue.frozen.sha256(phase1))
    path = tmp_path / "phase2-control-freeze-001.json"
    path.write_text(json.dumps(control))
    monkeypatch.setattr(snapshot.queue, "source_bindings", lambda: control["source_sha256"])
    return path, control, gate


def test_verified_control_schedule_and_sources_are_read_only(monkeypatch, tmp_path):
    path, control, gate = inputs(monkeypatch, tmp_path)
    before = path.read_bytes()
    assert snapshot.checked_inputs(tmp_path, path) == (control, gate)
    assert path.read_bytes() == before


@pytest.mark.parametrize("defect", ["source", "phase1", "gate", "schedule", "execution"])
def test_frozen_input_drift_rejected(monkeypatch, tmp_path, defect):
    path, control, _ = inputs(monkeypatch, tmp_path)
    if defect == "source":
        monkeypatch.setattr(snapshot.queue, "source_bindings", lambda: {})
    elif defect == "phase1":
        (tmp_path / "phase1-attempts.jsonl").write_text("changed")
    elif defect == "gate":
        Path(control["gate_path"]).write_text("{}")
    else:
        control["phase2_schedule_sha256" if defect == "schedule"
                else "execution_freeze_sha256"] = "0" * 64
        path.write_text(json.dumps(control))
    with pytest.raises(RuntimeError, match="drift|mismatch"):
        snapshot.checked_inputs(tmp_path, path)


def test_missing_journal_is_never_initialized(monkeypatch, tmp_path):
    path, _, _ = inputs(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError, match="initialize"):
        snapshot.collect(tmp_path, control_path=path)
    assert not (tmp_path / "phase2-attempts.jsonl").exists()


def populated(monkeypatch, tmp_path):
    path, control, gate = inputs(monkeypatch, tmp_path)
    journal = tmp_path / "phase2-attempts.jsonl"
    ledger = AttemptLedger(journal, tuple(c["cell_id"] for c in gate["schedule"]),
                           gate["phase2_schedule_sha256"])
    attempt = ledger.reserve(gate["schedule"][0]["cell_id"], "first",
                             control["execution_freeze_sha256"])
    ledger.settle("first", "valid", "nominal", "b" * 64)
    ledger.reserve(gate["schedule"][1]["cell_id"], "pending",
                   control["execution_freeze_sha256"])
    return path, journal, attempt


def test_pending_never_read_and_wrong_answer_retained(monkeypatch, tmp_path):
    path, journal, _ = populated(monkeypatch, tmp_path)
    before = journal.read_bytes()
    calls = []

    def settled(root, attempt, execution):
        calls.append(attempt.run_id)
        return {"execution_completed": True, "benchmark_score": 0,
                "unmeasured_model_work": None}

    monkeypatch.setattr(snapshot, "settled", settled)
    value = snapshot.collect(tmp_path, control_path=path)
    assert calls == ["first"]
    assert value["admitted_cells"] == 1 and value["pending_count"] == 1
    assert value["rows"][0]["attempts"][0]["benchmark_score"] == 0
    assert value["rows"][0]["attempts"][0]["unmeasured_model_work"] is None
    assert value["rows"][1]["pending_run_ids"] == ["pending"]
    assert not value["goal_complete"] and not value["private_semantic_audit_complete"]
    assert journal.read_bytes() == before


def test_advancing_journal_does_not_publish_snapshot(monkeypatch, tmp_path):
    path, journal, _ = populated(monkeypatch, tmp_path)

    def settled(*_):
        with journal.open("a") as stream:
            stream.write("changed\n")
        return {}

    monkeypatch.setattr(snapshot, "settled", settled)
    with pytest.raises(RuntimeError, match="journal advanced"):
        snapshot.collect(tmp_path, control_path=path)


def test_admission_digest_not_trusted(monkeypatch, tmp_path):
    _, _, attempt = populated(monkeypatch, tmp_path)
    directory = tmp_path / "evidence" / attempt.cell_id / "attempt1"
    directory.mkdir(parents=True)
    admission = {"disposition": "valid", "result_sha256": "c" * 64}
    (directory / "admission.json").write_text(json.dumps(admission))
    completed = replace(attempt, disposition="valid",
                        receipt_sha256=provenance_sha256(admission))
    assert snapshot.original_admission(tmp_path, completed) == admission
    corrupted = copy.deepcopy(admission)
    corrupted["disposition"] = "confounder"
    (directory / "admission.json").write_text(json.dumps(corrupted))
    with pytest.raises(RuntimeError, match="admission/settlement"):
        snapshot.original_admission(tmp_path, completed)


def test_atomic_source_mismatch_precedes_trace_read(monkeypatch, tmp_path):
    _, _, attempt = populated(monkeypatch, tmp_path)
    monkeypatch.setattr(snapshot.base, "settled_attempt", lambda *_: pytest.fail("read trace"))
    with pytest.raises(RuntimeError, match="different atomic source"):
        snapshot.settled(tmp_path, attempt, "0" * 64)


def test_real_settled_projection_preserves_unicode_without_exporting_bodies(
    monkeypatch, tmp_path,
):
    _, _, attempt = populated(monkeypatch, tmp_path)
    directory = tmp_path / "evidence" / attempt.cell_id / "attempt1"
    run = directory / "runs" / attempt.run_id
    run.mkdir(parents=True)
    sentinel = "PRIVATE-BODY\u2028PRIVATE-GOLD\u0085PRIVATE-PROMPT"
    result = {"execution_completed": True, "final_answer": sentinel,
              "evaluation": {"benchmark_score": 0, "format_valid": True,
                             "details": sentinel}, "loop": None,
              "failure": None, "telemetry": None}
    (run / "result.json").write_text(json.dumps(result), encoding="utf-8")
    event = {"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "input_items": [
            {"type": "message", "content": sentinel}]}}
    (run / "trace.jsonl").write_text(
        json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
    admission = {"disposition": "valid", "result_sha256": provenance_sha256(result)}
    (directory / "admission.json").write_text(json.dumps(admission))
    completed = replace(attempt, disposition="valid",
                        receipt_sha256=provenance_sha256(admission))
    row = snapshot.settled(tmp_path, completed, completed.execution_sha256)
    assert "PRIVATE-" not in json.dumps(row)
    assert row["benchmark_score"] == 0 and row["terminal_answer_sha256"]
    assert row["residency_validation"] is None
    assert row["worker_shutdown_verified"] is None
    assert row["actual_recipient_contexts_audited"] == 0
    assert row["trace_file_sha256"] == snapshot.queue.frozen.sha256(run / "trace.jsonl")
