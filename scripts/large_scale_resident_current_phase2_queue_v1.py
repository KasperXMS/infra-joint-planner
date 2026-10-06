"""Current-admission held-out controller, preserving the exact atomic executor.

Preparation only until actual completed audits and frozen pruning exist. This
separate source does not mutate a historical controller or the live PhaseI queue.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_current_phase2_gate_v1 as gate
import large_scale_resident_phase2_queue_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease
from infra_joint.experiments.large_scale_protocol import ScheduledCell, schedule_sha256

frozen = previous.frozen
cells_from_gate = previous.cells_from_gate
execute_cell = previous.execute_cell


def verified_gate(path: Path, inputs: dict[str, Path]) -> dict[str, Any]:
    if path.is_symlink() or path.resolve().parent != frozen.ROOT / "analysis":
        raise RuntimeError("PhaseII requires an owned frozen actual evidence gate")
    saved = json.loads(path.read_text())
    if saved != gate.verify_gate_inputs(inputs):
        raise RuntimeError("saved PhaseII gate differs from actual audit evidence")
    return saved


def source_bindings() -> dict[str, str]:
    sources = gate.evidence.sources
    reviewer = sources.reviewer
    paths = (
        __file__, previous.__file__, gate.__file__, gate.core.__file__, gate.evidence.__file__,
        sources.__file__, sources.previous.__file__, sources.previous.previous.__file__,
        sources.previous.previous.core.__file__, reviewer.__file__, reviewer.previous.__file__,
        reviewer.previous.previous.__file__, reviewer.methods.__file__, reviewer.records.__file__,
        reviewer.policy.__file__, gate.evidence.private.__file__,
        sys.modules[gate.evidence.resolved_membership.__module__].__file__,
        sys.modules[gate.evidence.private.scan_store.__module__].__file__,
        previous.method_contract.__file__, previous.quote.__file__,
        previous.quote.reviewer.__file__, frozen.__file__,
    )
    if any(p is None for p in paths):
        raise RuntimeError("current controller requires actual file-backed source dependencies")
    bindings: dict[str, str] = {}
    for p in paths:
        if p is not None:
            path = Path(p)
            digest = frozen.sha256(path)
            if path.name in bindings and bindings[path.name] != digest:
                raise RuntimeError("ambiguous source basename cannot bind a control freeze")
            bindings[path.name] = digest
    return bindings


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
        "version": "resident-current-admission-phase2-control-v1", "gate_path": str(path),
        "gate_file_sha256": gate.digest(path),
        "gate_input_paths": {k: str(p) for k, p in inputs.items()},
        "execution_freeze_sha256": execution,
        "atomic_execution_entrypoint": str(frozen.APP / "scripts/large_scale_resident_queue_v1.py"),
        "phase1_journal_sha256": value["journal_sha256"],
        "phase2_schedule_sha256": schedule_sha256(cells), "methods": value["methods"],
        "nominal_cells": len(cells), "prior_substantive_cells": 42,
        "phase1_substantive_cells": 168, "planned_cumulative_substantive_cells": 210 + len(cells),
        "global_cap": frozen.GLOBAL_CAP, "pricing_path": str(prices),
        "pricing_sha256": pricing_sha, "source_sha256": source_bindings(),
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


def run(path: Path) -> None:
    frozen.require_remote()
    gate.evidence.private.assert_inactive(frozen.ROOT)
    saved, cells = checked_control(path)
    with QueueLease(frozen.ROOT / "queue-lease.json"):
        ledger = previous.quote.reviewer.QuoteRepairAttemptLedger(
            frozen.ROOT / "phase2-attempts.jsonl", tuple(c.cell_id for c in cells),
            schedule_sha256(cells))
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
