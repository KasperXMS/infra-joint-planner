"""Resume only the unexecuted suffix using the unchanged frozen cell entry point."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from blind_3family_validation_v1 import _sha256, _yaml
from predecision_crossbenchmark_audit_v1 import audit_cell
from predecision_crossbenchmark_v1 import CONDITIONS, ensure_remote, validate_protocol
from run_predecision_matrix_v1 import write_new


def remaining_cells(protocol: dict[str, Any], after_cell: str) -> list[str]:
    validate_protocol(protocol)
    cells = [f"{row['label']}-{condition}" for row in protocol["tasks"]
             for condition in CONDITIONS]
    if after_cell not in cells:
        raise ValueError("continuation boundary is not in the frozen schedule")
    return cells[cells.index(after_cell) + 1:]


def require_clean_attempt(directory: Path) -> None:
    record = audit_cell(directory)
    if (record["validation"]["problems"] or record["probe_errors"]
            or not record["persistence"]["pass"] or not record["provenance"]["pass"]
            or not record["summary"]["logical_privacy_pass"]
            or record["terminal_answer_provenance_pass"] is False):
        raise RuntimeError("attempt requires audit; no suffix execution authorized")
    shutdown = json.loads((directory / "worker-shutdown.json").read_text())
    if shutdown["errors"]:
        raise RuntimeError("Worker shutdown incident; no suffix execution authorized")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--after-cell", required=True)
    parser.add_argument("--boundary-attempt", required=True,
                        choices=("primary", "operational-replacement-1", "transport-patch-1",
                                 "backend-client-patch-1", "isolation-patch-1"))
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--api-key-file", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    ensure_remote(root)
    protocol_path = args.protocol or (
        root / "app/configs/experiments/predecision-crossbenchmark-v1.yaml"
    )
    protocol = _yaml(protocol_path)
    freeze = json.loads((root / "protocol-freeze.json").read_text())
    entry = root / "app/scripts/predecision_crossbenchmark_v1.py"
    if (_sha256(entry) != freeze["runner_sha256"]
            or _sha256(protocol_path) != freeze["protocol_sha256"]):
        raise RuntimeError("frozen execution entry or protocol changed")
    cells = remaining_cells(protocol, args.after_cell)
    journal = root / f"continuation-after-{args.after_cell}.jsonl"
    with journal.open("x", encoding="utf-8") as stream:
        def record(value: object) -> None:
            stream.write(json.dumps(value) + "\n")
            stream.flush()

        record({"event": "started", "pid": os.getpid(), "remaining_cells": cells,
                "boundary_attempt": args.boundary_attempt,
                "controller_sha256": _sha256(Path(__file__))})
        try:
            if args.wait_pid is not None:
                handle = Path(f"/proc/{args.wait_pid}/cmdline")
                while handle.exists():
                    command = handle.read_bytes().decode()
                    if not command:
                        break
                    if root.name not in command or args.after_cell not in command:
                        raise RuntimeError("wait PID ownership changed")
                    time.sleep(5)
            require_clean_attempt(root / "evidence" / args.after_cell / args.boundary_attempt)
            env = dict(os.environ, PYTHONPATH=str(root / "app/src"),
                       INFRA_JOINT_CODE_REVISION=freeze["code_revision"])
            for cell in cells:
                if (root / "evidence" / cell).exists():
                    raise FileExistsError(f"scheduled suffix cell already exists: {cell}")
                if _sha256(entry) != freeze["runner_sha256"]:
                    raise RuntimeError("frozen entry changed during continuation")
                command = [str(root / "app/.venv/bin/python"), str(entry),
                           "--deployment-root", str(root), "--api-key-file",
                           str(args.api_key_file), "--protocol", str(protocol_path),
                           "--only-cell", cell]
                record({"event": "cell_started", "cell": cell})
                with (root / f"continuation-{cell}.log").open("x") as log:
                    subprocess.run(command, cwd=root / "app", env=env,
                                   stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
                require_clean_attempt(root / "evidence" / cell / "primary")
                record({"event": "cell_audited", "cell": cell})
            record({"event": "completed", "cells": len(cells)})
        except BaseException as error:
            record({"event": "audit_required", "exception_type": type(error).__name__,
                    "message": str(error)})
            raise
    write_new(root / f"continuation-after-{args.after_cell}-completed.json",
              {"completed_suffix": cells, "execution_revision": freeze["code_revision"]})


if __name__ == "__main__":
    main()
