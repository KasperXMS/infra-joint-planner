"""Read each verified attempt view once per ledger property, with no cached waiver.

External bookkeeping only. Preserve the frozen exact reviewer and original run
function; bind this adapter explicitly rather than mutate any historical globals.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_reviewed_queue_v1 as previous


class ReadOnceAttemptLedger(previous.ReviewedAttemptLedger):
    @property
    def completed_cells(self) -> tuple[str, ...]:
        completed = {a.cell_id for a in self.attempts if a.disposition == "valid"}
        return tuple(cell for cell in self.cells if cell in completed)

    def _check_reservation(self, cell_id: str) -> None:
        # One verified immutable view for this one pure invariant check. The
        # original validator body/error rules are reused without modification.
        # Every next check/access obtains and validates a new view, not a cache.
        attempts = self.attempts
        completed = {a.cell_id for a in attempts if a.disposition == "valid"}
        view = SimpleNamespace(
            cells=self.cells, attempts=attempts,
            completed_cells=tuple(c for c in self.cells if c in completed),
            pending=tuple(a for a in attempts if a.disposition is None),
            _repairs=dict(self._repairs),
        )
        previous.AttemptLedger._check_reservation(cast(previous.AttemptLedger, view), cell_id)


def create_review(run_id: str, parent_path: Path) -> dict[str, Any]:
    """Review another exact raw finding after previously reviewed reservations."""
    original = previous.create_review
    namespace = {**original.__globals__, "AttemptLedger": ReadOnceAttemptLedger}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(run_id, parent_path)
    return value


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


def assert_startup_safe(root: Path, *, proc_root: Path = Path("/proc"),
                        own_pid: int | None = None) -> None:
    """Ignore only this registered controller, never relax a private-body guard."""
    current = os.getpid() if own_pid is None else own_pid
    handles = [root / "queue-lease.json", *root.glob("queue-process-*.json"),
               *root.glob("evidence/*/attempt*/process.json")]
    for handle in handles:
        if not handle.exists():
            continue
        if handle.is_symlink():
            raise RuntimeError("startup process handles must be owned files")
        pid = json.loads(handle.read_text())["pid"]
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise RuntimeError("startup process identity invalid")
        command = proc_root / str(pid) / "cmdline"
        if not command.exists() or root.name.encode() not in command.read_bytes():
            continue
        if (pid != current or handle.parent != root
                or not handle.name.startswith("queue-process-")
                or b"large_scale_resident_phase2_read_once_v1" not in command.read_bytes()):
            raise RuntimeError("another live controller/atomic/lease prohibits startup")


def run(control: Path, receipt: Path) -> None:
    previous.frozen.require_remote()
    assert_startup_safe(previous.frozen.ROOT)
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

    # Only the original run function's startup check receives this view. The
    # original private module/global guard remains untouched and rejects this
    # very same live controller before any private body read.
    parent = previous.previous
    private = SimpleNamespace(**{**vars(parent.gate.evidence.private),
                                 "assert_inactive": assert_startup_safe})
    evidence = SimpleNamespace(**{**vars(parent.gate.evidence), "private": private})
    gate = SimpleNamespace(**{**vars(parent.gate), "evidence": evidence})
    startup_parent = SimpleNamespace(**{**vars(parent), "gate": gate})
    namespace = {**original.__globals__, "ReviewedAttemptLedger": ReadOnceAttemptLedger,
                 "checked_control": checked, "previous": startup_parent}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    bound(control)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-freeze", type=Path, required=True)
    parser.add_argument("--ledger-freeze", type=Path, required=True)
    args = parser.parse_args()
    run(args.control_freeze, args.ledger_freeze)
