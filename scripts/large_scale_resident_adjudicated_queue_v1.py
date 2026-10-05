"""Exact offline model-JSON review and continuation of never-started resident cells.

Preserve frozen execution app and every original rejected receipt. No broad
validation allowlist, Agent repair, replacement or runtime-global monkeypatch.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_adjudication_v1 as reviewer
import large_scale_resident_policy_review_v1 as policy_review
import large_scale_resident_queue_v1 as frozen
import large_scale_resident_record_review_v1 as record_review
import yaml
from large_scale_resident_policy_review_v1 import (
    ResidentPolicyAttemptLedger as SnapshotAttemptLedger,
)
from large_scale_resident_private_evidence_v1 import assert_inactive

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease


def create_review(run_id: str, *, record_fields: bool = False,
                  provider_policy: bool = False) -> dict[str, Any]:
    if record_fields and provider_policy:
        raise RuntimeError("mixed findings require their own exact proof")
    frozen.require_remote()
    root = frozen.ROOT
    assert_inactive(root)
    freeze_hash = frozen.verify_freeze()
    journal = root / "phase1-attempts.jsonl"
    before = journal.read_bytes()
    with QueueLease(root / "queue-lease.json"):
        cells = frozen.schedule()
        ledger = SnapshotAttemptLedger(journal, tuple(c.cell_id for c in cells),
                                       frozen.schedule_sha256(cells))
        if ledger.pending:
            raise RuntimeError("pending attempt cannot be reviewed or repeated")
        attempt = next(a for a in ledger.original_attempts if a.run_id == run_id)
        if attempt.execution_sha256 != freeze_hash:
            raise RuntimeError("review must bind this exact resident execution")
        directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
        original = json.loads((directory / "admission.json").read_text())
        config = frozen.frozen._yaml(root / "cell-configs" / (run_id + ".yaml"))
        prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
        if provenance_sha256(frozen.admit(directory, config, prices)) != attempt.receipt_sha256:
            raise RuntimeError("independent full admission differs from original finding")
        if (not json.loads((directory / "worker-shutdown.json").read_text())["verified_exited"]
                or not json.loads((directory / "private/residency-validation.json")
                                  .read_text())["passed"]):
            raise RuntimeError("review cannot waive Worker exit/residency confounders")
        trace = directory / "runs" / run_id / "trace.jsonl"
        events = [json.loads(line) for line in trace.open(encoding="utf-8")]
        shapes = record_review.shapes_for(root, directory, events) if record_fields else None
        historical_policy = provider_policy and original.get("problems") == [
            policy_review.legacy.GATE]
        review = (policy_review.legacy.review_policy(original, directory / "private/api")
                  if historical_policy else
                  policy_review.review(original, directory / "private/api", events)
                  if provider_policy else record_review.review(original, events, shapes)
                  if shapes is not None
                  else reviewer.review_model_json_failures(original, events))
        worker = frozen.APP / "src/infra_joint/worker/server.py"
        freeze = json.loads(frozen.FREEZE.read_text())
        worker_hash = freeze["source_sha256"]["src/infra_joint/worker/server.py"]
        if reviewer.sha256(worker) != worker_hash:
            raise RuntimeError("frozen Worker parsing source drift")
        value = {
            "version": "exact-model-output-adjudication-v1", "run_id": run_id,
            "original_admission_sha256": attempt.receipt_sha256,
            "original_execution_sha256": attempt.execution_sha256,
            "worker_source_sha256": worker_hash,
            "reviewer_source_sha256": reviewer.sha256(Path(
                policy_review.legacy.__file__ if historical_policy else
                policy_review.__file__ if provider_policy else record_review.__file__
                if record_fields else reviewer.__file__)),
            "resident_review_creator_sha256": reviewer.sha256(Path(__file__)),
            "original_evidence_file_sha256": {
                str(p.relative_to(directory)): reviewer.sha256(p)
                for p in sorted(directory.rglob("*")) if p.is_file()},
            **review, "reviewed_admission_sha256": provenance_sha256(review["reviewed_admission"]),
            "formal_execution_changed": False, "replacement_authorized": False,
            "model_behavior_repaired": False,
        }
        if record_fields:
            value.update(version="exact-materialized-record-field-review-v1",
                         materialized_shapes=shapes,
                         execution_sources_sha256={p: reviewer.sha256(frozen.APP / p)
                                                   for p in record_review.SOURCE_PATHS},
                         online_feedback=False, specialist_schema_visibility_not_assumed=True)
        if provider_policy:
            value.update(version="exact-resident-provider-policy-review-v1",
                         legacy_reviewer_source_sha256=reviewer.sha256(
                             Path(policy_review.legacy.__file__)),
                         input_censored=False, prompt_changed=False, evaluation_imputed=False)
        sidecar_directory = (policy_review.legacy.POLICY_DIRECTORY if historical_policy else
                             policy_review.DIRECTORY if provider_policy
                             else record_review.DIRECTORY if record_fields else "adjudications")
        path = root / sidecar_directory / (run_id + ".json")
        path.parent.mkdir(exist_ok=True)
        frozen.write_new(path, value)
        (policy_review.legacy.verify_policy_sidecar if historical_policy else
         policy_review.verify_sidecar if provider_policy else record_review.verify_sidecar
         if record_fields else reviewer.verify_sidecar)(path, attempt)
        if journal.read_bytes() != before:
            raise RuntimeError("offline review must not rewrite original journal")
    return {"run_id": run_id, "adjudication_sha256": provenance_sha256(value),
            "evidence_files": len(value["original_evidence_file_sha256"]),
            "reviewed_disposition": "valid",
            "confirmed_parse_failures": 0 if provider_policy else len(review.get("proof", [])),
            "confirmed_provider_refusals": len(review.get("proof", [])) if provider_policy else 0,
            "confirmed_record_field_failures": len(review.get("record_field_proof", [])),
            "provider_policy_failure": provider_policy,
            "rerun": False, "execution_changed": False}


def control_freeze() -> dict[str, Any]:
    frozen.require_remote()
    return {
        "version": "resident-exact-adjudicated-control-v1",
        "execution_freeze_sha256": frozen.verify_freeze(),
        "controller_source_sha256": reviewer.sha256(Path(__file__)),
        "reviewer_source_sha256": reviewer.sha256(Path(reviewer.__file__)),
        "record_reviewer_source_sha256": reviewer.sha256(Path(record_review.__file__)),
        "private_guard_source_sha256": reviewer.sha256(Path(
            sys.modules[assert_inactive.__module__].__file__)),
        "ledger_view_source_sha256": reviewer.sha256(Path(sys.modules[
            SnapshotAttemptLedger.__module__].__file__)),
        "ledger_dependency_sources_sha256": {
            cls.__module__: reviewer.sha256(Path(sys.modules[cls.__module__].__file__))
            for cls in SnapshotAttemptLedger.__mro__
            if cls.__module__.startswith("large_scale_")},
        "adjudications": {p.name: reviewer.sha256(p)
                          for p in sorted((frozen.ROOT / "adjudications").glob("*.json"))},
        "record_field_adjudications": {p.name: reviewer.sha256(p) for p in sorted(
            (frozen.ROOT / record_review.DIRECTORY).glob("*.json"))},
        "resident_provider_policy_adjudications": {p.name: reviewer.sha256(p) for p in sorted(
            (frozen.ROOT / policy_review.DIRECTORY).glob("*.json"))},
        "provider_policy_adjudications": {p.name: reviewer.sha256(p) for p in sorted(
            (frozen.ROOT / policy_review.legacy.POLICY_DIRECTORY).glob("*.json"))},
        "atomic_execution_entrypoint": str(Path(frozen.__file__).resolve()),
        "schedule_unchanged": True, "semantic_or_physical_execution_changed": False,
        "replacements_authorized": False,
    }


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if control_path.resolve().parent != root or not control_path.name.startswith(
            "queue-control-freeze-"):
        raise RuntimeError("continuation control remains an owned separate immutable receipt")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze() or not any(saved[key] for key in (
            "adjudications", "record_field_adjudications",
            "resident_provider_policy_adjudications", "provider_policy_adjudications")):
        raise RuntimeError("continuation control/adjudication drift")
    cells = frozen.schedule()
    prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    with QueueLease(root / "queue-lease.json"):
        ledger = SnapshotAttemptLedger(root / "phase1-attempts.jsonl",
                                       tuple(c.cell_id for c in cells),
                                       frozen.schedule_sha256(cells))
        if ledger.pending or any(a.disposition != "valid" for a in ledger.attempts):
            raise RuntimeError("unresolved original findings cannot be retried or bypassed")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            if saved != control_freeze():
                raise RuntimeError("continuation source/evidence freeze drift")
            if frozen.PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= frozen.GLOBAL_CAP:
                raise RuntimeError("cumulative substantive experiment cap reached")
            if any(a.cell_id == cell.cell_id for a in ledger.attempts):
                raise RuntimeError("only never-started scheduled cells may continue")
            run_id = f"{root.name}-{cell.cell_id}-attempt1"
            directory = root / "evidence" / cell.cell_id / "attempt1"
            ledger.reserve(cell.cell_id, run_id, saved["execution_freeze_sha256"])
            directory.mkdir(parents=True, exist_ok=False)
            config = frozen.cell_config(cell, run_id, frozen.reference(), root=root)
            config_path = root / "cell-configs" / (run_id + ".yaml")
            config_path.parent.mkdir(exist_ok=True)
            with config_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            # The offline controller can import external audit tools; a measured
            # child uses exactly the frozen app imports, not that audit path.
            child_env = dict(os.environ)
            child_env["PYTHONPATH"] = os.pathsep.join(
                str(frozen.APP / folder) for folder in ("src", "scripts"))
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
                receipt = frozen.admit(directory, config, prices)
                if not json.loads((directory / "private/residency-validation.json")
                                  .read_text())["passed"]:
                    raise RuntimeError("residency measurement invalid")
            except Exception as error:
                receipt = {"disposition": "confounder", "reason": "admission_unverifiable",
                           "problems": [type(error).__name__]}
            if returncode and receipt["disposition"] == "valid":
                receipt.update(disposition="confounder", reason="wrapper_execution_error")
            frozen.write_new(directory / "admission.json", receipt)
            ledger.settle(run_id, receipt["disposition"], receipt["reason"],
                          provenance_sha256(receipt))
            if receipt["disposition"] != "valid":
                raise RuntimeError("new finding requires exact offline audit; no automatic retry")
        frozen.write_new(root / "phase1-queue-completed.json", {
            "schedule_sha256": frozen.schedule_sha256(cells),
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "pruning_authorized": False, "control_sha256": provenance_sha256(saved),
            "next_required": "comprehensive private/recipient/failure audit before pruning"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review-run")
    modes.add_argument("--review-record-run")
    modes.add_argument("--review-policy-run")
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--control-freeze", type=Path)
    args = parser.parse_args()
    if args.review_run:
        print(json.dumps(create_review(args.review_run)))
    elif args.review_record_run:
        print(json.dumps(create_review(args.review_record_run, record_fields=True)))
    elif args.review_policy_run:
        print(json.dumps(create_review(args.review_policy_run, provider_policy=True)))
    elif args.freeze:
        if (args.control_freeze is None or args.control_freeze.resolve().parent != frozen.ROOT
                or not args.control_freeze.name.startswith("queue-control-freeze-")):
            raise RuntimeError("new control freeze stays inside the resident namespace")
        value = control_freeze()
        frozen.write_new(args.control_freeze, value)
        print(json.dumps({"control_sha256": provenance_sha256(value)}))
    else:
        if args.control_freeze is None:
            raise RuntimeError("continuation needs its frozen offline control receipt")
        run(args.control_freeze)
