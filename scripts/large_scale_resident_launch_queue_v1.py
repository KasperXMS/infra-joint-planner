"""Resume source-proved pre-execution launch repairs with unchanged atomic code.

This is external experiment control, not an Agent/model/runtime change. Repair
authorization is separately journaled; original confounders remain visible.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_launch_review_v1 as reviewer
import large_scale_resident_record_continuation_queue_v1 as previous
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

frozen, e = previous.frozen, previous.e
PARENT_FILE = "queue-control-freeze-018.json"
PARENT_SHA256 = "b78cdca1c5c2acf5902db36b42cecd2c487ae5b8802b0aab935d0e95fd2efd01"


def owned_ledger() -> reviewer.ProjectionAttemptLedger:
    cells = frozen.schedule()
    return reviewer.ProjectionAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
                                           tuple(c.cell_id for c in cells),
                                           frozen.schedule_sha256(cells))


def historical_control() -> dict[str, Any]:
    parent = previous.historical_control()
    path = frozen.ROOT / PARENT_FILE
    if path.is_symlink() or frozen.sha256(path) != PARENT_SHA256:
        raise RuntimeError("pinned record continuation control changed")
    saved = json.loads(path.read_text())
    for name, digest in saved["current_source_bound_record_adjudications"].items():
        proof = reviewer.owned_file(frozen.ROOT, reviewer.methods.RECORD_DIRECTORY + "/" + name)
        if frozen.sha256(proof) != digest:
            raise RuntimeError("original continuation proof scope changed")
    expected = {
        **parent, "version": "resident-exact-record-field-continuation-control-v1",
        "parent_control_file_sha256": previous.PARENT_SHA256,
        "parent_controller_source_sha256": frozen.sha256(Path(previous.previous.__file__)),
        "controller_source_sha256": frozen.sha256(Path(previous.__file__)),
        "current_source_bound_record_adjudications":
        saved["current_source_bound_record_adjudications"],
        "parent_proof_scope_preserved": True, "nominal_retries": False,
        "measured_execution_changed": False,
    }
    if saved != expected:
        raise RuntimeError("original record continuation source/receipt changed")
    return saved


def control_freeze() -> dict[str, Any]:
    parent = historical_control()
    ledger = owned_ledger()
    if not ledger.launch_repairs:
        raise RuntimeError("launch continuation requires an actual journaled exact repair")
    attempts = {a.run_id: a for a in ledger.attempts}
    record_proofs = {}
    for path in sorted((frozen.ROOT / reviewer.methods.RECORD_DIRECTORY).glob("*.json")):
        attempt = attempts.get(path.stem)
        if (path.is_symlink() or attempt is None or attempt.disposition != "valid"
                or attempt.reason != reviewer.records.REASON):
            raise RuntimeError("new record proof requires exact effective admission")
        record_proofs[path.name] = frozen.sha256(path)
    return {**parent, "version": "resident-exact-preexecution-launch-continuation-v1",
            "parent_control_file_sha256": PARENT_SHA256,
            "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "launch_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "launch_environment_source_sha256": frozen.sha256(Path(reviewer.environment.__file__)),
            "launch_repair_proofs": ledger.launch_repairs,
            "current_source_bound_record_adjudications": record_proofs,
            "measured_execution_changed": False, "semantic_retries": False,
            "max_preexecution_reexecutions_per_cell": 1}


def child_environment(ledger: reviewer.ProjectionAttemptLedger) -> dict[str, str]:
    corrections = []
    for run in ledger.launch_repairs:
        path = frozen.ROOT / reviewer.AUTH_DIRECTORY / (run + ".json")
        value = json.loads(path.read_text())
        corrections.append(reviewer.verify_repair_freeze(
            frozen.ROOT, value["repair_freeze_file"], value["repair_freeze_file_sha256"]))
    if not corrections or any(c["execution_sha256"] != e.EXECUTION_SHA256 for c in corrections):
        raise RuntimeError("launch repair requires unchanged actual execution004")
    correction = corrections[0]
    env = reviewer.environment.pinned_environment(
        frozen.APP, frozen.ROOT / correction["execution_freeze_file"],
        correction["execution_freeze_file_sha256"], os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(frozen.APP / p) for p in ("src", "scripts"))
    return env


def preflight(env: dict[str, str]) -> None:
    check = subprocess.run([
        sys.executable, "-c", "from large_scale_resident_queue_v1 import verify_freeze; "
        "assert verify_freeze() == " + repr(e.EXECUTION_SHA256),
    ], env=env, capture_output=True, text=True, timeout=120)
    if check.returncode:
        raise RuntimeError("archive launch preflight failed before reservation")


def prepare(run_id: str, repair_freeze: Path) -> None:
    frozen.require_remote()
    e.assert_inactive(frozen.ROOT)
    if repair_freeze.is_symlink():
        raise RuntimeError("owned immutable launch correction required")
    relative = str(repair_freeze.resolve().relative_to(frozen.ROOT.resolve()))
    digest = frozen.sha256(repair_freeze)
    reviewer.verify_repair_freeze(frozen.ROOT, relative, digest)
    with QueueLease(frozen.ROOT / "queue-lease.json"):
        ledger = owned_ledger()
        if ledger.pending:
            raise RuntimeError("possibly active attempt prohibits launch repair")
        attempt = next(a for a in ledger.attempts if a.run_id == run_id)
        directory = frozen.ROOT / "evidence" / attempt.cell_id / "attempt1"
        path = frozen.ROOT / reviewer.AUTH_DIRECTORY / (run_id + ".json")
        value = {"run_id": run_id, "original_admission_sha256": attempt.receipt_sha256,
                 "original_execution_sha256": attempt.execution_sha256,
                 "reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
                 "repair_freeze_file": relative, "repair_freeze_file_sha256": digest,
                 "original_evidence_file_sha256": reviewer.methods.evidence_files(directory),
                 "failure_class": "system_harness_preexecution_launch_defect",
                 "manager_calls": 0, "model_calls": 0, "measured_execution_changed": False,
                 "operational_replacement": False, "semantic_retry": False}
        if path.exists():
            if json.loads(path.read_text()) != value:
                raise RuntimeError("existing pre-execution repair differs; never overwrite")
        else:
            frozen.write_new(path, value)
        reviewer.verify_sidecar(path, attempt)
        if run_id not in ledger.launch_repairs:
            ledger.authorize_launch_repair(run_id)


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if (control_path.is_symlink() or control_path.parent.resolve() != root
            or not control_path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("owned immutable launch control required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("launch continuation source/proof drift")
    ledger = owned_ledger()
    preflight(child_environment(ledger))  # Before any reservation or Worker/tc action.
    cells = frozen.schedule()
    prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    with QueueLease(root / "queue-lease.json"):
        ledger = owned_ledger()
        authorization = json.loads((root / e.AUTHORIZATION).read_text())
        authorized = (set(e.historical_repairs(root)) | set(authorization["affected_original_runs"])
                      | set(ledger.launch_repairs))
        if ledger.pending or any(a.disposition == "confounder" and a.run_id not in authorized
                                 for a in ledger.attempts):
            raise RuntimeError("unresolved finding prohibits continuation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            if saved != control_freeze():
                raise RuntimeError("launch continuation control drift")
            if frozen.PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= frozen.GLOBAL_CAP:
                raise RuntimeError("cumulative substantive cap reached")
            env = child_environment(ledger)
            index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
            run_id = f"{root.name}-{cell.cell_id}-attempt{index}"
            directory = root / "evidence" / cell.cell_id / f"attempt{index}"
            ledger.reserve(cell.cell_id, run_id, e.EXECUTION_SHA256)
            directory.mkdir(parents=True, exist_ok=False)
            config = frozen.cell_config(cell, run_id, frozen.reference(), root=root)
            config_path = root / "cell-configs" / (run_id + ".yaml")
            with config_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            with (directory / "console.log").open("x", encoding="utf-8") as log:
                process = subprocess.Popen([
                    sys.executable, saved["atomic_execution_entrypoint"], "--attempt",
                    "--config", str(config_path), "--output", str(directory),
                ], stdout=log, stderr=subprocess.STDOUT, env=env)
                frozen.write_new(directory / "process.json", {"pid": process.pid, "run_id": run_id})
                returncode = process.wait()
            frozen.write_new(directory / "process-exit.json", {"pid": process.pid,
                                                               "returncode": returncode})
            value: dict[str, Any]
            try:
                value = previous.previous.previous.previous.quote.admission(directory, config,
                                                                           prices)
                if cell.method == "E":
                    events = [json.loads(line) for line in (
                        directory / "runs" / run_id / "trace.jsonl").open(encoding="utf-8")]
                    e.assert_E_tool_isolation(directory, events)
                if not json.loads((directory / "private/residency-validation.json").read_text())[
                        "passed"]:
                    raise RuntimeError("residency measurement invalid")
            except Exception as error:
                value = {"disposition": "confounder", "reason": "admission_unverifiable",
                         "problems": [type(error).__name__]}
            if returncode and value["disposition"] == "valid":
                value.update(disposition="confounder", reason="wrapper_execution_error")
            frozen.write_new(directory / "admission.json", value)
            ledger.settle(run_id, value["disposition"], value["reason"], provenance_sha256(value))
            if value["disposition"] != "valid":
                raise RuntimeError("new finding requires exact audit; no automatic retry")
        frozen.write_new(root / "phase1-queue-completed.json", {
            "schedule_sha256": frozen.schedule_sha256(cells),
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "pruning_authorized": False, "control_sha256": provenance_sha256(saved),
            "next_required": "all168 private/recipient/failure/adoption audit before pruning"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--control-freeze", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--repair-freeze", type=Path)
    args = parser.parse_args()
    if args.prepare:
        if args.run_id is None or args.repair_freeze is None:
            parser.error("prepare requires run-id and repair-freeze")
        prepare(args.run_id, args.repair_freeze)
    else:
        if args.control_freeze is None:
            parser.error("freeze/run requires control-freeze")
        if args.freeze:
            e.assert_inactive(frozen.ROOT)
            frozen.require_remote()
            if args.control_freeze.parent.resolve() != frozen.ROOT:
                raise RuntimeError("owned control receipt required")
            frozen.write_new(args.control_freeze, control_freeze())
        else:
            run(args.control_freeze)
