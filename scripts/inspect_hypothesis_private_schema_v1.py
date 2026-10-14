"""Print only field names/types of private evaluator rows on the experiment machine."""

import json
from pathlib import Path

path = Path("/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl")
selected = {
    "multihop:a647807d9a1d0efd",
    "multihop:667f4ac48afef820",
    "mmqa:0ed625390ca7f919b46fd99fe85d80b5",
}
for line in path.read_text().splitlines():
    row = json.loads(line)
    if row["task_id"] in selected:
        shape = {
            "task_id": row["task_id"],
            "fields": {key: type(value).__name__ for key, value in row.items()},
        }
        if row.get("supporting_context"):
            first = row["supporting_context"][0]
            shape["supporting_context_item_keys"] = (
                list(first) if isinstance(first, dict) else type(first).__name__
            )
        gold_refs = set(row.get("gold_evidence_artifact_refs", []))
        for raw_path in Path(
            "/home/super/xiaoming/infra-hypothesis-feasibility-v1/controller/out"
        ).glob("h*.json"):
            raw = json.loads(raw_path.read_text())
            if raw["task_id"] == row["task_id"]:
                shape.setdefault("runs", []).append(
                    {
                        "run_id": raw["run_id"],
                        "evidence_count": len(raw["evidence_ids"]),
                        "gold_ref_count": len(gold_refs),
                        "gold_ref_overlap": len(gold_refs.intersection(raw["evidence_ids"])),
                    }
                )
        print(json.dumps(shape))
