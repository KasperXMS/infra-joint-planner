# pyright: reportPrivateUsage=false
"""Affected E repair plus never-started resident cells, without semantic retries.

Offline control only. Atomic children import exactly execution004; actual Workers
keep immutable execution003. Original admissions and all prior reviewers remain.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import large_scale_resident_adjudicated_queue_v1 as previous
import large_scale_resident_method_contract_review_v1 as reviewer
import large_scale_resident_queue_v1 as frozen
import large_scale_resident_quote_repair_queue_v1 as quote
import yaml
from large_scale_resident_E_query_patch_v1 import APP_NAME
from large_scale_resident_private_evidence_v1 import assert_inactive

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

AUTHORIZATION = "E-query-contract-repair-authorization-001.json"
EXECUTION_SHA256 = "16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c"
PARENT_CONTROL_SHA256 = "968dc345cd7d522f932c82bbc4190e74607f68df7301147bd20d42559d029ed0"


def owned_ledger() -> reviewer.MethodContractAttemptLedger:
    cells = frozen.schedule()
    return reviewer.MethodContractAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
                                                tuple(c.cell_id for c in cells),
                                                frozen.schedule_sha256(cells))


def historical_repairs(root: Path) -> dict[str, str]:
    quotes = json.loads((root / "quote-repair-authorization-001.json").read_text())
    cardinality = json.loads((root / "input-cardinality-repair-authorization-001.json").read_text())
    return {**{run: quotes["new_execution_sha256"] for run in quotes["affected_original_runs"]},
            cardinality["original_run_id"]: cardinality["new_execution_sha256"]}


def authorization_value(reviews: dict[str, str]) -> dict[str, Any]:
    frozen.require_remote()
    root = frozen.ROOT
    if frozen.APP.name != APP_NAME or frozen.verify_freeze() != EXECUTION_SHA256:
        raise RuntimeError("E control requires the exact independently validated execution004")
    proof = json.loads((root / reviewer.BUG_PROOF).read_text())
    if (frozen.sha256(root / reviewer.BUG_PROOF) != reviewer.BUG_SHA256
            or set(reviews) != set(proof["affected_effective_run_ids"]) or len(reviews) != 14
            or frozen.sha256(root / "queue-control-freeze-010.json") != PARENT_CONTROL_SHA256):
        raise RuntimeError("only the fourteen proven E tool-space confounders may be repeated")
    return {"version": "E-query-contract-affected-only-authorization-v1",
            "new_execution_sha256": EXECUTION_SHA256, "bug_proof_sha256": reviewer.BUG_SHA256,
            "parent_control_file_sha256": PARENT_CONTROL_SHA256,
            "affected_original_runs": proof["affected_effective_run_ids"], "review_sha256": reviews,
            "historical_quote_authorization_sha256": frozen.sha256(
                root / "quote-repair-authorization-001.json"),
            "historical_cardinality_authorization_sha256": frozen.sha256(
                root / "input-cardinality-repair-authorization-001.json"),
            "generic_bug_repair_only": True, "operational_replacement": False,
            "ordinary_semantic_retries": False, "repair_repetitions": 1,
            "nominal_cells_added": False, "closed_predecessor_repeated": False}


def prepare() -> None:
    frozen.require_remote()
    root = frozen.ROOT
    assert_inactive(root)
    if frozen.APP.name != APP_NAME or frozen.verify_freeze() != EXECUTION_SHA256:
        raise RuntimeError("prepare must use actual frozen execution004")
    proof = json.loads((root / reviewer.BUG_PROOF).read_text())
    if frozen.sha256(root / reviewer.BUG_PROOF) != reviewer.BUG_SHA256:
        raise RuntimeError("actual E contract bug scope drift")
    with QueueLease(root / "queue-lease.json"):
        ledger = owned_ledger()
        if ledger.pending:
            raise RuntimeError("possibly live attempts prohibit retrospective changes")
        targets = {a.run_id: a for a in ledger.attempts
                   if a.run_id in proof["affected_effective_run_ids"]}
        reviews: dict[str, str] = {}
        for run in proof["affected_effective_run_ids"]:
            attempt = targets[run]
            path = root / reviewer.DIRECTORY / (run + ".json")
            if attempt.reason == reviewer.REASON:
                value = json.loads(path.read_text())
                original = replace(attempt, disposition="valid",
                                   reason=value["original_effective_reason"],
                                   receipt_sha256=value["original_admission_sha256"])
                reviewer.verify_e(path, original)
            else:
                directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
                raw = json.loads((directory / "admission.json").read_text())
                effective = reviewer.parent.effective_admission(root, attempt)
                events = [json.loads(line) for line in (
                    directory / "runs" / run / "trace.jsonl").read_text().splitlines()]
                value = {**reviewer.review_e(effective, events, directory / "private/api"),
                         "run_id": run, "original_admission_sha256": attempt.receipt_sha256,
                         "original_raw_admission_sha256": provenance_sha256(raw),
                         "original_effective_reason": attempt.reason,
                         "original_execution_sha256": attempt.execution_sha256,
                         "frozen_source_sha256": reviewer.frozen_sources(
                             root, attempt, (reviewer.SOURCE,))[reviewer.SOURCE],
                         "reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
                         "bug_proof_sha256": reviewer.BUG_SHA256,
                         "original_evidence_file_sha256": reviewer.evidence_files(directory)}
                value["reviewed_admission_sha256"] = provenance_sha256(value["reviewed_admission"])
                path.parent.mkdir(exist_ok=True)
                if path.exists():
                    if json.loads(path.read_text()) != value:
                        raise RuntimeError("existing exact E review differs; never overwrite")
                else:
                    frozen.write_new(path, value)
                reviewer.verify_e(path, attempt)
                ledger.invalidate_e(run)
            reviews[run] = frozen.sha256(path)
        expected = authorization_value(reviews)
        path = root / AUTHORIZATION
        if path.exists():
            if json.loads(path.read_text()) != expected:
                raise RuntimeError("immutable affected-only E authorization drift")
        else:
            frozen.write_new(path, expected)
        for run in expected["affected_original_runs"]:
            attempt = next(a for a in ledger.attempts if a.run_id == run)
            if run not in ledger._repairs:
                ledger.authorize_generic_repair(
                    run, original_admission_sha256=str(attempt.receipt_sha256),
                    repair_audit_sha256=provenance_sha256(expected),
                    new_execution_sha256=EXECUTION_SHA256)
            elif ledger._repairs[run] != EXECUTION_SHA256:
                raise RuntimeError("E repair already bound to another execution")


def control_freeze() -> dict[str, Any]:
    root = frozen.ROOT
    authorization_path = root / AUTHORIZATION
    saved = json.loads(authorization_path.read_text())
    actual_reviews = {run: frozen.sha256(root / reviewer.DIRECTORY / (run + ".json"))
                      for run in saved["affected_original_runs"]}
    if saved != authorization_value(actual_reviews):
        raise RuntimeError("affected-only authorization cannot be independently reproduced")
    current = previous.control_freeze()
    old = json.loads((root / "queue-control-freeze-010.json").read_text())
    for key in ("reviewer_source_sha256", "record_reviewer_source_sha256",
                "private_guard_source_sha256", "ledger_view_source_sha256",
                "ledger_dependency_sources_sha256"):
        if current[key] != old[key]:
            raise RuntimeError("historical exact reviewer source drift")
    for key in ("adjudications", "record_field_adjudications",
                "resident_provider_policy_adjudications", "provider_policy_adjudications"):
        if any(current[key].get(name) != digest for name, digest in old[key].items()):
            raise RuntimeError("historical exact review evidence drift")
    quote_reviews = {p.name: frozen.sha256(p) for p in
                     sorted((root / quote.reviewer.DIRECTORY).glob("*.json"))}
    if quote_reviews != old["quote_integrity_adjudications"]:
        raise RuntimeError("historical Quote review scope drift")
    ledger = owned_ledger()
    expected = {**historical_repairs(root),
                **{run: EXECUTION_SHA256 for run in saved["affected_original_runs"]}}
    if (ledger._repairs != expected
            or set(ledger._e_reviews) != set(saved["affected_original_runs"])):
        raise RuntimeError("all and only source-bound genuine repairs must be durably authorized")
    epochs = {}
    for index, app in enumerate(reviewer.APPS, 1):
        file = root / f"execution-freeze-{index:03d}.json"
        freeze = json.loads(file.read_text())
        if any(frozen.sha256(root / app / p) != digest
               for p, digest in freeze["source_sha256"].items()):
            raise RuntimeError("immutable historical or current execution epoch drift")
        epochs[str(index)] = provenance_sha256(freeze)
    return {**current, "version": "resident-exact-E-query-contract-control-v1",
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "method_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "quote_reviewer_source_sha256": frozen.sha256(Path(quote.reviewer.__file__)),
            "parent_control_file_sha256": PARENT_CONTROL_SHA256,
            "repair_authorization_file_sha256": frozen.sha256(authorization_path),
            "quote_integrity_adjudications": quote_reviews,
            "E_query_contract_adjudications": actual_reviews,
            "source_bound_record_adjudications": {p.name: frozen.sha256(p) for p in
                sorted((root / reviewer.RECORD_DIRECTORY).glob("*.json"))},
            "execution_epochs_sha256": epochs, "generic_affected_reruns":
            saved["affected_original_runs"], "ordinary_semantic_retries": False,
            "semantic_or_physical_execution_changed": "E optional query tools removed only"}


def assert_E_tool_isolation(directory: Path, events: list[dict[str, Any]]) -> None:
    starts = [e["payload"] for e in events if e["event_type"] == "method.variant.start"]
    if (len(starts) != 1 or starts[0].get("variant") != "route-e-v0"
            or starts[0].get("optional_cost_queries") is not False):
        raise RuntimeError("execution004 E method flag is inconsistent with its no-query contract")
    for path in (directory / "private/api").glob("*-usage.json"):
        usage = json.loads(path.read_text())
        if usage["recipient"] != "manager":
            continue
        call = usage["call_id"]
        if Path(call).name != call or path.name != call + "-usage.json":
            raise RuntimeError("E surface audit API identity mismatch")
        request = json.loads((path.parent / (call + "-request.json")).read_text())
        names = [t.get("function", {}).get("name", "") for t in request.get("tools", [])]
        if any(n.startswith("estimate_") or n in
               {"commit_quote", "discard_quote", "compare_ready_actions"} for n in names):
            raise RuntimeError("E method must not expose cost-query/quote/comparison tools")


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if control_path.parent.resolve() != root or not control_path.name.startswith(
            "queue-control-freeze-"):
        raise RuntimeError("owned immutable E control receipt required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("actual E control/source/evidence drift")
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
                raise RuntimeError("E continuation control drift")
            if frozen.PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= frozen.GLOBAL_CAP:
                raise RuntimeError("cumulative substantive cap reached")
            index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
            run_id = f"{root.name}-{cell.cell_id}-attempt{index}"
            directory = root / "evidence" / cell.cell_id / f"attempt{index}"
            ledger.reserve(cell.cell_id, run_id, EXECUTION_SHA256)
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
            value: dict[str, Any]
            try:
                value = quote.admission(directory, config, prices)
                if cell.method == "E":
                    trace = directory / "runs" / run_id / "trace.jsonl"
                    assert_E_tool_isolation(directory, [json.loads(line) for line in
                                                        trace.read_text().splitlines()])
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
            "completed_cells": ledger.completed_cells,
            "attempt_count": len(ledger.attempts), "pruning_authorized": False,
            "control_sha256": provenance_sha256(saved),
            "next_required": "all168 private/recipient/failure/adoption audit before pruning"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--control-freeze", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.control_freeze is None or args.control_freeze.parent.resolve() != frozen.ROOT:
        parser.error("owned exact E control receipt required")
    elif args.freeze:
        frozen.write_new(args.control_freeze, control_freeze())
    else:
        run(args.control_freeze)
