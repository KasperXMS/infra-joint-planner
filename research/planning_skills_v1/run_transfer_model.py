"""Reuse the identical inference engine; only instantiate presentation-aware tasks."""
import argparse
import time
from pathlib import Path

import run_model
from runtime_guard import append
from transfer_microbench import Task

run_model.Task = Task


def instrument_support(original, stage):
    def measured(condition, env, tokenizer=None):
        begun = time.perf_counter()
        text, metadata = original(condition, env, tokenizer=tokenizer)
        seconds = time.perf_counter() - begun
        append(stage / "support-work.jsonl", {"epoch": time.time(), "episode_id": env.task.task_id + "__" + condition,
                                             "condition": condition, "support_wall_seconds": seconds})
        return text, {**metadata, "support_wall_seconds": seconds}
    return measured


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--model", required=True)
    args = p.parse_args()
    import json
    config = json.loads(args.config.read_text())
    run_model.support = instrument_support(run_model.support, args.root / "results" / config["experiment_id"] / args.model)
    run_model.run(args.root, args.config, args.model)
