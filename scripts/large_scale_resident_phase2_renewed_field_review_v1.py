"""Create an exact initial-field proof after renewed historical adjudications.

Offline creator only: preserve all frozen reviewers, journal, execution sources,
environment exclusion, and the strict new-finding/lease/inactivity guards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import large_scale_resident_phase2_renewed_environment_v1 as environment

from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

review = environment.field.review


def pending_ledger(value: dict[str, Any], cells: tuple[Any, ...], journal: Path,
                   run_id: str) -> tuple[environment.EnvironmentLedger, Attempt]:
    """Replay the exact pinned historical view; allow only the target finding."""
    reviews = tuple((Attempt(**p["raw"]), Attempt(**p["effective"]))
                    for p in value["historical_reviews"])
    exclusion = value["exclusion"]
    ledger = environment.EnvironmentLedger(
        journal, tuple(c.cell_id for c in cells), value["parent"]["phase2_schedule_sha256"],
        reviews, (Attempt(**exclusion["raw"]), Attempt(**exclusion["effective"])))
    targets = [a for a in ledger.original_attempts if a.run_id == run_id]
    if len(targets) != 1:
        raise RuntimeError("one original target reservation/settlement required")
    target = targets[0]
    unresolved = [a for a in ledger.attempts if a.disposition != "valid"
                  and a != ledger.exclusion[1]]
    if (ledger.pending or target != ledger.original_attempts[-1] or unresolved != [target]
            or target.disposition != "confounder"
            or target.reason != review.field.GATE):
        raise RuntimeError("only the exact target initial-field finding may remain unresolved")
    ledger.check_disk()
    return ledger, target


def create_review(manifest: Path, manifest_sha256: str, run_id: str,
                  historical_path: Path) -> dict[str, Any]:
    environment.frozen.require_remote()
    root = environment.frozen.ROOT
    inactive = review.core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = environment.read(manifest)
    environment.fence(manifest, manifest_sha256, value)
    environment.environment.require_strata_stopped()
    directory = root / review.DIRECTORY
    path = directory / (run_id + ".json")
    if (Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase2-")
            or directory.is_symlink() or path.exists() or path.is_symlink()):
        raise RuntimeError("owned exclusive original initial-field sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    with QueueLease(root / "queue-lease.json"):
        # Parse the hash-pinned schedule first, so incompatible histories fail
        # before an expensive full gate. The full original gate still runs.
        parent_path = Path(environment.read(Path(value["control_path"]))["parent_control_path"])
        schedule = review.core.previous.cells_from_gate(
            environment.read(Path(value["parent"]["gate_path"])))
        ledger, target = pending_ledger(value, schedule, journal, run_id)
        saved, cells = review.core.previous.checked_control(parent_path)
        if saved != value["parent"] or cells != schedule:
            raise RuntimeError("full original parent/schedule changed")
        proof = review.proof(root, target, parent_path, historical_path)
        ledger.check_disk()
        environment.fence(manifest, manifest_sha256, value)
        environment.environment.require_strata_stopped()
        # The unchanged scanner may exempt only this auditor's own lease;
        # all controller and atomic receipts remain subject to its live guard.
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change the original journal")
        directory.mkdir(exist_ok=True)
        environment.frozen.write_new(path, proof)
        review.verify_sidecar(path, target)
        ledger.check_disk()
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change the original journal")
        expected = environment.inventory(value)
        delta = environment.extension_delta(expected, environment.current_inventory())
        if delta != {"model_json_sidecars": {}, "initial_field_sidecars": {
                path.name: environment.cadence.digest(path)}, "derived_field_sidecars": {}}:
            raise RuntimeError("creator may add only the exact target initial-field sidecar")
    return {"sidecar_path": str(path), "sha256": environment.cadence.digest(path),
            "creator_source_sha256": environment.cadence.digest(Path(__file__)),
            "parent_manifest_sha256": manifest_sha256,
            "original_journal_sha256": hashlib.sha256(before).hexdigest(),
            "confirmed_field_failures": len(proof["field_misuse_proof"]),
            "actual_manager_requests": len(proof["actual_manager_schema_wire_proof"]),
            "retry": False, "new_store_or_corpus_body_decoded": False,
            "atomic_execution_changed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.manifest, args.manifest_sha256,
                                   args.run_id, args.historical_sidecar)))
