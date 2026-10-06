"""Audited Quote-integrity repair and never-started resident continuation only."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_quote_repair_ledger_v1 as reviewer
import large_scale_resident_adjudicated_queue_v1 as parent_controller
import large_scale_resident_queue_v1 as frozen
import yaml
from large_scale_resident_private_evidence_v1 import assert_inactive
from large_scale_resident_quote_patch_v1 import BUG_REVIEW_SHA256, PARENT_SHA256

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease


def owned_ledger() -> reviewer.QuoteRepairAttemptLedger:
    cells = frozen.schedule()
    return reviewer.QuoteRepairAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
                                            tuple(c.cell_id for c in cells),
                                            frozen.schedule_sha256(cells))


def prepare_reviews() -> None:
    frozen.require_remote()
    root = frozen.ROOT
    assert_inactive(root)
    new_execution = frozen.verify_freeze()
    proof_path = root / "adjudications/quote-hash-confounder-002.json"
    if frozen.sha256(proof_path) != BUG_REVIEW_SHA256:
        raise RuntimeError("exact ten-rejection bug proof changed")
    proof = json.loads(proof_path.read_text())
    with QueueLease(root / "queue-lease.json"):
        ledger = owned_ledger()
        if ledger.pending:
            raise RuntimeError("possibly live attempt cannot be invalidated or repeated")
        targets = []
        for row in proof["affected_attempts"]:
            attempt = next(a for a in ledger.attempts if a.run_id == row["run_id"])
            targets.append(attempt.run_id)
            path = root / reviewer.DIRECTORY / (attempt.run_id + ".json")
            if attempt.reason == reviewer.REASON:
                continue  # A prior durable invalidation already revalidated this proof.
            directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
            original = json.loads((directory / "admission.json").read_text())
            trace = directory / "runs" / attempt.run_id / "trace.jsonl"
            residency = directory / "private/residency-validation.json"
            if (attempt.execution_sha256 != PARENT_SHA256
                    or provenance_sha256(original) != attempt.receipt_sha256
                    or frozen.sha256(trace) != row["trace_sha256"]
                    or frozen.sha256(directory / "admission.json")
                    != row["original_admission_sha256"]
                    or not json.loads((directory / "worker-shutdown.json").read_text())[
                        "verified_exited"]
                    or not json.loads(residency.read_text())["passed"]):
                raise RuntimeError("affected original/source/cleanup proof changed")
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            value = reviewer.review(original, events, directory / "private/api")
            value.update({
                "run_id": attempt.run_id, "original_admission_sha256": attempt.receipt_sha256,
                "original_execution_sha256": attempt.execution_sha256,
                "frozen_quote_source_sha256": proof["frozen_quote_source_sha256"],
                "reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
                "original_evidence_file_sha256": {str(p.relative_to(directory)): frozen.sha256(p)
                                                 for p in sorted(directory.rglob("*"))
                                                 if p.is_file()},
                "reviewed_admission_sha256": provenance_sha256(value["reviewed_admission"]),
                "exact_bug_proof_sha256": BUG_REVIEW_SHA256,
                "not_semantic_retry": True, "evidence_overwritten": False,
            })
            if path.exists():
                if json.loads(path.read_text()) != value:
                    raise RuntimeError("existing retrospective proof differs; never overwrite")
            else:
                frozen.write_new(path, value)
            ledger.invalidate_quote_integrity(attempt.run_id)
        for run in targets:
            if run not in ledger._repairs:
                current = next(a for a in ledger.attempts if a.run_id == run)
                ledger.authorize_generic_repair(
                    run, original_admission_sha256=current.receipt_sha256,
                    repair_audit_sha256=provenance_sha256({
                        "new_execution_sha256": new_execution,
                        "review_sha256": frozen.sha256(root / reviewer.DIRECTORY / (run + ".json")),
                        "bug_proof_sha256": BUG_REVIEW_SHA256}),
                    new_execution_sha256=new_execution)
            elif ledger._repairs[run] != new_execution:
                raise RuntimeError("existing affected repair was bound to another execution")
        receipt = {"version": "resident-quote-repair-authorization-v1",
                   "new_execution_sha256": new_execution, "affected_original_runs": targets,
                   "review_sha256": {run: frozen.sha256(root / reviewer.DIRECTORY / (run + ".json"))
                                     for run in targets},
                   "bug_proof_sha256": BUG_REVIEW_SHA256,
                   "ordinary_wrong_answers_not_repeated": True, "nominal_cells_not_added": True}
        output = root / "quote-repair-authorization-001.json"
        if output.exists():
            if json.loads(output.read_text()) != receipt:
                raise RuntimeError("existing authorization differs")
        else:
            frozen.write_new(output, receipt)


def control_freeze() -> dict[str, Any]:
    frozen.require_remote()
    root = frozen.ROOT
    original = json.loads((root / "queue-control-freeze-007.json").read_text())
    current = parent_controller.control_freeze()
    # Retain all prior scoped reviewers/sources exactly. Only the new explicit
    # atomic entrypoint and execution hash change; old sidecars cannot drift.
    for key in ("reviewer_source_sha256", "record_reviewer_source_sha256",
                "private_guard_source_sha256", "ledger_view_source_sha256",
                "ledger_dependency_sources_sha256"):
        if current[key] != original[key]:
            raise RuntimeError("prior exact review dependency source changed")
    for key in ("adjudications", "record_field_adjudications",
                "resident_provider_policy_adjudications", "provider_policy_adjudications"):
        if any(current[key].get(name) != digest for name, digest in original[key].items()):
            raise RuntimeError("historical exact sidecar changed")
    authorization = root / "quote-repair-authorization-001.json"
    saved = json.loads(authorization.read_text())
    if saved["new_execution_sha256"] != current["execution_freeze_sha256"]:
        raise RuntimeError("repair authorization and execution disagree")
    actual_reviews = {p.name: frozen.sha256(p)
                      for p in sorted((root / reviewer.DIRECTORY).glob("*.json"))}
    if actual_reviews != {run + ".json": digest for run, digest in saved["review_sha256"].items()}:
        raise RuntimeError("only exact proven affected attempts may be invalidated/repeated")
    ledger = owned_ledger()  # Independently reproduce scoped reviews and the hash-linked journal.
    if any(run not in ledger._repairs for run in saved["affected_original_runs"]):
        raise RuntimeError("missing durable affected-only authorization")
    return {**current, "version": "resident-exact-quote-integrity-repair-control-v1",
            "parent_control_file_sha256": frozen.sha256(root / "queue-control-freeze-007.json"),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "quote_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "quote_integrity_adjudications": actual_reviews,
            "repair_authorization_file_sha256": frozen.sha256(authorization),
            "semantic_or_physical_execution_changed": "audited quote-hash integrity fix only",
            "generic_affected_reruns": saved["affected_original_runs"],
            "ordinary_semantic_retries": False}


def admission(directory: Path, config: dict[str, Any], prices: Path) -> dict[str, Any]:
    value = frozen.admit(directory, config, prices)
    trace = directory / "runs" / config["run_id"] / "trace.jsonl"
    if trace.exists():
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        codes = {e["payload"].get("failure_code") for e in events
                 if e["event_type"] == "logical.cost_quote.rejected"}
        if "quoted_action_mutated" in codes:
            value = {**value, "disposition": "confounder", "reason": reviewer.REASON,
                     "problems": [*value.get("problems", []), reviewer.REASON]}
    return value


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if (control_path.parent.resolve() != root
            or not control_path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("owned immutable control receipt required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("repair control/source/evidence freeze drift")
    cells = frozen.schedule()
    prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    with QueueLease(root / "queue-lease.json"):
        ledger = owned_ledger()
        if ledger.pending or any(a.disposition == "confounder" and a.run_id not in ledger._repairs
                                 for a in ledger.attempts):
            raise RuntimeError("unresolved finding prohibits continuation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            if saved != control_freeze():
                raise RuntimeError("continuation repair/source/evidence freeze drift")
            if frozen.PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= frozen.GLOBAL_CAP:
                raise RuntimeError("cumulative substantive cap reached")
            index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
            run_id = f"{root.name}-{cell.cell_id}-attempt{index}"
            directory = root / "evidence" / cell.cell_id / f"attempt{index}"
            ledger.reserve(cell.cell_id, run_id, saved["execution_freeze_sha256"])
            directory.mkdir(parents=True, exist_ok=False)
            config = frozen.cell_config(cell, run_id, frozen.reference(), root=root)
            config_path = root / "cell-configs" / (run_id + ".yaml")
            with config_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            child_env = dict(os.environ, PYTHONPATH=os.pathsep.join(
                str(frozen.APP / folder) for folder in ("src", "scripts")))
            with (directory / "console.log").open("x", encoding="utf-8") as log:
                process = subprocess.Popen([
                    sys.executable, saved["atomic_execution_entrypoint"], "--attempt",
                    "--config", str(config_path), "--output", str(directory),
                ], stdout=log, stderr=subprocess.STDOUT, env=child_env)
                frozen.write_new(directory / "process.json", {"pid": process.pid, "run_id": run_id})
                returncode = process.wait()
            frozen.write_new(directory / "process-exit.json", {"pid": process.pid,
                                                               "returncode": returncode})
            try:
                value = admission(directory, config, prices)
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
                raise RuntimeError("new finding requires exact audit; no automatic semantic retry")
        frozen.write_new(root / "phase1-queue-completed.json", {
            "schedule_sha256": frozen.schedule_sha256(cells),
            "completed_cells": ledger.completed_cells,
            "attempt_count": len(ledger.attempts), "pruning_authorized": False,
            "control_sha256": provenance_sha256(saved),
            "next_required": "all168 private/recipient/failure/adoption audit before pruning"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-reviews", action="store_true")
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--control-freeze", type=Path)
    args = parser.parse_args()
    if args.prepare_reviews:
        prepare_reviews()
    elif args.freeze:
        if (args.control_freeze is None or args.control_freeze.parent.resolve() != frozen.ROOT
                or not args.control_freeze.name.startswith("queue-control-freeze-")):
            parser.error("new owned control receipt required")
        value = control_freeze()
        frozen.write_new(args.control_freeze, value)
        print(json.dumps({"control_sha256": provenance_sha256(value)}))
    elif args.control_freeze is None:
        parser.error("queue requires an exact control freeze")
    else:
        run(args.control_freeze)
