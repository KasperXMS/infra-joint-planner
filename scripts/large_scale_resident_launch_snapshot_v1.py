"""Current read-only projection retaining exact zero-execution launch failures.

Historical collectors/receipts remain untouched. Missing residency is permitted
only for a separately source-proved, journal-authorized pre-run failure; it is
never fabricated or counted as an admitted benchmark sample.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_resident_E_query_snapshot_v1 as core
import large_scale_resident_launch_review_v1 as reviewer
from cost_guidance_cell_analysis_v1 import analyze, model_evidence_audit, quote_decision_audit
from large_scale_graph_audit_v1 import graph_audit

from infra_joint.control.provenance import provenance_sha256

resident, EXECUTIONS = core.resident, core.EXECUTIONS


def residency_receipt(root: Path, directory: Path, attempt: Any,
                      ledger: reviewer.ProjectionAttemptLedger) -> dict[str, Any]:
    path = directory / "private/residency-validation.json"
    if attempt.run_id not in ledger.launch_repairs:
        # Keep the original strict missing-receipt behavior for every execution.
        return {"residency_validation": json.loads(path.read_text()),
                "preexecution_launch_repair_file_sha256": None}
    proof = root / reviewer.AUTH_DIRECTORY / (attempt.run_id + ".json")
    reviewer.verify_sidecar(proof, attempt)
    if reviewer.sha256(proof) != ledger.launch_repairs[attempt.run_id] or path.exists():
        raise RuntimeError("zero-execution exception requires its exact original proof")
    return {"residency_validation": None,
            "residency_receipt_scope": "not applicable: proved failure before Worker/model start",
            "preexecution_launch_repair_file_sha256": reviewer.sha256(proof),
            "original_rejection_preserved": True,
            "comparative_sample_eligible": False,
            "preexecution_launch_confounder": True,
            "operational_replacement": False}


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    before = (root / "phase1-attempts.jsonl").read_bytes()
    journal = [json.loads(line) for line in before.splitlines()]
    drain_path = root / "analysis/resident-E-query-contract-drain-completed-001.json"
    drain = json.loads(drain_path.read_text())
    if (resident.sha256(drain_path) != core.DRAIN_SHA256
            or hashlib.sha256(b"".join(before.splitlines(keepends=True)[:262])).hexdigest()
            != drain["journal_file_sha256"]
            or resident.sha256(root / core.reviewer.BUG_PROOF) != core.reviewer.BUG_SHA256):
        raise RuntimeError("exact original safe-drain and defect proofs required")
    epochs = {r["run_id"]: core.epoch_for(r) for r in journal if r["event"] == "reserved"}
    for index, app in enumerate(core.reviewer.APPS, 1):
        freeze = json.loads((root / f"execution-freeze-{index:03d}.json").read_text())
        if provenance_sha256(freeze) != EXECUTIONS[index] or any(
                resident.sha256(root / app / p) != h for p, h in freeze["source_sha256"].items()):
            raise RuntimeError("immutable measured execution freeze/source drift")
    selection = predecessor / "preparation/task-freeze-002"
    if (resident.sha256(selection / "manifest.json") != resident.TASK_FREEZE_SHA256
            or resident.sha256(predecessor / "phase1-attempts.jsonl")
            != resident.OLD_JOURNAL_SHA256):
        raise RuntimeError("original tasks or closed predecessor drift")
    schedule = json.loads((selection / "phase1-schedule.json").read_text())
    manifest = json.loads((selection / "manifest.json").read_text())
    ledger = reviewer.ProjectionAttemptLedger(root / "phase1-attempts.jsonl",
        tuple(c["cell_id"] for c in schedule), manifest["phase1_schedule_sha256"])
    by_run = {a.run_id: a for a in ledger.attempts}
    value = resident.base.snapshot(root, selection_root=selection,
        ledger_class=reviewer.ProjectionAttemptLedger,
        admission_reader=reviewer.effective_admission)
    if value["scheduled_cells"] != 168:
        raise RuntimeError("the original screening schedule cannot be enlarged")
    for row in value["rows"]:
        for attempt in row["attempts"]:
            epoch = epochs[attempt["run_id"]]
            if attempt["execution_sha256"] != EXECUTIONS[epoch]:
                raise RuntimeError("source cannot override its durable reservation")
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            trace = directory / "runs" / attempt["run_id"] / "trace.jsonl"
            events = [json.loads(line) for line in trace.open(encoding="utf-8")]
            attempt.update(execution_source_epoch=epoch, trace_file_sha256=resident.sha256(trace),
                comparative_sample_eligible=attempt["disposition"] == "valid",
                graph_audit=graph_audit(events), model_evidence_path=model_evidence_audit(events),
                quote_decision_audit=quote_decision_audit(events),
                estimated_vs_observed=analyze(events)["estimated_vs_observed"])
            folders = (
                (core.reviewer.DIRECTORY, "E_query_contract_review_file_sha256"),
                (core.reviewer.RECORD_DIRECTORY, "source_bound_record_review_file_sha256"),
                (reviewer.DIRECTORY, "projected_record_review_file_sha256"),
                (reviewer.previous.previous.TIMEOUT_DIRECTORY,
                 "compound_cloud_timeout_review_file_sha256"),
                (reviewer.previous.POLICY_DIRECTORY, "compound_record_policy_review_file_sha256"))
            for folder, key in folders:
                path = root / folder / (attempt["run_id"] + ".json")
                attempt[key] = resident.sha256(path) if path.exists() else None
                if not path.exists():
                    continue
                proof = json.loads(path.read_text())
                attempt["original_rejection_preserved"] = True
                if "projected_record_field_proof" in proof:
                    attempt["confirmed_projected_absent_field_failures"] = len(
                        proof["projected_record_field_proof"])
                if "record_field_proof" in proof:
                    attempt["confirmed_absent_field_failures"] = len(proof["record_field_proof"])
                if "provider_policy_proof" in proof:
                    attempt["confirmed_provider_policy_refusals"] = len(
                        proof["provider_policy_proof"])
            raw = json.loads((directory / "admission.json").read_text())
            attempt["actual_recipient_contexts_audited"] = len(
                raw.get("api_audit", {}).get("contexts", []))
            attempt.update(residency_receipt(root, directory, by_run[attempt["run_id"]], ledger))
            summaries = [e["payload"] for e in events
                         if e["event_type"] == "logical.cost_quote.run.end"]
            if len(summaries) > 1:
                raise RuntimeError("ambiguous actual Quote lifecycle")
            attempt["actual_quote_protocol_summary"] = summaries[0] if summaries else None
    if (root / "phase1-attempts.jsonl").read_bytes() != before:
        raise RuntimeError("journal advanced; never publish a stale projection")
    source_paths = {Path(module.__file__) for name, module in tuple(sys.modules.items())
                    if (name.startswith("large_scale_") or name == "cost_guidance_cell_analysis_v1")
                    and getattr(module, "__file__", None)}
    source_paths.add(Path(__file__))
    if len({p.name for p in source_paths}) != len(source_paths):
        raise RuntimeError("ambiguous collector source identity")
    value.update(version="resident-four-epoch-exact-preexecution-launch-projection-v1",
        captured_utc=datetime.now(UTC).isoformat(), journal_sha256=resident.sha256(
            root / "phase1-attempts.jsonl"),
        execution_freezes={str(k): v for k, v in EXECUTIONS.items()},
        predecessor_admissions_kept_separate=42, old_and_new_results_pooled=False,
        all_nominal_private_evidence_audited=False, phase2_authorized=False,
        logical_or_physical_execution_modified=False,
        preexecution_launch_confounded_attempts=len(ledger.launch_repairs),
        preexecution_launch_repair_authorizations=ledger.launch_repairs,
        collector_source_sha256={p.name: resident.sha256(p) for p in sorted(source_paths)})
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("evidence projection remains in its owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: v for key, v in value.items() if key != "rows"}))
