"""Exact offline provider-policy classification; no censorship or model retry.

Preserves the original failed attempt and both existing JSON reviewers. A policy
refusal is a classified nominal provider failure, not a wrong answer or outage.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from large_scale_adjudication_v1 import (
    ROOT,
    AdjudicatedAttemptLedger,
    sha256,
)
from large_scale_adjudication_v1 import (
    effective_admission as json_admission,
)

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

GATE = "unclassified_API_failure_requires_audit"
REASON = "audited_provider_input_policy_failure"
POLICY_DIRECTORY = "provider-policy-adjudications"


def review_policy(original: dict[str, Any], api_root: Path) -> dict[str, Any]:
    """Only exact raw HTTP400 input-policy responses, with no other finding."""
    terminal = original.get("terminal_failure") or {}
    if (original.get("disposition") != "confounder" or original.get("problems") != [GATE]
            or original.get("operational_incidents") or original.get("execution_completed")
            or original.get("original_evaluation") is not None
            or terminal.get("code") != "logical_loop_failed"
            or "data_inspection_failed" not in str(terminal.get("message", ""))):
        raise RuntimeError("policy review cannot waive other findings or evaluated results")
    proof = []
    for path in sorted(api_root.glob("*-usage.json")):
        row = json.loads(path.read_text())
        if row["status"] == 200:
            continue
        call_id = row["call_id"]
        response = api_root / (call_id + "-response.json")
        request = api_root / (call_id + "-request.json")
        if not response.is_file() or not request.is_file():
            raise RuntimeError("missing original policy request/response")
        error = json.loads(response.read_text()).get("error") or {}
        if (row["status"] != 400 or error.get("code") != "data_inspection_failed"
                or error.get("type") != "data_inspection_failed"
                or error.get("message") != "Input text data may contain inappropriate content."):
            raise RuntimeError("HTTP failure is not the exact provider input-policy refusal")
        proof.append({"call_id": call_id, "recipient": row["recipient"],
                      "requested_model": row["requested_model"], "http_status": 400,
                      "provider_error_code": "data_inspection_failed",
                      "request_sha256": sha256(request), "response_sha256": sha256(response),
                      "failed_call_usage": row["usage"]})
    if not proof:
        raise RuntimeError("no actual provider input-policy response")
    return {"reviewed_admission": {**original, "disposition": "valid", "reason": REASON,
                                   "problems": [], "failure_class": "provider_input_policy",
                                   "replacement_authorized": False}, "proof": proof}


def verify_policy_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    if path.is_symlink() or path.parent.name != POLICY_DIRECTORY:
        raise RuntimeError("policy sidecar path is not an immutable owned receipt")
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))):
        raise RuntimeError("policy sidecar identity/source/original receipt drift")
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if actual != set(value["original_evidence_file_sha256"]):
        raise RuntimeError("policy sidecar must bind every original evidence file")
    for relative, expected in value["original_evidence_file_sha256"].items():
        source = directory / relative
        if (source.is_symlink() or not source.resolve().is_relative_to(directory.resolve())
                or sha256(source) != expected):
            raise RuntimeError("original policy evidence drift or escaped path")
    review = review_policy(original, directory / "private/api")
    if (review != {key: value[key] for key in ("reviewed_admission", "proof")}
            or provenance_sha256(review["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("policy classification proof cannot be reproduced")
    return value


class ClassifiedAttemptLedger(AdjudicatedAttemptLedger):
    """Compose exact JSON behavior and provider refusals without editing history."""

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for attempt in super().attempts:
            path = self.path.parent / POLICY_DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_policy_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return json_admission(root, attempt)
    path = root / POLICY_DIRECTORY / (attempt.run_id + ".json")
    value = json.loads(path.read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective policy admission/ledger mismatch")
    return value["reviewed_admission"]


def create_review(root: Path, run_id: str) -> dict[str, Any]:
    if sys.platform != "linux" or root.resolve() != ROOT:
        raise RuntimeError("provider raw contexts remain on the experiment controller")
    import large_scale_queue_v1 as queue
    from large_scale_classified_queue_v1 import ClassifiedQueueView

    with QueueLease(root / "queue-lease.json"):
        cells = queue.schedule()
        ledger = ClassifiedQueueView(root / "phase1-attempts.jsonl",
                                     tuple(c.cell_id for c in cells), queue.schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("outstanding possibly-live attempt cannot be classified")
        attempt = next(x for x in ledger.attempts if x.run_id == run_id)
        directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
        for receipt in [*root.glob("queue-process-*.json"), directory / "process.json"]:
            pid = json.loads(receipt.read_text())["pid"]
            process = Path(f"/proc/{pid}/cmdline")
            if process.exists() and root.name.encode() in process.read_bytes():
                raise RuntimeError("owned experiment queue/attempt is still live")
        original = json.loads((directory / "admission.json").read_text())
        config = queue.frozen._yaml(root / "cell-configs" / (run_id + ".yaml"))
        prices, _ = queue.verified_prices(root, root / "app")
        if provenance_sha256(queue.admit(directory, config, prices)) != attempt.receipt_sha256:
            raise RuntimeError("independent full admission differs from original policy finding")
        review = review_policy(original, directory / "private/api")
        value = {"version": "exact-provider-policy-review-v1", "run_id": run_id,
                 "original_admission_sha256": attempt.receipt_sha256,
                 "original_execution_sha256": attempt.execution_sha256,
                 "reviewer_source_sha256": sha256(Path(__file__)),
                 "original_evidence_file_sha256": {
                     str(p.relative_to(directory)): sha256(p)
                     for p in sorted(directory.rglob("*")) if p.is_file()},
                 **review, "reviewed_admission_sha256": provenance_sha256(
                     review["reviewed_admission"]),
                 "formal_execution_changed": False, "replacement_authorized": False,
                 "input_censored": False, "prompt_changed": False}
        path = root / POLICY_DIRECTORY / (run_id + ".json")
        queue.write_new(path, value)
        verify_policy_sidecar(path, attempt)
        return {"run_id": run_id, "classification": "provider_input_policy",
                "adjudication_sha256": provenance_sha256(value),
                "evidence_files": len(value["original_evidence_file_sha256"]),
                "evaluation": None, "rerun": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    print(json.dumps(create_review(ROOT, arguments.run_id)))
