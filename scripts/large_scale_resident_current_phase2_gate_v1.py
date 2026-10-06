"""Current admission-view gate, retaining unchanged comprehensive audit guards.

This entrypoint only checks/freeze genuine completed audits. It cannot select
methods, bypass full168, launch PhaseII, change execution or query an Agent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import large_scale_resident_current_private_evidence_v1 as evidence
import large_scale_resident_phase2_gate_v1 as core


def verify_gate_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    return core.verify_gate_inputs(paths, evidence_module=evidence)


def digest(path: Path) -> str:
    return core.digest(path)


def freeze_gate(paths: dict[str, Path], output: Path) -> dict[str, Any]:
    return core.freeze_gate(paths, output, evidence_module=evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "private", "audit", "pruning", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    receipt = freeze_gate({n: getattr(args, n) for n in (
        "snapshot", "private", "audit", "pruning")}, args.output)
    print(json.dumps({k: v for k, v in receipt.items() if k != "schedule"}))
