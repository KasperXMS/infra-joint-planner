"""Resume never-started cells with hash-bound offline adjudication, not reruns.

The complete frozen execution app, Worker and all Agent inputs remain unchanged.
Only the queue's admission view understands independently reviewed sidecars.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from large_scale_adjudication_v1 import ROOT, AdjudicatedAttemptLedger, sha256

from infra_joint.control.provenance import provenance_sha256


def control_freeze() -> dict[str, Any]:
    import large_scale_queue_v1 as frozen

    if sys.platform != "linux" or frozen.ROOT != ROOT:
        raise RuntimeError("formal queue remains remote")
    execution = frozen.verify_execution_freeze(ROOT / "execution-freeze-002.json")
    return {"version": "offline-adjudicated-queue-control-v1",
            "frozen_execution_sha256": execution, "frozen_execution_changed": False,
            "queue_control_source_sha256": sha256(Path(__file__)),
            "adjudication_source_sha256": sha256(Path(__file__).with_name(
                "large_scale_adjudication_v1.py")),
            "adjudication_receipts": {p.name: sha256(p)
                                      for p in sorted((ROOT / "adjudications").glob("*.json"))},
            "schedule_unchanged": True, "repeat_valid_cells": False}


def run(control_path: Path) -> None:
    import large_scale_queue_v1 as frozen

    if control_path.resolve().parent != ROOT or not control_path.name.startswith(
            "queue-control-freeze-"):
        raise RuntimeError("queue-control freeze must be a separate owned immutable receipt")
    saved = json.loads(control_path.read_text())
    if saved != control_freeze() or not saved["adjudication_receipts"]:
        raise RuntimeError("queue-control/adjudication provenance drift")
    # This adapter changes only the offline nominal-admission view. The frozen
    # queue's child command still launches its original source/entry point.
    frozen.AttemptLedger = AdjudicatedAttemptLedger
    frozen.run_queue(ROOT / "execution-freeze-002.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if args.freeze:
        value = control_freeze()
        if args.control_freeze.resolve().parent != ROOT:
            raise RuntimeError("control freeze must stay inside the experiment namespace")
        with args.control_freeze.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
        print(json.dumps({"control_freeze_sha256": provenance_sha256(value)}))
    else:
        run(args.control_freeze)
