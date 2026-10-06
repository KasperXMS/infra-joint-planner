import copy
import importlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from infra_joint.experiments.attempt_ledger import AttemptLedger
from infra_joint.experiments.large_scale_protocol import (
    FAMILIES,
    PhaseOneGate,
    SelectedTask,
    phase_one_schedule,
    phase_two_schedule,
    schedule_sha256,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_resident_phase2_queue_v1")


def synthetic_gate() -> dict:
    tasks = tuple(SelectedTask(f, f"synthetic-{f}-{i}", i)
                  for f in FAMILIES for i in range(1, 7))
    phase1 = phase_one_schedule(tasks, e_history_tasks=())
    cells = phase_two_schedule(
        tasks, methods=("B0", "B1", "A"),
        gate=PhaseOneGate(schedule_sha256(phase1), tuple(c.cell_id for c in phase1), "a" * 64),
        e_history_tasks=(), pruning_manifest_sha256="b" * 64, prior_substantive_cells=42,
    )
    return {"schedule": [{"cell_id": c.cell_id, **asdict(c)} for c in cells],
            "methods": ["B0", "B1", "A"], "phase2_cells": 144,
            "phase2_schedule_sha256": schedule_sha256(cells),
            "phase2_execution_sha256": "c" * 64, "journal_sha256": "d" * 64}


def test_exact_heldout_schedule_is_reconstructed_without_semantic_changes() -> None:
    value = synthetic_gate()
    before = copy.deepcopy(value)
    cells = queue.cells_from_gate(value)
    assert value == before
    assert len(cells) == 144
    assert all(c.phase == 2 and c.task.position >= 3 for c in cells)
    assert schedule_sha256(cells) == value["phase2_schedule_sha256"]


@pytest.mark.parametrize("defect", ["phase", "position", "identity", "method", "hash", "count"])
def test_changed_schedule_cannot_enter_actual_queue(defect: str) -> None:
    value = synthetic_gate()
    row = value["schedule"][0]
    if defect == "phase":
        row["phase"] = 1
    elif defect == "position":
        row["task"]["position"] = 1
    elif defect == "identity":
        row["cell_id"] = "replacement"
    elif defect == "method":
        row["method"] = "D"
    elif defect == "hash":
        value["phase2_schedule_sha256"] = "0" * 64
    elif defect == "count":
        value["phase2_cells"] = 168
    with pytest.raises(RuntimeError, match="schedule changed"):
        queue.cells_from_gate(value)


def test_saved_gate_requires_real_recomputed_inputs(monkeypatch, tmp_path: Path) -> None:
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


def test_control_cannot_substitute_actual_execution_or_older_app(monkeypatch,
                                                              tmp_path: Path) -> None:
    value = synthetic_gate()
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.frozen, "APP", tmp_path / queue.frozen.E_QUERY_APP_NAME)
    monkeypatch.setattr(queue, "verified_gate", lambda *args: value)
    monkeypatch.setattr(queue.frozen, "verify_freeze", lambda: "0" * 64)
    with pytest.raises(RuntimeError, match="replace"):
        queue.control_value(tmp_path / "gate.json", {})
    monkeypatch.setattr(queue.frozen, "APP", tmp_path / "app")
    with pytest.raises(RuntimeError, match="execution004"):
        queue.control_value(tmp_path / "gate.json", {})
    monkeypatch.setattr(queue.frozen, "APP", tmp_path / queue.frozen.CARDINALITY_APP_NAME)
    with pytest.raises(RuntimeError, match="execution004"):
        queue.control_value(tmp_path / "gate.json", {})


def test_live_phase_one_blocks_phase_two_before_control_or_journal(monkeypatch,
                                                                tmp_path: Path) -> None:
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)

    def active(root):
        raise RuntimeError("live PhaseI")

    monkeypatch.setattr(queue.gate.evidence.private, "assert_inactive", active)
    monkeypatch.setattr(queue, "checked_control", lambda _: pytest.fail("must not load control"))
    with pytest.raises(RuntimeError, match="live PhaseI"):
        queue.run(tmp_path / "phase2-control-freeze-001.json")
    assert not (tmp_path / "phase2-attempts.jsonl").exists()


def simulated_queue(monkeypatch, tmp_path: Path, *, disposition: str = "valid",
                    returncode: int = 0) -> tuple[Path, list, tuple]:
    """Fake child processes only; actual ledger/files demonstrate controller rules."""
    (tmp_path / "cell-configs").mkdir()
    (tmp_path / "phase1-attempts.jsonl").write_text("immutable PhaseI\n")
    cells = queue.cells_from_gate(synthetic_gate())[:2]
    app = tmp_path / queue.frozen.E_QUERY_APP_NAME
    saved = {
        "global_cap": 420, "execution_freeze_sha256": "c" * 64,
        "atomic_execution_entrypoint": str(app / "scripts/large_scale_resident_queue_v1.py"),
        "pricing_path": str(tmp_path / "prices.json"),
    }
    calls = []
    monkeypatch.setattr(queue.frozen, "ROOT", tmp_path)
    monkeypatch.setattr(queue.frozen, "APP", app)
    monkeypatch.setattr(queue.frozen, "require_remote", lambda: None)
    monkeypatch.setattr(queue.gate.evidence.private, "assert_inactive", lambda _: None)
    monkeypatch.setattr(queue, "checked_control", lambda _: (saved, cells))
    monkeypatch.setattr(queue.quote.reviewer, "QuoteRepairAttemptLedger", AttemptLedger)
    monkeypatch.setattr(queue.frozen, "reference", lambda: {})
    monkeypatch.setattr(queue.frozen, "cell_config", lambda c, r, ref, root: {
        "run_id": r, "cell_id": c.cell_id, "method": c.method})

    class Atomic:
        def __init__(self, args, *, stdout, stderr, env):
            self.pid = 5000 + len(calls)
            calls.append({"args": args, "env": {"PYTHONPATH": env["PYTHONPATH"]}})
            output = Path(args[-1])
            private = output / "private"
            private.mkdir()
            (private / "residency-validation.json").write_text('{"passed":true}')

        def wait(self):
            return returncode

    monkeypatch.setattr(queue.subprocess, "Popen", Atomic)

    def admit(directory, config, prices):
        return {"disposition": disposition,
                "reason": "provider_outage" if disposition == "operational_excluded" else (
                    "unresolved_system" if disposition == "confounder" else "ordinary_quality"),
                "problems": [], "original_evaluation": {"benchmark_score": 0}}

    monkeypatch.setattr(queue.quote, "admission", admit)
    return tmp_path / "phase2-control-freeze-001.json", calls, cells


def test_same_archived_atomic_entrypoint_and_no_wrong_answer_retry(monkeypatch,
                                                               tmp_path: Path) -> None:
    path, calls, cells = simulated_queue(monkeypatch, tmp_path)
    queue.run(path)
    assert len(calls) == 2
    for call in calls:
        assert call["args"][1] == str(queue.frozen.APP / "scripts/large_scale_resident_queue_v1.py")
        assert call["args"][2] == "--attempt"
        assert call["env"]["PYTHONPATH"] == str(queue.frozen.APP / "src") + (
            queue.os.pathsep + str(queue.frozen.APP / "scripts"))
        assert "audit-tools" not in call["env"]["PYTHONPATH"]
    result = json.loads((tmp_path / "phase2-queue-completed.json").read_text())
    assert result["completed_cells"] == [c.cell_id for c in cells]
    assert result["goal_complete"] is False
    assert (tmp_path / "phase1-attempts.jsonl").read_text() == "immutable PhaseI\n"
    # It cannot create a second completion receipt or repeat valid nominal cells.
    with pytest.raises(FileExistsError):
        queue.run(path)
    assert len(calls) == 2


@pytest.mark.parametrize(("disposition", "returncode"), [
    ("confounder", 0), ("operational_excluded", 0), ("valid", 1),
])
def test_nonvalid_attempt_retained_and_stops_before_next_cell(monkeypatch, tmp_path: Path,
                                                           disposition: str,
                                                           returncode: int) -> None:
    path, calls, cells = simulated_queue(monkeypatch, tmp_path, disposition=disposition,
                                        returncode=returncode)
    with pytest.raises(RuntimeError, match="actual audit"):
        queue.run(path)
    assert len(calls) == 1
    assert not (tmp_path / "phase2-queue-completed.json").exists()
    assert not (tmp_path / "evidence" / cells[1].cell_id).exists()
    directory = tmp_path / "evidence" / cells[0].cell_id / "attempt1"
    admission = json.loads((directory / "admission.json").read_text())
    assert admission["disposition"] != "valid"
    assert (directory / "process.json").exists()
    assert (directory / "process-exit.json").exists()
    ledger = AttemptLedger(tmp_path / "phase2-attempts.jsonl", tuple(c.cell_id for c in cells),
                           schedule_sha256(cells))
    assert len(ledger.attempts) == 1 and not ledger.pending


def test_pending_handle_cannot_start_replacement(monkeypatch, tmp_path: Path) -> None:
    path, calls, cells = simulated_queue(monkeypatch, tmp_path)
    journal = tmp_path / "phase2-attempts.jsonl"
    ledger = AttemptLedger(journal, tuple(c.cell_id for c in cells), schedule_sha256(cells))
    ledger.reserve(cells[0].cell_id, "synthetic-pending", "c" * 64)
    before = journal.read_bytes()
    with pytest.raises(RuntimeError, match="unresolved"):
        queue.run(path)
    assert not calls
    assert journal.read_bytes() == before


def test_single_identical_operational_replacement_limit(monkeypatch, tmp_path: Path) -> None:
    path, calls, _ = simulated_queue(monkeypatch, tmp_path, disposition="operational_excluded")
    for _ in range(2):
        with pytest.raises(RuntimeError, match="actual audit"):
            queue.run(path)
    assert len(calls) == 2
    with pytest.raises(RuntimeError, match="replacement exhausted"):
        queue.run(path)
    assert len(calls) == 2


def test_hash_only_repair_event_cannot_waive_current_control(monkeypatch, tmp_path: Path) -> None:
    path, calls, cells = simulated_queue(monkeypatch, tmp_path, disposition="confounder")
    with pytest.raises(RuntimeError, match="actual audit"):
        queue.run(path)
    ledger = AttemptLedger(tmp_path / "phase2-attempts.jsonl", tuple(c.cell_id for c in cells),
                           schedule_sha256(cells))
    failed = ledger.attempts[0]
    assert failed.receipt_sha256 is not None
    ledger.authorize_generic_repair(failed.run_id,
                                   original_admission_sha256=failed.receipt_sha256,
                                   repair_audit_sha256="e" * 64, new_execution_sha256="f" * 64)
    with pytest.raises(RuntimeError, match="unresolved"):
        queue.run(path)
    assert len(calls) == 1


def test_cumulative_cap_blocks_child_before_reservation(monkeypatch, tmp_path: Path) -> None:
    _, calls, cells = simulated_queue(monkeypatch, tmp_path)
    ledger = AttemptLedger(tmp_path / "phase2-attempts.jsonl", tuple(c.cell_id for c in cells),
                           schedule_sha256(cells))
    before = ledger.path.read_bytes()
    with pytest.raises(RuntimeError, match="cap reached"):
        queue.execute_cell(cells[0], ledger, {"global_cap": 210})
    assert ledger.path.read_bytes() == before
    assert not calls


@pytest.fixture
def short_E_root():
    # Full production run IDs intentionally remain long. Keep the Windows test
    # root short instead of changing Linux run identity or disabling checks.
    with TemporaryDirectory(prefix="p2e-") as directory:
        yield Path(directory)


@pytest.mark.parametrize("bad_surface", [False, True])
def test_heldout_E_reuses_every_request_no_query_surface_guard(
    monkeypatch, short_E_root: Path, bad_surface: bool,
) -> None:
    tmp_path = short_E_root
    _, calls, original_cells = simulated_queue(monkeypatch, tmp_path)
    cell = replace(original_cells[0], method="E")
    run_id = f"{tmp_path.name}-{cell.cell_id}-attempt1"
    trace = tmp_path / "evidence" / cell.cell_id / "attempt1/runs" / run_id / "trace.jsonl"
    ledger = AttemptLedger(tmp_path / "phase2-attempts.jsonl", (cell.cell_id,), "a" * 64)
    saved = {"global_cap": 420, "execution_freeze_sha256": "c" * 64,
             "atomic_execution_entrypoint": "unchanged-atomic.py",
             "pricing_path": str(tmp_path / "prices.json")}
    checks = []
    old_admit = queue.quote.admission

    def admit(directory, config, prices):
        trace.parent.mkdir(parents=True)
        trace.write_text('{"event_type":"method.variant.start","payload":{}}\n')
        return old_admit(directory, config, prices)

    def surface(directory, events):
        checks.append((directory, events))
        if bad_surface:
            raise RuntimeError("E unexpectedly exposes query tools")

    monkeypatch.setattr(queue.quote, "admission", admit)
    monkeypatch.setattr(queue.method_contract, "assert_E_tool_isolation", surface)
    if bad_surface:
        with pytest.raises(RuntimeError, match="actual audit"):
            queue.execute_cell(cell, ledger, saved)
        assert ledger.attempts[0].disposition == "confounder"
    else:
        queue.execute_cell(cell, ledger, saved)
        assert ledger.attempts[0].disposition == "valid"
    assert len(calls) == len(checks) == 1
    assert checks[0][1][0]["event_type"] == "method.variant.start"
