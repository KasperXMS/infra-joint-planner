"""Offline held-out telemetry projection; never imported by the execution app.

Reads settled receipts only. No private gold/support scan, new Agent calls,
method selection, historical mutation or inference about missing measurements.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_resident_current_phase2_queue_v1 as queue
import large_scale_snapshot_v1 as base
from large_scale_graph_audit_v1 import graph_audit

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import AttemptLedger

ROOT = queue.frozen.ROOT


def original_admission(root: Path, attempt: Any) -> dict[str, Any]:
    path = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value: dict[str, Any] = json.loads((path / "admission.json").read_text())
    if (value["disposition"] != attempt.disposition
            or provenance_sha256(value) != attempt.receipt_sha256):
        raise RuntimeError("held-out original admission/settlement drift")
    return value


def checked_inputs(root: Path, control_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if (control_path.is_symlink() or control_path.resolve().parent != root.resolve()
            or not control_path.name.startswith("phase2-control-freeze-")):
        raise RuntimeError("owned existing held-out control required")
    control = json.loads(control_path.read_text())
    gate_path = Path(control["gate_path"])
    if (gate_path.is_symlink() or gate_path.resolve().parent != root.resolve() / "analysis"
            or queue.frozen.sha256(gate_path) != control["gate_file_sha256"]
            or queue.frozen.sha256(root / "phase1-attempts.jsonl")
            != control["phase1_journal_sha256"]
            or queue.source_bindings() != control["source_sha256"]):
        raise RuntimeError("frozen held-out gate/source/PhaseI drift")
    gate = json.loads(gate_path.read_text())
    queue.cells_from_gate(gate)
    if (gate["phase2_schedule_sha256"] != control["phase2_schedule_sha256"]
            or gate["phase2_execution_sha256"] != control["execution_freeze_sha256"]
            or gate["methods"] != control["methods"]
            or gate["phase2_cells"] != control["nominal_cells"]):
        raise RuntimeError("held-out control/schedule mismatch")
    return control, gate


def settled(root: Path, attempt: Any, execution_sha256: str) -> dict[str, Any]:
    if attempt.execution_sha256 != execution_sha256:
        raise RuntimeError("different atomic source cannot fill held-out schedule")
    row = base.settled_attempt(root, attempt.cell_id, attempt,
                               admission_reader=original_admission)
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    trace = directory / "runs" / attempt.run_id / "trace.jsonl"
    events = JsonlTraceWriter(trace).read_all()
    admission = original_admission(root, attempt)
    shutdown_path = directory / "worker-shutdown.json"
    residency_path = directory / "private/residency-validation.json"
    row.update(
        trace_file_sha256=queue.frozen.sha256(trace), graph_audit=graph_audit(events),
        actual_recipient_contexts_audited=len(admission.get("api_audit", {}).get("contexts", [])),
        worker_shutdown_verified=json.loads(shutdown_path.read_text()).get("verified_exited")
        if shutdown_path.exists() else None,
        residency_validation=json.loads(residency_path.read_text())
        if residency_path.exists() else None,
    )
    return row


def collect(root: Path = ROOT, *, control_path: Path | None = None) -> dict[str, Any]:
    path = control_path or root / "phase2-control-freeze-001.json"
    control, gate = checked_inputs(root, path)
    journal = root / "phase2-attempts.jsonl"
    if not journal.is_file():
        raise RuntimeError("read-only collector must not initialize a missing journal")
    before = journal.read_bytes()
    cells = tuple(row["cell_id"] for row in gate["schedule"])
    ledger = AttemptLedger(journal, cells, gate["phase2_schedule_sha256"])
    # Future repairs/replacements need an independently audited admission view.
    # Never silently relabel original evidence through the simple initial view.
    with journal.open(encoding="utf-8") as stream:
        if any(json.loads(line)["event"] not in {"freeze", "reserved", "settled"}
               for line in stream):
            raise RuntimeError("new held-out adjudication requires source-bound collector review")
    rows: list[dict[str, Any]] = []
    for cell in gate["schedule"]:
        attempts = [a for a in ledger.attempts if a.cell_id == cell["cell_id"]]
        rows.append({
            "condition": cell,
            "attempts": [settled(root, a, control["execution_freeze_sha256"])
                         for a in attempts if a.disposition is not None],
            "pending_run_ids": [a.run_id for a in attempts if a.disposition is None],
        })
    if journal.read_bytes() != before:
        raise RuntimeError("journal advanced; repeat only read-only collection")
    return {
        "version": "resident-phase2-original-settled-projection-v1",
        "captured_utc": datetime.now(UTC).isoformat(),
        "control_file_sha256": queue.frozen.sha256(path),
        "journal_sha256": queue.frozen.sha256(journal),
        "phase2_schedule_sha256": gate["phase2_schedule_sha256"],
        "execution_freeze_sha256": control["execution_freeze_sha256"],
        "scheduled_cells": len(cells), "admitted_cells": len(ledger.completed_cells),
        "attempt_count": len(ledger.attempts), "pending_count": len(ledger.pending),
        "confounded_attempts": sum(a.disposition == "confounder" for a in ledger.attempts),
        "operational_excluded_attempts": sum(a.disposition == "operational_excluded"
                                            for a in ledger.attempts),
        "phase2_complete": len(ledger.completed_cells) == len(cells),
        "collector_source_sha256": queue.frozen.sha256(Path(__file__)),
        "private_semantic_audit_complete": False, "goal_complete": False,
        "old_and_new_results_pooled": False, "score_aggregation": "not performed",
        "source_payload_exported": False, "planner_or_model_calls": 0, "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("projection stays in the owned remote analysis namespace")
    value = collect()
    queue.frozen.write_new(args.output, value)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
