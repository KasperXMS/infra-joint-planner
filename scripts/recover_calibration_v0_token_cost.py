"""Read-only reconstruction of calibration_v0 per-model token usage.

Emit redacted JSON on stdout; never read prompts, answers or evaluator labels.
Weights are sensitivity assumptions, not measured local GPU monetary prices.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover(root: Path, workers: Path) -> dict[str, Any]:
    raw_path = root / "raw_runs.jsonl"
    runs = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
    source_hashes = {"raw_runs.jsonl": sha256(raw_path)}
    model_tags = {}
    for worker in ("a4", "a5", "a28", "strong-4090"):
        path = workers / (worker + ".yaml")
        matches = re.findall(r"^\s+model:\s+(\S+)\s*$", path.read_text(), re.MULTILINE)
        if len(matches) != 1:
            raise ValueError("ambiguous historical worker model configuration")
        model_tags[worker] = matches[0]
        source_hashes["worker-config/" + path.name] = sha256(path)
    per_call = []
    incomplete = []
    run_ids = set()
    for run in runs:
        run_id = run["run_id"]
        if run_id in run_ids:
            raise ValueError("duplicate run ID")
        run_ids.add(run_id)
        path = root / "traces" / run_id / "trace.jsonl"
        source_hashes["traces/" + run_id + "/trace.jsonl"] = sha256(path)
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        selected = {
            event["action_id"]: event
            for event in events
            if event.get("event_type") == "executor.selected" and event.get("model_id")
        }
        ends = {}
        for event in events:
            if event.get("event_type") != "worker.execution.end":
                continue
            action_id = event.get("action_id")
            if action_id not in selected:
                continue
            if action_id in ends:
                raise ValueError("duplicate model completion event")
            ends[action_id] = event
        total: Counter[str] = Counter()
        for action_id, selection in selected.items():
            event = ends.get(action_id)
            if event is None:
                incomplete.append({"run_id": run_id, "action_id": action_id})
                continue
            for field in ("input_tokens", "output_tokens"):
                if type(event.get(field)) is not int or event[field] < 0:
                    raise ValueError("missing or invalid recorded token usage")
                total[field] += event[field]
            per_call.append(
                {
                    "run_id": run_id,
                    "action_id": action_id,
                    "task_id": run["task_id"],
                    "workflow": run["workflow_id"],
                    "world": run["world_id"],
                    "repeat": run["repeat"],
                    "run_status": run["status"],
                    "logical_model": selection["model_id"],
                    "configured_model_tag": model_tags[selection["worker_id"]],
                    "executor": selection["executor"],
                    "worker": selection["worker_id"],
                    "input_tokens": event["input_tokens"],
                    "output_tokens": event["output_tokens"],
                }
            )
        if run.get("usage") and any(
            total[field] != run["usage"][field] for field in ("input_tokens", "output_tokens")
        ):
            raise ValueError("per-call usage does not reconcile with raw run total")
    if incomplete:
        raise ValueError("incomplete model calls in recorded run scope")
    aggregates: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for call in per_call:
        if call["run_status"] != "completed":
            continue
        target = aggregates[call["workflow"], call["logical_model"]]
        target["calls"] += 1
        target["input_tokens"] += call["input_tokens"]
        target["output_tokens"] += call["output_tokens"]
    orphan_paths = [
        path for path in (root / "traces").glob("*/trace.jsonl") if path.parent.name not in run_ids
    ]
    orphan_model_selections = 0
    for path in orphan_paths:
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        orphan_model_selections += sum(
            event.get("event_type") == "executor.selected" and bool(event.get("model_id"))
            for event in events
        )
    return {
        "schema": "calibration-v0-token-cost-recovery-v1",
        "scope": "main raw_runs only; early attempt1/2/3 and profiling excluded",
        "recorded_run_statuses": dict(Counter(run["status"] for run in runs)),
        "completed_runs_by_method": dict(
            Counter(run["workflow_id"] for run in runs if run["status"] == "completed")
        ),
        "per_call": per_call,
        "method_model_totals": [
            {"method": key[0], "logical_model": key[1], **value}
            for key, value in sorted(aggregates.items())
        ],
        "reconciliation_mismatches": 0,
        "unrecorded_trace_directories": len(orphan_paths),
        "unrecorded_trace_model_selections": orphan_model_selections,
        "monetary_local_gpu_cost": "unknown",
        "weight_origin": "post-hoc sensitivity assumptions; not frozen measured prices",
        "source_sha256": source_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--workers-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(recover(args.runs_root, args.workers_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
