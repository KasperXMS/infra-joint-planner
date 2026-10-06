"""Post-block body audit across all three exact resident source epochs.

No body reads until every effective PhaseI cell is settled and queue/Workers
are inactive. This external analysis entrypoint never changes Agent execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_cardinality_snapshot_v1 as sources
import large_scale_resident_private_evidence_v1 as private
from large_scale_resident_repaired_private_evidence_v1 import resolved_membership

BOUNDARIES = {
    "original-execution-001": "1",
    "quote-integrity-repair-002": "2",
    "input-cardinality-repair-003": "3",
}


def source_bound_membership(
    snapshot: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected = resolved_membership(snapshot)
    freezes = snapshot.get("execution_freezes", {})
    if (set(freezes) != set(BOUNDARIES.values())
            or freezes["1"] != sources.resident.EXECUTION_FREEZE_SHA256
            or freezes["2"] != sources.REPAIR_SHA256
            or not isinstance(freezes["3"], str)
            or len(freezes["3"]) != 64
            or any(c not in "0123456789abcdef" for c in freezes["3"])
            or len(set(freezes.values())) != 3):
        raise RuntimeError("private audit requires three distinct verified source freezes")
    for row in snapshot["rows"]:
        for attempt in row["attempts"]:
            boundary = attempt.get("execution_source_boundary")
            if boundary not in BOUNDARIES or attempt.get("execution_sha256") != freezes[
                    BOUNDARIES[boundary]]:
                raise RuntimeError("private audit attempt/source boundary mismatch")
    return selected


def audit_phase_one(root: Path = private.ROOT, predecessor: Path = private.PREDECESSOR,
                   corpus: Path = private.CORPUS) -> dict[str, Any]:
    private.assert_inactive(root)
    snapshot = sources.collect(root, predecessor)
    selected = source_bound_membership(snapshot)
    # Check all exits before ANY corpus/store body read, not just each row in turn.
    directories = []
    for row, attempt in selected:
        directory = root / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(attempt["attempt_index"]))
        if not json.loads((directory / "worker-shutdown.json").read_text())["verified_exited"]:
            raise RuntimeError("private evidence scan requires every effective Worker exited")
        directories.append(directory)
    records = []
    for (row, attempt), directory in zip(selected, directories, strict=True):
        private.assert_inactive(root)
        annotated = row["condition"]["task"]["family"] == "multihop_rag"
        private_source = predecessor / "preparation/task-freeze-002" / (
            "multihop_rag-" + str(row["condition"]["task"]["position"])) / (
            "private-evaluation.json")
        records.append({
            "cell_id": row["condition"]["cell_id"], "run_id": attempt["run_id"],
            "execution_sha256": attempt["execution_sha256"],
            "execution_source_boundary": attempt["execution_source_boundary"],
            "benchmark_score": attempt["benchmark_score"],
            "coverage": private.audit_multihop(directory, corpus, private_source)
            if annotated else None,
            "unannotated_retention": None, "semantic_primary_cause": None,
            "primary_cause_requires_manual_private_audit": True,
        })
    private.assert_inactive(root)
    if private.sha256(root / "phase1-attempts.jsonl") != snapshot["journal_sha256"]:
        raise RuntimeError("private audit attempt membership changed")
    return {
        "version": "resident-cardinality-private-evidence-paths-v1", "records": records,
        "journal_sha256": snapshot["journal_sha256"],
        "execution_freezes": snapshot["execution_freezes"],
        "collector_source_sha256": snapshot["collector_source_sha256"],
        "audit_source_sha256": {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in (__file__, private.__file__,
                                          sys.modules[resolved_membership.__module__].__file__,
                                          sys.modules[private.scan_store.__module__].__file__)},
        "excluded_historical_run_ids": [a["run_id"] for row in snapshot["rows"]
                                        for a in row["attempts"] if a["disposition"] != "valid"],
        "phase2_authorized": False, "semantic_audit_complete": False,
        "method_pruning_authorized": False, "planner_or_model_calls": 0,
        "artifact_bodies_exported": False, "measured_execution_modified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (sys.platform != "linux" or args.output.is_symlink()
            or args.output.resolve().parent != private.ROOT / "analysis"):
        raise RuntimeError("private evidence remains inside its4090 analysis namespace")
    if args.output.exists():
        raise FileExistsError("private evidence audit is append-only")
    value = audit_phase_one()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"audited_cells": len(value["records"]), "model_calls": 0,
                      "semantic_audit_complete": False, "phase2_authorized": False}))
