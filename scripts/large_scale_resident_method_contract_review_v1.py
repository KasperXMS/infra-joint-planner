"""Exact E tool-space exclusions and source-bound record review, offline only.

No Agent feedback, evidence rewrite, semantic retries, or historical reviewer edits.
Every effective view revalidates its actual immutable evidence and execution epoch.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_quote_repair_ledger_v1 as parent
import large_scale_resident_record_review_v1 as records
from large_scale_adjudication_v1 import sha256

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = "E-query-contract-adjudications"
RECORD_DIRECTORY = "source-bound-record-field-adjudications"
REASON = "E_optional_query_tool_space_confounder"
BUG_PROOF = "adjudications/E-query-contract-confounder-001.json"
BUG_SHA256 = "6ee115bbae667060bb19209cb7e1cbf1ae1c3e641d7d2378f55addb7a2cc111c"
SOURCE = "src/infra_joint/control/bde_native.py"
OLD_SOURCE_SHA256 = "a5faddc67b76fa9c4340bb608f6697fc2ec0b71014f7e12a11d08e3c06e6dc51"
APPS = ("app", "app-quote-integrity-repair-002", "app-input-cardinality-repair-003",
        "app-E-query-contract-repair-004")


def frozen_sources(root: Path, attempt: Attempt, paths: tuple[str, ...]) -> dict[str, str]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for index, app in enumerate(APPS, 1):
        file = root / f"execution-freeze-{index:03d}.json"
        if file.exists():
            value = json.loads(file.read_text())
            if provenance_sha256(value) == attempt.execution_sha256:
                matches.append((app, value))
    if len(matches) != 1:
        raise RuntimeError("exact original execution epoch is required")
    app, freeze = matches[0]
    actual = {p: sha256(root / app / p) for p in paths}
    if any(actual[p] != freeze["source_sha256"].get(p) for p in paths):
        raise RuntimeError("original frozen execution source drift")
    return actual


def evidence_files(directory: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in directory.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise RuntimeError("original evidence must not follow symlinks")
        if path.is_file():
            files[str(path.relative_to(directory))] = sha256(path)
    return files


def review_e(original: dict[str, Any], events: list[dict[str, Any]],
             api: Path) -> dict[str, Any]:
    if original.get("disposition") != "valid" or original.get("problems"):
        raise RuntimeError("E review cannot waive unrelated original findings")
    starts = [e["payload"] for e in events if e["event_type"] == "method.variant.start"]
    if len(starts) != 1 or starts[0].get("variant") != "route-e-v0":
        raise RuntimeError("only an actual E route may receive this review")
    proof: list[dict[str, Any]] = []
    for usage_path in sorted(api.glob("*-usage.json")):
        usage = json.loads(usage_path.read_text())
        if usage["recipient"] != "manager":
            continue
        call = usage["call_id"]
        if Path(call).name != call or usage_path.name != call + "-usage.json":
            raise RuntimeError("exact API call identity required")
        request_path = api / (call + "-request.json")
        request = json.loads(request_path.read_text())
        names = [t.get("function", {}).get("name", "") for t in request.get("tools", [])]
        extras = sorted(n for n in names if n.startswith("estimate_"))
        if not extras or "invoke_model" not in names:
            raise RuntimeError("every affected E Manager request must prove query exposure")
        proof.append({"request_file": request_path.name, "request_sha256": sha256(request_path),
                      "usage_file": usage_path.name, "usage_sha256": sha256(usage_path),
                      "estimate_tool_names": extras})
    if not proof:
        raise RuntimeError("actual Manager tool schemas, not a source-only inference, are required")
    return {"proof": proof, "reviewed_admission": {
        **original, "disposition": "confounder", "reason": REASON, "problems": [REASON],
        "failure_class": "method_contract_tool_space_defect", "ordinary_semantic_failure": False,
        "replacement_authorized": False,
    }}


def verify_e(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original_raw = json.loads((directory / "admission.json").read_text())
    original = parent.effective_admission(root, attempt)
    proof_file = root / BUG_PROOF
    bug = json.loads(proof_file.read_text())
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "valid" or not attempt.cell_id.endswith("-E")
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_raw_admission_sha256"] != provenance_sha256(original_raw)
            or value["original_execution_sha256"] != attempt.execution_sha256
            or sha256(proof_file) != BUG_SHA256 or value["bug_proof_sha256"] != BUG_SHA256
            or attempt.run_id not in bug["affected_effective_run_ids"]
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["frozen_source_sha256"] != frozen_sources(root, attempt, (SOURCE,))[SOURCE]
            or value["frozen_source_sha256"] != OLD_SOURCE_SHA256
            or value["original_evidence_file_sha256"] != evidence_files(directory)):
        raise RuntimeError("E retrospective identity, scope, source or evidence drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").read_text().splitlines()]
    actual = review_e(original, events, directory / "private/api")
    if (actual != {k: value[k] for k in actual}
            or value["reviewed_admission_sha256"]
            != provenance_sha256(actual["reviewed_admission"])):
        raise RuntimeError("E retrospective proof cannot be reproduced")
    return value


def verify_record(path: Path, attempt: Attempt) -> dict[str, Any]:
    """Reuse exact record proof, but bind its actual epoch rather than assume app001."""
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != RECORD_DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != records.GATE_PROBLEM
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["record_reviewer_source_sha256"] != sha256(Path(records.__file__))
            or value["execution_sources_sha256"] != frozen_sources(root, attempt,
                                                                    records.SOURCE_PATHS)
            or value["original_evidence_file_sha256"] != evidence_files(directory)):
        raise RuntimeError("source-bound record identity, source or evidence drift")
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    for aid, shape in value["materialized_shapes"].items():
        metadata = {k: shape[k] for k in ("artifact_id", "media_type", "size_bytes", "sha256_hex")}
        replicas = [a for state in states.values() for a in state["artifacts"]
                    if a["artifact_id"] == aid]
        if not replicas or any(a != metadata for a in replicas):
            raise RuntimeError("record shape/actual replica mismatch")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").read_text().splitlines()]
    actual = records.review(original, events, value["materialized_shapes"])
    if (actual != {k: value[k] for k in actual}
            or value["reviewed_admission_sha256"]
            != provenance_sha256(actual["reviewed_admission"])):
        raise RuntimeError("source-bound record proof cannot be reproduced")
    return value


class MethodContractAttemptLedger(parent.QuoteRepairAttemptLedger):
    def __init__(self, path: Path, cells: tuple[str, ...], schedule_sha256: str) -> None:
        self._e_reviews: dict[str, str] = {}
        super().__init__(path, cells, schedule_sha256)

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
        for attempt in super().attempts:
            path = self.path.parent / RECORD_DIRECTORY / (attempt.run_id + ".json")
            if path.exists() and attempt.disposition == "confounder":
                value = verify_record(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=records.REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            if attempt.run_id in self._e_reviews:
                path = self.path.parent / DIRECTORY / (attempt.run_id + ".json")
                value = verify_e(path, attempt)
                if sha256(path) != self._e_reviews[attempt.run_id]:
                    raise RuntimeError("durable E review file drift")
                attempt = replace(attempt, disposition="confounder", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)

    def _apply(self, record: dict[str, object]) -> None:
        if record["event"] == "generic_repair" and str(record["run_id"]) in self._e_reviews:
            run = str(record["run_id"])
            original = next(a for a in self.attempts if a.run_id == run)
            new_execution = str(record["new_execution_sha256"])
            digests = (str(record["repair_audit_sha256"]), new_execution)
            if (original.disposition != "confounder" or run in self._repairs
                    or record["original_admission_sha256"] != original.receipt_sha256
                    or new_execution == original.execution_sha256
                    or any(len(d) != 64 or any(c not in "0123456789abcdef" for c in d)
                           for d in digests)):
                raise RuntimeError("E repair requires exact unresolved proof and new freeze")
            self._repairs[run] = new_execution
            return
        if record["event"] != "E_query_contract_confounded":
            super()._apply(record)
            return
        run = str(record["run_id"])
        original = next((a for a in super().attempts if a.run_id == run), None)
        if original is None or original.disposition != "valid" or self.pending:
            raise RuntimeError("E invalidation requires a settled original valid attempt")
        if run in self._e_reviews:
            raise RuntimeError("duplicate E retrospective invalidation")
        path = self.path.parent / DIRECTORY / (run + ".json")
        value = verify_e(path, original)
        if (record["review_file_sha256"] != sha256(path)
                or record["original_admission_sha256"] != original.receipt_sha256
                or record["reviewed_admission_sha256"] != value["reviewed_admission_sha256"]):
            raise RuntimeError("E retrospective journal proof drift")
        # Keep the raw settlement and prior exact reviews intact. In particular,
        # an otherwise valid E run may already have an absent-field adjudication.
        self._e_reviews[run] = sha256(path)

    def invalidate_e(self, run_id: str) -> None:
        if self.pending:
            raise RuntimeError("cannot invalidate E while an attempt may still be live")
        original = next(a for a in super().attempts if a.run_id == run_id)
        path = self.path.parent / DIRECTORY / (run_id + ".json")
        value = verify_e(path, original)
        self._append({"event": "E_query_contract_confounded", "run_id": run_id,
                      "original_admission_sha256": original.receipt_sha256,
                      "review_file_sha256": sha256(path),
                      "reviewed_admission_sha256": value["reviewed_admission_sha256"]})


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    directory = DIRECTORY if attempt.reason == REASON else (
        RECORD_DIRECTORY if attempt.reason == records.REASON
        and (root / RECORD_DIRECTORY / (attempt.run_id + ".json")).exists() else None)
    if directory is None:
        return parent.effective_admission(root, attempt)
    value = json.loads((root / directory / (attempt.run_id + ".json")).read_text())
    if provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256:
        raise RuntimeError("effective source-bound admission drift")
    return value["reviewed_admission"]
