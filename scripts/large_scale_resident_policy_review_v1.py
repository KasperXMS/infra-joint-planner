"""Exact offline resident-provider refusal review; never retry/censor Agent input.

The resident runner persists both terminal and HTTP audit gates for the same
HTTP400. Keep the historical single-gate reviewer and all measured code frozen.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_provider_policy_review_v1 as legacy
from large_scale_resident_record_review_v1 import RecordAttemptLedger
from large_scale_resident_record_review_v1 import effective_admission as previous_admission

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = "resident-provider-policy-adjudications"
TERMINAL_GATE = "terminal_failure_requires_system_audit"
REASON = legacy.REASON


def review(original: dict[str, Any], api_root: Path,
           events: list[dict[str, Any]]) -> dict[str, Any]:
    terminal = original.get("terminal_failure") or {}
    failures = [e["payload"].get("failure") for e in events if e["event_type"] == "run.failed"]
    if (original.get("reason") != TERMINAL_GATE
            or original.get("problems") != [TERMINAL_GATE, legacy.GATE]
            or original.get("api_audit", {}).get("problems") != [legacy.GATE]
            or terminal.get("code") != "control_plane_failed"
            or terminal.get("exception_type") != "BadRequestError" or failures != [terminal]):
        raise RuntimeError("resident policy review cannot waive other terminal/audit findings")
    # Translate ONLY the duplicate gate/runner label for the existing exact raw
    # HTTP proof. Never change original persisted admission, response or request.
    translated = {**original, "problems": [legacy.GATE],
                  "terminal_failure": {**terminal, "code": "logical_loop_failed"}}
    proof = legacy.review_policy(translated, api_root)["proof"]
    rows = [json.loads(p.read_text()) for p in api_root.glob("*-usage.json")]
    if len({r["call_id"] for r in rows}) != len(rows) or len(proof) != 1:
        raise RuntimeError("resident refusal requires one unique failed HTTP call")
    failed = next(r for r in rows if r["call_id"] == proof[0]["call_id"])
    if (failed["recipient"] != "manager"
            or any(r["finished_utc"] > failed["finished_utc"] for r in rows)
            or not events or events[-1]["event_type"] != "run.failed"):
        raise RuntimeError("terminal refusal does not match the last root Manager call")
    return {"proof": proof, "reviewed_admission": {
        **original, "disposition": "valid", "reason": REASON, "problems": [],
        "failure_class": "provider_input_policy", "replacement_authorized": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != TERMINAL_GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != legacy.sha256(Path(__file__))
            or value["legacy_reviewer_source_sha256"] != legacy.sha256(Path(legacy.__file__))):
        raise RuntimeError("resident policy identity/source/admission drift")
    files = {}
    for p in directory.rglob("*"):
        if p.is_symlink() or not p.resolve().is_relative_to(directory.resolve()):
            raise RuntimeError("resident policy evidence escaped attempt")
        if p.is_file():
            files[str(p.relative_to(directory))] = legacy.sha256(p)
    if files != value["original_evidence_file_sha256"]:
        raise RuntimeError("resident policy original evidence drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").open(encoding="utf-8")]
    actual = review(original, directory / "private/api", events)
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("resident policy proof cannot be reproduced")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    path = root / DIRECTORY / (attempt.run_id + ".json")
    if not path.exists():
        return previous_admission(root, attempt)
    value = json.loads(path.read_text())
    if attempt.reason != REASON or value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("resident policy effective admission mismatch")
    return value["reviewed_admission"]


class ResidentPolicyAttemptLedger(RecordAttemptLedger):
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
