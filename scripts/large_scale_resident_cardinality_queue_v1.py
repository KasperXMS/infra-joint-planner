"""Affected-only cardinality repair plus never-started resident cells.

Separate offline controller: preserve prior reviews and execution002 Quote
authorizations. Provider input-policy refusals never authorize a replacement.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import large_scale_resident_adjudicated_queue_v1 as previous
import large_scale_resident_queue_v1 as frozen
import large_scale_resident_quote_repair_queue_v1 as quote
import yaml
from large_scale_resident_cardinality_patch_v1 import (
    APP_NAME,
    BUG_SHA256,
    ORIGINAL_ADMISSION_SHA256,
    ORIGINAL_RUN,
    PARENT_SHA256,
    PREFIX_SHA256,
    verify_bug_evidence,
)
from large_scale_resident_private_evidence_v1 import assert_inactive

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

AUTHORIZATION = "input-cardinality-repair-authorization-001.json"
CONTROL009_FILE_SHA256 = "d9d959cd1c04f7866b825fac0b47052be0e70f2bc7211029d5593393ef60c2d0"


def verify_prefix(root: Path) -> None:
    with (root / "phase1-attempts.jsonl").open("rb") as stream:
        lines = [stream.readline() for _ in range(229)]
    if sha256(b"".join(lines)).hexdigest() != PREFIX_SHA256:
        raise RuntimeError("pre-repair stopped journal prefix drift")


def authorization_value() -> dict[str, Any]:
    frozen.require_remote()
    if frozen.APP.name != APP_NAME:
        raise RuntimeError("cardinality control requires execution003, not historical archives")
    verify_prefix(frozen.ROOT)
    verify_bug_evidence(frozen.ROOT)
    old_control = frozen.ROOT / "queue-control-freeze-009.json"
    if frozen.sha256(old_control) != CONTROL009_FILE_SHA256:
        raise RuntimeError("historical control freeze drift")
    return {
        "version": "resident-input-cardinality-repair-authorization-v1",
        "original_run_id": ORIGINAL_RUN,
        "original_admission_sha256": ORIGINAL_ADMISSION_SHA256,
        "original_execution_sha256": PARENT_SHA256,
        "new_execution_sha256": frozen.verify_freeze(),
        "bug_proof_sha256": BUG_SHA256, "stopped_journal_prefix_sha256": PREFIX_SHA256,
        "parent_control_file_sha256": CONTROL009_FILE_SHA256,
        "historical_quote_authorization_sha256": frozen.sha256(
            frozen.ROOT / "quote-repair-authorization-001.json"),
        "generic_bug_repair_only": True, "operational_replacement": False,
        "provider_policy_retry": False, "ordinary_semantic_retries": False,
        "nominal_cells_added": False, "repair_repetitions": 1,
    }


def prepare() -> None:
    assert_inactive(frozen.ROOT)
    expected = authorization_value()
    path = frozen.ROOT / AUTHORIZATION
    with QueueLease(frozen.ROOT / "queue-lease.json"):
        ledger = quote.owned_ledger()
        original = next(a for a in ledger.attempts if a.run_id == ORIGINAL_RUN)
        if (ledger.pending or original.disposition != "confounder"
                or original.receipt_sha256 != ORIGINAL_ADMISSION_SHA256
                or original.execution_sha256 != PARENT_SHA256):
            raise RuntimeError("repair requires the exact settled unresolved original")
        if path.exists():
            if json.loads(path.read_text()) != expected:
                raise RuntimeError("immutable repair authorization differs")
        else:
            frozen.write_new(path, expected)
        if ORIGINAL_RUN not in ledger._repairs:
            ledger.authorize_generic_repair(
                ORIGINAL_RUN, original_admission_sha256=ORIGINAL_ADMISSION_SHA256,
                repair_audit_sha256=provenance_sha256(expected),
                new_execution_sha256=expected["new_execution_sha256"])
        elif ledger._repairs[ORIGINAL_RUN] != expected["new_execution_sha256"]:
            raise RuntimeError("original already authorized against a different freeze")


def control_freeze() -> dict[str, Any]:
    expected = authorization_value()
    root = frozen.ROOT
    path = root / AUTHORIZATION
    if json.loads(path.read_text()) != expected:
        raise RuntimeError("repair authorization drift")
    old = json.loads((root / "queue-control-freeze-009.json").read_text())
    current = previous.control_freeze()
    for key in ("reviewer_source_sha256", "record_reviewer_source_sha256",
                "private_guard_source_sha256", "ledger_view_source_sha256",
                "ledger_dependency_sources_sha256"):
        if current[key] != old[key]:
            raise RuntimeError("historical exact reviewer dependency source drift")
    for key in ("adjudications", "record_field_adjudications",
                "resident_provider_policy_adjudications", "provider_policy_adjudications"):
        if any(current[key].get(name) != digest for name, digest in old[key].items()):
            raise RuntimeError("historical exact sidecar drift")
    quote_auth_path = root / "quote-repair-authorization-001.json"
    quote_auth = json.loads(quote_auth_path.read_text())
    if quote_auth["new_execution_sha256"] != PARENT_SHA256:
        raise RuntimeError("prior Quote repairs must remain bound to execution002")
    actual_reviews = {p.name: frozen.sha256(p)
                      for p in sorted((root / quote.reviewer.DIRECTORY).glob("*.json"))}
    if actual_reviews != old["quote_integrity_adjudications"]:
        raise RuntimeError("prior Quote repair reviews changed")
    ledger = quote.owned_ledger()
    authorized = {**{run: PARENT_SHA256 for run in quote_auth["affected_original_runs"]},
                  ORIGINAL_RUN: expected["new_execution_sha256"]}
    if ledger._repairs != authorized:
        raise RuntimeError("only separately source-bound affected repairs are authorized")
    with (root / "phase1-attempts.jsonl").open(encoding="utf-8") as stream:
        repairs = [r for line in stream if (r := json.loads(line))["event"] == "generic_repair"
                   and r["run_id"] == ORIGINAL_RUN]
    if len(repairs) != 1 or repairs[0]["repair_audit_sha256"] != provenance_sha256(expected):
        raise RuntimeError("durable authorization lacks the exact complete repair audit")
    return {
        **current, "version": "resident-exact-input-cardinality-control-v1",
        "controller_source_sha256": frozen.sha256(Path(__file__)),
        "parent_control_file_sha256": CONTROL009_FILE_SHA256,
        "quote_controller_source_sha256": frozen.sha256(Path(quote.__file__)),
        "quote_reviewer_source_sha256": frozen.sha256(Path(quote.reviewer.__file__)),
        "quote_integrity_adjudications": actual_reviews,
        "historical_quote_authorization_file_sha256": frozen.sha256(quote_auth_path),
        "repair_authorization_file_sha256": frozen.sha256(path),
        "generic_affected_reruns": [ORIGINAL_RUN],
        "semantic_or_physical_execution_changed": "five structured input schemas aligned",
        "ordinary_semantic_retries": False, "provider_policy_replacement": False,
    }


def run(control_path: Path) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    if control_path.parent.resolve() != root or not control_path.name.startswith(
            "queue-control-freeze-"):
        raise RuntimeError("owned immutable control receipt required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("repair/source/evidence control drift")
    cells = frozen.schedule()
    prices, _ = frozen.verified_prices(frozen.PREDECESSOR, frozen.APP)
    with QueueLease(root / "queue-lease.json"):
        ledger = quote.owned_ledger()
        if ledger.pending or any(a.disposition == "confounder" and a.run_id not in ledger._repairs
                                 for a in ledger.attempts):
            raise RuntimeError("unresolved finding prohibits continuation")
        for cell in cells:
            if cell.cell_id in ledger.completed_cells:
                continue
            if saved != control_freeze():
                raise RuntimeError("continuation freeze drift")
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
                value = quote.admission(directory, config, prices)
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
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--control-freeze", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.control_freeze is None or args.control_freeze.parent.resolve() != frozen.ROOT:
        parser.error("owned exact control receipt required")
    elif args.freeze:
        frozen.write_new(args.control_freeze, control_freeze())
    else:
        run(args.control_freeze)
