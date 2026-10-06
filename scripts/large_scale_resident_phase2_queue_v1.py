"""Evidence-gated held-out queue, reusing the exact execution004 atomic substrate.

No survivor choice, prompt tuning, new policy or historical queue mutation.
All real runs require a completed PhaseI audit plus frozen pruning/schedule.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import large_scale_resident_E_query_phase2_gate_v1 as gate
import large_scale_resident_E_query_queue_v1 as method_contract
import large_scale_resident_queue_v1 as frozen
import large_scale_resident_quote_repair_queue_v1 as quote
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import QueueLease
from infra_joint.experiments.large_scale_protocol import (
    Family,
    Method,
    Network,
    Planner,
    ScheduledCell,
    SelectedTask,
    schedule_sha256,
)


def verified_gate(path: Path, inputs: dict[str, Path]) -> dict[str, Any]:
    if path.is_symlink() or path.resolve().parent != frozen.ROOT / "analysis":
        raise RuntimeError("PhaseII requires an owned frozen actual evidence gate")
    saved = json.loads(path.read_text())
    expected = gate.verify_gate_inputs(inputs)
    if saved != expected:
        raise RuntimeError("saved PhaseII gate differs from actual audit evidence")
    return saved


def cells_from_gate(value: dict[str, Any]) -> tuple[ScheduledCell, ...]:
    cells = tuple(ScheduledCell(
        2, SelectedTask(cast(Family, r["task"]["family"]), r["task"]["source_task_id"],
                        r["task"]["position"]),
        cast(Planner, r["planner"]), cast(Network, r["network"]), cast(Method, r["method"]),
        r["round_index"],
    ) for r in value["schedule"])
    if (any(r["phase"] != 2 or c.task.position not in range(3, 7)
            or r["cell_id"] != c.cell_id for r, c in zip(value["schedule"], cells, strict=True))
            or schedule_sha256(cells) != value["phase2_schedule_sha256"]
            or len(cells) != value["phase2_cells"]
            or any(c.method not in value["methods"] for c in cells)):
        raise RuntimeError("held-out schedule changed after preregistration")
    return cells


def control_value(path: Path, inputs: dict[str, Path]) -> dict[str, Any]:
    frozen.require_remote()
    if frozen.APP.name != frozen.E_QUERY_APP_NAME:
        raise RuntimeError("PhaseII must reuse actual latest execution004, not an older app")
    value = verified_gate(path, inputs)
    cells = cells_from_gate(value)
    execution = frozen.verify_freeze()
    if execution != value["phase2_execution_sha256"]:
        raise RuntimeError("PhaseII cannot replace the frozen resident execution contract")
    prices, pricing_sha = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    return {
        "version": "resident-phase2-control-v1", "gate_path": str(path),
        "gate_file_sha256": gate.digest(path),
        "gate_input_paths": {k: str(p) for k, p in inputs.items()},
        "execution_freeze_sha256": execution,
        "atomic_execution_entrypoint": str(frozen.APP / "scripts/large_scale_resident_queue_v1.py"),
        "phase1_journal_sha256": value["journal_sha256"],
        "phase2_schedule_sha256": schedule_sha256(cells), "methods": value["methods"],
        "nominal_cells": len(cells), "prior_substantive_cells": 42,
        "phase1_substantive_cells": 168,
        "planned_cumulative_substantive_cells": 210 + len(cells),
        "global_cap": frozen.GLOBAL_CAP, "pricing_path": str(prices),
        "pricing_sha256": pricing_sha,
        "source_sha256": {Path(p).name: frozen.sha256(Path(p)) for p in (
            __file__, gate.__file__, gate.core.__file__, gate.evidence.__file__,
            gate.evidence.sources.__file__, gate.evidence.sources.reviewer.__file__,
            gate.evidence.sources.core.__file__,
            gate.evidence.sources.reviewer.previous.__file__,
            gate.evidence.sources.reviewer.records.__file__,
            method_contract.__file__, quote.__file__, quote.reviewer.__file__, frozen.__file__,
        )},
        "old_and_new_results_pooled": False, "phase1_journal_modified": False,
        "new_scheduling_policy": False, "semantic_tuning": False,
        "ordinary_semantic_retries": False, "resident_inference_required": True,
    }


def freeze_control(path: Path, inputs: dict[str, Path], output: Path) -> None:
    gate.evidence.private.assert_inactive(frozen.ROOT)
    if (output.is_symlink() or output.resolve().parent != frozen.ROOT
            or not output.name.startswith("phase2-control-freeze-")):
        raise RuntimeError("owned append-only PhaseII control receipt required")
    value = control_value(path, inputs)
    gate.evidence.private.assert_inactive(frozen.ROOT)
    frozen.write_new(output, value)


def checked_control(path: Path) -> tuple[dict[str, Any], tuple[ScheduledCell, ...]]:
    if (path.is_symlink() or path.resolve().parent != frozen.ROOT
            or not path.name.startswith("phase2-control-freeze-")):
        raise RuntimeError("owned immutable PhaseII control receipt required")
    saved = json.loads(path.read_text())
    gate_path = Path(saved["gate_path"])
    inputs = {k: Path(p) for k, p in saved["gate_input_paths"].items()}
    if saved != control_value(gate_path, inputs):
        raise RuntimeError("PhaseII execution/control/audit drift")
    return saved, cells_from_gate(json.loads(gate_path.read_text()))


def admission(directory: Path, config: dict[str, Any], prices: Path) -> dict[str, Any]:
    """Preserve the Quote guard without splitting Unicode inside JSON strings.

    Historical controllers remain archived unchanged. Reuse the canonical JSONL
    reader and base admission, retaining the same explicit mutation rejection.
    """
    value = frozen.admit(directory, config, prices)
    trace = directory / "runs" / config["run_id"] / "trace.jsonl"
    events = JsonlTraceWriter(trace).read_all()
    codes = {event["payload"].get("failure_code") for event in events
             if event["event_type"] == "logical.cost_quote.rejected"}
    if "quoted_action_mutated" in codes:
        value = {**value, "disposition": "confounder", "reason": quote.reviewer.REASON,
                 "problems": [*value.get("problems", []), quote.reviewer.REASON]}
    return value


def execute_cell(cell: ScheduledCell, ledger: quote.reviewer.QuoteRepairAttemptLedger,
                 saved: dict[str, Any]) -> None:
    """One actual archived atomic process; no runtime implementation duplicated."""
    root = frozen.ROOT
    if 210 + len(ledger.completed_cells) >= saved["global_cap"]:
        raise RuntimeError("cumulative substantive experiment cap reached")
    index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
    run_id = f"{root.name}-{cell.cell_id}-attempt{index}"
    directory = root / "evidence" / cell.cell_id / f"attempt{index}"
    ledger.reserve(cell.cell_id, run_id, saved["execution_freeze_sha256"])
    directory.mkdir(parents=True, exist_ok=False)
    config = frozen.cell_config(cell, run_id, frozen.reference(), root=root)
    config_path = root / "cell-configs" / (run_id + ".yaml")
    with config_path.open("x", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, sort_keys=False)
    child_env = dict(os.environ, PYTHONPATH=os.pathsep.join(
        str(frozen.APP / folder) for folder in ("src", "scripts")))
    with (directory / "console.log").open("x", encoding="utf-8") as log:
        process = subprocess.Popen([
            sys.executable, saved["atomic_execution_entrypoint"], "--attempt",
            "--config", str(config_path), "--output", str(directory),
        ], stdout=log, stderr=subprocess.STDOUT, env=child_env)
        frozen.write_new(directory / "process.json", {"pid": process.pid, "run_id": run_id})
        returncode = process.wait()
    frozen.write_new(directory / "process-exit.json", {"pid": process.pid,
                                                     "returncode": returncode})
    value: dict[str, Any]
    try:
        value = admission(directory, config, Path(saved["pricing_path"]))
        if cell.method == "E":
            events = JsonlTraceWriter(directory / "runs" / run_id / "trace.jsonl").read_all()
            method_contract.assert_E_tool_isolation(directory, events)
        if json.loads((directory / "private/residency-validation.json").read_text())[
                "passed"] is not True:
            raise RuntimeError("resident model measurement invalid")
    except Exception as error:
        value = {"disposition": "confounder", "reason": "admission_unverifiable",
                 "problems": [type(error).__name__]}
    if returncode and value["disposition"] == "valid":
        value.update(disposition="confounder", reason="wrapper_execution_error")
    frozen.write_new(directory / "admission.json", value)
    ledger.settle(run_id, value["disposition"], value["reason"], provenance_sha256(value))
    if value["disposition"] != "valid":
        raise RuntimeError("PhaseII finding requires actual audit; no hidden retry or next cell")


def run(path: Path) -> None:
    frozen.require_remote()
    gate.evidence.private.assert_inactive(frozen.ROOT)
    saved, cells = checked_control(path)
    with QueueLease(frozen.ROOT / "queue-lease.json"):
        ledger = quote.reviewer.QuoteRepairAttemptLedger(
            frozen.ROOT / "phase2-attempts.jsonl", tuple(c.cell_id for c in cells),
            schedule_sha256(cells))
        # This initial execution004 control contains no PhaseII bug-repair
        # authorization. A future genuine fix needs a separately source-bound
        # control receipt, not a raw hash-only repair event or implicit waiver.
        if ledger.pending or any(a.disposition == "confounder" for a in ledger.attempts):
            raise RuntimeError("unresolved PhaseII finding prohibits continuation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            current, current_cells = checked_control(path)
            if current != saved or current_cells != cells:
                raise RuntimeError("PhaseII immutable preregistration changed")
            execute_cell(cell, ledger, saved)
        frozen.write_new(frozen.ROOT / "phase2-queue-completed.json", {
            "schedule_sha256": schedule_sha256(cells), "completed_cells": ledger.completed_cells,
            "attempt_count": len(ledger.attempts), "control_sha256": provenance_sha256(saved),
            "next_required": "complete PhaseII private/failure/recipient/adoption and Q1-Q10 audit",
            "goal_complete": False,
        })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    parser.add_argument("--gate", type=Path)
    for name in ("snapshot", "private", "audit", "pruning"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.freeze:
        if args.gate is None or any(getattr(args, n) is None for n in (
                "snapshot", "private", "audit", "pruning")):
            parser.error("freeze requires the actual completed gate and its four input files")
        freeze_control(args.gate, {n: getattr(args, n) for n in (
            "snapshot", "private", "audit", "pruning")}, args.control_freeze)
    else:
        run(args.control_freeze)
