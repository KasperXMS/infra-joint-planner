"""Offline PhaseII field proof using already verified, hash-identical record shapes.

No new corpus/store body scans, executable aliases, Agent feedback or retries.
Keep original admissions/journal and the exact historical model-JSON reviewer.
This module supplies an effective ledger only, not permission to restart a queue.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_field_only_review_v1 as field
import large_scale_resident_phase2_read_once_v1 as parent

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

core = parent.previous
bindings = core.bindings
DIRECTORY = "phase2-record-field-adjudications"


def sources() -> dict[str, str]:
    return {Path(p).name: core.legacy.sha256(Path(p)) for p in (
        __file__, field.__file__, bindings.__file__, bindings.records.__file__,
        core.__file__, parent.__file__)}


def historical_attempt(root: Path, run_id: str) -> Attempt:
    if Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase1-"):
        raise RuntimeError("owned historical PhaseI run required")
    path = root / "phase1-attempts.jsonl"
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("owned historical journal required")
    with path.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    reservations = [r for r in rows if r["event"] == "reserved" and r["run_id"] == run_id]
    settlements = [r for r in rows if r["event"] == "settled" and r["run_id"] == run_id]
    if len(reservations) != 1 or len(settlements) != 1:
        raise RuntimeError("unique raw historical reservation/settlement required")
    r, s = reservations[0], settlements[0]
    return Attempt(r["cell_id"], run_id, r["attempt_index"], r["execution_sha256"],
                   s["disposition"], s["reason"], s["receipt_sha256"])


def reuse_shapes(task: dict[str, Any], states: dict[str, Any],
                 historical: dict[str, Any], ids: set[str]) -> dict[str, Any]:
    """Pure metadata binding; never open a source, preparation payload or store."""
    visible = {a["artifact_id"]: a for a in task["artifacts"]}
    if len(visible) != len(task["artifacts"]):
        raise RuntimeError("duplicate task artifact identities")
    result: dict[str, Any] = {}
    for aid in sorted(ids):
        if aid not in visible:
            raise RuntimeError("only initial visible artifacts may reuse historical shapes")
        replicas = [a for state in states.values() for a in state["artifacts"]
                    if a["artifact_id"] == aid]
        if not replicas or any(a != replicas[0] for a in replicas):
            raise RuntimeError("current record replicas missing or inconsistent")
        matches = [s for s in historical["materialized_shapes"].values()
                   if all(s[k] == replicas[0][k]
                          for k in ("media_type", "size_bytes", "sha256_hex"))]
        if len(matches) != 1:
            raise RuntimeError("unique hash/bytes/media-identical historical shape required")
        shape, schema = matches[0], visible[aid]["content_schema"]
        fields = schema.get("fields", {})
        if (replicas[0]["media_type"] != "application/json"
                or shape["record_count"] <= 0 or not shape["all_records_have_string_body"]
                or schema.get("kind") != "record_array" or schema.get("text_field") != "body"
                or not isinstance(fields, dict) or fields.get("body") != "string"
                or sorted(fields) != sorted(shape["actual_union_fields"])
                or schema.get("record_count") != shape["record_count"]):
            raise RuntimeError("visible record schema must match verified historical shape")
        result[aid] = {"actual_union_fields": shape["actual_union_fields"],
                       "all_declared_fields": sorted(fields), "schema": schema,
                       "sha256": shape["sha256_hex"]}
    return result


def sdk_schema_proof(api: Path, task: dict[str, Any]) -> list[dict[str, Any]]:
    """Actual persisted Manager wire requests, not merely pre-wire trace input."""
    proof: list[dict[str, Any]] = []
    for usage_path in sorted(api.glob("*-usage.json")):
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        if usage["recipient"] != "manager":
            continue
        call = usage["call_id"]
        request_path = api / (call + "-request.json")
        if (Path(call).name != call or usage_path.name != call + "-usage.json"
                or usage_path.is_symlink() or request_path.is_symlink()):
            raise RuntimeError("owned exact Manager request/usage identity required")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        matches = []
        for message in request.get("messages", []):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            texts = ([p.get("text", "") for p in content if p.get("type") == "text"]
                     if isinstance(content, list) else [content])
            for text in texts:
                if not isinstance(text, str):
                    continue
                try:
                    value = json.loads(text)
                except ValueError:
                    continue
                if isinstance(value, dict) and "task" in value:
                    matches.append(value["task"])
        if len(matches) != 1 or matches[0] != task:
            raise RuntimeError("actual Manager request must contain the exact visible task schema")
        proof.append({"request_file": request_path.name,
                      "request_sha256": core.legacy.sha256(request_path),
                      "usage_file": usage_path.name,
                      "usage_sha256": core.legacy.sha256(usage_path),
                      "task_view_sha256": provenance_sha256(task)})
    if not proof:
        raise RuntimeError("actual Manager requests required")
    return proof


def proof(root: Path, attempt: Attempt, parent_path: Path,
          historical_path: Path) -> dict[str, Any]:
    if (parent_path.is_symlink() or parent_path.resolve().parent != root
            or not parent_path.name.startswith("phase2-control-freeze-")):
        raise RuntimeError("owned original PhaseII parent required")
    saved = json.loads(parent_path.read_text(encoding="utf-8"))
    if (saved["source_sha256"] != core.previous.source_bindings()
            or saved["execution_freeze_sha256"] != core.frozen.verify_freeze()):
        raise RuntimeError("original parent/atomic source drift")
    directory = core.evidence(root, attempt)
    original = json.loads((directory / "admission.json").read_text(encoding="utf-8"))
    if (attempt.disposition != "confounder" or attempt.reason != field.GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or attempt.execution_sha256 != saved["execution_freeze_sha256"]):
        raise RuntimeError("exact original settled field gate required")
    config = core.frozen.frozen._yaml(root / "cell-configs" / (attempt.run_id + ".yaml"))
    if (core.previous.previous.admission(directory, config, Path(saved["pricing_path"]))
            != original
            or json.loads((directory / "process-exit.json").read_text())["returncode"] != 0
            or json.loads((directory / "worker-shutdown.json").read_text())[
                "verified_exited"] is not True
            or json.loads((directory / "private/residency-validation.json").read_text())[
                "passed"] is not True):
        raise RuntimeError("full original admission/exit/residency must reproduce")
    if (historical_path.is_symlink() or historical_path.parent.is_symlink()
            or historical_path.resolve().parent != root / bindings.RECORD_DIRECTORY
            or not historical_path.name.endswith(".json")):
        raise RuntimeError("owned source-bound historical record proof required")
    old_attempt = historical_attempt(root, historical_path.stem)
    historical = bindings.verify_record(historical_path, old_attempt)
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    root_inputs = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.input"
                   and e["payload"]["logical_agent_id"] == "manager"]
    if not root_inputs:
        raise RuntimeError("actual root input missing")
    task = json.loads(root_inputs[0]["input_items"][0]["content"])["task"]
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    ids = {aid for e in events if e["event_type"] == "logical.observation"
           and e["payload"].get("failure_code") == "validation_failed"
           for aid in actions[e["payload"]["action_id"]]["inputs"]}
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    shapes = reuse_shapes(task, states, historical, ids)
    reviewed = field.review(original, events, shapes)
    wire = sdk_schema_proof(directory / "private/api", task)
    if len(wire) != len(root_inputs):
        raise RuntimeError("every actual Manager turn must have its schema wire proof")
    paths = (*bindings.records.SOURCE_PATHS, core.SOURCES[0])
    actual_sources = bindings.frozen_sources(root, attempt, paths)
    worker_app = root / "app-input-cardinality-repair-003"
    worker_freeze = root / "execution-freeze-003.json"
    worker_contract = json.loads(worker_freeze.read_text())["source_sha256"]
    if any(actual_sources[p] != worker_contract.get(p)
           or core.legacy.sha256(worker_app / p) != actual_sources[p] for p in paths):
        raise RuntimeError("actual Worker003/atomic004 operator sources must agree")
    return {"version": "phase2-hash-bound-initial-field-review-v1", **reviewed,
            "run_id": attempt.run_id, "original_admission_sha256": attempt.receipt_sha256,
            "original_execution_sha256": attempt.execution_sha256,
            "parent_control_path": str(parent_path),
            "parent_control_file_sha256": core.legacy.sha256(parent_path),
            "historical_sidecar_path": str(historical_path),
            "historical_sidecar_file_sha256": core.legacy.sha256(historical_path),
            "historical_raw_attempt": {"cell_id": old_attempt.cell_id,
                                       "run_id": old_attempt.run_id,
                                       "execution_sha256": old_attempt.execution_sha256,
                                       "receipt_sha256": old_attempt.receipt_sha256},
            "reused_initial_shapes": shapes, "actual_manager_schema_wire_proof": wire,
            "execution_sources_sha256": actual_sources,
            "worker_freeze_file_sha256": core.legacy.sha256(worker_freeze),
            "reviewer_sources_sha256": sources(),
            "original_evidence_file_sha256": bindings.evidence_files(directory),
            "reviewed_admission_sha256": provenance_sha256(reviewed["reviewed_admission"]),
            "new_store_or_corpus_body_decoded": False, "online_feedback": False,
            "formal_execution_changed": False, "replacement_authorized": False}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact PhaseII record sidecar required")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value != proof(root, attempt, Path(value["parent_control_path"]),
                      Path(value["historical_sidecar_path"])):
        raise RuntimeError("field sidecar/evidence/source drift")
    return value


class FieldReviewedAttemptLedger(parent.ReadOnceAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for attempt in super().attempts:
            path = self.path.parent / DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                if (self.path.parent / core.DIRECTORY / path.name).exists():
                    raise RuntimeError("overlapping field and model-JSON reviews prohibited")
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=field.REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != field.REASON:
        return core.effective_admission(root, attempt)
    path = root / DIRECTORY / (attempt.run_id + ".json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective field admission/ledger mismatch")
    return value["reviewed_admission"]


def create_review(run_id: str, parent_path: Path, historical_path: Path) -> dict[str, Any]:
    core.frozen.require_remote()
    root = core.frozen.ROOT
    core.previous.gate.evidence.private.assert_inactive(root)
    saved, cells = core.previous.checked_control(parent_path)
    journal = root / "phase2-attempts.jsonl"
    if not journal.is_file():
        raise RuntimeError("review cannot initialize a missing journal")
    before = journal.read_bytes()
    with QueueLease(root / "queue-lease.json"):
        ledger = FieldReviewedAttemptLedger(journal, tuple(c.cell_id for c in cells),
                                           saved["phase2_schedule_sha256"])
        if ledger.pending:
            raise RuntimeError("possibly-live pending actions cannot be reviewed")
        attempt = next(a for a in ledger.original_attempts if a.run_id == run_id)
        value = proof(root, attempt, parent_path, historical_path)
        path = root / DIRECTORY / (run_id + ".json")
        path.parent.mkdir(exist_ok=True)
        core.frozen.write_new(path, value)
        verify_sidecar(path, attempt)
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change original journal")
    return {"sidecar_path": str(path), "sha256": core.legacy.sha256(path),
            "confirmed_field_failures": len(value["field_misuse_proof"]),
            "actual_manager_requests": len(value["actual_manager_schema_wire_proof"]),
            "retry": False, "new_store_or_corpus_body_decoded": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--parent-control", required=True, type=Path)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.run_id, args.parent_control, args.historical_sidecar)))
