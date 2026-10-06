"""External admission compatibility; reuse unchanged launch/atomic execution.

Only the ledger factory and pure control verifier are replaced in a copied
function namespace. Historical modules/globals/files and Agent imports are not
mutated. Both actual source implementations and all exact proofs are pinned.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import large_scale_resident_launch_queue_v1 as previous
import large_scale_resident_sdk_argument_review_v1 as reviewer

frozen, e = previous.frozen, previous.e
PARENT_FILE = "queue-control-freeze-020.json"
PARENT_SHA256 = "5ffc04aa075b7bbb2546f85dc5b681e995eb1175b9affbfcea2c97c06eec5d10"


def owned_ledger() -> reviewer.ProjectionAttemptLedger:
    cells = frozen.schedule()
    return reviewer.ProjectionAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
        tuple(c.cell_id for c in cells), frozen.schedule_sha256(cells))


def control_freeze() -> dict[str, Any]:
    previous.historical_control()
    path = frozen.ROOT / PARENT_FILE
    if path.is_symlink() or frozen.sha256(path) != PARENT_SHA256:
        raise RuntimeError("pinned launch continuation parent drift")
    parent = json.loads(path.read_text())
    for key, source in (("controller_source_sha256", previous.__file__),
                        ("launch_reviewer_source_sha256", previous.reviewer.__file__),
                        ("launch_environment_source_sha256",
                         previous.reviewer.environment.__file__)):
        if parent[key] != frozen.sha256(Path(source)):
            raise RuntimeError("original launch controller/reviewer source drift")
    ledger = owned_ledger()
    if parent["launch_repair_proofs"] != ledger.launch_repairs:
        raise RuntimeError("original exact pre-execution authorization scope changed")
    for name, digest in parent["current_source_bound_record_adjudications"].items():
        if frozen.sha256(frozen.ROOT / reviewer.methods.RECORD_DIRECTORY / name) != digest:
            raise RuntimeError("original source-bound record proof scope changed")
    attempts = {a.run_id: a for a in ledger.attempts}
    proofs = {}
    for path in sorted((frozen.ROOT / reviewer.SEMANTIC_DIRECTORY).glob("*.json")):
        attempt = attempts.get(path.stem)
        if (path.is_symlink() or attempt is None or attempt.disposition != "valid"
                or attempt.reason != reviewer.REASON):
            raise RuntimeError("native argument proof requires exact effective admission")
        proofs[path.name] = frozen.sha256(path)
    return {**parent, "version": "resident-exact-native-specialist-json-continuation-v1",
            "parent_control_file_sha256": PARENT_SHA256,
            "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "native_argument_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
            "native_argument_adjudications": proofs, "measured_execution_changed": False,
            "semantic_retries": False, "SDK_argument_error_recovery_changed": False}


def run(path: Path) -> None:
    # Explicit, local dependency injection into external control only. No global
    # monkeypatch, broad exception waiver, new scheduler or atomic source delta.
    namespace = {**previous.run.__globals__, "owned_ledger": owned_ledger,
                 "control_freeze": control_freeze}
    entrypoint = FunctionType(previous.run.__code__, namespace, previous.run.__name__,
                              previous.run.__defaults__, previous.run.__closure__)
    entrypoint(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--control-freeze", type=Path, required=True)
    args = parser.parse_args()
    if args.freeze:
        frozen.require_remote()
        e.assert_inactive(frozen.ROOT)
        if args.control_freeze.is_symlink() or args.control_freeze.parent.resolve() != frozen.ROOT:
            raise RuntimeError("owned append-only control receipt required")
        frozen.write_new(args.control_freeze, control_freeze())
    else:
        run(args.control_freeze)
