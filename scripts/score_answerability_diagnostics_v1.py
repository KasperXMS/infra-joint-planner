"""Score completed task diagnostics offline; this process never calls the model."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from run_hypothesis_feasibility_v1 import rows, score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--diagnostics-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.diagnostics_root
    target = root / "diagnostic-scores-public.json"
    if target.exists():
        raise FileExistsError(target)
    tasks = rows(args.study_root / "controller" / "study" / "task-candidates.jsonl")
    private = rows(
        Path("/home/super/xiaoming/infra-evaluation-workload-v0.1/private/evaluator-private.jsonl")
    )
    outcomes = [
        json.loads(line)
        for line in (root / "diagnostic-outcomes-public.jsonl").read_text().splitlines()
    ]
    scored = []
    for outcome in outcomes:
        raw = json.loads((root / "private" / (outcome["run_id"] + ".json")).read_text())
        answer = raw["response"].get("message", {}).get("content", "").strip()
        evaluation = (
            asyncio.run(score(tasks[outcome["task_id"]], private[outcome["task_id"]], answer))
            if answer
            else None
        )
        scored.append(
            {
                "run_id": outcome["run_id"],
                "task_id": outcome["task_id"],
                "condition": outcome["condition"],
                "evaluation": evaluation,
                "answer_characters": len(answer),
                "returned_unknown": outcome["returned_unknown"],
                "done_reason": outcome["done_reason"],
                "error": outcome["error"],
            }
        )
    target.write_text(json.dumps(scored, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "scored": len(scored),
                "successful": sum(
                    bool(row["evaluation"] and row["evaluation"]["task_success"]) for row in scored
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
