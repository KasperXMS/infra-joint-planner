"""Read each verified attempt view once per ledger property, with no cached waiver.

External bookkeeping only. Preserve the frozen exact reviewer and original run
function; bind this adapter explicitly rather than mutate any historical globals.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import large_scale_resident_phase2_reviewed_queue_v1 as previous


class ReadOnceAttemptLedger(previous.ReviewedAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        completed = {a.cell_id for a in self.attempts if a.disposition == "valid"}
        return tuple(cell for cell in self.cells if cell in completed)


def control_from_verified_parent(parent_path: Path, parent: dict[str, Any],
                                 cells: tuple[Any, ...]) -> dict[str, Any]:
    original = previous._control_value
    namespace = {**original.__globals__, "ReviewedAttemptLedger": ReadOnceAttemptLedger}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(parent_path, parent, cells)
    return value


def freeze_value(control: Path) -> dict[str, Any]:
    if (control.is_symlink() or control.resolve().parent != previous.frozen.ROOT
            or not control.name.startswith("phase2-reviewed-control-freeze-")):
        raise RuntimeError("owned immutable reviewed control required")
    value = json.loads(control.read_text())
    return {"version": "phase2-read-once-ledger-v1", "reviewed_control_path": str(control),
            "reviewed_control_sha256": previous.legacy.sha256(control),
            "source_sha256": previous.legacy.sha256(Path(__file__)),
            "reviewer_source_sha256": previous.legacy.sha256(Path(previous.__file__)),
            "execution_freeze_sha256": value["execution_freeze_sha256"],
            "phase2_schedule_sha256": value["phase2_schedule_sha256"],
            "attempt_view_revalidated_on_each_access": True, "validation_cached": False,
            "atomic_execution_changed": False, "semantic_retries": False}


def validate(control: Path, receipt: Path) -> None:
    if (receipt.is_symlink() or receipt.resolve().parent != previous.frozen.ROOT
            or not receipt.name.startswith("phase2-ledger-read-once-freeze-")):
        raise RuntimeError("owned immutable ledger adapter freeze required")
    if json.loads(receipt.read_text()) != freeze_value(control):
        raise RuntimeError("ledger adapter/control/source drift")


def run(control: Path, receipt: Path) -> None:
    previous.frozen.require_remote()
    previous.previous.gate.evidence.private.assert_inactive(previous.frozen.ROOT)
    validate(control, receipt)
    original = previous.run

    def checked(path: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
        validate(path, receipt)
        control = previous.checked_control
        namespace = {**control.__globals__, "_control_value": control_from_verified_parent}
        bound = FunctionType(control.__code__, namespace, control.__name__,
                             control.__defaults__, control.__closure__)
        value: tuple[dict[str, Any], tuple[Any, ...]] = bound(path)
        return value

    namespace = {**original.__globals__, "ReviewedAttemptLedger": ReadOnceAttemptLedger,
                 "checked_control": checked}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    bound(control)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-freeze", type=Path, required=True)
    parser.add_argument("--ledger-freeze", type=Path, required=True)
    args = parser.parse_args()
    run(args.control_freeze, args.ledger_freeze)
