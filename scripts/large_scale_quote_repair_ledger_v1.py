"""Exact retrospective Quote confounders, outside the measured Agent runtime.

Append new proof, never rewrite a nominal settlement or authorize semantic retries.
The inherited ledger still enforces order, outstanding attempts and repair freezes.
"""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256 as bytes_sha256
from pathlib import Path
from typing import Any

from large_scale_adjudication_v1 import sha256
from large_scale_resident_policy_review_v1 import ResidentPolicyAttemptLedger
from large_scale_resident_policy_review_v1 import effective_admission as previous_admission

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = "quote-integrity-adjudications"
REASON = "quote_hash_serialization_confounder"


def original_action_sha256(action: dict[str, Any]) -> str:
    """Replay the original Quote byte encoding, not receipt provenance encoding."""
    payload = json.dumps(action, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    return bytes_sha256(payload).hexdigest()


def review(original: dict[str, Any], events: list[dict[str, Any]],
           api_root: Path) -> dict[str, Any]:
    if original.get("disposition") != "valid" or original.get("problems"):
        raise RuntimeError("retrospective review requires an otherwise nominally valid attempt")
    quotes = {e["payload"]["quote"]["quote_id"]: e["payload"] for e in events
              if e["event_type"] == "logical.cost_quote.created"}
    failures = [(i, e["payload"]) for i, e in enumerate(events)
                if e["event_type"] == "logical.cost_quote.rejected"
                and e["payload"]["failure_code"] == "quoted_action_mutated"]
    if not failures:
        raise RuntimeError("ordinary semantic/quality failure is not a Quote integrity confounder")
    calls = {}
    for path in sorted(api_root.glob("*-response.json")):
        value = json.loads(path.read_text())
        for choice in value.get("choices", []):
            for call in choice.get("message", {}).get("tool_calls", []) or []:
                calls[call["id"]] = (call, path)
    proof = []
    for index, failure in failures:
        control = next((e["payload"] for e in reversed(events[:index])
                        if e["event_type"] == "logical.cost_quote.control_timing"
                        and e["payload"]["operation"] == "authorize"), None)
        if control is None or control["succeeded"] is not False:
            raise RuntimeError("mutation rejection lacks exact failed authorization")
        quote_id = control["identifier"]
        created = quotes[quote_id]
        call_id = failure["action_id"].removeprefix("manager:")
        call, path = calls[call_id]
        action = created["action"]
        requirements = action.get("requirements", {})
        if (call["function"]["name"] != "commit_quote"
                or json.loads(call["function"]["arguments"]) != {"quote_id": quote_id}
                or action.get("action_type") != "model"
                or original_action_sha256(action) != created["quote"]["action_sha256"]
                or not any(len(requirements.get(key, [])) > 1
                           for key in ("modalities", "required_capabilities"))):
            raise RuntimeError("exact unchanged multi-set model quote proof failed")
        proof.append({"quote_id": quote_id, "action_id": action["action_id"],
                      "commit_call_id": call_id, "commit_only_supplied_quote_id": True,
                      "response_file": path.name, "response_sha256": sha256(path)})
    corrected = {**original, "disposition": "confounder", "reason": REASON,
                 "problems": [REASON], "failure_class": "serialization_runtime_defect",
                 "ordinary_semantic_failure": False, "replacement_authorized": False}
    return {"proof": proof, "reviewed_admission": corrected}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    freeze = json.loads((root / "execution-freeze-001.json").read_text())
    source = root / "app/src/infra_joint/control/quote.py"
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "valid"
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or provenance_sha256(freeze) != attempt.execution_sha256
            or sha256(source) != freeze["source_sha256"]["src/infra_joint/control/quote.py"]
            or value["frozen_quote_source_sha256"] != sha256(source)
            or value["reviewer_source_sha256"] != sha256(Path(__file__))):
        raise RuntimeError("Quote retrospective identity/source/admission drift")
    files = {}
    for file in directory.rglob("*"):
        if file.is_symlink() or not file.resolve().is_relative_to(directory.resolve()):
            raise RuntimeError("Quote retrospective evidence escaped attempt")
        if file.is_file():
            files[str(file.relative_to(directory))] = sha256(file)
    if files != value["original_evidence_file_sha256"]:
        raise RuntimeError("original Quote evidence changed")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").read_text().splitlines()]
    actual = review(original, events, directory / "private/api")
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("Quote retrospective proof cannot be reproduced")
    return value


class QuoteRepairAttemptLedger(ResidentPolicyAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        # Like the existing SnapshotAttemptLedger: validate the effective view
        # once per membership calculation, not once for every scheduled cell.
        # No cross-call cache, source/evidence bypass or changed admission rule.
        admitted = {a.cell_id for a in self.attempts if a.disposition == "valid"}
        return tuple(cell for cell in self.cells if cell in admitted)

    def _apply(self, record: dict[str, object]) -> None:
        if record["event"] != "quote_integrity_confounded":
            super()._apply(record)
            return
        run = str(record["run_id"])
        original = self._attempts.get(run)
        if original is None or original.disposition != "valid" or self.pending:
            raise RuntimeError("only a settled nominal attempt may be retrospectively audited")
        path = self.path.parent / DIRECTORY / (run + ".json")
        value = verify_sidecar(path, original)
        if (record["review_file_sha256"] != sha256(path)
                or record["original_admission_sha256"] != original.receipt_sha256
                or record["reviewed_admission_sha256"] != value["reviewed_admission_sha256"]):
            raise RuntimeError("retrospective journal proof digest mismatch")
        self._attempts[run] = replace(original, disposition="confounder", reason=REASON,
                                      receipt_sha256=value["reviewed_admission_sha256"])

    def invalidate_quote_integrity(self, run_id: str) -> None:
        if self.pending:
            raise RuntimeError("cannot invalidate while an attempt may still be live")
        original = self._attempts[run_id]
        path = self.path.parent / DIRECTORY / (run_id + ".json")
        value = verify_sidecar(path, original)
        self._append({"event": "quote_integrity_confounded", "run_id": run_id,
                      "original_admission_sha256": original.receipt_sha256,
                      "review_file_sha256": sha256(path),
                      "reviewed_admission_sha256": value["reviewed_admission_sha256"]})


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous_admission(root, attempt)
    value = json.loads((root / DIRECTORY / (attempt.run_id + ".json")).read_text())
    corrected = value["reviewed_admission"]
    if provenance_sha256(corrected) != attempt.receipt_sha256:
        raise RuntimeError("retrospective effective admission drift")
    return corrected
