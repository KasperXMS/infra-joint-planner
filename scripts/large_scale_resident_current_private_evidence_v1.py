"""Post-block private audit over the exact current nominal admission view.

Preserve historical entrypoints; only the metadata collector changes. Every
body guard and owner-local evidence scan remains the existing implementation.
No execution, Agent feedback, outcome repair, pruning or PhaseII is authorized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import large_scale_resident_private_evidence_v1 as private
import large_scale_resident_rate_policy_snapshot_v1 as sources
from large_scale_resident_repaired_private_evidence_v1 import resolved_membership

VERSION = "resident-current-mixed-provider-private-evidence-paths-v3"
SOURCE_FIELD = "execution_source_epoch"
CURRENT_EPOCH = "4"


def source_bound_membership(
    snapshot: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected = resolved_membership(snapshot)
    if snapshot.get("execution_freezes") != {str(k): v for k, v in sources.EXECUTIONS.items()}:
        raise RuntimeError("private audit requires all four exact immutable source freezes")
    for row in snapshot["rows"]:
        for attempt in row["attempts"]:
            epoch = attempt.get(SOURCE_FIELD)
            if (type(epoch) is not int or epoch not in sources.EXECUTIONS
                    or attempt.get("execution_sha256") != sources.EXECUTIONS[epoch]):
                raise RuntimeError("private audit attempt/source epoch mismatch")
    return selected


def audit_phase_one(root: Path = private.ROOT, predecessor: Path = private.PREDECESSOR,
                   corpus: Path = private.CORPUS) -> dict[str, Any]:
    private.assert_inactive(root)
    snapshot = sources.collect(root, predecessor)
    selected = source_bound_membership(snapshot)
    directories: list[Path] = []
    for row, attempt in selected:
        directory = root / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(attempt["attempt_index"]))
        if json.loads((directory / "worker-shutdown.json").read_text()).get(
                "verified_exited") is not True:
            raise RuntimeError("private evidence scan requires every effective Worker exited")
        directories.append(directory)
    records: list[dict[str, Any]] = []
    for (row, attempt), directory in zip(selected, directories, strict=True):
        private.assert_inactive(root)
        annotated = row["condition"]["task"]["family"] == "multihop_rag"
        private_source = predecessor / "preparation/task-freeze-002" / (
            "multihop_rag-" + str(row["condition"]["task"]["position"])) / (
            "private-evaluation.json")
        records.append({
            "cell_id": row["condition"]["cell_id"], "run_id": attempt["run_id"],
            "execution_sha256": attempt["execution_sha256"],
            SOURCE_FIELD: attempt[SOURCE_FIELD], "benchmark_score": attempt["benchmark_score"],
            "coverage": private.audit_multihop(directory, corpus, private_source)
            if annotated else None,
            "unannotated_retention": None, "semantic_primary_cause": None,
            "primary_cause_requires_manual_private_audit": True,
        })
    private.assert_inactive(root)
    if private.sha256(root / "phase1-attempts.jsonl") != snapshot["journal_sha256"]:
        raise RuntimeError("private audit attempt membership changed")
    dependency_paths = (__file__, private.__file__,
                        sys.modules[resolved_membership.__module__].__file__,
                        sys.modules[private.scan_store.__module__].__file__)
    if any(p is None for p in dependency_paths):
        raise RuntimeError("private audit requires actual file-backed source dependencies")
    source_paths = tuple(p for p in dependency_paths if p is not None)
    return {
        "version": VERSION, "records": records,
        "journal_sha256": snapshot["journal_sha256"],
        "execution_freezes": snapshot["execution_freezes"],
        "collector_source_sha256": snapshot["collector_source_sha256"],
        "audit_source_sha256": {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in source_paths},
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
