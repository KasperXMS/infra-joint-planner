"""Read-only projection of disjoint exact reviews, preserving every raw finding."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_resident_phase2_field_queue_v1 as queue


def collect(root: Path = queue.frozen.ROOT, *, control_path: Path) -> dict[str, Any]:
    journal = root / "phase2-attempts.jsonl"
    if not journal.is_file():
        raise RuntimeError("collector cannot initialize a missing journal")
    before = journal.read_bytes()
    parent, gate, ledger = queue.projection_inputs(root, control_path)
    original = {a.run_id: a for a in ledger.original_attempts}
    effective = ledger.attempts
    rows = []
    for condition in gate["schedule"]:
        attempts = [a for a in effective if a.cell_id == condition["cell_id"]]
        records = []
        for attempt in attempts:
            if attempt.disposition is None:
                continue
            raw = original[attempt.run_id]
            record = queue.base.settled(root, raw, parent["execution_freeze_sha256"])
            record.update(original_disposition=raw.disposition, original_reason=raw.reason,
                          original_receipt_sha256=raw.receipt_sha256,
                          disposition=attempt.disposition, reason=attempt.reason,
                          receipt_sha256=attempt.receipt_sha256,
                          effective_admission=queue.review.effective_admission(root, attempt),
                          adjudicated=raw != attempt)
            records.append(record)
        rows.append({"condition": condition, "attempts": records,
                     "pending_run_ids": [a.run_id for a in attempts if a.disposition is None]})
    if journal.read_bytes() != before:
        raise RuntimeError("journal advanced; repeat only read-only collection")
    completed = {a.cell_id for a in effective if a.disposition == "valid"}
    pending = sum(a.disposition is None for a in effective)
    return {"version": "resident-phase2-disjoint-exact-reviewed-projection-v1",
            "captured_utc": datetime.now(UTC).isoformat(),
            "control_file_sha256": queue.core.legacy.sha256(control_path),
            "parent_control_file_sha256": queue.core.legacy.sha256(
                Path(json.loads(control_path.read_text())["parent_control_path"])),
            "journal_sha256": queue.core.legacy.sha256(journal),
            "phase2_schedule_sha256": gate["phase2_schedule_sha256"],
            "execution_freeze_sha256": parent["execution_freeze_sha256"],
            "scheduled_cells": len(rows), "admitted_cells": len(completed),
            "attempt_count": len(effective), "pending_count": pending,
            "confounded_attempts": sum(a.disposition == "confounder" for a in effective),
            "original_confounded_attempts": sum(a.disposition == "confounder"
                                                 for a in original.values()),
            "operational_excluded_attempts": sum(a.disposition == "operational_excluded"
                                                  for a in effective),
            "phase2_complete": len(completed) == len(rows),
            "collector_source_sha256": queue.core.legacy.sha256(Path(__file__)),
            "private_semantic_audit_complete": False, "goal_complete": False,
            "old_and_new_results_pooled": False, "score_aggregation": "not performed",
            "source_payload_exported": False, "planner_or_model_calls": 0, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != queue.frozen.ROOT / "analysis"):
        raise RuntimeError("projection stays in owned remote analysis namespace")
    queue.frozen.write_new(args.output, collect(control_path=args.control_freeze))
