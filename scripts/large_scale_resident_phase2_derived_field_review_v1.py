"""Source-bound derived record field proof, metadata only and outside execution.

Reuse verified historical initial shapes; never decode a corpus/store body, alter
Agent feedback or authorize replacement. Unknown transformations fail closed.
"""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path
from typing import Any

import large_scale_resident_derived_field_review_v1 as derived
import large_scale_resident_phase2_field_review_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

core = previous.core
bindings = previous.bindings
DIRECTORY = "phase2-derived-record-field-adjudications"
REASON = "audited_source_propagated_derived_record_field_misuse"


def sources() -> dict[str, str]:
    return {**previous.sources(), **{Path(p).name: core.legacy.sha256(Path(p))
                                    for p in (__file__, derived.__file__)}}


def _initial_shapes(task: dict[str, Any], states: dict[str, Any],
                    historical: dict[str, Any]) -> dict[str, Any]:
    ids = {a["artifact_id"] for a in task["artifacts"]}
    # Revalidate the declared schema, full replicas and hash-identical inspected
    # historical shapes before propagating fields through successful producers.
    reused = previous.reuse_shapes(task, states, historical, ids)
    result: dict[str, Any] = {}
    for aid, schema in reused.items():
        replica = next(a for s in states.values() for a in s["artifacts"]
                       if a["artifact_id"] == aid)
        matches = [s for s in historical["materialized_shapes"].values()
                   if all(s[k] == replica[k]
                          for k in ("media_type", "size_bytes", "sha256_hex"))]
        if len(matches) != 1:
            raise RuntimeError("one historical shape required")
        result[aid] = {**replica, "record_count": matches[0]["record_count"],
                       "actual_union_fields": schema["actual_union_fields"],
                       "all_records_have_string_body":
                       matches[0]["all_records_have_string_body"]}
    return result


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
    if (attempt.disposition != "confounder" or attempt.reason != previous.field.GATE
            or original.get("problems") != [previous.field.GATE]
            or original.get("operational_incidents")
            or provenance_sha256(original) != attempt.receipt_sha256
            or attempt.execution_sha256 != saved["execution_freeze_sha256"]):
        raise RuntimeError("only the exact original field gate can be reviewed")
    config = vars(core.frozen.frozen)["_yaml"](
        root / "cell-configs" / (attempt.run_id + ".yaml"))
    if (core.previous.previous.admission(directory, config, Path(saved["pricing_path"]))
            != original
            or json.loads((directory / "process-exit.json").read_text())["returncode"] != 0
            or json.loads((directory / "worker-shutdown.json").read_text())[
                "verified_exited"] is not True
            or json.loads((directory / "private/residency-validation.json").read_text())[
                "passed"] is not True):
        raise RuntimeError("complete original admission/exit/residency must reproduce")
    tc = json.loads((directory / "tc-attestation.json").read_text())
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        raise RuntimeError("field proof cannot waive network cleanup")
    if (historical_path.is_symlink() or historical_path.parent.is_symlink()
            or historical_path.resolve().parent != root / bindings.RECORD_DIRECTORY):
        raise RuntimeError("owned source-bound historical record proof required")
    old_attempt = previous.historical_attempt(root, historical_path.stem)
    historical = bindings.verify_record(historical_path, old_attempt)
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    root_inputs = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.input"
                   and e["payload"]["logical_agent_id"] == "manager"]
    if not root_inputs:
        raise RuntimeError("actual root task view required")
    task = json.loads(root_inputs[0]["input_items"][0]["content"])["task"]
    states = json.loads((directory / "private/worker-state-after.json").read_text())
    shapes = _initial_shapes(task, states, historical)
    result = json.loads((directory / "runs" / attempt.run_id / "result.json").read_text())
    verified = derived.review(events, result, task, shapes, states)
    reviewed: dict[str, Any] = {
        **original, "disposition": "valid", "reason": REASON, "problems": [],
        "failure_class": "workflow_composition_absent_field_misuse",
        "replacement_authorized": False}
    wire = previous.sdk_schema_proof(directory / "private/api", task)
    if len(wire) != len(root_inputs):
        raise RuntimeError("every actual Manager turn requires its exact task schema")
    actual_sources = bindings.frozen_sources(root, attempt, derived.SOURCE_PATHS)
    worker_app = root / "app-input-cardinality-repair-003"
    worker_freeze = root / "execution-freeze-003.json"
    worker_contract = json.loads(worker_freeze.read_text())["source_sha256"]
    if any(actual_sources[p] != worker_contract.get(p)
           or core.legacy.sha256(worker_app / p) != actual_sources[p]
           for p in derived.SOURCE_PATHS):
        raise RuntimeError("actual Worker003/atomic004 transformation sources must agree")
    tested_sources = {}
    for path in derived.SOURCE_PATHS:
        module = import_module(path.removeprefix("src/").removesuffix(".py").replace("/", "."))
        if module.__file__ is None:
            raise RuntimeError("file-backed transformation implementation required")
        tested_sources[path] = core.legacy.sha256(Path(module.__file__))
    if tested_sources != actual_sources:
        raise RuntimeError("proof rules must use the actual frozen transformation implementation")
    return {"version": "phase2-source-propagated-derived-field-review-v1", **verified,
            "covered_original_findings": [previous.field.GATE],
            "reviewed_admission": reviewed,
            "run_id": attempt.run_id, "original_admission_sha256": attempt.receipt_sha256,
            "original_execution_sha256": attempt.execution_sha256,
            "parent_control_path": str(parent_path),
            "parent_control_file_sha256": core.legacy.sha256(parent_path),
            "historical_sidecar_path": str(historical_path),
            "historical_sidecar_file_sha256": core.legacy.sha256(historical_path),
            "reused_initial_shapes": shapes, "actual_manager_schema_wire_proof": wire,
            "execution_sources_sha256": actual_sources,
            "tested_transformation_sources_sha256": tested_sources,
            "worker_freeze_file_sha256": core.legacy.sha256(worker_freeze),
            "reviewer_sources_sha256": sources(),
            "original_evidence_file_sha256": bindings.evidence_files(directory),
            "reviewed_admission_sha256": provenance_sha256(reviewed),
            "new_store_or_corpus_body_decoded": False, "online_feedback": False,
            "formal_execution_changed": False, "replacement_authorized": False}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact derived field sidecar required")
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if value != proof(root, attempt, Path(value["parent_control_path"]),
                      Path(value["historical_sidecar_path"])):
        raise RuntimeError("derived field source/evidence proof drift")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous.effective_admission(root, attempt)
    path = root / DIRECTORY / (attempt.run_id + ".json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["reviewed_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256):
        raise RuntimeError("effective derived field admission/ledger mismatch")
    admission: dict[str, Any] = value["reviewed_admission"]
    return admission


def create_review(run_id: str, parent: Path, historical: Path) -> dict[str, Any]:
    core.frozen.require_remote()
    root = core.frozen.ROOT
    core.previous.gate.evidence.private.assert_inactive(root)
    before = (root / "phase2-attempts.jsonl").read_bytes()
    rows = [json.loads(line) for line in before.decode("utf-8").splitlines()]
    reservations = {r["run_id"]: r for r in rows if r["event"] == "reserved"}
    settled = [r for r in rows if r["event"] == "settled" and r["run_id"] == run_id]
    all_settled = [r for r in rows if r["event"] == "settled"]
    if (len(settled) != 1
            or len(reservations) != sum(r["event"] == "reserved" for r in rows)
            or len(all_settled) != len({r["run_id"] for r in all_settled})
            or set(reservations) != {r["run_id"] for r in all_settled}):
        raise RuntimeError("unique settled target and no pending attempts required")
    r, s = reservations[run_id], settled[0]
    attempt = Attempt(r["cell_id"], run_id, r["attempt_index"], r["execution_sha256"],
                      s["disposition"], s["reason"], s["receipt_sha256"])
    path = root / DIRECTORY / (run_id + ".json")
    if path.exists():
        raise FileExistsError("review creator must not repeat")
    with QueueLease(root / "queue-lease.json"):
        value = proof(root, attempt, parent, historical)
        core.frozen.write_new(path, value)
        verify_sidecar(path, attempt)
        if (root / "phase2-attempts.jsonl").read_bytes() != before:
            raise RuntimeError("review cannot alter the original journal")
    core.previous.gate.evidence.private.assert_inactive(root)
    return {"sidecar_path": str(path), "sha256": core.legacy.sha256(path),
            "new_store_or_corpus_body_decoded": False, "retry": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--parent-control", required=True, type=Path)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.run_id, args.parent_control, args.historical_sidecar)))
