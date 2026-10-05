"""Offline proof of initial-corpus field misuse plus exact provider refusal.

No schema guessing, Agent repair, input censorship, retry, or gate allowlist.
The root had the correct semantic schema; delegation did not forward it. Keep
that information-flow limitation explicit rather than claiming specialists saw it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_compound_review_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

ROOT = previous.ROOT
DIRECTORY = "field-policy-adjudications"
REASON = "audited_initial_corpus_field_misuse_and_provider_policy"
GATES = previous.GATES
sha256 = previous.sha256
SOURCE_PATHS = ("src/infra_joint/operators/retrieval.py",
                "src/infra_joint/control/native_agents.py")


def sources() -> dict[str, str]:
    return {"field": sha256(Path(__file__)), **previous.reviewer_sources()}


def artifact_shapes(root: Path, directory: Path) -> dict[str, dict[str, Any]]:
    """Recheck frozen prepared payloads locally on 4090; never export record text."""
    task = json.loads((directory / "private/task-contract.json").read_text())
    frozen = json.loads((directory / "attempt-freeze.json").read_text())
    after = json.loads((directory / "private/worker-state-after.json").read_text())
    refs = {a["artifact_id"]: a for a in task["artifacts"]}
    result = {}
    for item in frozen["task_receipt"]["artifacts"]:
        artifact_id = item["artifact_id"]
        ref = refs[artifact_id]
        schema = ref.get("content_schema") or {}
        path = Path(item["path"])
        if (path.is_symlink() or not path.resolve().is_relative_to(
                (root / "preparation/task-freeze-002").resolve())
                or sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]
                or item["media_type"] != "application/json"
                or schema.get("kind") != "record_array"):
            raise RuntimeError("initial corpus source/schema/hash/owned path mismatch")
        rows = json.loads(path.read_text())
        field = schema.get("text_field")
        if (not isinstance(field, str) or schema.get("fields", {}).get(field) != "string"
                or not isinstance(rows, list) or not rows
                or len(rows) != schema.get("record_count")
                or not all(isinstance(row, dict) and isinstance(row.get(field), str)
                           for row in rows)):
            raise RuntimeError("declared corpus string field does not match actual records")
        persisted = [a for state in after.values() for a in state["artifacts"]
                     if a["artifact_id"] == artifact_id]
        if (not persisted or any(a["sha256_hex"] != item["sha256"]
                                or a["size_bytes"] != item["bytes"]
                                or a["media_type"] != item["media_type"] for a in persisted)):
            raise RuntimeError("actual Worker input metadata does not match frozen source")
        result[artifact_id] = {"path": str(path), "sha256": item["sha256"],
                               "schema": schema, "record_count": len(rows),
                               "all_declared_fields": sorted(schema["fields"]),
                               "actual_union_fields": sorted({k for row in rows for k in row}),
                               "declared_text_field_valid_in_all_records": True}
    return result


def review(original: dict[str, Any], events: list[dict[str, Any]],
           shapes: dict[str, dict[str, Any]], api_root: Path) -> dict[str, Any]:
    if (original.get("disposition") != "confounder"
            or original.get("problems") != list(GATES)
            or original.get("operational_incidents")):
        raise RuntimeError("field review requires exactly the field and policy findings")
    policy = previous.policy_review.review_policy(
        {**original, "problems": [previous.policy_review.GATE]}, api_root)
    root_inputs = [e["payload"] for e in events
                   if e["event_type"] == "logical.reasoning.input"
                   and e["payload"]["logical_agent_id"] == "manager"]
    if not root_inputs:
        raise RuntimeError("missing actual root input")
    initial = json.loads(root_inputs[0]["input_items"][0]["content"])
    visible = {a["artifact_id"]: a for a in initial["task"]["artifacts"]}
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    physical = {e["payload"]["action_id"]: e["payload"] for e in events
                if e["event_type"] == "physical.execution"}
    completed = {e["payload"]["action_id"] for e in events
                 if e["event_type"] == "action.completed"
                 and e["payload"].get("succeeded") is False}
    graph = next((e["payload"] for e in reversed(events)
                  if e["event_type"] == "workflow.graph.snapshot"), {})
    statuses = {n["action_id"]: n["status"] for n in graph.get("nodes", [])}
    proof, seen = [], set()
    for event in events:
        p = event["payload"]
        if (event["event_type"] != "logical.observation"
                or p.get("failure_code") != "validation_failed"):
            continue
        action_id = p["action_id"]
        action, receipt = actions.get(action_id, {}), physical.get(action_id, {})
        inputs, arguments = action.get("inputs", []), action.get("arguments", {})
        field = arguments.get("text_field", "text")
        failure = receipt.get("failure", {})
        message = f"document field must be text: {field}"
        if (action_id in seen or p.get("succeeded") is not False
                or action.get("action_type") != "tool"
                or action.get("operator") != "bm25_retrieve" or len(inputs) != 1
                or inputs[0] not in shapes or inputs[0] not in visible
                or not isinstance(field, str) or not field
                or field in shapes[inputs[0]]["actual_union_fields"]
                or field in shapes[inputs[0]]["all_declared_fields"]
                or visible[inputs[0]].get("content_schema") != shapes[inputs[0]]["schema"]
                or p.get("failure_message") != message
                or failure.get("failure_message") != message
                or failure.get("failure_code") != "validation_failed"
                or failure.get("operator") != "bm25_retrieve"
                or failure.get("stage") != "execution"
                or not receipt.get("selection", {}).get("selected_agent_id")
                or action_id not in completed or statuses.get(action_id) != "failed"):
            raise RuntimeError("not exact absent initial-corpus field misuse")
        seen.add(action_id)
        proof.append({"action_id": action_id, "action_sha256": provenance_sha256(action),
                      "input_artifact_id": inputs[0], "requested_field": field,
                      "input_sha256": shapes[inputs[0]]["sha256"],
                      "root_received_correct_schema": True, "reached_model_inference": False})
    if not proof:
        raise RuntimeError("no proven initial-corpus field misuse")
    return {"covered_original_findings": list(GATES), "field_misuse_proof": proof,
            "provider_policy_proof": policy["proof"],
            "reviewed_admission": {**original, "disposition": "valid", "reason": REASON,
                                   "problems": [], "failure_class":
                                   "provider_input_policy_with_delegated_corpus_field_misuse",
                                   "replacement_authorized": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("field sidecar identity/path mismatch")
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (attempt.disposition != "confounder" or attempt.reason != GATES[0]
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["run_id"] != attempt.run_id or value["reviewer_sources_sha256"] != sources()):
        raise RuntimeError("field source/original admission drift")
    files = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    if files != set(value["original_evidence_file_sha256"]):
        raise RuntimeError("field proof must bind every original file")
    for relative, digest in value["original_evidence_file_sha256"].items():
        p = directory / relative
        if (p.is_symlink() or not p.resolve().is_relative_to(directory.resolve())
                or sha256(p) != digest):
            raise RuntimeError("original field evidence changed or escaped")
    if value["execution_sources_sha256"] != {
            p: sha256(root / "app" / p) for p in SOURCE_PATHS}:
        raise RuntimeError("operator/delegation implementation drift")
    shapes = artifact_shapes(root, directory)
    trace = directory / "runs" / attempt.run_id / "trace.jsonl"
    actual = review(original, [json.loads(line) for line in trace.read_text().splitlines()],
                    shapes, directory / "private/api")
    if (shapes != value["initial_artifact_shapes"] or actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("field/policy proof cannot be reproduced")
    return value


class FieldAttemptLedger(previous.CompoundAttemptLedger):
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
        return previous.effective_admission(root, attempt)
    value = json.loads((root / DIRECTORY / (attempt.run_id + ".json")).read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective field admission/ledger mismatch")
    return value["reviewed_admission"]


def create_review(root: Path, run_id: str) -> dict[str, Any]:
    if sys.platform != "linux" or root.resolve() != ROOT:
        raise RuntimeError("field evidence stays on the experiment controller")
    import large_scale_queue_v1 as queue

    with QueueLease(root / "queue-lease.json"):
        previous.require_stopped(root, ignore_pid=os.getpid())
        cells = queue.schedule()
        ledger = FieldAttemptLedger(root / "phase1-attempts.jsonl", tuple(c.cell_id for c in cells),
                                    queue.schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("outstanding attempt cannot be classified")
        attempt = next(a for a in ledger.attempts if a.run_id == run_id)
        directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
        config = queue.frozen._yaml(root / "cell-configs" / (run_id + ".yaml"))
        prices, _ = queue.verified_prices(root, root / "app")
        original = json.loads((directory / "admission.json").read_text())
        if provenance_sha256(queue.admit(directory, config, prices)) != attempt.receipt_sha256:
            raise RuntimeError("independent full admission differs from original field finding")
        shapes = artifact_shapes(root, directory)
        trace = directory / "runs" / run_id / "trace.jsonl"
        proof = review(original, [json.loads(line) for line in trace.read_text().splitlines()],
                       shapes, directory / "private/api")
        value = {"version": "exact-field-policy-review-v1", "run_id": run_id,
                 "original_admission_sha256": attempt.receipt_sha256,
                 "original_execution_sha256": attempt.execution_sha256,
                 "reviewer_sources_sha256": sources(),
                 "execution_sources_sha256": {p: sha256(root / "app" / p) for p in SOURCE_PATHS},
                 "initial_artifact_shapes": shapes,
                 "original_evidence_file_sha256": {str(p.relative_to(directory)): sha256(p)
                     for p in sorted(directory.rglob("*")) if p.is_file()}, **proof,
                 "reviewed_admission_sha256": provenance_sha256(proof["reviewed_admission"]),
                 "formal_execution_changed": False, "replacement_authorized": False,
                 "specialist_schema_visibility_not_assumed": True}
        path = root / DIRECTORY / (run_id + ".json")
        queue.write_new(path, value)
        verify_sidecar(path, attempt)
        return {"adjudication_sha256": provenance_sha256(value),
                "evidence_files": len(value["original_evidence_file_sha256"]),
                "field_failures": len(proof["field_misuse_proof"]), "rerun": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(create_review(ROOT, args.run_id)))
