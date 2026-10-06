"""Offline composition of exact record-field and HTTP400 policy proofs.

Provider input-policy refusal is a nominal failure, never an outage or grounds
for replacement. Preserve all historical execution/review sources and receipts.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_provider_policy_review_v1 as policy
import large_scale_resident_timeout_review_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = previous.DIRECTORY
POLICY_DIRECTORY = "compound-record-policy-adjudications"
REASON = "audited_materialized_record_and_provider_input_policy_failure"
records = previous.previous.records
methods = previous.previous.previous
sha256 = previous.previous.sha256


def review(original: dict[str, Any], events: list[dict[str, Any]],
           shapes: dict[str, Any], api: Path) -> dict[str, Any]:
    terminal: dict[str, Any] = original.get("terminal_failure") or {}
    failures = [e["payload"].get("failure") for e in events if e["event_type"] == "run.failed"]
    if (original.get("disposition") != "confounder"
            or len(original.get("problems", [])) != 2
            or set(original["problems"]) != {records.GATE_PROBLEM, policy.GATE}
            or original.get("operational_incidents")
            or original.get("execution_completed") is not False
            or original.get("original_evaluation") is not None
            or terminal.get("code") != "logical_loop_failed"
            or terminal.get("exception_type") != "AgentLoopError"
            or not str(terminal.get("message", "")).startswith(
                "Blind verifier failed: BadRequestError: Error code: 400")
            or not events or events[-1]["event_type"] != "run.failed" or failures != [terminal]):
        raise RuntimeError("field/policy review cannot waive other findings or evaluated results")
    field = records.review({**original, "problems": [records.GATE_PROBLEM]}, events, shapes)
    refusals = policy.review_policy({**original, "problems": [policy.GATE]}, api)["proof"]
    usages = [json.loads(p.read_text()) for p in sorted(api.glob("*-usage.json"))]
    if len({r["call_id"] for r in usages}) != len(usages):
        raise RuntimeError("duplicate provider-policy HTTP identity")
    failed = [r for r in usages if r["status"] != 200]
    terminal_calls = [r for r in failed if r["recipient"] == "verifier"]
    if (len(terminal_calls) != 1 or not refusals
            or any(r["recipient"] not in {"specialist", "verifier"} for r in failed)
            or any(r["finished_utc"] > terminal_calls[0]["finished_utc"] for r in usages)
            or terminal_calls[0]["requested_model"] != "qwen3.8-max"
            or sum(e["event_type"] == "logical.verification.input" for e in events)
            != sum(e["event_type"] == "logical.verification" for e in events) + 1):
        raise RuntimeError("policy refusal must match the terminal fixed Blind Verifier")
    return {"record_field_proof": field["record_field_proof"],
            "provider_policy_proof": refusals,
            "covered_original_findings": sorted((records.GATE_PROBLEM, policy.GATE)),
            "reviewed_admission": {**original, "disposition": "valid", "reason": REASON,
                "problems": [], "failure_class": "provider_input_policy_with_absent_field_misuse",
                "primary_failure": "provider_input_policy",
                "secondary_failure": "workflow_composition_absent_field_misuse",
                "replacement_authorized": False, "evaluation_imputed": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != POLICY_DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != records.GATE_PROBLEM
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["timeout_reviewer_source_sha256"] != sha256(Path(previous.__file__))
            or value["method_reviewer_source_sha256"] != sha256(Path(methods.__file__))
            or value["record_reviewer_source_sha256"] != sha256(Path(records.__file__))
            or value["policy_reviewer_source_sha256"] != sha256(Path(policy.__file__))
            or value["execution_sources_sha256"] != methods.frozen_sources(
                root, attempt, previous.SOURCE_PATHS)
            or value["original_evidence_file_sha256"] != methods.evidence_files(directory)):
        raise RuntimeError("compound record/policy identity/source/evidence drift")
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    for identifier, shape in value["materialized_shapes"].items():
        metadata = {k: shape[k] for k in ("artifact_id", "media_type", "size_bytes", "sha256_hex")}
        replicas = [a for state in states.values() for a in state["artifacts"]
                    if a["artifact_id"] == identifier]
        if not replicas or any(a != metadata for a in replicas):
            raise RuntimeError("record shape/actual replica drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").read_text().splitlines()]
    actual = review(original, events, value["materialized_shapes"], directory / "private/api")
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("compound record/policy proof cannot be reproduced")
    return value


class ProjectionAttemptLedger(previous.ProjectionAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
        for attempt in super().attempts:
            path = self.path.parent / POLICY_DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    path = root / POLICY_DIRECTORY / (attempt.run_id + ".json")
    if not path.exists():
        return previous.effective_admission(root, attempt)
    value = json.loads(path.read_text())
    if provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256:
        raise RuntimeError("effective record/policy admission drift")
    return value["reviewed_admission"]
