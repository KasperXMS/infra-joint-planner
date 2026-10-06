"""Offline absent-field proof through successful body-preserving projections.

This is a new audit view, not a modification of historical reviewers or Agent
execution. No field aliases, schema repair, retries, or validation-error waiver.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import large_scale_resident_method_contract_review_v1 as previous
import large_scale_resident_record_review_v1 as records
from large_scale_adjudication_v1 import sha256

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = "projected-record-field-adjudications"
REASON = "audited_body_preserving_projection_absent_field_misuse"


def review(original: dict[str, Any], events: list[dict[str, Any]],
           shapes: dict[str, Any]) -> dict[str, Any]:
    if (original.get("disposition") != "confounder"
            or original.get("problems") != [records.GATE_PROBLEM]
            or original.get("operational_incidents")):
        raise RuntimeError("projection review cannot waive other findings")
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    physical = {e["payload"]["action_id"]: e["payload"] for e in events
                if e["event_type"] == "physical.execution"}
    observations = {e["payload"]["action_id"]: e["payload"] for e in events
                    if e["event_type"] == "logical.observation"}
    for kind, indexed in (("logical.action.prepared", actions),
                          ("physical.execution", physical), ("logical.observation", observations)):
        if len(indexed) != sum(e["event_type"] == kind for e in events):
            raise RuntimeError("duplicate action evidence")
    producers: dict[str, dict[str, Any]] = {}
    for action in actions.values():
        if observations.get(action["action_id"], {}).get("succeeded") is not True:
            continue
        for output in action.get("outputs", []):
            identifier = output["artifact_id"]
            if identifier in producers:
                raise RuntimeError("ambiguous artifact producer")
            producers[identifier] = action
    root_input = next(e["payload"] for e in events if e["event_type"] == "logical.reasoning.input"
                      and e["payload"]["logical_agent_id"] == "manager")
    task = json.loads(root_input["input_items"][0]["content"])["task"]
    initial = {a["artifact_id"]: a for a in task["artifacts"]}

    def ancestry(identifier: str, seen: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
        if identifier in seen:
            raise RuntimeError("cyclic record provenance")
        if identifier in initial:
            schema = initial[identifier].get("content_schema", {})
            if (schema.get("kind") != "record_array" or schema.get("text_field") != "body"
                    or schema.get("fields", {}).get("body") != "string"):
                raise RuntimeError("initial body schema not established")
            return []
        action = producers.get(identifier, {})
        operator, inputs, args = (action.get("operator"), action.get("inputs", []),
                                  action.get("arguments", {}))
        receipt = physical.get(action.get("action_id", ""), {})
        if (action.get("action_type") != "tool" or not inputs or receipt.get("failure")
                or not receipt.get("selection", {}).get("selected_agent_id")):
            raise RuntimeError("producer must have successful physical execution")
        if operator == "bm25_retrieve":
            if len(inputs) != 1 or args.get("text_field") != "body":
                raise RuntimeError("retrieval did not preserve the declared body field")
        elif operator == "select_fields":
            fields = args.get("fields")
            if (len(inputs) != 1 or not isinstance(fields, list) or "body" not in fields
                    or not all(isinstance(field, str) for field in cast(list[Any], fields))):
                raise RuntimeError("projection must retain the original body field")
        elif operator != "aggregate_artifacts":
            raise RuntimeError("unknown record transformation")
        upstream = [item for source in inputs for item in ancestry(source, seen | {identifier})]
        return [*upstream, {"artifact_id": identifier, "producer_action_id": action["action_id"],
                           "operator": operator, "action_sha256": provenance_sha256(action),
                           "body_preserved": True}]

    failures = {aid for aid, obs in observations.items()
                if obs.get("failure_code") == "validation_failed"}
    physical_failures = {aid for aid, p in physical.items()
                         if cast(dict[str, Any], p.get("failure") or {}).get(
                             "failure_code") == "validation_failed"}
    if not failures or failures != physical_failures:
        raise RuntimeError("every validation failure needs exact proof")
    proof: list[dict[str, Any]] = []
    for aid in sorted(failures):
        action, obs, receipt = actions.get(aid, {}), observations[aid], physical[aid]
        inputs = action.get("inputs", [])
        if len(inputs) != 1 or inputs[0] not in shapes:
            raise RuntimeError("exact materialized input required")
        shape, failure = shapes[inputs[0]], receipt.get("failure", {})
        field = action.get("arguments", {}).get("text_field", "text")
        message = f"document field must be text: {field}"
        if (action.get("action_type") != "tool" or action.get("operator") != "bm25_retrieve"
                or not isinstance(field, str) or not field
                or shape.get("artifact_id") != inputs[0] or shape.get("record_count", 0) <= 0
                or shape.get("media_type") != "application/json"
                or not shape.get("all_records_have_string_body")
                or field in shape.get("actual_union_fields", [])
                or "body" not in shape.get("actual_union_fields", [])
                or obs.get("succeeded") is not False
                or obs.get("owner_agent_id") != action.get("owner_agent_id")
                or obs.get("failure_message") != message
                or failure.get("failure_message") != message
                or failure.get("operator") != "bm25_retrieve"
                or failure.get("stage") != "execution"
                or not receipt.get("selection", {}).get("selected_agent_id")):
            raise RuntimeError("not exact absent-field misuse on materialized records")
        path = ancestry(inputs[0])
        if not any(item["operator"] == "select_fields" for item in path):
            raise RuntimeError("historical whole-record proof must use its existing reviewer")
        proof.append({"action_id": aid, "owner_agent_id": action["owner_agent_id"],
                      "action_sha256": provenance_sha256(action), "input_artifact_id": inputs[0],
                      "input_sha256": shape["sha256_hex"], "missing_fields": [field],
                      "root_initial_schema_correct": True,
                      "specialist_received_artifact_schema": None,
                      "reached_model_inference": False, "successful_body_preserving_path": path})
    return {"projected_record_field_proof": proof, "reviewed_admission": {
        **original, "disposition": "valid", "reason": REASON, "problems": [],
        "failure_class": "workflow_composition_absent_field_misuse",
        "replacement_authorized": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != records.GATE_PROBLEM
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["previous_reviewer_source_sha256"] != sha256(Path(previous.__file__))
            or value["record_reviewer_source_sha256"] != sha256(Path(records.__file__))
            or value["execution_sources_sha256"] != previous.frozen_sources(root, attempt,
                                                                           records.SOURCE_PATHS)
            or value["original_evidence_file_sha256"] != previous.evidence_files(directory)):
        raise RuntimeError("projection sidecar identity/source/evidence drift")
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    for identifier, shape in value["materialized_shapes"].items():
        metadata = {k: shape[k] for k in ("artifact_id", "media_type", "size_bytes", "sha256_hex")}
        replicas = [a for state in states.values() for a in state["artifacts"]
                    if a["artifact_id"] == identifier]
        if not replicas or any(a != metadata for a in replicas):
            raise RuntimeError("materialized shape/actual replica drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").read_text().splitlines()]
    actual = review(original, events, value["materialized_shapes"])
    if (actual != {k: value[k] for k in actual}
            or value["reviewed_admission_sha256"]
            != provenance_sha256(actual["reviewed_admission"])):
        raise RuntimeError("projection proof cannot be reproduced")
    return value


class ProjectionAttemptLedger(previous.MethodContractAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
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
    if provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256:
        raise RuntimeError("effective projection admission drift")
    return value["reviewed_admission"]
