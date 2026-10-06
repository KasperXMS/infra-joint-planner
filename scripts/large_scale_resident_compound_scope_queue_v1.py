"""Append-only compound admission scope; unchanged SDK and atomic execution.

An additional independently proved nominal policy failure is not an outage and
must not be repeated. Preserve the complete historical parent receipt and bind
the current exact sidecar set without mutating its controller or source files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import large_scale_resident_field_policy_review_v1 as compound
import large_scale_resident_sdk_argument_queue_v1 as previous

frozen, e = previous.frozen, previous.e
PARENT_FILE = "queue-control-freeze-021.json"
PARENT_SHA256 = "c983bc145764b49a8a4850d4728e7e50bbfb2025ae57a4a0bbb1845acdab00ad"
owned_ledger = previous.owned_ledger


def control_freeze() -> dict[str, Any]:
    path = frozen.ROOT / PARENT_FILE
    if path.is_symlink() or frozen.sha256(path) != PARENT_SHA256:
        raise RuntimeError("pinned native continuation parent drift")
    parent = json.loads(path.read_text())
    if parent != previous.control_freeze():
        raise RuntimeError("historical native continuation scope drift")
    ledger = owned_ledger()
    raw_attempts = {a.run_id: a for a in ledger.original_attempts}
    attempts = {a.run_id: a for a in ledger.attempts}
    proofs: dict[str, str] = {}
    for proof in sorted((frozen.ROOT / compound.POLICY_DIRECTORY).glob("*.json")):
        attempt = attempts.get(proof.stem)
        original = raw_attempts.get(proof.stem)
        if (proof.is_symlink() or attempt is None or original is None
                or attempt.disposition != "valid" or attempt.reason != compound.REASON):
            raise RuntimeError("compound scope requires exact proved nominal membership")
        compound.verify_sidecar(proof, original)
        proofs[proof.name] = frozen.sha256(proof)
    old = parent["compound_record_policy_adjudications"]
    if any(proofs.get(name) != digest for name, digest in old.items()):
        raise RuntimeError("historical compound proof cannot change or disappear")
    if not set(proofs) - set(old):
        raise RuntimeError("continuation requires an additional exact compound proof")
    return {**parent, "version": "resident-exact-compound-scope-continuation-v1",
            "parent_control_file_sha256": PARENT_SHA256,
            "parent_controller_source_sha256": frozen.sha256(Path(previous.__file__)),
            "controller_source_sha256": frozen.sha256(Path(__file__)),
            "compound_reviewer_source_sha256": frozen.sha256(Path(compound.__file__)),
            "compound_record_policy_adjudications": proofs,
            "parent_proof_scope_preserved": True, "measured_execution_changed": False,
            "semantic_retries": False, "provider_policy_retry": False,
            "input_censored": False}


def run(path: Path) -> None:
    # Reuse the exact launch implementation and its pinned archive environment.
    # This copied namespace changes only external control/admission dependencies.
    original = previous.previous.run
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
