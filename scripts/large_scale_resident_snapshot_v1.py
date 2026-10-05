"""Independent offline projection of the resident block; never an Agent input.

Deploy outside the frozen execution app. Preserves old namespace/evidence,
unknown measurements, per-cell results and no-pruning-before-full-audit policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_snapshot_v1 as base
from cost_guidance_cell_analysis_v1 import (
    analyze,
    model_evidence_audit,
    quote_decision_audit,
)
from large_scale_graph_audit_v1 import graph_audit

from infra_joint.control.provenance import provenance_sha256

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-resident-v1")
PREDECESSOR = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")
TASK_FREEZE_SHA256 = "25e65b22b452bc164efe61ad895d20e5fcf3c8d407e4e9c7380a204bbec9b3ad"
OLD_JOURNAL_SHA256 = "bddc83d7ef5230d3aca3c440602cea25bfd8be34bea6ceba47c3ce8746c0fb86"
EXECUTION_FREEZE_SHA256 = "4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root: Path = ROOT, predecessor: Path = PREDECESSOR) -> dict[str, Any]:
    selection = predecessor / "preparation/task-freeze-002"
    freeze = json.loads((root / "execution-freeze-001.json").read_text())
    if provenance_sha256(freeze) != EXECUTION_FREEZE_SHA256:
        raise RuntimeError("resident execution freeze drift")
    if (sha256(selection / "manifest.json") != TASK_FREEZE_SHA256
            or freeze["task_selection_sha256"] != TASK_FREEZE_SHA256
            or freeze["old_journal_sha256"] != OLD_JOURNAL_SHA256
            or sha256(predecessor / "phase1-attempts.jsonl") != OLD_JOURNAL_SHA256):
        raise RuntimeError("resident analysis cannot rewrite or mix predecessor evidence/tasks")
    journal = root / "phase1-attempts.jsonl"
    if not journal.exists():
        raise RuntimeError("read-only collector cannot initialize a missing ledger")
    journal_before = journal.read_bytes()
    if list((root / "record-field-adjudications").glob("*.json")):
        from large_scale_resident_record_review_v1 import RecordAttemptLedger, effective_admission

        value = base.snapshot(root, selection_root=selection,
                              ledger_class=RecordAttemptLedger,
                              admission_reader=effective_admission)
    else:
        value = base.snapshot(root, selection_root=selection)
    if (value["scheduled_cells"] != 168
            or freeze["phase1_schedule_sha256"] != json.loads(
                (selection / "manifest.json").read_text())["phase1_schedule_sha256"]):
        raise RuntimeError("resident projection schedule differs from the frozen168 cells")
    for row in value["rows"]:
        for attempt in row["attempts"]:
            if attempt["execution_sha256"] != provenance_sha256(freeze):
                raise RuntimeError("a different execution environment cannot fill this new block")
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            trace = directory / "runs" / attempt["run_id"] / "trace.jsonl"
            events = [json.loads(line) for line in trace.open(encoding="utf-8")]
            attempt["trace_file_sha256"] = sha256(trace)
            attempt["graph_audit"] = graph_audit(events)
            attempt["quote_decision_audit"] = quote_decision_audit(events)
            attempt["model_evidence_path"] = model_evidence_audit(events)
            # Only bounded cost/feature fields, never arbitrary rejection messages,
            # task bodies, prompts, gold, queries or raw recipient context.
            attempt["estimated_vs_observed"] = analyze(events)["estimated_vs_observed"]
            residency = directory / "private/residency-validation.json"
            attempt["residency_validation"] = (
                json.loads(residency.read_text()) if residency.exists() else None)
            attempt["residency_validation_sha256"] = (
                sha256(residency) if residency.exists() else None)
            admission = json.loads((directory / "admission.json").read_text())
            attempt["actual_recipient_contexts_audited"] = len(
                admission.get("api_audit", {}).get("contexts", []))
    if journal.read_bytes() != journal_before:
        raise RuntimeError(
            "journal advanced during projection; repeat only this read-only collection")
    value.update({
        "version": "large-scale-resident-settled-projection-v1",
        "captured_utc": datetime.now(UTC).isoformat(),
        "journal_sha256": hashlib.sha256(journal_before).hexdigest(),
        "execution_freeze_sha256": provenance_sha256(freeze),
        "predecessor_admissions_kept_separate": 42,
        "old_and_new_results_pooled": False,
        "all_nominal_private_evidence_audited": False,
        "phase2_authorized": False,
        "collector_source_sha256": {p.name: sha256(p) for p in (
            Path(__file__), Path(base.__file__),
            Path(sys.modules[graph_audit.__module__].__file__),
            Path(sys.modules[analyze.__module__].__file__))},
        "logical_or_physical_execution_modified": False,
    })
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("new-block evidence projection remains in its4090 namespace")
    value = collect()
    args.output.parent.mkdir(exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: item for key, item in value.items() if key not in {"rows"}},
                     ensure_ascii=False))
