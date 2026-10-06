"""Continue exact record-field admissions without mutating historical controls.

The existing four-epoch record reviewer/ledger already validates these proofs.
Only historical control scope changes: verify its pinned receipt and every bound
source/proof, rather than recomputing old manifests using newly added sidecars.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_field_policy_queue_v1 as previous
import yaml

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import QueueLease

frozen = previous.frozen
e = previous.e
reviewer = previous.reviewer
owned_ledger = previous.owned_ledger
PARENT_FILE = "queue-control-freeze-015.json"
PARENT_SHA256 = "9ff88aca201824b1d48d561198463bd4a6f433ad7f78cdb179ac5ad5c3b0fecf"
SOURCE_KEYS = {
    "controller_source_sha256": "large_scale_resident_field_policy_queue_v1",
    "reviewer_source_sha256": "large_scale_adjudication_v1",
    "record_reviewer_source_sha256": "large_scale_resident_record_review_v1",
    "private_guard_source_sha256": "large_scale_resident_private_evidence_v1",
    "ledger_view_source_sha256": "large_scale_resident_policy_review_v1",
    "method_reviewer_source_sha256": "large_scale_resident_method_contract_review_v1",
    "quote_reviewer_source_sha256": "large_scale_quote_repair_ledger_v1",
    "parent_controller_source_sha256": "large_scale_resident_timeout_queue_v1",
    "projection_reviewer_source_sha256": "large_scale_resident_projection_review_v1",
    "timeout_reviewer_source_sha256": "large_scale_resident_timeout_review_v1",
    "field_policy_reviewer_source_sha256": "large_scale_resident_field_policy_review_v1",
    "policy_reviewer_source_sha256": "large_scale_provider_policy_review_v1",
}
PROOF_FOLDERS = {
    "adjudications": "adjudications",
    "record_field_adjudications": "record-field-adjudications",
    "resident_provider_policy_adjudications": "resident-provider-policy-adjudications",
    "provider_policy_adjudications": "provider-policy-adjudications",
    "quote_integrity_adjudications": "quote-integrity-adjudications",
    "E_query_contract_adjudications": "E-query-contract-adjudications",
    "source_bound_record_adjudications": "source-bound-record-field-adjudications",
    "projected_record_adjudications": "projected-record-field-adjudications",
    "compound_cloud_timeout_adjudications": "compound-cloud-timeout-adjudications",
    "compound_record_policy_adjudications": "compound-record-policy-adjudications",
}


def source_sha256(name: str) -> str:
    path = importlib.import_module(name).__file__
    if path is None:
        raise RuntimeError("historical control requires actual file-backed source")
    return frozen.sha256(Path(path))


def historical_control() -> dict[str, Any]:
    root = frozen.ROOT
    path = root / PARENT_FILE
    if path.is_symlink() or frozen.sha256(path) != PARENT_SHA256:
        raise RuntimeError("pinned historical field/policy control receipt drift")
    parent = json.loads(path.read_text())
    for key, name in SOURCE_KEYS.items():
        if parent[key] != source_sha256(name):
            raise RuntimeError("historical control source drift")
    for name, digest in parent["ledger_dependency_sources_sha256"].items():
        if source_sha256(name) != digest:
            raise RuntimeError("historical ledger dependency source drift")
    for key, folder in PROOF_FOLDERS.items():
        for name, digest in parent[key].items():
            filename = name if name.endswith(".json") else name + ".json"
            proof = root / folder / filename
            if (Path(filename).name != filename or proof.is_symlink()
                    or frozen.sha256(proof) != digest):
                raise RuntimeError("historical bound proof drift")
    if (frozen.sha256(root / previous.PARENT_FILE) != parent["parent_control_file_sha256"]
            or frozen.sha256(root / e.AUTHORIZATION)
            != parent["repair_authorization_file_sha256"]):
        raise RuntimeError("historical parent or affected-only authorization drift")
    for index, app in enumerate(reviewer.methods.APPS, 1):
        freeze = json.loads((root / f"execution-freeze-{index:03d}.json").read_text())
        if (provenance_sha256(freeze) != parent["execution_epochs_sha256"][str(index)]
                or any(frozen.sha256(root / app / p) != digest
                       for p, digest in freeze["source_sha256"].items())):
            raise RuntimeError("historical immutable execution source drift")
    return parent


def control_freeze() -> dict[str, Any]:
    parent = historical_control()
    ledger = owned_ledger()
    attempts = {a.run_id: a for a in ledger.attempts}
    proofs: dict[str, str] = {}
    for path in sorted((frozen.ROOT / reviewer.methods.RECORD_DIRECTORY).glob("*.json")):
        attempt = attempts.get(path.stem)
        if (path.is_symlink() or attempt is None or attempt.disposition != "valid"
                or attempt.reason != reviewer.records.REASON):
            raise RuntimeError("record continuation requires exact settled nominal membership")
        proofs[path.name] = frozen.sha256(path)
    if not set(proofs) - set(parent["source_bound_record_adjudications"]):
        raise RuntimeError("record continuation requires a newly reproduced record proof")
    return {
        **parent, "version": "resident-exact-record-field-continuation-control-v1",
        "parent_control_file_sha256": PARENT_SHA256,
        "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
        "controller_source_sha256": frozen.sha256(Path(__file__)),
        "current_source_bound_record_adjudications": proofs,
        "parent_proof_scope_preserved": True, "nominal_retries": False,
        "measured_execution_changed": False,
    }


def run(control_path: Path) -> None:
    frozen.require_remote()
    e.assert_inactive(frozen.ROOT)
    root = frozen.ROOT
    if (control_path.is_symlink() or control_path.parent.resolve() != root
            or not control_path.name.startswith("queue-control-freeze-")):
        raise RuntimeError("owned immutable record continuation control receipt required")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze():
        raise RuntimeError("record continuation source/evidence drift")
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
                raise RuntimeError("record continuation control drift")
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
                value = previous.previous.previous.quote.admission(directory, config, prices)
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
