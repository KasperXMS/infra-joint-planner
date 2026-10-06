"""Append-only mixed rate/policy scope, preserving actual frozen execution004."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import large_scale_resident_compound_scope_queue_v1 as previous
import large_scale_resident_rate_policy_review_v1 as reviewer

frozen, e = previous.frozen, previous.e
PARENT_FILE = "queue-control-freeze-022.json"
PARENT_SHA256 = "3080fae100032913e7d825d0da9619727dc2c99c037c3ec08b40fc51c16b9c18"


def owned_ledger() -> reviewer.ProjectionAttemptLedger:
    cells = frozen.schedule()
    return reviewer.ProjectionAttemptLedger(frozen.ROOT / "phase1-attempts.jsonl",
        tuple(c.cell_id for c in cells), frozen.schedule_sha256(cells))


def control_freeze() -> dict[str, Any]:
    path = frozen.ROOT / PARENT_FILE
    if path.is_symlink() or frozen.sha256(path) != PARENT_SHA256:
        raise RuntimeError("pinned compound continuation parent drift")
    parent = json.loads(path.read_text())
    if parent != previous.control_freeze():
        raise RuntimeError("historical compound continuation scope drift")
    ledger = owned_ledger()
    raw = {a.run_id: a for a in ledger.original_attempts}
    effective = {a.run_id: a for a in ledger.attempts}
    proofs = {}
    for proof in sorted((frozen.ROOT / reviewer.RATE_DIRECTORY).glob("*.json")):
        attempt, original = effective.get(proof.stem), raw.get(proof.stem)
        if (proof.is_symlink() or original is None or attempt is None
                or attempt.disposition != "operational_excluded"
                or attempt.reason != reviewer.REASON):
            raise RuntimeError("exact mixed external provider membership required")
        reviewer.verify_sidecar(proof, original)
        proofs[proof.name] = frozen.sha256(proof)
    if not proofs:
        raise RuntimeError("operational continuation requires actual token-rate evidence")
    return {**parent, "version": "resident-exact-mixed-rate-policy-continuation-v1",
        "parent_control_file_sha256": PARENT_SHA256,
        "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
        "controller_source_sha256": frozen.sha256(Path(__file__)),
        "mixed_provider_reviewer_source_sha256": frozen.sha256(Path(reviewer.__file__)),
        "mixed_token_rate_policy_adjudications": proofs, "parent_proof_scope_preserved": True,
        "measured_execution_changed": False, "semantic_retries": False,
        "policy_only_replacement_authorized": False,
        "operational_replacement_requires_identical_execution": True,
        "max_operational_replacements_per_cell": 1, "API_concurrency_changed": False,
        "quota_or_billing_configuration_changed": False}


def run(path: Path) -> None:
    original = previous.previous.previous.run
    namespace = {**original.__globals__, "owned_ledger": owned_ledger,
                 "control_freeze": control_freeze}
    entrypoint = FunctionType(original.__code__, namespace, original.__name__,
                              original.__defaults__, original.__closure__)
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
