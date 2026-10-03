"""Resume only not-yet-started cells after audited admission; never rerun an attempt."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from cost_guidance_exploration_v1 import (
    CONDITIONS,
    _sha256,
    ensure_remote,
    journal,
    protocol,
)


def admitted(directory: Path) -> bool:
    if not directory.exists():
        return False
    validation_path = directory / "lightweight-validation.json"
    if not validation_path.is_file():
        raise RuntimeError("existing cell incomplete; audit, never resume or replace its execution")
    validation: dict[str, Any] = json.loads(validation_path.read_text())
    if not validation["problems"]:
        return True
    # Explicit independent postrun adjudication, not a permissive error-code whitelist.
    audit_path = directory / "postrun-eligibility-audit-001.json"
    if not audit_path.is_file():
        raise RuntimeError("existing cell requires an independent operational/semantic audit")
    audit = json.loads(audit_path.read_text())
    results = list(directory.glob("runs/*/result.json"))
    if (len(results) != 1 or not audit.get("effective_cell_retained")
            or audit.get("rerun") is not False or not audit.get("remaining_operational_gates_pass")
            or audit.get("runtime_or_semantic_behavior_changed") is not False
            or _sha256(results[0]) != audit.get("result_sha256")
            or _sha256(results[0].parent / "trace.jsonl") != audit.get("trace_sha256")):
        raise RuntimeError("postrun audit missing/inconsistent; never silently admit a confounder")
    return True


def main(args: argparse.Namespace) -> None:
    root = args.deployment_root.resolve()
    ensure_remote(root)
    freeze = json.loads((root / "protocol-freeze.json").read_text())
    env = dict(os.environ, INFRA_JOINT_CODE_REVISION=freeze["code_revision"],
               PYTHONPATH=str(root / "app/src"))
    driver = root / "app/scripts/cost_guidance_exploration_v1.py"
    if _sha256(driver) != freeze["component_sha256"]["scripts/cost_guidance_exploration_v1.py"]:
        raise RuntimeError("frozen cell driver drift")
    journal(root, {"event": "resume_started", "pid": os.getpid(),
                   "controller_source_sha256": _sha256(Path(__file__))})
    for row in protocol()["tasks"]:
        for condition in CONDITIONS:
            cell = row["label"] + "-" + condition
            directory = root / "evidence" / cell
            if admitted(directory):
                journal(root, {"event": "existing_admitted_cell_preserved", "cell": cell})
                continue
            command = [sys.executable, str(driver), "--deployment-root", str(root),
                       "--api-key-file", str(args.api_key_file), "--only-cell", cell]
            with (root / f"controller-cell-{cell}.log").open("x") as log:
                child = subprocess.Popen(command, cwd=root / "app", env=env,
                                         stdin=subprocess.DEVNULL, stdout=log,
                                         stderr=subprocess.STDOUT)
                journal(root, {"event": "child_controller_started", "cell": cell,
                               "pid": child.pid})
                return_code = child.wait()
            if return_code != 0:
                journal(root, {"event": "resume_audit_required", "cell": cell,
                               "child_return_code": return_code})
                raise RuntimeError("child audit stop; preserve evidence and diagnose before continuing")
            if not admitted(directory):
                raise RuntimeError("child exited without an admitted result")
    journal(root, {"event": "all_primary_cells_finished", "primary_cells": 16})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    main(parser.parse_args())
