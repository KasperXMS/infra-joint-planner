"""All-attempt inactive-only final audit for the exact environmental exclusion.

This is a post-block entrypoint, not online feedback. Keep the original private
scanner and global inactivity guard, including invalid cell71 in the inventory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import large_scale_resident_phase2_environment_v1 as environment
import large_scale_resident_phase2_private_evidence_v1 as previous


def audit_phase_two(manifest: Path, manifest_sha256: str) -> dict[str, Any]:
    root = environment.frozen.ROOT
    previous.private.assert_inactive(root)  # Before any control/evidence/body access.
    value = environment.read(manifest)
    environment.fence(manifest, manifest_sha256, value)
    control = Path(value["control_path"])
    parent, cells = environment.full_control(control, Path(value["sidecar_path"]))
    if parent != value["parent"]:
        raise RuntimeError("final audit parent drift")
    ledger = environment.membership(environment.read(control), cells,
                                    Path(value["sidecar_path"]), require_dispatch_ready=True)
    projection = environment.collect(value, ledger)
    if not projection["phase2_complete"] or projection["operational_excluded_attempts"] != 1:
        raise RuntimeError("all192resolved plus exact excluded original required before body scan")
    selected = []
    for row in projection["rows"]:
        admitted = [a for a in row["attempts"] if a["disposition"] == "valid"]
        if len(admitted) != 1:
            raise RuntimeError("every nominal cell requires one admitted attempt")
        for attempt in row["attempts"]:
            if attempt["disposition"] != "valid" and attempt["run_id"] != environment.RUN:
                raise RuntimeError("unreviewed additional attempt cannot be dropped")
            directory = root / "evidence" / row["condition"]["cell_id"] / (
                "attempt" + str(attempt["attempt_index"]))
            if (attempt["execution_sha256"] != parent["execution_freeze_sha256"]
                    or environment.read(directory / "worker-shutdown.json")[
                        "verified_exited"] is not True):
                raise RuntimeError("actual source/exited Workers required for every attempt")
            selected.append((row, attempt, directory))
    if len(selected) != len(cells) + 1:
        raise RuntimeError("final private audit must retain all193preserved attempts")
    environment.audit_wire(projection, Path(value["sidecar_path"]))
    records = []
    for row, attempt, directory in selected:
        previous.private.assert_inactive(root)
        task = row["condition"]["task"]
        private_source = previous.private.PREDECESSOR / "preparation/task-freeze-002" / (
            "multihop_rag-" + str(task["position"])) / "private-evaluation.json"
        records.append({
            "cell_id": row["condition"]["cell_id"], "run_id": attempt["run_id"],
            "disposition": attempt["disposition"],
            "environment_stage": attempt["environment_stage"],
            "benchmark_score": attempt["benchmark_score"],
            "coverage": previous.audit_multihop(directory, previous.private.CORPUS, private_source)
            if task["family"] == "multihop_rag" else None,
            "semantic_primary_cause": None, "primary_cause_requires_manual_private_audit": True,
            "admitted_baseline_sample": attempt["disposition"] == "valid",
        })
    previous.private.assert_inactive(root)
    environment.fence(manifest, manifest_sha256, value)
    if environment.cadence.digest(ledger.path) != projection["journal_sha256"]:
        raise RuntimeError("final private journal changed")
    return {"version": "resident-phase2-environment-all-attempt-private-paths-v1",
            "records": records, "journal_sha256": projection["journal_sha256"],
            "manifest_sha256": manifest_sha256, "source_sha256": environment.sources(),
            "semantic_audit_complete": False, "planner_or_model_calls": 0,
            "artifact_bodies_exported": False, "original_private_guard_changed": False,
            "excluded_attempt_omitted": False}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().parent != environment.frozen.ROOT / "analysis":
        parser.error("private output stays in remote owned analysis")
    if args.output.exists():
        raise FileExistsError("final private creator must not repeat")
    result = audit_phase_two(args.manifest, args.manifest_sha256)
    environment.frozen.write_new(args.output, result)
    print(json.dumps({"audited_attempts": len(result["records"]), "model_calls": 0,
                      "semantic_audit_complete": False}))
