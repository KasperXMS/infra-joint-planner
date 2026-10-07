"""Separate continuation control for exact model-JSON and initial-field reviews.

The frozen atomic executor/run body and all historical controls remain unchanged.
Only unexecuted cells are dispatched; the original private guard is not relaxed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import large_scale_resident_phase2_field_review_v1 as review
import large_scale_resident_phase2_snapshot_v1 as base

core = review.core
frozen = core.frozen
CONTROL_PREFIX = "phase2-field-reviewed-control-freeze-"
LEDGER_PREFIX = "phase2-field-ledger-freeze-"


def sources() -> dict[str, str]:
    paths = (Path(__file__), Path(base.__file__),
             Path(__file__).with_name("large_scale_resident_phase2_field_snapshot_v1.py"),
             Path(__file__).with_name("large_scale_resident_phase2_field_private_v1.py"))
    return {**review.sources(), **{p.name: core.legacy.sha256(p) for p in paths}}


def owned(path: Path, prefix: str) -> None:
    if (path.is_symlink() or path.resolve().parent != frozen.ROOT
            or not path.name.startswith(prefix)):
        raise RuntimeError("owned immutable continuation path required")


def sidecars(directory: str) -> dict[str, str]:
    root = frozen.ROOT / directory
    if root.is_symlink():
        raise RuntimeError("review directory must not be a symlink")
    paths = sorted(root.glob("*.json"))
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise RuntimeError("review sidecars must be owned files")
    return {p.name: core.legacy.sha256(p) for p in paths}


def control_bindings(parent_path: Path, parent: dict[str, Any],
                     model_control: Path, model_receipt: Path) -> dict[str, Any]:
    """Reproduce old control bytes without asking its JSON-only ledger to waive fields."""
    owned(parent_path, "phase2-control-freeze-")
    review.parent.validate(model_control, model_receipt)
    models, fields = sidecars(core.DIRECTORY), sidecars(review.DIRECTORY)
    if not models or not fields or set(models) & set(fields):
        raise RuntimeError("disjoint actual model-JSON/field review sidecars required")
    expected_old = {
        "version": "resident-phase2-exact-model-json-continuation-v1",
        "parent_control_path": str(parent_path),
        "parent_control_file_sha256": core.legacy.sha256(parent_path),
        "sidecars": models,
        "source_sha256": {Path(p).name: core.legacy.sha256(Path(p))
                          for p in (core.__file__, core.legacy.__file__, core.bindings.__file__)},
        "execution_freeze_sha256": parent["execution_freeze_sha256"],
        "phase2_schedule_sha256": parent["phase2_schedule_sha256"],
        "nominal_cells": parent["nominal_cells"], "no_retry": True,
        "semantic_tuning": False, "prior_results_modified": False,
    }
    if json.loads(model_control.read_text(encoding="utf-8")) != expected_old:
        raise RuntimeError("preserved model-JSON control/source/sidecar drift")
    return {
        "version": "resident-phase2-disjoint-exact-review-continuation-v1",
        "parent_control_path": str(parent_path),
        "parent_control_file_sha256": core.legacy.sha256(parent_path),
        "preserved_model_control_path": str(model_control),
        "preserved_model_control_file_sha256": core.legacy.sha256(model_control),
        "preserved_model_ledger_path": str(model_receipt),
        "preserved_model_ledger_file_sha256": core.legacy.sha256(model_receipt),
        "model_json_sidecars": models, "initial_field_sidecars": fields,
        "source_sha256": sources(),
        "execution_freeze_sha256": parent["execution_freeze_sha256"],
        "phase2_schedule_sha256": parent["phase2_schedule_sha256"],
        "nominal_cells": parent["nominal_cells"], "no_retry": True,
        "semantic_tuning": False, "prior_results_modified": False,
    }


def checked_membership(value: dict[str, Any], cells: tuple[Any, ...], *,
                       require_dispatch_ready: bool) -> review.FieldReviewedAttemptLedger:
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    if not journal.is_file() or journal.is_symlink():
        raise RuntimeError("existing owned PhaseII journal required")
    ledger = review.FieldReviewedAttemptLedger(journal, tuple(c.cell_id for c in cells),
                                             value["phase2_schedule_sha256"])
    effective = ledger.attempts
    raw = ledger.original_attempts
    reviewed = set(value["model_json_sidecars"]) | set(value["initial_field_sidecars"])
    if reviewed != {a.run_id + ".json" for a in raw if a.disposition == "confounder"}:
        raise RuntimeError("every original finding requires its disjoint exact review")
    if require_dispatch_ready and any(a.disposition != "valid" for a in effective):
        raise RuntimeError("pending/unresolved attempt prohibits continuation")
    return ledger


def control_value(parent_path: Path, model_control: Path,
                  model_receipt: Path) -> dict[str, Any]:
    parent, cells = core.previous.checked_control(parent_path)
    value = control_bindings(parent_path, parent, model_control, model_receipt)
    checked_membership(value, cells, require_dispatch_ready=True)
    return value


def checked_control(path: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    owned(path, CONTROL_PREFIX)
    value = json.loads(path.read_text(encoding="utf-8"))
    parent_path = Path(value["parent_control_path"])
    parent, cells = core.previous.checked_control(parent_path)
    expected = control_bindings(parent_path, parent,
                                Path(value["preserved_model_control_path"]),
                                Path(value["preserved_model_ledger_path"]))
    if value != expected:
        raise RuntimeError("combined continuation control/source/evidence drift")
    checked_membership(value, cells, require_dispatch_ready=True)
    return parent, cells


def projection_inputs(root: Path, path: Path) -> tuple[dict[str, Any], dict[str, Any],
                                                     review.FieldReviewedAttemptLedger]:
    if root != frozen.ROOT:
        raise RuntimeError("projection must use the owned resident block")
    owned(path, CONTROL_PREFIX)
    value = json.loads(path.read_text(encoding="utf-8"))
    parent_path = Path(value["parent_control_path"])
    parent, gate = base.checked_inputs(root, parent_path)
    expected = control_bindings(parent_path, parent,
                                Path(value["preserved_model_control_path"]),
                                Path(value["preserved_model_ledger_path"]))
    if value != expected:
        raise RuntimeError("combined projection source/evidence/control drift")
    ledger = checked_membership(value, core.previous.cells_from_gate(gate),
                                require_dispatch_ready=False)
    return parent, gate, ledger


def freeze_value(control: Path) -> dict[str, Any]:
    owned(control, CONTROL_PREFIX)
    value = json.loads(control.read_text(encoding="utf-8"))
    return {"version": "phase2-disjoint-exact-reviews-ledger-v1",
            "reviewed_control_path": str(control),
            "reviewed_control_sha256": core.legacy.sha256(control),
            "source_sha256": sources(),
            "execution_freeze_sha256": value["execution_freeze_sha256"],
            "phase2_schedule_sha256": value["phase2_schedule_sha256"],
            "attempt_view_revalidated_on_each_access": True,
            "validation_cached": False, "atomic_execution_changed": False,
            "semantic_retries": False}


def validate(control: Path, receipt: Path) -> None:
    owned(receipt, LEDGER_PREFIX)
    if json.loads(receipt.read_text(encoding="utf-8")) != freeze_value(control):
        raise RuntimeError("combined ledger/source/control drift")


def assert_startup_safe(root: Path, *, proc_root: Path = Path("/proc"),
                        own_pid: int | None = None) -> None:
    current = os.getpid() if own_pid is None else own_pid
    handles = [root / "queue-lease.json", *root.glob("queue-process-*.json"),
               *root.glob("evidence/*/attempt*/process.json")]
    for handle in handles:
        if not handle.exists():
            continue
        if handle.is_symlink():
            raise RuntimeError("startup handles must be owned files")
        pid = json.loads(handle.read_text())["pid"]
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise RuntimeError("startup process identity invalid")
        command = proc_root / str(pid) / "cmdline"
        if not command.exists() or root.name.encode() not in command.read_bytes():
            continue
        if (pid != current or handle.parent != root
                or not handle.name.startswith("queue-process-")
                or b"large_scale_resident_phase2_field_queue_v1" not in command.read_bytes()):
            raise RuntimeError("another live controller/atomic/lease prohibits startup")


def run(control: Path, receipt: Path) -> None:
    frozen.require_remote()
    assert_startup_safe(frozen.ROOT)
    validate(control, receipt)

    def checked(path: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
        validate(path, receipt)
        return checked_control(path)

    original = core.run
    parent = core.previous
    private = SimpleNamespace(**{**vars(parent.gate.evidence.private),
                                 "assert_inactive": assert_startup_safe})
    evidence = SimpleNamespace(**{**vars(parent.gate.evidence), "private": private})
    gate = SimpleNamespace(**{**vars(parent.gate), "evidence": evidence})
    startup_parent = SimpleNamespace(**{**vars(parent), "gate": gate})
    namespace = {**original.__globals__, "ReviewedAttemptLedger": review.FieldReviewedAttemptLedger,
                 "checked_control": checked, "previous": startup_parent}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    bound(control)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-freeze", required=True, type=Path)
    parser.add_argument("--ledger-freeze", required=True, type=Path)
    args = parser.parse_args()
    run(args.control_freeze, args.ledger_freeze)
