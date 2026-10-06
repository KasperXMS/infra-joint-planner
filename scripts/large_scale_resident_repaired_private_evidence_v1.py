"""Post-block private audit of the source-bound, resolved resident population.

Historical confounded attempts stay visible but never enter semantic coverage.
This offline entrypoint does not change measured execution or earlier auditors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_private_evidence_v1 as private
import large_scale_resident_repaired_snapshot_v1 as repaired


def resolved_membership(snapshot: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Check exact effective membership, not the count of retained old failures."""
    if (snapshot.get("scheduled_cells") != 168 or snapshot.get("admitted_cells") != 168
            or snapshot.get("phase1_complete") is not True or snapshot.get("pending_count") != 0
            or len(snapshot.get("rows", [])) != 168):
        raise RuntimeError("private audit requires the completed resolved168-cell block")
    selected = []
    cells: set[str] = set()
    runs: set[str] = set()
    for row in snapshot["rows"]:
        cell_id = row["condition"]["cell_id"]
        valid = [a for a in row["attempts"] if a["disposition"] == "valid"]
        if (cell_id in cells or row.get("pending_run_ids") or len(valid) != 1
                or any(a["disposition"] not in {"valid", "confounder", "operational_excluded"}
                       for a in row["attempts"])):
            raise RuntimeError("private audit requires unique resolved cell membership")
        attempt = valid[0]
        if (attempt["run_id"] in runs or attempt.get("comparative_sample_eligible") is not True
                or attempt.get("admission_problems")):
            raise RuntimeError("private audit cannot select an ineligible effective admission")
        cells.add(cell_id)
        runs.add(attempt["run_id"])
        selected.append((row, attempt))
    return selected


def audit_phase_one(root: Path = private.ROOT, predecessor: Path = private.PREDECESSOR,
                   corpus: Path = private.CORPUS) -> dict[str, Any]:
    private.assert_inactive(root)
    snapshot = repaired.collect(root, predecessor)
    selected = resolved_membership(snapshot)
    records = []
    for row, attempt in selected:
        directory = root / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(attempt["attempt_index"]))
        if not json.loads((directory / "worker-shutdown.json").read_text())["verified_exited"]:
            raise RuntimeError("private evidence scan requires verified Worker exits")
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
        "version": "resident-repaired-private-evidence-paths-v1", "records": records,
        "journal_sha256": snapshot["journal_sha256"],
        "execution_freezes": snapshot["execution_freezes"],
        "collector_source_sha256": snapshot["collector_source_sha256"],
        "audit_source_sha256": {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in (__file__, private.__file__,
                                          sys.modules[private.scan_store.__module__].__file__)},
        "excluded_historical_run_ids": [a["run_id"] for row in snapshot["rows"]
                                        for a in row["attempts"] if a["disposition"] != "valid"],
        "phase2_authorized": False, "semantic_audit_complete": False,
        "method_pruning_authorized": False, "planner_or_model_calls": 0,
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
