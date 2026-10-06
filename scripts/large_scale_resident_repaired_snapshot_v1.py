"""Read-only, source-aware projection across the exact resident Quote repair.

Keep confounded originals visible and separate from their authorized reruns.
No evidence body, prompt, gold, ranking, pruning or semantic retry is exported.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_quote_repair_ledger_v1 as reviewer
import large_scale_resident_snapshot_v1 as resident
from cost_guidance_cell_analysis_v1 import analyze, model_evidence_audit, quote_decision_audit
from large_scale_graph_audit_v1 import graph_audit

from infra_joint.control.provenance import provenance_sha256

REPAIR_SHA256 = "9dd761f7d4022ae262ada59e8f810b4ab2cac7106e50f0817093916861977198"
DRAIN_SHA256 = "af992c6734ea5823c4cc334ca8a01745b0ea0a3abdfc7ee2aeef3637f7e3c4e7"


def validate_attempt_source(attempt: dict[str, Any], original_runs: set[str]) -> str:
    original = attempt["run_id"] in original_runs
    expected = resident.EXECUTION_FREEZE_SHA256 if original else REPAIR_SHA256
    if attempt["execution_sha256"] != expected:
        raise RuntimeError("attempt execution does not match its durable source boundary")
    if original and attempt["attempt_index"] != 1:
        raise RuntimeError("original resident prefix cannot contain an invented retry")
    return "original-execution-001" if original else "quote-integrity-repair-002"


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    before = (root / "phase1-attempts.jsonl").read_bytes()
    records = [json.loads(line) for line in before.splitlines()]
    drain = root / "analysis/resident-quote-hash-drain-completed-001.json"
    if resident.sha256(drain) != DRAIN_SHA256:
        raise RuntimeError("source boundary requires the original safe-drain attestation")
    original_records = [r for r in records if r["sequence"] <= 170]
    original_runs = {r["run_id"] for r in original_records if r["event"] == "reserved"}
    if (len(original_runs) != 85 or len(original_records) != 171
            or original_records[-1]["sha256"]
            != "78f0fbf3ee20b2039e69b5f4dce66825e04e508c12633cd99aa8afbe20e6e7f1"):
        raise RuntimeError("original settled prefix changed")
    freezes = {}
    for index, expected in ((1, resident.EXECUTION_FREEZE_SHA256), (2, REPAIR_SHA256)):
        freeze = json.loads((root / f"execution-freeze-{index:03d}.json").read_text())
        app = root / ("app" if index == 1 else "app-quote-integrity-repair-002")
        if provenance_sha256(freeze) != expected or any(
                resident.sha256(app / name) != digest
                for name, digest in freeze["source_sha256"].items()):
            raise RuntimeError("immutable execution source/freeze changed")
        freezes[str(index)] = expected
    selection = predecessor / "preparation/task-freeze-002"
    if (resident.sha256(selection / "manifest.json") != resident.TASK_FREEZE_SHA256
            or resident.sha256(predecessor / "phase1-attempts.jsonl")
            != resident.OLD_JOURNAL_SHA256):
        raise RuntimeError("task set or closed predecessor changed")
    value = resident.base.snapshot(root, selection_root=selection,
                                   ledger_class=reviewer.QuoteRepairAttemptLedger,
                                   admission_reader=reviewer.effective_admission)
    if value["scheduled_cells"] != 168:
        raise RuntimeError("projection cannot extend the frozen schedule")
    for row in value["rows"]:
        for attempt in row["attempts"]:
            attempt["execution_source_boundary"] = validate_attempt_source(attempt, original_runs)
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            trace = directory / "runs" / attempt["run_id"] / "trace.jsonl"
            with trace.open(encoding="utf-8") as stream:
                events = [json.loads(line) for line in stream]
            attempt.update(trace_file_sha256=resident.sha256(trace),
                           graph_audit=graph_audit(events),
                           quote_decision_audit=quote_decision_audit(events),
                           model_evidence_path=model_evidence_audit(events),
                           estimated_vs_observed=analyze(events)["estimated_vs_observed"])
            protocols = [e["payload"] for e in events
                         if e["event_type"] == "logical.cost_quote.run.end"]
            if len(protocols) > 1:
                raise RuntimeError("ambiguous Quote lifecycle summary")
            # The original helper predates rejected states. Preserve its output,
            # but expose the actual protocol summary rather than infer pending.
            attempt["actual_quote_protocol_summary"] = protocols[0] if protocols else None
            sidecar = root / reviewer.DIRECTORY / (attempt["run_id"] + ".json")
            attempt["quote_integrity_review_file_sha256"] = (
                resident.sha256(sidecar) if sidecar.exists() else None)
            attempt["comparative_sample_eligible"] = attempt["disposition"] == "valid"
            residency = directory / "private/residency-validation.json"
            attempt["residency_validation"] = json.loads(residency.read_text())
            attempt["residency_validation_sha256"] = resident.sha256(residency)
            admission = json.loads((directory / "admission.json").read_text())
            attempt["actual_recipient_contexts_audited"] = len(
                admission.get("api_audit", {}).get("contexts", []))
    if (root / "phase1-attempts.jsonl").read_bytes() != before:
        raise RuntimeError("journal advanced during read-only projection; do not emit stale output")
    value.update(version="resident-source-aware-quote-repair-projection-v1",
                 captured_utc=datetime.now(UTC).isoformat(),
                 journal_sha256=resident.sha256(root / "phase1-attempts.jsonl"),
                 execution_freezes=freezes, predecessor_admissions_kept_separate=42,
                 old_and_new_results_pooled=False, all_nominal_private_evidence_audited=False,
                 phase2_authorized=False, logical_or_physical_execution_modified=False,
                 collector_source_sha256={str(Path(p).name): resident.sha256(Path(p)) for p in (
                     __file__, reviewer.__file__, resident.__file__, resident.base.__file__,
                     sys.modules[graph_audit.__module__].__file__,
                     sys.modules[analyze.__module__].__file__)})
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("read-only evidence projection stays in its remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: item for key, item in value.items() if key != "rows"}))
