"""Inactive-only private audit of exact reviewed held-out membership.

Keep the historical owner-local scanner and strict inactivity guard unchanged.
Use an explicitly source-bound reviewed projection, never rewrite the raw journal
or inject private audit information into an execution process.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import large_scale_resident_phase2_private_evidence_v1 as previous
import large_scale_resident_phase2_read_once_v1 as ledger
import large_scale_resident_phase2_reviewed_snapshot_v1 as reviewed

ROOT = previous.ROOT


def projection(root: Path, control: Path, receipt: Path) -> dict[str, Any]:
    ledger.validate(control, receipt)
    original = reviewed.collect
    queue = SimpleNamespace(**{**vars(reviewed.queue),
                               "ReviewedAttemptLedger": ledger.ReadOnceAttemptLedger})
    namespace = {**original.__globals__, "queue": queue}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(root, control_path=control)
    ledger.validate(control, receipt)
    return value


def audit_phase_two(control: Path, receipt: Path, *, root: Path = ROOT,
                    predecessor: Path = previous.private.PREDECESSOR,
                    corpus: Path = previous.private.CORPUS) -> dict[str, Any]:
    # This is the original global guard, not the controller startup self view.
    # It runs before even control/metadata reads, and the historical audit checks
    # it again before and after every private scan.
    previous.private.assert_inactive(root)
    ledger.validate(control, receipt)

    def collect(current_root: Path) -> dict[str, Any]:
        return projection(current_root, control, receipt)

    sources = SimpleNamespace(**{**vars(previous.sources), "collect": collect})
    original = previous.audit_phase_two
    namespace = {**original.__globals__, "sources": sources}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(root, predecessor, corpus)
    previous.private.assert_inactive(root)
    ledger.validate(control, receipt)
    value.update(
        version="resident-phase2-reviewed-private-evidence-paths-v1",
        reviewed_control_sha256=previous.private.sha256(control),
        ledger_adapter_freeze_sha256=previous.private.sha256(receipt),
        reviewed_source_sha256={Path(p).name: previous.private.sha256(Path(p))
                                for p in (__file__, reviewed.__file__, ledger.__file__)},
        raw_journal_rewritten=False, original_private_guard_changed=False,
        historical_modules_mutated=False,
    )
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-freeze", type=Path, required=True)
    parser.add_argument("--ledger-freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("reviewed private audit remains in owned remote analysis")
    if args.output.exists():
        raise FileExistsError("reviewed private audit is append-only")
    value = audit_phase_two(args.control_freeze, args.ledger_freeze)
    reviewed.queue.frozen.write_new(args.output, value)
    print(json.dumps({"audited_cells": len(value["records"]), "model_calls": 0,
                      "semantic_audit_complete": False}))
