"""Projection-aware continuation without legacy full-journal replay.

Measured execution004 and all historical controller/reviewer sources stay frozen.
A settled semantic misuse is admitted by proof, never repaired or re-executed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_E_query_queue_v1 as previous
import large_scale_resident_projection_review_v1 as reviewer
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

frozen = previous.frozen
quote = previous.quote
PARENT_SHA256 = "6ffabb58e6d35224bb9709559dbb22d3e948fe72a387ef0f045b62f2899a401a"


def owned_ledger() -> reviewer.ProjectionAttemptLedger:
    cells = frozen.schedule()
    return reviewer.ProjectionAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
                                           tuple(c.cell_id for c in cells),
                                           frozen.schedule_sha256(cells))


def historical_control() -> dict[str, Any]:
    root = frozen.ROOT
    authorization_path = root / previous.AUTHORIZATION
    saved = json.loads(authorization_path.read_text())
    actual_reviews = {run: frozen.sha256(root / previous.reviewer.DIRECTORY / (run + ".json"))
                      for run in saved["affected_original_runs"]}
    if saved != previous.authorization_value(actual_reviews):
        raise RuntimeError("affected-only authorization cannot be independently reproduced")
    current = previous.previous.control_freeze()
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
    journal = [json.loads(line) for line in (root / "phase1-attempts.jsonl").open(
        encoding="utf-8")]
    repair_bindings = {r["run_id"]: r["new_execution_sha256"] for r in journal
                       if r["event"] == "generic_repair"}
    e_exclusions = {r["run_id"] for r in journal if r["event"] == "E_query_contract_confounded"}
    expected = {**previous.historical_repairs(root),
                **{run: previous.EXECUTION_SHA256 for run in saved["affected_original_runs"]}}
    if (repair_bindings != expected
            or e_exclusions != set(saved["affected_original_runs"])):
        raise RuntimeError("all and only source-bound genuine repairs must be durably authorized")
    epochs = {}
    for index, app in enumerate(previous.reviewer.APPS, 1):
        file = root / f"execution-freeze-{index:03d}.json"
        freeze = json.loads(file.read_text())
        if any(frozen.sha256(root / app / p) != digest
               for p, digest in freeze["source_sha256"].items()):
            raise RuntimeError("immutable historical or current execution epoch drift")
        epochs[str(index)] = provenance_sha256(freeze)
    return {**current, "version": "resident-exact-E-query-contract-control-v1",
            "controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "method_reviewer_source_sha256": frozen.sha256(Path(previous.reviewer.__file__)),
            "quote_reviewer_source_sha256": frozen.sha256(Path(quote.reviewer.__file__)),
            "parent_control_file_sha256": previous.PARENT_CONTROL_SHA256,
            "repair_authorization_file_sha256": frozen.sha256(authorization_path),
            "quote_integrity_adjudications": quote_reviews,
            "E_query_contract_adjudications": actual_reviews,
            "source_bound_record_adjudications": {p.name: frozen.sha256(p) for p in
                sorted((root / previous.reviewer.RECORD_DIRECTORY).glob("*.json"))},
            "execution_epochs_sha256": epochs, "generic_affected_reruns":
            saved["affected_original_runs"], "ordinary_semantic_retries": False,
            "semantic_or_physical_execution_changed": "E optional query tools removed only"}


def control_freeze() -> dict[str, Any]:
    root = frozen.ROOT
    if frozen.sha256(root / "queue-control-freeze-011.json") != PARENT_SHA256:
        raise RuntimeError("historical E controller receipt drift")
    ledger = owned_ledger()
    parent = historical_control()
    if parent != json.loads((root / "queue-control-freeze-011.json").read_text()):
        raise RuntimeError("historical E sources or review scope drift")
    effective = {a.run_id: a for a in ledger.attempts}
    proofs = {}
    for path in sorted((root / reviewer.DIRECTORY).glob("*.json")):
        run = path.stem
        if run not in effective or effective[run].reason != reviewer.REASON:
            raise RuntimeError("projection review must match exact settled membership")
        proofs[path.name] = frozen.sha256(path)
    if not proofs:
        raise RuntimeError("new continuation requires actual reproducible projection proof")
    return {**parent, "version": "resident-body-preserving-projection-control-v2",
            "parent_control_file_sha256": PARENT_SHA256,
            "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "projection_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "projected_record_adjudications": proofs,
            "measured_execution_changed": False, "semantic_retries": False}


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
        authorization = json.loads((root / previous.AUTHORIZATION).read_text())
        authorized = set(previous.historical_repairs(root)) | set(
            authorization["affected_original_runs"])
        if ledger.pending or any(a.disposition == "confounder" and a.run_id not in authorized
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
            ledger.reserve(cell.cell_id, run_id, previous.EXECUTION_SHA256)
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
                    previous.assert_E_tool_isolation(directory, [json.loads(line) for line in
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
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if args.freeze:
        previous.assert_inactive(frozen.ROOT)
        frozen.require_remote()
        if args.control_freeze.parent.resolve() != frozen.ROOT:
            raise RuntimeError("owned control receipt required")
        frozen.write_new(args.control_freeze, control_freeze())
    else:
        run(args.control_freeze)

