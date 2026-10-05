"""Offline proof of absent-field misuse on materialized record arrays.

No Agent feedback, field aliases, retries or generic validation-error waiver.
Body inspection stays on its owning device while measured execution is inactive.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from large_scale_adjudication_v1 import GATE_PROBLEM, sha256
from large_scale_provider_policy_review_v1 import effective_admission as previous_admission
from large_scale_resident_private_evidence_v1 import HOSTS, assert_inactive
from large_scale_snapshot_v1 import SnapshotAttemptLedger

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = "record-field-adjudications"
REASON = "audited_materialized_record_absent_field_misuse"
SOURCE_PATHS = ("src/infra_joint/operators/retrieval.py",
                "src/infra_joint/operators/structured.py",
                "src/infra_joint/control/native_agents.py")


def inspect_store(store: Path, artifact_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Return shape/hash only; never record values, query, gold or source text."""
    import hashlib

    name = hashlib.sha256(artifact_id.encode()).hexdigest()
    blob, metadata = store / (name + ".blob"), store / (name + ".json")
    if store.is_symlink() or blob.is_symlink() or metadata.is_symlink():
        raise RuntimeError("record proof store must not follow symlinks")
    value = json.loads(metadata.read_text())
    content = blob.read_bytes()
    if (value != expected or value["artifact_id"] != artifact_id
            or value["media_type"] != "application/json"
            or len(content) != value["size_bytes"]
            or hashlib.sha256(content).hexdigest() != value["sha256_hex"]):
        raise RuntimeError("record proof content/metadata mismatch")
    rows = json.loads(content)
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("record proof requires a nonempty record array")
    return {**value, "record_count": len(rows),
            "actual_union_fields": sorted({key for row in rows for key in row}),
            "all_records_have_string_body": all(isinstance(row.get("body"), str) for row in rows)}


def shapes_for(root: Path, directory: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    assert_inactive(root, allow_current_audit_lease=True)
    run_id = json.loads((directory / "process.json").read_text())["run_id"]
    if not run_id.startswith(root.name + "-phase1-") or Path(run_id).name != run_id:
        raise RuntimeError("record scan escaped exact run")
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    ids = {artifact for e in events if e["event_type"] == "logical.observation"
           and e["payload"].get("failure_code") == "validation_failed"
           for artifact in actions.get(e["payload"]["action_id"], {}).get("inputs", [])}
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    result = {}
    for artifact_id in sorted(ids):
        matches = [(node, artifact) for node, state in states.items()
                   for artifact in state["artifacts"]
                   if artifact["artifact_id"] == artifact_id]
        if not matches or any(item != matches[0][1] for _, item in matches):
            raise RuntimeError("record proof missing or inconsistent replicas")
        node, metadata = matches[0]
        if node not in HOSTS:
            raise RuntimeError("record proof unknown owning device")
        base = Path("/home/super" if node == "strong-4090" else "/mnt/ssd")
        store = base / "heterogeneous-v1/artifacts" / root.name / run_id / node
        if node == "strong-4090":
            shape = inspect_store(store, artifact_id, metadata)
        else:
            # Code only travels from4090 to the owning edge; bodies remain there.
            import inspect

            code = "import json\nfrom pathlib import Path\nfrom typing import Any\n"
            code += inspect.getsource(inspect_store)
            code += "\nprint(json.dumps(inspect_store(Path(" + repr(str(store)) + "),"
            code += repr(artifact_id) + ",json.loads(" + repr(json.dumps(metadata)) + "))))"
            command = ["ssh", "-n", HOSTS[node], "python3 -S -c " + shlex.quote(code)]
            response = subprocess.run(command,
                                      check=True, capture_output=True, text=True, timeout=60)
            shape = json.loads(response.stdout)
        result[artifact_id] = {**shape, "owning_node": node, "store_root": str(store)}
    assert_inactive(root, allow_current_audit_lease=True)
    return result


def review(original: dict[str, Any], events: list[dict[str, Any]],
           shapes: dict[str, Any]) -> dict[str, Any]:
    if (original.get("disposition") != "confounder"
            or original.get("problems") != [GATE_PROBLEM] or original.get("operational_incidents")):
        raise RuntimeError("record review cannot waive other findings")
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"}
    physical = {e["payload"]["action_id"]: e["payload"] for e in events
                if e["event_type"] == "physical.execution"}
    if (len(actions) != sum(e["event_type"] == "logical.action.prepared" for e in events)
            or len(physical) != sum(e["event_type"] == "physical.execution" for e in events)):
        raise RuntimeError("duplicate action/physical evidence")
    successful = {e["payload"]["action_id"]: e["payload"] for e in events
                  if e["event_type"] == "logical.observation" and e["payload"].get("succeeded")}
    producers = {o["artifact_id"]: a for a in actions.values() for o in a.get("outputs", [])
                 if a["action_id"] in successful}
    root_input = next(e["payload"] for e in events if e["event_type"] == "logical.reasoning.input"
                      and e["payload"]["logical_agent_id"] == "manager")
    task = json.loads(root_input["input_items"][0]["content"])["task"]
    initial = {a["artifact_id"]: a for a in task["artifacts"]}

    def ancestors(artifact_id: str, seen: frozenset[str] = frozenset()) -> None:
        if artifact_id in seen:
            raise RuntimeError("cyclic record information flow")
        if artifact_id in initial:
            schema = initial[artifact_id].get("content_schema", {})
            if (schema.get("kind") != "record_array" or schema.get("text_field") != "body"
                    or schema.get("fields", {}).get("body") != "string"):
                raise RuntimeError("initial record schema not established")
            return
        producer = producers.get(artifact_id, {})
        if producer.get("operator") not in {"bm25_retrieve", "aggregate_artifacts"}:
            raise RuntimeError("record provenance requires whole-record preserving producers")
        if (producer["operator"] == "bm25_retrieve"
                and producer.get("arguments", {}).get("text_field") != "body"):
            raise RuntimeError("retrieval provenance has wrong source field")
        if not producer.get("inputs"):
            raise RuntimeError("record provenance missing input")
        for identifier in producer["inputs"]:
            ancestors(identifier, seen | {artifact_id})

    proof, seen = [], set()
    for event in events:
        p = event["payload"]
        if (event["event_type"] != "logical.observation"
                or p.get("failure_code") != "validation_failed"):
            continue
        aid = p["action_id"]
        action, receipt = actions.get(aid, {}), physical.get(aid, {})
        inputs = action.get("inputs", [])
        failure = receipt.get("failure", {})
        if len(inputs) != 1 or inputs[0] not in shapes:
            raise RuntimeError("absent field has no exact materialized input proof")
        shape = shapes[inputs[0]]
        fields = shape.get("actual_union_fields", [])
        args, operator = action.get("arguments", {}), action.get("operator")
        if operator == "bm25_retrieve":
            requested = [args.get("text_field", "text")]
            missing = [f for f in requested if f not in fields]
            message = f"document field must be text: {requested[0]}"
        elif operator == "select_fields":
            requested = args.get("fields", [])
            missing = sorted(set(requested) - set(fields))
            message = f"selected fields are missing: {missing}"
        else:
            raise RuntimeError("not a reviewed record operator")
        if (aid in seen or p.get("succeeded") is not False or action.get("action_type") != "tool"
                or p.get("owner_agent_id") != action.get("owner_agent_id")
                or not requested or not missing or shape.get("record_count", 0) <= 0
                or not shape.get("all_records_have_string_body")
                or p.get("failure_message") != message or failure.get("failure_message") != message
                or failure.get("failure_code") != "validation_failed"
                or failure.get("stage") != "execution" or failure.get("operator") != operator
                or not receipt.get("selection", {}).get("selected_agent_id")):
            raise RuntimeError("not exact absent materialized record field misuse")
        ancestors(inputs[0])
        seen.add(aid)
        proof.append({"action_id": aid, "owner_agent_id": action["owner_agent_id"],
                      "operator": operator, "action_sha256": provenance_sha256(action),
                      "input_artifact_id": inputs[0], "input_sha256": shape["sha256_hex"],
                      "missing_fields": missing, "root_initial_schema_correct": True,
                      "specialist_received_artifact_schema": None,
                      "reached_model_inference": False})
    failed = {p["action_id"] for p in physical.values()
              if (p.get("failure") or {}).get("failure_code") == "validation_failed"}
    if not proof or seen != failed:
        raise RuntimeError("every validation failure needs exact record proof")
    return {"record_field_proof": proof, "reviewed_admission": {
        **original, "disposition": "valid", "reason": REASON, "problems": [],
        "failure_class": "workflow_composition_absent_field_misuse",
        "replacement_authorized": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != DIRECTORY or path.name != attempt.run_id + ".json"
            or attempt.disposition != "confounder" or attempt.reason != GATE_PROBLEM
            or value["run_id"] != attempt.run_id
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256):
        raise RuntimeError("record sidecar identity/admission/source drift")
    files = {str(p.relative_to(directory)): sha256(p) for p in directory.rglob("*") if p.is_file()}
    if files != value["original_evidence_file_sha256"]:
        raise RuntimeError("record original evidence drift")
    for relative in files:
        source = directory / relative
        if source.is_symlink() or not source.resolve().is_relative_to(directory.resolve()):
            raise RuntimeError("record evidence escaped attempt")
    if value["execution_sources_sha256"] != {p: sha256(root / "app" / p) for p in SOURCE_PATHS}:
        raise RuntimeError("record operator/delegation source drift")
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    for aid, shape in value["materialized_shapes"].items():
        metadata = {k: shape[k] for k in ("artifact_id", "media_type", "size_bytes", "sha256_hex")}
        replicas = [a for state in states.values() for a in state["artifacts"]
                    if a["artifact_id"] == aid]
        if not replicas or any(a != metadata for a in replicas):
            raise RuntimeError("record shape/actual replica mismatch")
    trace = directory / "runs" / attempt.run_id / "trace.jsonl"
    actual = review(original, [json.loads(line) for line in trace.open(encoding="utf-8")],
                    value["materialized_shapes"])
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("record proof cannot be reproduced")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous_admission(root, attempt)
    value = json.loads((root / DIRECTORY / (attempt.run_id + ".json")).read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective record admission/ledger mismatch")
    return value["reviewed_admission"]


class RecordAttemptLedger(SnapshotAttemptLedger):
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
