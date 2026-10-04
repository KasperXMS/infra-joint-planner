"""Resume only never-started BDE cells after exact evidence admission; never retry."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from cost_guidance_bde_v1 import CONDITIONS
from cost_guidance_exploration_v1 import _sha256, ensure_remote, journal
from resume_cost_guidance_exploration_v1 import admitted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    args = parser.parse_args()
    root = args.deployment_root.resolve()
    ensure_remote(root)
    freeze = json.loads((root / "protocol-freeze.json").read_text())
    driver = root / "app/scripts/cost_guidance_bde_v1.py"
    if _sha256(driver) != freeze["component_sha256"]["scripts/cost_guidance_bde_v1.py"]:
        raise RuntimeError("frozen BDE driver drift")
    env = dict(os.environ, INFRA_JOINT_CODE_REVISION=freeze["code_revision"],
               PYTHONPATH=str(root / "app/src"))
    journal(root, {"event": "resume_started", "pid": os.getpid(),
                   "controller_source_sha256": _sha256(Path(__file__))})
    for task in freeze["protocol"]["tasks"]:
        for condition in CONDITIONS:
            cell = task["label"] + "-" + condition
            directory = root / "evidence" / cell
            if admitted(directory):
                journal(root, {"event": "existing_admitted_cell_preserved", "cell": cell})
                continue
            command = [sys.executable, str(driver), "--deployment-root", str(root),
                       "--api-key-file", str(args.api_key_file), "--only-cell", cell]
            with (root / ("controller-cell-" + cell + ".log")).open("x") as log:
                child = subprocess.Popen(command, cwd=root / "app", env=env,
                                         stdin=subprocess.DEVNULL, stdout=log,
                                         stderr=subprocess.STDOUT)
                journal(root, {"event": "child_controller_started", "cell": cell,
                               "pid": child.pid})
                return_code = child.wait()
            if return_code != 0:
                journal(root, {"event": "resume_audit_required", "cell": cell,
                               "child_return_code": return_code})
                raise RuntimeError("child audit stop; preserve and diagnose, never replace")
            if not admitted(directory):
                raise RuntimeError("child exited without an admitted retained result")
    journal(root, {"event": "all_primary_cells_finished", "primary_cells": 18})


if __name__ == "__main__":
    main()
