"""Freeze selected task specs before inference; no adaptive in-matrix changes."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from microbench import make_task

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
tasks = [make_task("development", seed, depth=depth, width=2, refresh=refresh)
         for depth in (1, 3) for refresh in (False, True) for seed in (11, 23)]
config = {"experiment_id": "diagnostic-v1", "seed": 1701,
          "conditions": ["none", "static", "local", "ledger"], "batch_size": 4,
          "context_tokens": 16384, "max_new_tokens": 256, "turn_budget": 48,
          "task_timeout_seconds": 3600, "sampling": "greedy", "thinking": False,
          "models": ["Qwen3.5-4B", "Qwen3.5-9B"], "tasks": [asdict(t) for t in tasks],
          "design": "Development only. Capacity x observed-state update x depth. No heldout evidence yet."}
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(config, stream, indent=2, sort_keys=True)
