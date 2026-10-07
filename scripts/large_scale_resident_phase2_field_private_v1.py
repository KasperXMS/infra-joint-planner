"""Full-block inactive-only private audit of disjoint exact reviewed membership."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import large_scale_resident_phase2_field_snapshot_v1 as reviewed
import large_scale_resident_phase2_private_evidence_v1 as previous

queue = reviewed.queue


def audit_phase_two(control: Path, receipt: Path, *, root: Path = previous.ROOT,
                    predecessor: Path = previous.private.PREDECESSOR,
                    corpus: Path = previous.private.CORPUS) -> dict[str, Any]:
    # Original global guard, before even control reads. Never the startup self-view.
    previous.private.assert_inactive(root)
    queue.validate(control, receipt)

    def collect(current_root: Path) -> dict[str, Any]:
        queue.validate(control, receipt)
        value = reviewed.collect(current_root, control_path=control)
        queue.validate(control, receipt)
        return value

    sources = SimpleNamespace(**{**vars(previous.sources), "collect": collect})
    original = previous.audit_phase_two
    namespace = {**original.__globals__, "sources": sources}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    value: dict[str, Any] = bound(root, predecessor, corpus)
    previous.private.assert_inactive(root)
    queue.validate(control, receipt)
    value.update(version="resident-phase2-disjoint-reviewed-private-paths-v1",
                 reviewed_control_sha256=previous.private.sha256(control),
                 ledger_adapter_freeze_sha256=previous.private.sha256(receipt),
                 reviewed_source_sha256={**queue.sources(), Path(previous.__file__).name:
                                        previous.private.sha256(Path(previous.__file__))},
                 raw_journal_rewritten=False, original_private_guard_changed=False,
                 historical_modules_mutated=False)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-freeze", type=Path, required=True)
    parser.add_argument("--ledger-freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != previous.ROOT / "analysis"):
        raise RuntimeError("private audit remains in owned remote analysis")
    if args.output.exists():
        raise FileExistsError("private audit is append-only")
    queue.frozen.write_new(args.output, audit_phase_two(args.control_freeze, args.ledger_freeze))
    print(json.dumps({"model_calls": 0, "semantic_audit_complete": False}))
