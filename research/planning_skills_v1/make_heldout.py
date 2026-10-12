"""Freeze paired policy-stable/flip updates independently of model outcomes."""
import argparse
import copy
import json
import random
from dataclasses import asdict
from pathlib import Path

from microbench import digest, make_task, reference


def paired_tasks(template, depth, seed):
    for attempt in range(100):
        task = make_task("heldout", seed + attempt * 100003, depth=depth, width=3, template=template)
        before = reference(task, False)
        candidates = {"stable": [], "flip": []}
        for value in range(1, 65):
            if value == task.sources[task.changed_source]:
                continue
            task.replacement = value
            after = reference(task, True)
            if after["values"][task.root] == before["values"][task.root]:
                continue
            mode = "stable" if after["operations"] == before["operations"] else "flip"
            candidates[mode].append(value)
        if all(candidates.values()):
            break
    else:
        raise RuntimeError("Cannot construct matched policy update controls")
    cluster = "graph-" + digest([template, depth, seed, attempt])[:12]
    tasks = []
    for mode in ("none", "stable", "flip"):
        variant = copy.deepcopy(task)
        variant.cluster_id = cluster
        variant.update_mode = mode
        variant.refresh = mode != "none"
        variant.task_id = "case-" + digest([cluster, mode])[:16]
        if variant.refresh:
            variant.replacement = random.Random(f"replacement/{cluster}/{mode}").choice(candidates[mode])
        tasks.append(variant)
    return tasks, {"cluster_id": cluster, "template": template, "depth": depth, "requested_seed": seed,
                   "actual_seed": task.seed, "resampling_attempts": attempt,
                   "stable_candidates": len(candidates["stable"]), "flip_candidates": len(candidates["flip"])}


def build():
    tasks, generation = [], []
    for template in ("relative", "parity"):
        for depth in (1, 3):
            for seed in (43017, 43033, 43059):
                variants, record = paired_tasks(template, depth, seed)
                tasks.extend(variants)
                generation.append(record)
    # Fixed seeded interleaving, not an outcome-dependent execution schedule.
    random.Random(8041).shuffle(tasks)
    return {"experiment_id": "heldout-binding-v1", "seed": 1701,
            "models": ["Qwen3.5-4B", "Qwen3.5-9B"], "batch_size": 2,
            "context_tokens": 16384, "max_new_tokens": 256, "turn_budget": 64,
            "request_timeout_seconds": 300, "task_timeout_seconds": 3600, "sampling": "greedy", "thinking": False,
            "conditions": ["none", "static_system", "static", "local", "ledger_system", "binding_system", "unbound_system"],
            "tasks": [asdict(t) for t in tasks], "generator_records": generation,
            "planned_episodes": len(tasks) * 7 * 2, "independent_graph_clusters": len(generation),
            "design": "Held-out relative/parity templates and new seeds; three paired update regimes per graph. Seven controlled support/placement conditions. No static rule changes.",
            "selection_limit": "Diagnostic graphs are selected before inference to admit genuine value changes both with stable and with changed reference operation vectors; root outcomes must also change. This is not natural-task prevalence.",
            "primary_contrasts": ["binding_system vs unbound_system: per-state information/repetition/token-matched join", "binding_system vs static_system: combined runtime binding support", "static vs static_system: same-rule placement", "ledger_system vs static_system: bookkeeping", "local vs static_system: selective delivery, not pure granularity"],
            "analysis_unit": "12 independent generated graphs; update modes paired within graph. Do not treat all 36 task variants as independent."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"tasks": len(config["tasks"]), "clusters": config["independent_graph_clusters"],
                      "planned_episodes": config["planned_episodes"]}))
