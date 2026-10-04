"""One remote, serial, append-only Phase I queue over the frozen native substrate.

No outcome-based pruning, prompt tuning, retries inside a run or new scheduling
policy. Individual attempts have independent processes, stores and tc receipts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from large_scale_admission_v1 import admit
from large_scale_execution_v1 import (
    ROOT,
    TASK_FREEZE_SHA256,
    cell_config,
    execute_once,
    frozen,
    require_remote,
)
from large_scale_repair_freeze_v1 import (
    environment_fingerprint,
    original_attempt,
    prepare,
    prepare_prices,
    verified_prices,
)
from predecision_crossbenchmark_v1 import audit_artifact_persistence
from run_predecision_matrix_v1 import HOSTS, remote_python, start_worker, stop_worker, write_new
from run_sdk_native_infra_cell_with_tc_v1_3 import DEFAULT_ENDPOINTS
from run_sdk_native_infra_cell_with_tc_v1_3 import run as run_shaped

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import AttemptLedger, QueueLease
from infra_joint.experiments.large_scale_protocol import (
    ScheduledCell,
    SelectedTask,
    phase_one_schedule,
    schedule_sha256,
)
from infra_joint.workflow.trace import WorkflowTraceRecorder

SELECTION = ROOT / "preparation/task-freeze-002"
HISTORY = Path("/home/super/xiaoming/cost-guidance-history-v0-00ff980/freeze-001")
RULES = Path("/home/super/xiaoming/cost-guidance-exploration-v1-bde-17b8bf0"
             "/rules/rules-freeze.json")


def schedule() -> tuple[ScheduledCell, ...]:
    if frozen._sha256(SELECTION / "manifest.json") != TASK_FREEZE_SHA256:
        raise RuntimeError("frozen 18-task manifest drift")
    manifest = json.loads((SELECTION / "manifest.json").read_text())
    tasks = tuple(SelectedTask(row["family"], row["source_task_id"], row["position"])
                  for row in manifest["tasks"])
    cells = phase_one_schedule(tasks, e_history_tasks=tuple(
        (family, source) for family, source in manifest["e_history_task_identities"]),
        seed=manifest["schedule_seed"])
    expected = json.loads((SELECTION / "phase1-schedule.json").read_text())
    if (schedule_sha256(cells) != manifest["phase1_schedule_sha256"]
            or [cell.cell_id for cell in cells] != [row["cell_id"] for row in expected]):
        raise RuntimeError("deterministic Phase I schedule drift")
    return cells


def execution_freeze() -> dict[str, Any]:
    app = Path(__file__).resolve().parents[1]
    paths = [path for folder in ("src", "scripts", "configs")
             for path in (app / folder).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"]
    hashes = {str(path.relative_to(app)): frozen._sha256(path) for path in sorted(paths)}
    _, pricing_sha256 = verified_prices(ROOT, app)
    for path, digest in ((HISTORY / "cost-history.json", frozen.HISTORY_SHA256),
                         (HISTORY / "manifest.json", frozen.HISTORY_MANIFEST_SHA256)):
        if frozen._sha256(path) != digest:
            raise RuntimeError("shared pricing/history freeze drift")
    manifest = json.loads((SELECTION / "manifest.json").read_text())
    if frozen._sha256(RULES) != manifest["e_rules_manifest_sha256"]:
        raise RuntimeError("shared E rules freeze drift")
    return {"version": "large-scale-execution-repair-v1", "commit_sha": frozen._revision(),
            "source_sha256": hashes, "task_selection_sha256": TASK_FREEZE_SHA256,
            "pricing_sha256": pricing_sha256,
            "history_sha256": frozen.HISTORY_SHA256,
            "history_manifest_sha256": frozen.HISTORY_MANIFEST_SHA256,
            "rules_sha256": manifest["e_rules_manifest_sha256"],
            "phase1_schedule_sha256": schedule_sha256(schedule()),
            "fixed_verifier": "qwen3.8-max", "Phase_I_cells": 168,
            "formal_runs_at_execution_freeze": 0,
            "repair_lineage": original_attempt(ROOT),
            "environment_repair": environment_fingerprint(ROOT)}


def verify_execution_freeze(path: Path | None = None) -> str:
    path = path or ROOT / "execution-freeze-002.json"
    if path.resolve().parent != ROOT.resolve() or path.name != "execution-freeze-002.json":
        raise RuntimeError("repaired execution freeze must have a new owned namespace")
    saved = json.loads(path.read_text())
    if saved != execution_freeze():
        raise RuntimeError("execution/config/model/protocol drift; queue stopped")
    return provenance_sha256(saved)


async def worker_states(config: dict[str, Any], *, clean: bool) -> dict[str, Any]:
    states = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for agent, url in config["worker_urls"].items():
            for attempt in range(60 if clean else 1):
                try:
                    response = await client.get(url + "/state")
                    response.raise_for_status()
                    state = response.json()
                    if state["agent_id"] != agent or (clean and state["artifacts"]):
                        raise RuntimeError("fresh Worker identity/store mismatch")
                    states[agent] = state
                    break
                except httpx.HTTPError:
                    if attempt == (59 if clean else 0):
                        raise
                    # Startup readiness polling only; never repeats an Agent action.
                    await asyncio.sleep(1)
    return states


def owned_process_exists(agent: str, pid: int) -> bool:
    code = (
        "from pathlib import Path; "
        f"p=Path('/proc/{pid}/cmdline'); "
        "value=p.read_bytes().decode() if p.exists() else ''; "
        f"assert not value or {ROOT.name!r} in value, 'PID ownership changed'; "
        "print(int(bool(value)))"
    )
    if HOSTS[agent] is None:
        output = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                text=True, check=True).stdout
    else:
        output = remote_python(HOSTS[agent], code)
    return output.strip() == "1"


async def with_workers(args: argparse.Namespace) -> None:
    config = frozen._yaml(args.config)
    pids: dict[str, int] = {}
    try:
        for agent in HOSTS:
            worker_config = ROOT / "worker-configs" / f"{config['run_id']}-{agent}.yaml"
            prepare(args.config, agent, worker_config)
            pids[agent] = start_worker(
                ROOT, worker_config, agent, config["fresh_worker_stores"][agent])
            # Persist immediately: a later startup error cannot hide already-owned PIDs.
            write_new(args.output / "worker-starts" / f"{agent}.json", {"pid": pids[agent]})
        write_new(args.output / "worker-pids.json", pids)
        write_new(args.output / "private/worker-state-before.json",
                  await worker_states(config, clean=True))
        try:
            await execute_once(args)
        finally:
            write_new(args.output / "private/worker-state-after.json",
                      await worker_states(config, clean=False))
        result = args.output / "runs" / config["run_id"] / "result.json"
        if result.exists():
            write_new(args.output / "private/artifact-persistence.json",
                      audit_artifact_persistence(args.output, config["run_id"]))
    finally:
        errors = []
        exited = {}
        for agent, pid in pids.items():
            try:
                stop_worker(ROOT, agent, pid)
                for _ in range(30):
                    if not owned_process_exists(agent, pid):
                        exited[agent] = True
                        break
                    await asyncio.sleep(1)
                else:
                    errors.append(f"{agent}:owned_process_still_live")
            except Exception as error:
                # Full stderr remains in the private process log, not logical feedback.
                errors.append(f"{agent}:{type(error).__name__}")
        write_new(args.output / "worker-shutdown.json", {
            "errors": errors, "verified_exited": len(exited) == len(pids),
            "owned_processes": pids, "exited": exited,
        })
        if errors:
            raise RuntimeError("owned Worker shutdown incomplete; queue must stop")


def fallback_failure(args: argparse.Namespace, error: BaseException) -> None:
    """Persist failures before the benchmark runner, never fabricate evaluator output."""
    config = frozen._yaml(args.config)
    path = args.output / "runs" / config["run_id"] / "result.json"
    write_new(args.output / "attempt-error.json", {
        "exception_type": type(error).__name__, "message": str(error),
        "before_runner": not path.exists(),
    })
    if path.exists():
        return
    record = {"run_id": config["run_id"], "execution_completed": False,
              "final_answer": None, "evaluation": None, "attempt_before_runner": True,
              "failure": {"code": "attempt_prerun_failed", "exception_type": type(error).__name__,
                          "message": str(error)}}
    write_new(path, record)
    recorder = WorkflowTraceRecorder(config["run_id"], JsonlTraceWriter(
        path.with_name("trace.jsonl")))
    recorder.emit("run.start", {"attempt_before_runner": True})
    recorder.emit("run.failed", {"failure": record["failure"]})


async def attempt(args: argparse.Namespace) -> None:
    require_remote(args.deployment_root)
    try:
        verify_execution_freeze(args.execution_freeze)
        await run_shaped(args, execute_cell=with_workers)
    except BaseException as error:
        fallback_failure(args, error)
        raise


def run_queue(execution_freeze_path: Path | None = None) -> None:
    require_remote(ROOT)
    frozen.validate_runtime_import_root()
    cells = schedule()
    freeze_hash = verify_execution_freeze(execution_freeze_path)
    prices_path, _ = verified_prices(ROOT, Path(__file__).resolve().parents[1])
    with QueueLease(ROOT / "queue-lease.json"):
        ledger = AttemptLedger(ROOT / "phase1-attempts.jsonl",
                               tuple(cell.cell_id for cell in cells), schedule_sha256(cells))
        # Even the existing same-PID lease/reservation cannot be treated as a job.
        if ledger.pending:
            raise RuntimeError("pending attempt must be reconciled against actual process/evidence")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            verify_execution_freeze(execution_freeze_path)
            index = 1 + sum(item.cell_id == cell.cell_id for item in ledger.attempts)
            run_id = f"{ROOT.name}-{cell.cell_id}-attempt{index}"
            directory = ROOT / "evidence" / cell.cell_id / f"attempt{index}"
            # Reservation is durable BEFORE any Worker/model/tc launch.
            ledger.reserve(cell.cell_id, run_id, freeze_hash)
            directory.mkdir(parents=True, exist_ok=False)
            config = cell_config(cell, run_id, frozen.protocol())
            config_path = ROOT / "cell-configs" / f"{run_id}.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            with (directory / "console.log").open("x", encoding="utf-8") as log:
                process = subprocess.Popen([
                    sys.executable, str(Path(__file__).resolve()), "--attempt",
                    "--config", str(config_path), "--output", str(directory),
                    "--execution-freeze", str(execution_freeze_path or
                                              ROOT / "execution-freeze-002.json"),
                ], stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ))
                write_new(directory / "process.json", {"pid": process.pid, "run_id": run_id})
                returncode = process.wait()
            write_new(directory / "process-exit.json", {
                "pid": process.pid, "returncode": returncode})
            try:
                receipt = admit(directory, config, prices_path)
            except Exception as error:
                receipt = {"disposition": "confounder",
                           "reason": "admission_unverifiable",
                           "problems": [type(error).__name__]}
            if returncode and receipt["disposition"] == "valid":
                receipt["disposition"], receipt["reason"] = "confounder", "wrapper_execution_error"
            write_new(directory / "admission.json", receipt)
            ledger.settle(run_id, receipt["disposition"], receipt["reason"],
                          provenance_sha256(receipt))
            if receipt["disposition"] == "operational_excluded":
                # Do not execute the next cell or silently repeat in this process.
                # A subsequent explicit queue continuation may reserve the one
                # identical replacement after availability/cleanup reconciliation.
                raise RuntimeError("operational attempt excluded; reconcile before one replacement")
            if receipt["disposition"] == "confounder":
                raise RuntimeError("unresolved attempt confounder; audit before continuing")
        write_new(ROOT / "phase1-queue-completed.json", {
            "schedule_sha256": schedule_sha256(cells), "completed_cells": ledger.completed_cells,
            "attempt_count": len(ledger.attempts), "pruning_authorized": False,
            "next_required": "comprehensive Phase I audit before method pruning",
        })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    modes.add_argument("--attempt", action="store_true")
    modes.add_argument("--prepare-repair", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execution-freeze", type=Path,
                        default=ROOT / "execution-freeze-002.json")
    value = parser.parse_args()
    value.deployment_root = ROOT
    value.endpoint_config = DEFAULT_ENDPOINTS
    value.cost_history = HISTORY / "cost-history.json"
    value.history_manifest = HISTORY / "manifest.json"
    value.rules_manifest = RULES
    value.api_key_file = Path("/home/super/xiaoming/blind_baseline_6task_v1/api_key.txt")
    if value.attempt and (value.config is None or value.output is None):
        parser.error("individual attempt requires config and fresh evidence directory")
    return value


if __name__ == "__main__":
    arguments = parse_args()
    require_remote(ROOT)
    if arguments.freeze:
        if arguments.execution_freeze != ROOT / "execution-freeze-002.json":
            raise RuntimeError("do not overwrite original execution freeze")
        write_new(arguments.execution_freeze, execution_freeze())
    elif arguments.prepare_repair:
        prepare_prices(ROOT, Path(__file__).resolve().parents[1])
    elif arguments.queue:
        run_queue(arguments.execution_freeze)
    else:
        asyncio.run(attempt(arguments))
