"""Offline, gold-blind integrity check for the proposed source-local index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from answerability_provenance_v1 import build_provenanced_index, validate_selected_records
from audit_answerability_evidence_v1 import ArchiveStore, worker_bm25
from run_hypothesis_cell_v1 import PUBLISHERS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stores = {
        node: ArchiveStore(
            args.parent_root / f"infra-evaluation-{node}.tgz",
            args.parent_root / f"infra-evaluation-{node}-delta.tgz",
        )
        for node in ("source-a", "source-b")
    }
    public = args.study_root / "controller" / "study"
    residency = [
        json.loads(line) for line in (public / "source-residency.jsonl").read_text().splitlines()
    ]
    tasks = {
        row["task_id"]: row
        for row in map(json.loads, (public / "task-candidates.jsonl").read_text().splitlines())
    }
    summary = []
    for task_id in PUBLISHERS:
        task = tasks[task_id]
        for producer in ("source-a", "source-b"):

            def read_original(artifact_id: str, *, node: str = producer) -> bytes:
                store = stores[node]
                basename = hashlib.sha256(artifact_id.encode()).hexdigest()
                return store.files[f"artifacts/{basename}.blob"]

            content, sources = build_provenanced_index(
                residency,
                read_original,
                producer=producer,
                publisher_groups=frozenset(PUBLISHERS[task_id]),
            )
            selected = worker_bm25(json.loads(content), task["question"], 4, "body")
            validated = validate_selected_records(
                selected,
                residency,
                read_original,
                producer=producer,
                publisher_groups=frozenset(PUBLISHERS[task_id]),
            )
            summary.append(
                {
                    "task_id": task_id,
                    "producer": producer,
                    "index_records": len(sources),
                    "index_bytes": len(content),
                    "selected_records": validated,
                    "selected_original_ids_present": all(
                        record.get("_origin_artifact_id") for record in selected
                    ),
                    "source_scope": "question-named publishers; gold blind",
                }
            )
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"checks": len(summary), "all_valid": True}))


if __name__ == "__main__":
    main()
