import argparse
import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from infra_joint.experiments.attempt_ledger import AttemptLedger
from infra_joint.experiments.large_scale_protocol import (
    ScheduledCell,
    SelectedTask,
    schedule_sha256,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
queue = importlib.import_module("large_scale_queue_v1")


def cell(position: int) -> ScheduledCell:
    return ScheduledCell(1, SelectedTask("multihop_rag", f"synthetic-{position}", position),
                         "deepseek-v4-pro", "slow", "B0", 0)


def configure_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    cells = (cell(1), cell(2))
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.setattr(queue, "require_remote", lambda root: None)
    monkeypatch.setattr(queue.frozen, "validate_runtime_import_root", lambda: None)
    monkeypatch.setattr(queue, "schedule", lambda: cells)
    monkeypatch.setattr(queue, "verify_execution_freeze", lambda path=None: "a" * 64)
    monkeypatch.setattr(queue, "verified_prices",
                        lambda root, app: (tmp_path / "prices.json", "b" * 64))
    return cells


def test_real_entrypoint_refuses_local_benchmark_execution() -> None:
    if sys.platform != "linux":
        with pytest.raises(RuntimeError, match="4090"):
            queue.run_queue()


def test_queue_retains_semantic_failure_and_does_not_repeat_completed_cells(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = configure_queue(tmp_path, monkeypatch)
    starts = []

    class Process:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            path = Path(command[command.index("--config") + 1])
            config = yaml.safe_load(path.read_text())
            starts.append(config)
            # Reservation must already be durable before starting a child.
            current = AttemptLedger(tmp_path / "phase1-attempts.jsonl",
                                    tuple(c.cell_id for c in cells), schedule_sha256(cells))
            assert current.pending[0].run_id == config["run_id"]
            self.pid = 101

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(queue.subprocess, "Popen", Process)
    monkeypatch.setattr(queue, "admit", lambda *args: {
        "disposition": "valid", "reason": "budget_exhaustion",
        "execution_completed": False, "original_evaluation": None})
    queue.run_queue()
    assert len(starts) == 2
    assert (tmp_path / "phase1-queue-completed.json").exists()
    assert not (tmp_path / "queue-lease.json").exists()
    journal = AttemptLedger(tmp_path / "phase1-attempts.jsonl",
                            tuple(c.cell_id for c in cells), schedule_sha256(cells))
    assert journal.completed_cells == tuple(c.cell_id for c in cells)
    # Re-entry cannot launch anything; completion evidence cannot be overwritten.
    with pytest.raises(FileExistsError):
        queue.run_queue()
    assert len(starts) == 2


@pytest.mark.parametrize("disposition", ["confounder", "operational_excluded"])
def test_queue_stops_after_invalid_attempt_without_automatic_retry_or_next_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disposition: str,
) -> None:
    cells = configure_queue(tmp_path, monkeypatch)
    starts = []

    class Process:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            starts.append(command)
            self.pid = 101

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(queue.subprocess, "Popen", Process)
    monkeypatch.setattr(queue, "admit", lambda *args: {
        "disposition": disposition, "reason": "provider_outage"})
    with pytest.raises(RuntimeError):
        queue.run_queue()
    assert len(starts) == 1
    assert "--execution-freeze" in starts[0]
    assert not (tmp_path / "phase1-queue-completed.json").exists()
    assert not (tmp_path / "queue-lease.json").exists()
    journal = AttemptLedger(tmp_path / "phase1-attempts.jsonl",
                            tuple(c.cell_id for c in cells), schedule_sha256(cells))
    assert journal.attempts[0].disposition == disposition


def test_prerunner_failure_always_has_result_and_reconstructable_JSONL(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("run_id: synthetic-run\n")
    args = argparse.Namespace(config=path, output=tmp_path / "evidence")
    queue.fallback_failure(args, RuntimeError("synthetic preflight failure"))
    result = json.loads((args.output / "runs/synthetic-run/result.json").read_text())
    assert result["evaluation"] is None and not result["execution_completed"]
    assert result["attempt_before_runner"] is True
    events = queue.JsonlTraceWriter(args.output / "runs/synthetic-run/trace.jsonl").read_all()
    assert [event["event_type"] for event in events] == ["run.start", "run.failed"]
    assert events[1]["parent_id"] == events[0]["step_id"]


def test_postrunner_exception_preserves_completed_result(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("run_id: synthetic-run\n")
    output = tmp_path / "evidence"
    result_path = output / "runs/synthetic-run/result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text('{"original":"immutable"}')
    original = result_path.read_bytes()
    queue.fallback_failure(argparse.Namespace(config=path, output=output),
                           RuntimeError("cleanup error"))
    assert result_path.read_bytes() == original
    assert not json.loads((output / "attempt-error.json").read_text())["before_runner"]


@pytest.mark.asyncio
async def test_partial_worker_start_failure_still_stops_and_verifies_owned_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    args = argparse.Namespace(config=tmp_path / "config.yaml", output=tmp_path / "evidence")
    args.config.write_text(yaml.safe_dump({
        "run_id": "synthetic-run", "fresh_worker_stores": {"A4": "new-A4", "A5": "new-A5"}}))
    monkeypatch.setattr(queue, "prepare", lambda *args: None)
    monkeypatch.setattr(queue, "HOSTS", {"A4": None, "A5": None})
    stopped = []

    def start(root: Path, config: Path, agent: str, store: str) -> int:
        if agent == "A5":
            raise RuntimeError("synthetic worker startup failure")
        return 123

    monkeypatch.setattr(queue, "start_worker", start)
    monkeypatch.setattr(queue, "stop_worker", lambda root, agent, pid: stopped.append((agent, pid)))
    monkeypatch.setattr(queue, "owned_process_exists", lambda agent, pid: False)
    with pytest.raises(RuntimeError, match="startup"):
        await queue.with_workers(args)
    assert stopped == [("A4", 123)]
    assert (args.output / "worker-starts/A4.json").exists()
    receipt = json.loads((args.output / "worker-shutdown.json").read_text())
    assert receipt["verified_exited"] and not receipt["errors"]
