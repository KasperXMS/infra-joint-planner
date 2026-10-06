"""Read-only four-epoch resident projection, retaining all confounded originals.

No prompt/body/gold export, method ranking, pruning, or execution-side imports.
Historical collectors remain immutable and must not interpret new ledger events.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import large_scale_resident_method_contract_review_v1 as reviewer
import large_scale_resident_snapshot_v1 as resident
from cost_guidance_cell_analysis_v1 import analyze, model_evidence_audit, quote_decision_audit
from large_scale_graph_audit_v1 import graph_audit

from infra_joint.control.provenance import provenance_sha256

EXECUTIONS = {
    1: "4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c",
    2: "9dd761f7d4022ae262ada59e8f810b4ab2cac7106e50f0817093916861977198",
    3: "09f0a5e978623c145b1c075ecb575ed6ea54eec20110c0b7059e1db2b5b905e6",
    4: "16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c",
}
BOUNDARIES = ((170, 1), (228, 2), (261, 3))
DRAIN_SHA256 = "8f8ec012d1600ef6ece5090209dabc2e37fff18fb20202e186b6a35302628c75"


def epoch_for(record: dict[str, Any]) -> int:
    if record["event"] != "reserved":
        raise RuntimeError("only actual durable reservations establish execution epochs")
    epoch = next((e for last, e in BOUNDARIES if record["sequence"] <= last), 4)
    if record["execution_sha256"] != EXECUTIONS[epoch]:
        raise RuntimeError("attempt source differs from its actual durable epoch boundary")
    return epoch


def collect(root: Path = resident.ROOT, predecessor: Path = resident.PREDECESSOR) -> dict[str, Any]:
    before = (root / "phase1-attempts.jsonl").read_bytes()
    records = [json.loads(line) for line in before.splitlines()]
    drain_path = root / "analysis/resident-E-query-contract-drain-completed-001.json"
    drain = json.loads(drain_path.read_text())
    if (resident.sha256(drain_path) != DRAIN_SHA256
            or hashlib.sha256(b"".join(before.splitlines(keepends=True)[:262])).hexdigest()
            != drain["journal_file_sha256"]
            or resident.sha256(root / reviewer.BUG_PROOF) != reviewer.BUG_SHA256):
        raise RuntimeError("four-source projection requires exact safe-drain and E-defect proofs")
    epochs = {r["run_id"]: epoch_for(r) for r in records if r["event"] == "reserved"}
    for index, app in enumerate(reviewer.APPS, 1):
        freeze = json.loads((root / f"execution-freeze-{index:03d}.json").read_text())
        if provenance_sha256(freeze) != EXECUTIONS[index] or any(
                resident.sha256(root / app / p) != h for p, h in freeze["source_sha256"].items()):
            raise RuntimeError("immutable execution freeze/source drift")
    selection = predecessor / "preparation/task-freeze-002"
    if (resident.sha256(selection / "manifest.json") != resident.TASK_FREEZE_SHA256
            or resident.sha256(predecessor / "phase1-attempts.jsonl")
            != resident.OLD_JOURNAL_SHA256):
        raise RuntimeError("original tasks or closed predecessor drift")
    value = resident.base.snapshot(root, selection_root=selection,
                                   ledger_class=reviewer.MethodContractAttemptLedger,
                                   admission_reader=reviewer.effective_admission)
    if value["scheduled_cells"] != 168:
        raise RuntimeError("the original screening schedule cannot be enlarged")
    for row in value["rows"]:
        for attempt in row["attempts"]:
            epoch = epochs[attempt["run_id"]]
            if attempt["execution_sha256"] != EXECUTIONS[epoch]:
                raise RuntimeError("snapshot source cannot override its durable reservation")
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            trace = directory / "runs" / attempt["run_id"] / "trace.jsonl"
            events = [json.loads(line) for line in trace.open(encoding="utf-8")]
            attempt.update(execution_source_epoch=epoch, trace_file_sha256=resident.sha256(trace),
                           comparative_sample_eligible=attempt["disposition"] == "valid",
                           graph_audit=graph_audit(events),
                           model_evidence_path=model_evidence_audit(events),
                           quote_decision_audit=quote_decision_audit(events),
                           estimated_vs_observed=analyze(events)["estimated_vs_observed"])
            for key, folder in (("E_query_contract_review_file_sha256", reviewer.DIRECTORY),
                                ("source_bound_record_review_file_sha256",
                                 reviewer.RECORD_DIRECTORY)):
                path = root / folder / (attempt["run_id"] + ".json")
                attempt[key] = resident.sha256(path) if path.exists() else None
            admission = json.loads((directory / "admission.json").read_text())
            attempt["actual_recipient_contexts_audited"] = len(
                admission.get("api_audit", {}).get("contexts", []))
            attempt["residency_validation"] = json.loads(
                (directory / "private/residency-validation.json").read_text())
            summaries = [e["payload"] for e in events
                         if e["event_type"] == "logical.cost_quote.run.end"]
            if len(summaries) > 1:
                raise RuntimeError("ambiguous actual Quote lifecycle")
            attempt["actual_quote_protocol_summary"] = summaries[0] if summaries else None
    if (root / "phase1-attempts.jsonl").read_bytes() != before:
        raise RuntimeError("journal advanced; never publish a stale read-only projection")
    dependency_paths = (__file__, reviewer.__file__, resident.__file__, resident.base.__file__,
                        sys.modules[graph_audit.__module__].__file__,
                        sys.modules[analyze.__module__].__file__)
    if any(p is None for p in dependency_paths):
        raise RuntimeError("every collector dependency must have an actual source file")
    source_paths = tuple(p for p in dependency_paths if p is not None)
    value.update(version="resident-four-epoch-E-query-contract-projection-v1",
                 captured_utc=datetime.now(UTC).isoformat(),
                 journal_sha256=resident.sha256(root / "phase1-attempts.jsonl"),
                 execution_freezes={str(k): v for k, v in EXECUTIONS.items()},
                 predecessor_admissions_kept_separate=42, old_and_new_results_pooled=False,
                 all_nominal_private_evidence_audited=False, phase2_authorized=False,
                 logical_or_physical_execution_modified=False,
                 collector_source_sha256={Path(p).name: resident.sha256(Path(p))
                                          for p in source_paths})
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != resident.ROOT / "analysis"):
        raise RuntimeError("read-only projection remains in the owned remote namespace")
    value = collect()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != "rows"}))
