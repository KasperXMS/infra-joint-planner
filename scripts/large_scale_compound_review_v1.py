"""Compose two independently proven nominal failures without changing old reviews.

Only exact post-inference invalid JSON plus exact HTTP400 input-policy refusal.
All original findings must be covered; no wildcard gate waiver or replacement.
Deploy outside the frozen execution app. Raw evidence remains on the controller.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_adjudication_v1 as model_review
import large_scale_provider_policy_review_v1 as policy_review

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

ROOT = model_review.ROOT
DIRECTORY = "compound-failure-adjudications"
REASON = "audited_model_json_and_provider_input_policy_failure"
GATES = tuple(sorted((model_review.GATE_PROBLEM, policy_review.GATE)))
sha256 = model_review.sha256


def review_compound(original: dict[str, Any], events: list[dict[str, Any]],
                   api_root: Path) -> dict[str, Any]:
    """Prove every finding with unchanged component validators, not a partial waiver."""
    if (original.get("disposition") != "confounder"
            or original.get("problems") != list(GATES)
            or original.get("operational_incidents")):
        raise RuntimeError("compound review requires exactly both independently known findings")
    # Projections isolate each validator's sole-finding input. The full original
    # is unchanged; both original gates and both proofs are required in the union.
    model = model_review.review_model_json_failures(
        {**original, "problems": [model_review.GATE_PROBLEM]}, events)
    policy = policy_review.review_policy(
        {**original, "problems": [policy_review.GATE]}, api_root)
    return {
        "covered_original_findings": list(GATES),
        "model_json_proof": model["proof"],
        "provider_policy_proof": policy["proof"],
        "reviewed_admission": {
            **original, "disposition": "valid", "reason": REASON, "problems": [],
            "failure_class": "provider_input_policy_with_post_inference_model_json_failure",
            "replacement_authorized": False,
        },
    }


def reviewer_sources() -> dict[str, str]:
    return {"compound": sha256(Path(__file__)),
            "model_json": sha256(Path(model_review.__file__)),
            "provider_policy": sha256(Path(policy_review.__file__))}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("compound sidecar path/identity is not owned")
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (attempt.disposition != "confounder" or attempt.reason != GATES[0]
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["run_id"] != attempt.run_id
            or value["reviewer_sources_sha256"] != reviewer_sources()):
        raise RuntimeError("compound source/original receipt/identity drift")
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if actual != set(value["original_evidence_file_sha256"]):
        raise RuntimeError("compound review must bind every original file")
    for relative, digest in value["original_evidence_file_sha256"].items():
        source = directory / relative
        if (source.is_symlink() or not source.resolve().is_relative_to(directory.resolve())
                or sha256(source) != digest):
            raise RuntimeError("compound original evidence changed or escaped")
    worker = root / "app/src/infra_joint/worker/server.py"
    if sha256(worker) != value["worker_source_sha256"]:
        raise RuntimeError("compound Worker parsing source drift")
    text = worker.read_text()
    if (text.index("completion = await deployment.backend.invoke(model_request)")
            >= text.index('raise ValueError("model output is not valid JSON")')):
        raise RuntimeError("JSON parsing failure is not after inference completion")
    trace = directory / "runs" / attempt.run_id / "trace.jsonl"
    review = review_compound(original, [json.loads(line)
                                       for line in trace.read_text().splitlines()],
                             directory / "private/api")
    if (review != {key: value[key] for key in review}
            or provenance_sha256(review["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("compound proof cannot be reproduced")
    return value


class CompoundAttemptLedger(policy_review.ClassifiedAttemptLedger):
    """Additional exact sidecar view; original hash-linked journal stays immutable."""

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for attempt in super().attempts:
            path = self.path.parent / DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return policy_review.effective_admission(root, attempt)
    value = json.loads((root / DIRECTORY / (attempt.run_id + ".json")).read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective compound admission/ledger mismatch")
    return value["reviewed_admission"]


def require_stopped(root: Path, *, ignore_pid: int | None = None) -> None:
    for receipt in [*root.glob("queue-process-*.json"),
                    *root.glob("evidence/*/attempt*/process.json")]:
        pid = json.loads(receipt.read_text())["pid"]
        process = Path(f"/proc/{pid}/cmdline")
        if pid != ignore_pid and process.exists() and root.name.encode() in process.read_bytes():
            raise RuntimeError("owned queue or atomic attempt is still live")


def create_review(root: Path, run_id: str) -> dict[str, Any]:
    if sys.platform != "linux" or root.resolve() != ROOT:
        raise RuntimeError("raw compound evidence remains on the experiment controller")
    import large_scale_queue_v1 as queue

    with QueueLease(root / "queue-lease.json"):
        require_stopped(root, ignore_pid=os.getpid())
        cells = queue.schedule()
        ledger = CompoundAttemptLedger(root / "phase1-attempts.jsonl",
                                       tuple(c.cell_id for c in cells),
                                       queue.schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("outstanding attempt cannot be classified")
        attempt = next(a for a in ledger.attempts if a.run_id == run_id)
        directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
        config = queue.frozen._yaml(root / "cell-configs" / (run_id + ".yaml"))
        prices, _ = queue.verified_prices(root, root / "app")
        original = json.loads((directory / "admission.json").read_text())
        if provenance_sha256(queue.admit(directory, config, prices)) != attempt.receipt_sha256:
            raise RuntimeError("independent complete admission does not match original")
        trace = directory / "runs" / run_id / "trace.jsonl"
        review = review_compound(original, [json.loads(line)
                                           for line in trace.read_text().splitlines()],
                                 directory / "private/api")
        value = {"version": "exact-compound-json-policy-review-v1", "run_id": run_id,
                 "original_admission_sha256": attempt.receipt_sha256,
                 "original_execution_sha256": attempt.execution_sha256,
                 "reviewer_sources_sha256": reviewer_sources(),
                 "worker_source_sha256": sha256(root / "app/src/infra_joint/worker/server.py"),
                 "original_evidence_file_sha256": {
                     str(p.relative_to(directory)): sha256(p)
                     for p in sorted(directory.rglob("*")) if p.is_file()},
                 **review,
                 "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"]),
                 "formal_execution_changed": False, "replacement_authorized": False,
                 "input_censored": False, "model_behavior_repaired": False}
        path = root / DIRECTORY / (run_id + ".json")
        queue.write_new(path, value)
        verify_sidecar(path, attempt)
        return {"run_id": run_id, "adjudication_sha256": provenance_sha256(value),
                "evidence_files": len(value["original_evidence_file_sha256"]), "rerun": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    print(json.dumps(create_review(ROOT, arguments.run_id)))
