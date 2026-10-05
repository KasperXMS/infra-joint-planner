"""Remote-only audit/authorize/resume for one tested physical-receipt repair.

Deploy outside the formal app; preserve prior review helpers and control receipts.
No admission waiver, action retry, semantic tuning, or outcome-based repetition.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import large_scale_queue_v1 as queue
import large_scale_transport_freeze_v1 as repair
import yaml
from large_scale_classified_queue_v1 import ClassifiedQueueView
from large_scale_provider_policy_review_v1 import sha256
from run_predecision_matrix_v1 import write_new

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")
PARENT_CONTROL = "12e68fb0d64e9edba060de4ecebb292904837851631a19fbb3e69419da728317"


def require_stopped(root: Path, *, ignore_pid: int | None = None) -> None:
    for receipt in [*root.glob("queue-process-*.json"),
                    *root.glob("evidence/*/attempt*/process.json")]:
        pid = json.loads(receipt.read_text())["pid"]
        proc = Path("/proc") / str(pid) / "cmdline"
        if pid != ignore_pid and proc.exists() and root.name.encode() in proc.read_bytes():
            raise RuntimeError("owned queue or atomic attempt is live; do not restart")


def interrupted_model_proof(events: list[dict[str, Any]]) -> dict[str, Any]:
    models = {e["payload"]["action"]["action_id"] for e in events
              if e["event_type"] == "logical.action.prepared"
              and e["payload"]["action"]["action_type"] == "model"}
    physical = {e["payload"]["action_id"] for e in events
                if e["event_type"] == "physical.execution"}
    failed = [e["payload"] for e in events if e["event_type"] == "logical.observation"
              and e["payload"].get("succeeded") is False
              and e["payload"].get("failure_code") == "physical_execution_failed"]
    if not failed or any(p["action_id"] not in models or p["action_id"] in physical
                         or p.get("failure_message") !=
                         "unrecoverable physical execution error: ReadTimeout" for p in failed):
        raise RuntimeError("repair requires exact interrupted-model missing-receipt proof")
    graph = next((e["payload"] for e in reversed(events)
                  if e["event_type"] == "workflow.graph.snapshot"), {})
    statuses = {n["action_id"]: n["status"] for n in graph.get("nodes", [])}
    completed = {e["payload"]["action_id"] for e in events
                 if e["event_type"] == "action.completed"
                 and e["payload"].get("succeeded") is False}
    ids = {p["action_id"] for p in failed}
    if (len(ids) != len(failed) or not ids <= completed
            or any(statuses.get(i) != "failed" for i in ids)):
        raise RuntimeError("interrupted model must have unique closed failed-action evidence")
    return {"interrupted_model_actions": [p["action_id"] for p in failed],
            "missing_physical_receipts": len(failed), "exception_type": "ReadTimeout",
            "inference_status": "unknown", "original_trajectory_changed": False}


def ledger() -> ClassifiedQueueView:
    cells = queue.schedule()
    return ClassifiedQueueView(ROOT / "phase1-attempts.jsonl",
                               tuple(c.cell_id for c in cells), queue.schedule_sha256(cells))


def create_audit(run_id: str, test_proof_path: Path) -> dict[str, Any]:
    queue.require_remote(ROOT)
    app = Path(queue.__file__).resolve().parents[1]
    tests = json.loads(test_proof_path.read_text())
    candidate = queue.execution_freeze()
    if (tests.get("tested_code_revision") != candidate["commit_sha"]
            or tests.get("gates") != {"pytest": "passed", "ruff": "passed",
                                     "strict_pyright": "passed", "diff_check": "passed"}
            or not isinstance(tests.get("pytest_passed"), int)
            or tests["pytest_passed"] < 811
            or any(tests.get("tested_overlay_sha256", {}).get(p) !=
                   candidate["source_sha256"][p] for p in repair.CHANGED | repair.ADDED)):
        raise RuntimeError("full test receipt does not bind the deployed source overlay")
    parent = json.loads((ROOT / "execution-freeze-002.json").read_text())
    if provenance_sha256(parent) != repair.PARENT_SHA256:
        raise RuntimeError("parent freeze drift")
    repair.validate_execution_repair(parent, candidate)
    repair.validate_harness_repair(
        yaml.safe_load((app / repair.HARNESS_PARENT).read_text()),
        yaml.safe_load((app / repair.HARNESS).read_text()))
    with QueueLease(ROOT / "queue-lease.json"):
        require_stopped(ROOT)
        current = ledger()
        if current.pending:
            raise RuntimeError("an outstanding attempt requires reconciliation, not repair")
        original = next(a for a in current.original_attempts if a.run_id == run_id)
        directory = ROOT / "evidence" / original.cell_id / f"attempt{original.attempt_index}"
        admission = json.loads((directory / "admission.json").read_text())
        config = queue.frozen._yaml(ROOT / "cell-configs" / (run_id + ".yaml"))
        prices, _ = queue.verified_prices(ROOT, app)
        if (original.disposition != "confounder"
                or admission.get("problems") != [
                    "typed_action_failure_requires_audit:physical_execution_failed"]
                or admission.get("operational_incidents")
                or provenance_sha256(queue.admit(directory, config, prices))
                != original.receipt_sha256):
            raise RuntimeError("independent full admission does not establish the exact defect")
        trace = directory / "runs" / run_id / "trace.jsonl"
        proof = interrupted_model_proof([
            json.loads(line) for line in trace.read_text().splitlines()])
        value = {"version": "transport-receipt-repair-audit-v1", "run_id": run_id,
                 "cell_id": original.cell_id, "attempt_index": original.attempt_index,
                 "original_admission_sha256": original.receipt_sha256,
                 "parent_execution_sha256": provenance_sha256(parent),
                 "repaired_execution_candidate_sha256": provenance_sha256(candidate),
                 "allowed_source_delta": repair.source_delta(
                     parent["source_sha256"], candidate["source_sha256"]),
                 "semantic_contracts_unchanged": True, "original_evidence_unchanged": True,
                 "queue_and_attempt_absent": True, "test_gates": tests["gates"],
                 "test_proof_sha256": sha256(test_proof_path), "proof": proof,
                 "classified_nominal_cells_at_repair": len(current.completed_cells),
                 "original_evidence_file_sha256": {str(p.relative_to(directory)): sha256(p)
                     for p in sorted(directory.rglob("*")) if p.is_file()},
                 "control_source_sha256": sha256(Path(__file__)),
                 "unaffected_valid_cells_repeated": False}
        write_new(ROOT / "readiness" / repair.AUDIT_NAME, value)
        repair._read_audit(ROOT, parent, candidate)
        return value


def control_value() -> dict[str, Any]:
    import large_scale_adjudicated_queue_v1 as json_control
    import large_scale_adjudication_v1 as json_review
    import large_scale_classified_queue_v1 as classified
    import large_scale_provider_policy_review_v1 as policy_review

    app = Path(queue.__file__).resolve().parents[1]
    parent = json.loads((ROOT / "queue-control-freeze-004.json").read_text())
    if provenance_sha256(parent) != PARENT_CONTROL:
        raise RuntimeError("immutable previous control freeze drift")
    expected = {json_review.__file__: parent["previous_json_control"]["adjudication_source_sha256"],
                json_control.__file__: parent["previous_json_control"][
                    "queue_control_source_sha256"],
                policy_review.__file__: parent["policy_reviewer_source_sha256"],
                classified.__file__: parent["queue_control_source_sha256"]}
    if any(sha256(Path(p)) != h for p, h in expected.items()):
        raise RuntimeError("previous reviewers/controller source changed")
    return {"version": "transport-receipt-repair-control-v1",
            "parent_control_sha256": PARENT_CONTROL,
            "execution_sha256": repair.verify(ROOT, app, ROOT / repair.NAME),
            "repair_control_source_sha256": sha256(Path(__file__)),
            "previous_review_sources_sha256": expected,
            "review_receipts": {str(p.relative_to(ROOT)): sha256(p)
                for folder in ("adjudications", "provider-policy-adjudications")
                for p in sorted((ROOT / folder).glob("*.json"))},
            "repeat_valid_cells": False, "schedule_unchanged": True,
            "affected_only_repair_authorization_required": True}


def authorize() -> None:
    queue.require_remote(ROOT)
    app = Path(queue.__file__).resolve().parents[1]
    digest = repair.verify(ROOT, app, ROOT / repair.NAME)
    audit_path = ROOT / "readiness" / repair.AUDIT_NAME
    audit = json.loads(audit_path.read_text())
    with QueueLease(ROOT / "queue-lease.json"):
        require_stopped(ROOT)
        ledger().authorize_generic_repair(
            audit["run_id"], original_admission_sha256=audit["original_admission_sha256"],
            repair_audit_sha256=sha256(audit_path), new_execution_sha256=digest)


def run(control_path: Path) -> None:
    queue.require_remote(ROOT)
    if (control_path.is_symlink() or control_path.resolve().parent != ROOT
            or not control_path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("control receipt must remain a new owned namespace")
    if json.loads(control_path.read_text()) != control_value():
        raise RuntimeError("transport repair control provenance drift")
    require_stopped(ROOT, ignore_pid=os.getpid())
    queue.AttemptLedger = ClassifiedQueueView
    queue.run_queue(ROOT / repair.NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in ("audit", "freeze", "authorize", "freeze-control", "queue"):
        modes.add_argument("--" + mode, action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--test-proof", type=Path)
    parser.add_argument("--control-freeze", type=Path)
    args = parser.parse_args()
    queue.require_remote(ROOT)
    if args.audit:
        print(json.dumps({"repair_audit_sha256": provenance_sha256(
            create_audit(args.run_id, args.test_proof))}))
    elif args.freeze:
        write_new(ROOT / repair.NAME, repair.execution_value(
            ROOT, Path(queue.__file__).resolve().parents[1]))
        print(json.dumps({"execution_sha256": queue.verify_execution_freeze(ROOT / repair.NAME)}))
    elif args.authorize:
        authorize()
        print(json.dumps({"repair_authorization_appended": True}))
    elif args.freeze_control:
        if args.control_freeze.resolve().parent != ROOT:
            raise RuntimeError("control freeze must remain a new owned namespace")
        value = control_value()
        write_new(args.control_freeze, value)
        print(json.dumps({"control_sha256": provenance_sha256(value)}))
    else:
        run(args.control_freeze)
