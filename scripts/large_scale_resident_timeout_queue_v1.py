"""Separate exact timeout continuation; no measured execution changes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_projection_queue_v2 as previous
import large_scale_resident_timeout_review_v1 as reviewer
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

frozen = previous.frozen
e = previous.previous
PARENT_FILE = "queue-control-freeze-013.json"
PARENT_SHA256 = "a06073aefa13d0363ec403ab7ffa9756ed62b20d7eec8ea0f5ed00cde674d8a5"


def owned_ledger() -> reviewer.ProjectionAttemptLedger:
    cells = frozen.schedule()
    return reviewer.ProjectionAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
                                           tuple(c.cell_id for c in cells),
                                           frozen.schedule_sha256(cells))


def historical_control() -> dict[str, Any]:
    """Reproduce the exact parent without replay through its obsolete ledger."""
    root = frozen.ROOT
    if frozen.sha256(root / PARENT_FILE) != PARENT_SHA256:
        raise RuntimeError("historical projection control receipt drift")
    if frozen.sha256(root / "queue-control-freeze-011.json") != previous.PARENT_SHA256:
        raise RuntimeError("historical E control receipt drift")
    parent = previous.historical_control()
    if parent != json.loads((root / "queue-control-freeze-011.json").read_text()):
        raise RuntimeError("historical E sources or proof scope drift")
    proofs = {p.name: frozen.sha256(p) for p in sorted(
        (root / previous.reviewer.DIRECTORY).glob("*.json"))}
    value = {**parent, "version": "resident-body-preserving-projection-control-v2",
             "parent_control_file_sha256": previous.PARENT_SHA256,
             "parent_controller_source_sha256": frozen.sha256(Path(e.__file__)),
             "controller_source_sha256": frozen.sha256(Path(previous.__file__)),
             "projection_reviewer_source_sha256": frozen.sha256(
                 Path(previous.reviewer.__file__)),
             "projected_record_adjudications": proofs,
             "measured_execution_changed": False, "semantic_retries": False}
    if value != json.loads((root / PARENT_FILE).read_text()):
        raise RuntimeError("historical projection sources or proof scope drift")
    return value


def control_freeze() -> dict[str, Any]:
    ledger = owned_ledger()
    parent = historical_control()
    attempts = {a.run_id: a for a in ledger.attempts}
    proofs = {}
    for path in sorted((frozen.ROOT / reviewer.TIMEOUT_DIRECTORY).glob("*.json")):
        attempt = attempts.get(path.stem)
        if (attempt is None or attempt.disposition != "operational_excluded"
                or attempt.reason != reviewer.REASON):
            raise RuntimeError("timeout proof requires exact settled operational membership")
        proofs[path.name] = frozen.sha256(path)
    if not proofs:
        raise RuntimeError("continuation requires an actual independently reproduced timeout")
    return {**parent, "version": "resident-exact-compound-cloud-timeout-control-v1",
            "parent_control_file_sha256": PARENT_SHA256,
            "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "timeout_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "compound_cloud_timeout_adjudications": proofs,
            "operational_replacement_requires_identical_execution": True,
            "max_operational_replacements_per_cell": 1}


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if control_path.parent.resolve() != root or not control_path.name.startswith(
            "queue-control-freeze-"):
        raise RuntimeError("owned immutable timeout control receipt required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("timeout continuation source/evidence drift")
    cells = frozen.schedule()
    prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    with QueueLease(root / "queue-lease.json"):
        ledger = owned_ledger()
        authorization = json.loads((root / e.AUTHORIZATION).read_text())
        authorized = set(e.historical_repairs(root)) | set(authorization["affected_original_runs"])
        if ledger.pending or any(a.disposition == "confounder" and a.run_id not in authorized
                                 for a in ledger.attempts):
            raise RuntimeError("unresolved finding prohibits continuation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            if saved != control_freeze():
                raise RuntimeError("timeout continuation control drift")
            if frozen.PRIOR_SUBSTANTIVE_CELLS + len(ledger.completed_cells) >= frozen.GLOBAL_CAP:
                raise RuntimeError("cumulative substantive cap reached")
            index = 1 + sum(a.cell_id == cell.cell_id for a in ledger.attempts)
            run_id = f"{root.name}-{cell.cell_id}-attempt{index}"
            directory = root / "evidence" / cell.cell_id / f"attempt{index}"
            ledger.reserve(cell.cell_id, run_id, e.EXECUTION_SHA256)
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
                value = previous.quote.admission(directory, config, prices)
                if cell.method == "E":
                    trace = directory / "runs" / run_id / "trace.jsonl"
                    e.assert_E_tool_isolation(directory, [json.loads(line) for line in
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
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "pruning_authorized": False, "control_sha256": provenance_sha256(saved),
            "next_required": "all168 private/recipient/failure/adoption audit before pruning"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if args.freeze:
        e.assert_inactive(frozen.ROOT)
        frozen.require_remote()
        if args.control_freeze.parent.resolve() != frozen.ROOT:
            raise RuntimeError("owned control receipt required")
        frozen.write_new(args.control_freeze, control_freeze())
    else:
        run(args.control_freeze)
