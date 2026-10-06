import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from test_resident_phase2_queue import queue as historical
from test_resident_phase2_queue import simulated_queue, synthetic_gate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_current_phase2_queue_v1")


def test_same_executor_and_schedule_with_current_gate_only():
    assert queue.execute_cell is historical.execute_cell
    assert queue.cells_from_gate is historical.cells_from_gate
    assert queue.gate.evidence.sources.__name__ == "large_scale_resident_field_policy_snapshot_v1"
    assert len(queue.cells_from_gate(synthetic_gate())) == 144


def test_current_dependency_closure_binds_policy_timeout_and_atomic_sources():
    bindings = queue.source_bindings()
    for name in (
        "large_scale_resident_current_phase2_queue_v1.py",
        "large_scale_resident_phase2_queue_v1.py",
        "large_scale_resident_current_phase2_gate_v1.py",
        "large_scale_resident_current_private_evidence_v1.py",
        "large_scale_resident_field_policy_snapshot_v1.py",
        "large_scale_resident_field_policy_review_v1.py",
        "large_scale_resident_timeout_review_v1.py",
        "large_scale_resident_projection_review_v1.py",
        "large_scale_resident_queue_v1.py",
    ):
        assert name in bindings and len(bindings[name]) == 64


def test_current_gate_is_recomputed_not_trusted(monkeypatch, tmp_path):
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    path = tmp_path / "analysis/gate.json"
    path.parent.mkdir()
    value = synthetic_gate()
    path.write_text(json.dumps(value))
    monkeypatch.setattr(queue.gate, "verify_gate_inputs", lambda _: copy.deepcopy(value))
    assert queue.verified_gate(path, {}) == value
    path.write_text(json.dumps(dict(value, phase2_cells=192)))
    with pytest.raises(RuntimeError, match="actual audit"):
        queue.verified_gate(path, {})


def test_current_live_guard_precedes_control_and_phase2_journal(monkeypatch, tmp_path):
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)

    def active(_):
        raise RuntimeError("live PhaseI")

    monkeypatch.setattr(queue.gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(queue, "checked_control", lambda _: pytest.fail("control read"))
    with pytest.raises(RuntimeError, match="live PhaseI"):
        queue.run(tmp_path / "phase2-control-freeze-001.json")
    assert not (tmp_path / "phase2-attempts.jsonl").exists()


def test_current_control_preserves_preregistered_schedule_models_prices_and_source004(
    monkeypatch, tmp_path,
):
    value = synthetic_gate()
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    app = tmp_path / queue.frozen.E_QUERY_APP_NAME
    monkeypatch.setattr(queue.frozen, "APP", app)
    monkeypatch.setattr(queue, "verified_gate", lambda *_: copy.deepcopy(value))
    monkeypatch.setattr(queue.frozen, "verify_freeze", lambda: value["phase2_execution_sha256"])
    monkeypatch.setattr(queue.frozen, "verified_prices", lambda *_: (tmp_path / "prices", "e" * 64))
    monkeypatch.setattr(queue.gate, "digest", lambda _: "f" * 64)
    result = queue.control_value(tmp_path / "gate.json", {})
    assert result["nominal_cells"] == 144
    assert result["planned_cumulative_substantive_cells"] == 354
    assert result["atomic_execution_entrypoint"] == str(
        app / "scripts/large_scale_resident_queue_v1.py")
    assert result["execution_freeze_sha256"] == value["phase2_execution_sha256"]
    assert result["methods"] == value["methods"] and not result["semantic_tuning"]
    monkeypatch.setattr(queue.frozen, "verify_freeze", lambda: "0" * 64)
    with pytest.raises(RuntimeError, match="replace"):
        queue.control_value(tmp_path / "gate.json", {})


def test_current_queue_reuses_atomic_child_and_does_not_retry_wrong_answer(monkeypatch, tmp_path):
    path, calls, cells = simulated_queue(monkeypatch, tmp_path)
    monkeypatch.setattr(queue, "checked_control", historical.checked_control)
    queue.run(path)
    assert len(calls) == 2
    assert all(call["args"][1] == str(queue.frozen.APP / "scripts/large_scale_resident_queue_v1.py")
               for call in calls)
    assert all("audit-tools" not in call["env"]["PYTHONPATH"] for call in calls)
    completed = json.loads((tmp_path / "phase2-queue-completed.json").read_text())
    assert completed["completed_cells"] == [c.cell_id for c in cells]
    assert (tmp_path / "phase1-attempts.jsonl").read_text() == "immutable PhaseI\n"
    with pytest.raises(FileExistsError):
        queue.run(path)
    assert len(calls) == 2


@pytest.mark.parametrize(("disposition", "returncode"), [
    ("confounder", 0), ("operational_excluded", 0), ("valid", 1),
])
def test_current_queue_stops_with_failed_evidence_intact_before_next_cell(
    monkeypatch, tmp_path, disposition, returncode,
):
    path, calls, cells = simulated_queue(monkeypatch, tmp_path, disposition=disposition,
                                        returncode=returncode)
    monkeypatch.setattr(queue, "checked_control", historical.checked_control)
    with pytest.raises(RuntimeError, match="actual audit"):
        queue.run(path)
    assert len(calls) == 1
    assert not (tmp_path / "evidence" / cells[1].cell_id).exists()
    assert (tmp_path / "evidence" / cells[0].cell_id / "attempt1/admission.json").exists()
    assert not (tmp_path / "phase2-queue-completed.json").exists()
