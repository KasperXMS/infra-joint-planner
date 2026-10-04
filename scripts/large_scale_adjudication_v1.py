"""Offline, exact invalid-JSON model-output adjudication; no Agent/runtime changes.

The original ledger and admission remain intact. Effective admission is supplied
by an independently checked sidecar, never a wildcard validation_failed allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, AttemptLedger, QueueLease

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")
REVIEW_REASON = "audited_post_inference_model_json_failure"
GATE_PROBLEM = "typed_action_failure_requires_audit:validation_failed"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_model_json_failures(
    original: dict[str, Any], events: list[dict[str, Any]],
) -> dict[str, Any]:
    """A Worker-specific post-inference failure, not a general format bypass."""
    if (original.get("disposition") != "confounder"
            or original.get("problems") != [GATE_PROBLEM]
            or original.get("operational_incidents")):
        raise RuntimeError("adjudication cannot waive other system/operational findings")
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    physical = {e["payload"]["action_id"]: e["payload"] for e in events
                if e["event_type"] == "physical.execution"}
    proof = []
    reviewed_actions: set[str] = set()
    for event in events:
        if event["event_type"] != "logical.observation":
            continue
        p = event["payload"]
        if p.get("failure_code") != "validation_failed":
            continue
        if p["action_id"] in reviewed_actions:
            raise RuntimeError("duplicate post-inference failure observation")
        reviewed_actions.add(p["action_id"])
        action = actions.get(p["action_id"], {})
        receipt = physical.get(p["action_id"], {})
        outputs = action.get("outputs", [])
        failure = receipt.get("failure", {})
        selection = receipt.get("selection", {})
        if (p.get("succeeded") is not False or action.get("action_type") != "model"
                or len(outputs) != 1 or outputs[0].get("media_type") != "application/json"
                or p.get("failure_message") != "model output is not valid JSON"
                or failure.get("failure_code") != "validation_failed"
                or failure.get("failure_message") != "model output is not valid JSON"
                or failure.get("stage") != "execution"
                or not selection.get("selected_deployment_id")):
            raise RuntimeError("validation failure is not the exact reviewed model JSON case")
        proof.append({"action_id": p["action_id"], "action_sha256": provenance_sha256(action),
                      "failure_code": "validation_failed", "reached_model_inference": True,
                      "model_output_parse_failed": True, "model_service_tokens_unknown": True})
    if not proof:
        raise RuntimeError("no matching post-inference model-output failure")
    reviewed = {**original, "disposition": "valid", "reason": REVIEW_REASON, "problems": []}
    return {"reviewed_admission": reviewed, "proof": proof}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    """Reproduce the narrow review and verify all original evidence, read-only."""
    if path.is_symlink():
        raise RuntimeError("adjudication sidecar must not be a symlink")
    value = json.loads(path.read_text())
    root = path.parent.parent
    if path.parent.name != "adjudications" or path.name != attempt.run_id + ".json":
        raise RuntimeError("adjudication path/run mismatch")
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    original = json.loads((directory / "admission.json").read_text())
    if (attempt.disposition != "confounder" or attempt.reason != GATE_PROBLEM
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["run_id"] != attempt.run_id):
        raise RuntimeError("adjudication does not match the original settled rejection")
    actual_files = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if actual_files != set(value["original_evidence_file_sha256"]):
        raise RuntimeError("adjudication must bind every original evidence file")
    if value["reviewer_source_sha256"] != sha256(Path(__file__)):
        raise RuntimeError("independent reviewer implementation drift")
    for relative, expected in value["original_evidence_file_sha256"].items():
        source = directory / relative
        if source.is_symlink() or not source.resolve().is_relative_to(directory.resolve()):
            raise RuntimeError("adjudication evidence path escaped its attempt")
        if sha256(source) != expected:
            raise RuntimeError("original adjudicated evidence drift")
    worker = root / "app/src/infra_joint/worker/server.py"
    if sha256(worker) != value["worker_source_sha256"]:
        raise RuntimeError("reviewed Worker parsing implementation drift")
    source = worker.read_text()
    if (source.index("completion = await deployment.backend.invoke(model_request)")
            >= source.index('raise ValueError("model output is not valid JSON")')):
        raise RuntimeError("Worker failure is not established after model completion")
    trace = directory / "runs" / attempt.run_id / "trace.jsonl"
    review = review_model_json_failures(original, [json.loads(line)
                                                 for line in trace.read_text().splitlines()])
    if review != {key: value[key] for key in ("reviewed_admission", "proof")}:
        raise RuntimeError("adjudication proof/review cannot be reproduced")
    if provenance_sha256(review["reviewed_admission"]) != value["reviewed_admission_sha256"]:
        raise RuntimeError("reviewed admission hash drift")
    return value


class AdjudicatedAttemptLedger(AttemptLedger):
    """Sidecar-aware view over the unchanged hash-linked original attempt journal."""

    @property
    def original_attempts(self) -> tuple[Attempt, ...]:
        return super().attempts

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for attempt in self.original_attempts:
            path = self.path.parent / "adjudications" / (attempt.run_id + ".json")
            if path.exists() and attempt.disposition is not None:
                sidecar = verify_sidecar(path, attempt)
                reviewed = sidecar["reviewed_admission"]
                attempt = replace(attempt, disposition="valid", reason=reviewed["reason"],
                                  receipt_sha256=sidecar["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    sidecar = root / "adjudications" / (attempt.run_id + ".json")
    if sidecar.exists() and attempt.reason == REVIEW_REASON:
        value = json.loads(sidecar.read_text())
        if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
            raise RuntimeError("effective admission and ledger view differ")
        return value["reviewed_admission"]
    return json.loads((root / "evidence" / attempt.cell_id /
                       f"attempt{attempt.attempt_index}" / "admission.json").read_text())


def create_review(root: Path, run_id: str) -> dict[str, Any]:
    """Only after the owned queue exits; re-audit every real recipient/receipt."""
    if sys.platform != "linux" or root.resolve() != ROOT:
        raise RuntimeError("raw evidence and adjudication stay on the experiment controller")
    import large_scale_queue_v1 as queue

    with QueueLease(root / "queue-lease.json"):
        cells = queue.schedule()
        ledger = AttemptLedger(root / "phase1-attempts.jsonl",
                               tuple(c.cell_id for c in cells), queue.schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("cannot adjudicate an outstanding possibly-live attempt")
        attempt = next(x for x in ledger.attempts if x.run_id == run_id)
        directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
        for receipt in (root / "queue-process-002.json", directory / "process.json"):
            pid = json.loads(receipt.read_text())["pid"]
            process = Path(f"/proc/{pid}/cmdline")
            if process.exists() and root.name.encode() in process.read_bytes():
                raise RuntimeError("owned queue/attempt process is still live")
        original = json.loads((directory / "admission.json").read_text())
        config = queue.frozen._yaml(root / "cell-configs" / (run_id + ".yaml"))
        prices, _ = queue.verified_prices(root, root / "app")
        fresh_audit = queue.admit(directory, config, prices)
        if provenance_sha256(fresh_audit) != attempt.receipt_sha256:
            raise RuntimeError("independent full admission audit disagrees with original evidence")
        trace = directory / "runs" / run_id / "trace.jsonl"
        review = review_model_json_failures(original, [json.loads(line)
                                                     for line in trace.read_text().splitlines()])
        freeze = json.loads((root / "execution-freeze-002.json").read_text())
        worker_hash = freeze["source_sha256"]["src/infra_joint/worker/server.py"]
        if sha256(root / "app/src/infra_joint/worker/server.py") != worker_hash:
            raise RuntimeError("frozen Worker implementation drift")
        value = {"version": "exact-model-output-adjudication-v1", "run_id": run_id,
                 "original_admission_sha256": attempt.receipt_sha256,
                 "original_execution_sha256": attempt.execution_sha256,
                 "worker_source_sha256": worker_hash,
                 "reviewer_source_sha256": sha256(Path(__file__)),
                 "original_evidence_file_sha256": {
                     str(p.relative_to(directory)): sha256(p)
                     for p in sorted(directory.rglob("*")) if p.is_file()},
                 **review,
                 "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"]),
                 "formal_execution_changed": False, "replacement_authorized": False,
                 "model_behavior_repaired": False}
        path = root / "adjudications" / (run_id + ".json")
        queue.write_new(path, value)
        verify_sidecar(path, attempt)
        return {"run_id": run_id, "adjudication_sha256": provenance_sha256(value),
                "evidence_files": len(value["original_evidence_file_sha256"]),
                "reviewed_disposition": "valid", "rerun": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    print(json.dumps(create_review(ROOT, arguments.run_id)))
