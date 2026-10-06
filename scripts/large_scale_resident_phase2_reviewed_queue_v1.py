"""Source-bound offline model-JSON review and held-out continuation, without retries.

The original controller, admission, journal and atomic execution stay immutable.
Only independently reviewed post-backend JSON failures receive an effective view.
Other findings still stop the queue and require their own actual audit.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_adjudication_v1 as legacy
import large_scale_resident_current_phase2_queue_v1 as previous
import large_scale_resident_method_contract_review_v1 as bindings

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, AttemptLedger, QueueLease

frozen = previous.frozen
DIRECTORY = "phase2-model-json-adjudications"
SOURCES = ("src/infra_joint/worker/server.py", "src/infra_joint/control/ledger.py")


def evidence(root: Path, attempt: Attempt) -> Path:
    return root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"


def proof(root: Path, attempt: Attempt, parent_path: Path) -> dict[str, Any]:
    parent, _ = previous.checked_control(parent_path)
    directory = evidence(root, attempt)
    original = json.loads((directory / "admission.json").read_text())
    if (attempt.disposition != "confounder" or attempt.reason != legacy.GATE_PROBLEM
            or original.get("reason") != legacy.GATE_PROBLEM
            or provenance_sha256(original) != attempt.receipt_sha256
            or attempt.execution_sha256 != parent["execution_freeze_sha256"]):
        raise RuntimeError("exact original settled model-JSON finding required")
    config = frozen.frozen._yaml(root / "cell-configs" / (attempt.run_id + ".yaml"))
    if (previous.previous.admission(directory, config, Path(parent["pricing_path"])) != original
            or json.loads((directory / "process-exit.json").read_text())["returncode"] != 0
            or json.loads((directory / "worker-shutdown.json").read_text())[
                "verified_exited"] is not True
            or json.loads((directory / "private/residency-validation.json").read_text())[
                "passed"] is not True):
        raise RuntimeError("full original admission, Worker exit and residency must reproduce")
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    for kind, field in (("logical.action.prepared", "action"),
                        ("physical.execution", None), ("logical.observation", None)):
        ids = [(e["payload"][field] if field else e["payload"])["action_id"]
               for e in events if e["event_type"] == kind]
        if len(ids) != len(set(ids)):
            raise RuntimeError("duplicate action/receipt identities cannot establish exact proof")
    review = legacy.review_model_json_failures(original, events)
    sources = bindings.frozen_sources(root, attempt, SOURCES)
    # Actual Workers still use epoch003. Both epochs must advertise identical source.
    worker_app = root / "app-input-cardinality-repair-003"
    worker_freeze = root / "execution-freeze-003.json"
    worker_contract = json.loads(worker_freeze.read_text())["source_sha256"]
    if any(sources[p] != worker_contract.get(p)
           or legacy.sha256(worker_app / p) != sources[p] for p in SOURCES):
        raise RuntimeError("actual Worker003 and atomic004 parsing/ledger source must agree")
    source = (worker_app / SOURCES[0]).read_text()
    if not (source.index("completion = await deployment.backend.invoke(model_request)")
            < source.index("json.loads(completion.text)")
            < source.index('raise ValueError("model output is not valid JSON")')):
        raise RuntimeError("failure must follow completed backend inference")
    return {**review, "execution_sources_sha256": sources,
            "worker_freeze_file_sha256": legacy.sha256(worker_freeze),
            "original_evidence_file_sha256": bindings.evidence_files(directory),
            "parent_control_path": str(parent_path),
            "parent_control_file_sha256": legacy.sha256(parent_path),
            "reviewer_source_sha256": legacy.sha256(Path(__file__)),
            "legacy_reviewer_source_sha256": legacy.sha256(Path(legacy.__file__)),
            "binding_source_sha256": legacy.sha256(Path(bindings.__file__)),
            "original_admission_sha256": attempt.receipt_sha256,
            "original_execution_sha256": attempt.execution_sha256,
            "run_id": attempt.run_id, "replacement_authorized": False,
            "formal_execution_changed": False, "missing_model_telemetry_imputed": False,
            "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"])}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact PhaseII review path required")
    value = json.loads(path.read_text())
    if value != proof(root, attempt, Path(value["parent_control_path"])):
        raise RuntimeError("original evidence/source/review drift")
    return value


class ReviewedAttemptLedger(AttemptLedger):
    @property
    def original_attempts(self) -> tuple[Attempt, ...]:
        return super().attempts

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
        for attempt in self.original_attempts:
            path = self.path.parent / DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="valid", reason=legacy.REVIEW_REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    path = root / DIRECTORY / (attempt.run_id + ".json")
    if path.exists():
        value = json.loads(path.read_text())
        if (attempt.reason != legacy.REVIEW_REASON
                or attempt.receipt_sha256 != value["reviewed_admission_sha256"]):
            raise RuntimeError("effective held-out admission/ledger drift")
        return value["reviewed_admission"]
    return json.loads((evidence(root, attempt) / "admission.json").read_text())


def create_review(run_id: str, parent_path: Path) -> dict[str, Any]:
    frozen.require_remote()
    root = frozen.ROOT
    previous.gate.evidence.private.assert_inactive(root)
    parent, cells = previous.checked_control(parent_path)
    journal = root / "phase2-attempts.jsonl"
    if not journal.is_file():
        raise RuntimeError("review cannot initialize a missing journal")
    before = journal.read_bytes()
    with QueueLease(root / "queue-lease.json"):
        ledger = AttemptLedger(journal, tuple(c.cell_id for c in cells),
                               parent["phase2_schedule_sha256"])
        if ledger.pending:
            raise RuntimeError("pending possibly-live actions cannot be reviewed")
        attempt = next(a for a in ledger.attempts if a.run_id == run_id)
        value = proof(root, attempt, parent_path)
        path = root / DIRECTORY / (run_id + ".json")
        path.parent.mkdir(exist_ok=True)
        frozen.write_new(path, value)
        verify_sidecar(path, attempt)
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot modify the original journal")
    return {"sidecar_path": str(path), "sha256": legacy.sha256(path),
            "confirmed_model_parse_failures": len(value["proof"]), "retry": False}


def control_value(parent_path: Path) -> dict[str, Any]:
    parent, cells = previous.checked_control(parent_path)
    paths = sorted((frozen.ROOT / DIRECTORY).glob("*.json"))
    if not paths:
        raise RuntimeError("reviewed continuation requires actual exact sidecars")
    ledger = ReviewedAttemptLedger(frozen.ROOT / "phase2-attempts.jsonl",
                                   tuple(c.cell_id for c in cells),
                                   parent["phase2_schedule_sha256"])
    if (ledger.pending or any(a.disposition != "valid" for a in ledger.attempts)
            or {p.name for p in paths} != {
                a.run_id + ".json" for a in ledger.original_attempts
                if a.disposition == "confounder"}):
        raise RuntimeError("unresolved or unowned findings prohibit continuation")
    return {"version": "resident-phase2-exact-model-json-continuation-v1",
            "parent_control_path": str(parent_path),
            "parent_control_file_sha256": legacy.sha256(parent_path),
            "sidecars": {p.name: legacy.sha256(p) for p in paths},
            "source_sha256": {Path(p).name: legacy.sha256(Path(p)) for p in (
                __file__, legacy.__file__, bindings.__file__)},
            "execution_freeze_sha256": parent["execution_freeze_sha256"],
            "phase2_schedule_sha256": parent["phase2_schedule_sha256"],
            "nominal_cells": parent["nominal_cells"], "no_retry": True,
            "semantic_tuning": False, "prior_results_modified": False}


def checked_control(path: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    if (path.is_symlink() or path.resolve().parent != frozen.ROOT
            or not path.name.startswith("phase2-reviewed-control-freeze-")):
        raise RuntimeError("owned immutable reviewed control required")
    value = json.loads(path.read_text())
    parent_path = Path(value["parent_control_path"])
    parent, cells = previous.checked_control(parent_path)
    if value != control_value(parent_path):
        raise RuntimeError("reviewed control/evidence drift")
    return parent, cells


def run(path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    previous.gate.evidence.private.assert_inactive(root)
    saved, cells = checked_control(path)
    with QueueLease(root / "queue-lease.json"):
        ledger = ReviewedAttemptLedger(root / "phase2-attempts.jsonl",
                                       tuple(c.cell_id for c in cells),
                                       saved["phase2_schedule_sha256"])
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            current, current_cells = checked_control(path)
            if current != saved or current_cells != cells:
                raise RuntimeError("unchanged PhaseII contract required")
            previous.execute_cell(cell, ledger, saved)
        frozen.write_new(root / "phase2-queue-completed.json", {
            "schedule_sha256": saved["phase2_schedule_sha256"],
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "reviewed_control_sha256": legacy.sha256(path),
            "next_required": "complete PhaseII private/failure/recipient/adoption and Q1-Q10 audit",
            "goal_complete": False,
        })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review", action="store_true")
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--parent-control", type=Path)
    parser.add_argument("--control-freeze", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.review:
        if args.parent_control is None or args.run_id is None:
            parser.error("review requires parent control and original run ID")
        print(json.dumps(create_review(args.run_id, args.parent_control)))
    elif args.freeze:
        if args.parent_control is None or args.control_freeze is None:
            parser.error("freeze requires parent and reviewed control paths")
        frozen.require_remote()
        previous.gate.evidence.private.assert_inactive(frozen.ROOT)
        if (args.control_freeze.is_symlink()
                or args.control_freeze.resolve().parent != frozen.ROOT
                or not args.control_freeze.name.startswith("phase2-reviewed-control-freeze-")):
            parser.error("owned append-only reviewed control path required")
        frozen.write_new(args.control_freeze, control_value(args.parent_control))
    else:
        if args.control_freeze is None:
            parser.error("queue requires reviewed control")
        run(args.control_freeze)
