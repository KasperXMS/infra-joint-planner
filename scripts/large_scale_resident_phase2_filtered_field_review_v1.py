"""Offline, source-bound filtered-record proof with immutable v1 reviewer pins.

Only the last unresolved original field finding is eligible. No store body,
formal action, feedback, replacement, original admission or journal is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
from pathlib import Path
from typing import Any

import large_scale_resident_derived_field_review_v2 as filtered
import large_scale_resident_phase2_derived_field_review_v1 as previous
import large_scale_resident_phase2_renewed_environment_v1 as renewed
import large_scale_resident_phase2_renewed_field_review_v1 as creator

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

core = previous.core
bindings = previous.bindings
DIRECTORY = "phase2-filtered-record-field-adjudications"
REASON = "audited_source_propagated_filtered_record_field_misuse"


def sources() -> dict[str, str]:
    return {**previous.sources(), **renewed.sources(),
            **{Path(p).name: core.legacy.sha256(Path(p))
               for p in (__file__, filtered.__file__, creator.__file__)}}


def proof(root: Path, attempt: Attempt, parent_path: Path,
          historical_path: Path) -> dict[str, Any]:
    # Every v1 admission, residency, tc, actual SDK and Worker003/atomic004
    # source gate remains active. Only the privately bound pure inference
    # module admits the additional proven filter_records transformation.
    value: dict[str, Any] = renewed.copied(previous.proof, {
        "derived": filtered, "REASON": REASON, "sources": sources})(
            root, attempt, parent_path, historical_path)
    value["version"] = "phase2-source-propagated-filtered-field-review-v1"
    if not value["derived_field_proof"] or not any(
            item.get("source_preserving_filter_ancestors")
            for item in value["derived_field_proof"]):
        raise RuntimeError("filtered reviewer requires actual source-bound filter provenance")
    return value


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact filtered field sidecar required")
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if value != proof(root, attempt, Path(value["parent_control_path"]),
                      Path(value["historical_sidecar_path"])):
        raise RuntimeError("filtered field source/evidence proof drift")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous.effective_admission(root, attempt)
    path = root / DIRECTORY / (attempt.run_id + ".json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (value["reviewed_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256):
        raise RuntimeError("effective filtered field admission/ledger mismatch")
    admission: dict[str, Any] = value["reviewed_admission"]
    return admission


def create_review(manifest: Path, manifest_sha256: str, run_id: str,
                  historical_path: Path) -> dict[str, Any]:
    # Import here to avoid a circular module initialization. The environment
    # explicitly includes all four groups, unlike the immutable v1 renewal.
    environment = import_module("large_scale_resident_phase2_filtered_environment_v1")
    core.frozen.require_remote()
    root = core.frozen.ROOT
    inactive = core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = renewed.read(manifest)
    if value.get("extension_version") == environment.VERSION:
        environment.fence(manifest, manifest_sha256, value)
    else:
        if manifest.name != environment.PARENT_NAME or manifest_sha256 != environment.PARENT_SHA:
            raise RuntimeError("initial filtered review requires pinned renewed003 authority")
        if environment.current_inventory()["filtered_field_sidecars"]:
            raise RuntimeError("renewed003 cannot ignore existing filtered proof inventory")
        renewed.fence(manifest, manifest_sha256, value)
    renewed.environment.require_strata_stopped()
    directory = root / DIRECTORY
    path = directory / (run_id + ".json")
    if (Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase2-")
            or directory.is_symlink() or path.exists() or path.is_symlink()):
        raise RuntimeError("owned exclusive original filtered-field sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    expected = environment.inventory(value)
    with QueueLease(root / "queue-lease.json"):
        parent_path = Path(renewed.read(Path(value["control_path"]))["parent_control_path"])
        schedule = core.previous.cells_from_gate(renewed.read(Path(value["parent"]["gate_path"])))
        ledger, target = creator.pending_ledger(value, schedule, journal, run_id)
        saved, cells = core.previous.checked_control(parent_path)
        if saved != value["parent"] or cells != schedule:
            raise RuntimeError("full original parent/schedule changed")
        verified = proof(root, target, parent_path, historical_path)
        ledger.check_disk()
        if value.get("extension_version") == environment.VERSION:
            environment.fence(manifest, manifest_sha256, value)
        else:
            renewed.fence(manifest, manifest_sha256, value)
        renewed.environment.require_strata_stopped()
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before or environment.current_inventory() != expected:
            raise RuntimeError("review cannot change the original journal or inventory")
        directory.mkdir(exist_ok=True)
        core.frozen.write_new(path, verified)
        verify_sidecar(path, target)
        ledger.check_disk()
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change the original journal")
        delta = environment.extension_delta(expected, environment.current_inventory())
        exact_delta: dict[str, dict[str, str]] = {key: {} for key in environment.GROUPS}
        exact_delta["filtered_field_sidecars"] = {path.name: renewed.cadence.digest(path)}
        if delta != exact_delta:
            raise RuntimeError("creator may add only the exact target filtered-field sidecar")
    inactive(root)
    return {"sidecar_path": str(path), "sha256": renewed.cadence.digest(path),
            "creator_source_sha256": renewed.cadence.digest(Path(__file__)),
            "parent_manifest_sha256": manifest_sha256,
            "original_journal_sha256": hashlib.sha256(before).hexdigest(),
            "confirmed_field_failures": len(verified["derived_field_proof"]),
            "actual_manager_requests": len(verified["actual_manager_schema_wire_proof"]),
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
