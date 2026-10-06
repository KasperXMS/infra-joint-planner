"""Explicit reviewed held-out projection retaining every original rejection.

No Agent inputs, body export, inferred missing telemetry or historical rewriting.
The original collector remains archived unchanged. This view requires a frozen,
source-bound reviewed control and revalidates all exact sidecars on every read.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_resident_phase2_reviewed_queue_v1 as queue
import large_scale_resident_phase2_snapshot_v1 as previous


def collect(root: Path = queue.frozen.ROOT, *, control_path: Path) -> dict[str, Any]:
    if (control_path.is_symlink() or control_path.resolve().parent != root
            or not control_path.name.startswith("phase2-reviewed-control-freeze-")):
        raise RuntimeError("owned reviewed snapshot control required")
    reviewed = json.loads(control_path.read_text())
    parent_path = Path(reviewed["parent_control_path"])
    parent, gate = previous.checked_inputs(root, parent_path)
    if (reviewed["parent_control_file_sha256"] != queue.legacy.sha256(parent_path)
            or reviewed["execution_freeze_sha256"] != parent["execution_freeze_sha256"]
            or reviewed["phase2_schedule_sha256"] != gate["phase2_schedule_sha256"]
            or reviewed["nominal_cells"] != parent["nominal_cells"]
            or reviewed["source_sha256"] != {Path(p).name: queue.legacy.sha256(Path(p))
                for p in (queue.__file__, queue.legacy.__file__, queue.bindings.__file__)}
            or reviewed["sidecars"] != {p.name: queue.legacy.sha256(p)
                for p in sorted((root / queue.DIRECTORY).glob("*.json"))}):
        raise RuntimeError("reviewed projection source/evidence/control drift")
    journal = root / "phase2-attempts.jsonl"
    if not journal.is_file():
        raise RuntimeError("collector cannot initialize a missing journal")
    before = journal.read_bytes()
    ledger = queue.ReviewedAttemptLedger(journal, tuple(c["cell_id"] for c in gate["schedule"]),
                                         gate["phase2_schedule_sha256"])
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
            record = previous.settled(root, raw, parent["execution_freeze_sha256"])
            record.update(original_disposition=raw.disposition, original_reason=raw.reason,
                          original_receipt_sha256=raw.receipt_sha256,
                          disposition=attempt.disposition, reason=attempt.reason,
                          receipt_sha256=attempt.receipt_sha256,
                          effective_admission=queue.effective_admission(root, attempt),
                          adjudicated=raw != attempt)
            records.append(record)
        rows.append({"condition": condition, "attempts": records,
                     "pending_run_ids": [a.run_id for a in attempts if a.disposition is None]})
    if journal.read_bytes() != before:
        raise RuntimeError("journal advanced; repeat only read-only collection")
    return {"version": "resident-phase2-exact-reviewed-settled-projection-v1",
            "captured_utc": datetime.now(UTC).isoformat(),
            "control_file_sha256": queue.legacy.sha256(control_path),
            "parent_control_file_sha256": queue.legacy.sha256(parent_path),
            "journal_sha256": queue.legacy.sha256(journal),
            "phase2_schedule_sha256": gate["phase2_schedule_sha256"],
            "execution_freeze_sha256": parent["execution_freeze_sha256"],
            "scheduled_cells": len(rows), "admitted_cells": len(ledger.completed_cells),
            "attempt_count": len(effective), "pending_count": len(ledger.pending),
            "confounded_attempts": sum(a.disposition == "confounder" for a in effective),
            "original_confounded_attempts": sum(a.disposition == "confounder"
                                                 for a in original.values()),
            "operational_excluded_attempts": sum(a.disposition == "operational_excluded"
                                                  for a in effective),
            "phase2_complete": len(ledger.completed_cells) == len(rows),
            "collector_source_sha256": queue.legacy.sha256(Path(__file__)),
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
        raise RuntimeError("reviewed projection stays in owned remote analysis namespace")
    value = collect(control_path=args.control_freeze)
    queue.frozen.write_new(args.output, value)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
