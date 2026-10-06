"""Exact offline compound field-misuse/cloud-timeout proof.

Historical evidence, validators and measured execution remain immutable. Only
an independently evidenced terminal cloud service timeout permits the existing
one-identical-replacement rule; ordinary field mistakes never permit a retry.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import large_scale_resident_projection_review_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = previous.DIRECTORY  # Preserve the historical projection collector contract.
TIMEOUT_DIRECTORY = "compound-cloud-timeout-adjudications"
REASON = "external_model_service_failure"
API_GATE = "unclassified_API_failure_requires_audit"
CLOUD_TIMEOUT_SECONDS = 180
SOURCE_PATHS = (*previous.records.SOURCE_PATHS,
                "src/infra_joint/experiments/sdk_api_meter.py",
                "scripts/large_scale_execution_v1.py")


def review(original: dict[str, Any], events: list[dict[str, Any]],
           shapes: dict[str, Any], api: Path) -> dict[str, Any]:
    terminal: dict[str, Any] = original.get("terminal_failure") or {}
    if (original.get("disposition") != "confounder"
            or len(original.get("problems", [])) != 2
            or set(original["problems"]) != {previous.records.GATE_PROBLEM, API_GATE}
            or original.get("operational_incidents")
            or original.get("execution_completed") is not False
            or original.get("original_evaluation") is not None
            or terminal.get("code") != "logical_loop_failed"
            or terminal.get("exception_type") != "AgentLoopError"
            or terminal.get("message") !=
            "Blind verifier failed: APITimeoutError: Request timed out."):
        raise RuntimeError("timeout review cannot waive other findings or semantic failures")
    # The unchanged exact validator still sees only its own finding. Both
    # independent proofs are mandatory; the full original admission is preserved.
    fields = previous.records.review(
        {**original, "problems": [previous.records.GATE_PROBLEM]}, events, shapes)
    usages = [(p, json.loads(p.read_text())) for p in sorted(api.glob("*-usage.json"))]
    failed = [(p, row) for p, row in usages if row.get("status") != 200]
    if len(failed) != 1:
        raise RuntimeError("exactly one terminal timeout and all other HTTP200 receipts required")
    usage_path, row = failed[0]
    call = row.get("call_id", "")
    if not isinstance(call, str) or not call or Path(call).name != call:
        raise RuntimeError("exact API call identity required")
    request_path, response_path = api / (call + "-request.json"), api / (call + "-response.json")
    if any(p.is_symlink() or not p.is_file() for p in (
            usage_path, request_path, response_path)):
        raise RuntimeError("exact original API files required")
    request = json.loads(request_path.read_text())
    duration = row.get("latency_ms")
    if (usage_path.name != call + "-usage.json" or row.get("recipient") != "verifier"
            or row.get("agent_name") != "blind_evidence_verifier"
            or row.get("intended_model") != "qwen3.8-max"
            or row.get("requested_model") != "qwen3.8-max"
            or request.get("model") != "qwen3.8-max"
            or [t.get("function", {}).get("name") for t in request.get("tools", [])]
            != ["submit_verification"]
            or row.get("status") is not None or row.get("usage") is not None
            or row.get("response_model") is not None or row.get("request_id") is not None
            or row.get("error_type") != "APITimeoutError"
            or json.loads(response_path.read_text()) is not None
            or isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not CLOUD_TIMEOUT_SECONDS * 1000 <= duration < CLOUD_TIMEOUT_SECONDS * 2000):
        raise RuntimeError("not an exact no-response terminal Verifier deadline")
    try:
        started = datetime.fromisoformat(row["started_utc"])
        finished = datetime.fromisoformat(row["finished_utc"])
    except (KeyError, ValueError, TypeError) as error:
        raise RuntimeError("timeout interval is not evidenced") from error
    if (started.tzinfo is None or finished.tzinfo is None
            or abs((finished - started).total_seconds() * 1000 - duration) > 1000
            or any(datetime.fromisoformat(other["finished_utc"]) > finished
                   for _, other in usages if other is not row)):
        raise RuntimeError("timeout must be the terminal recorded API interval")
    verification_inputs = sum(e["event_type"] == "logical.verification.input" for e in events)
    verification_results = sum(e["event_type"] == "logical.verification" for e in events)
    if (sum(r.get("recipient") == "verifier" for _, r in usages) != verification_inputs
            or verification_inputs != verification_results + 1):
        raise RuntimeError("failed terminal Verifier call must match execution trace")
    proof = {"call_id": call, "recipient": "verifier", "requested_model": "qwen3.8-max",
             "error_type": "APITimeoutError", "http_status": None,
             "latency_ms": duration, "frozen_timeout_seconds": CLOUD_TIMEOUT_SECONDS,
             "request_sha256": previous.sha256(request_path),
             "response_sha256": previous.sha256(response_path),
             "usage_sha256": previous.sha256(usage_path),
             "failed_call_usage": None, "provider_wide_outage_proven": False,
             "timeout_origin": None}
    return {"record_field_proof": fields["record_field_proof"], "timeout_proof": proof,
            "reviewed_admission": {**original, "disposition": "operational_excluded",
                "reason": REASON, "problems": [], "operational_incidents": [REASON],
                "failure_class": "external_verifier_timeout_with_absent_field_misuse",
                "primary_failure": "external_model_service_timeout",
                "secondary_failure": "workflow_composition_absent_field_misuse",
                "replacement_authorized": True, "identical_execution_required": True,
                "max_operational_replacements": 1, "evaluation_imputed": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != TIMEOUT_DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder"
            or attempt.reason != previous.records.GATE_PROBLEM
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != previous.sha256(Path(__file__))
            or value["projection_reviewer_source_sha256"] != previous.sha256(
                Path(previous.__file__))
            or value["method_reviewer_source_sha256"] != previous.sha256(
                Path(previous.previous.__file__))
            or value["record_reviewer_source_sha256"] != previous.sha256(
                Path(previous.records.__file__))
            or value["execution_sources_sha256"] != previous.previous.frozen_sources(
                root, attempt, SOURCE_PATHS)
            or value["original_evidence_file_sha256"] != previous.previous.evidence_files(
                directory)):
        raise RuntimeError("compound timeout identity/source/evidence drift")
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
        raise RuntimeError("compound timeout proof cannot be reproduced")
    return value


class ProjectionAttemptLedger(previous.ProjectionAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
        for attempt in super().attempts:
            path = self.path.parent / TIMEOUT_DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="operational_excluded", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    path = root / TIMEOUT_DIRECTORY / (attempt.run_id + ".json")
    if not path.exists():
        return previous.effective_admission(root, attempt)
    value = json.loads(path.read_text())
    if provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256:
        raise RuntimeError("effective timeout admission drift")
    return value["reviewed_admission"]
