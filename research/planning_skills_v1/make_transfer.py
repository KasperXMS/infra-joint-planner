"""Pre-register independent structural transfer without inspecting model outcomes."""
import argparse
import copy
import json
import random
import string
from dataclasses import asdict
from pathlib import Path

from make_heldout import paired_tasks
from microbench import digest, reference
from transfer_microbench import Task


def transform(variants, record):
    rng = random.Random("opaque-order/" + variants[0].cluster_id)
    names = list(variants[0].sources) + [node["node"] for node in variants[0].nodes]
    mapping = {}
    while len(mapping) < len(names):
        label = "v" + "".join(rng.choices(string.ascii_lowercase, k=5))
        if label not in mapping.values():
            mapping[names[len(mapping)]] = label
    order = [mapping[node["node"]] for node in variants[0].nodes]
    rng.shuffle(order)
    # Extremely unlikely canonical permutation is rejected before inference.
    indexed = {name: i for i, name in enumerate(order)}
    while not any(indexed[mapping[p]] > indexed[mapping[n["node"]]]
                  for n in variants[0].nodes for p in n["parents"] if p not in variants[0].sources):
        rng.shuffle(order)
        indexed = {name: i for i, name in enumerate(order)}
    cluster = "transfer-" + digest([record, "opaque-public-permutation-v1"])[:12]
    output = []
    for original in variants:
        spec = asdict(copy.deepcopy(original))
        spec["split"] = "transfer"
        spec["cluster_id"] = cluster
        spec["task_id"] = "transfer-case-" + digest([cluster, original.update_mode])[:16]
        spec["sources"] = {mapping[key]: value for key, value in original.sources.items()}
        spec["changed_source"] = mapping[original.changed_source]
        spec["root"] = mapping[original.root]
        for node in spec["nodes"]:
            node["node"] = mapping[node["node"]]
            node["parents"] = [mapping[p] for p in node["parents"]]
        spec["presentation_order"] = order
        task = Task(**spec)
        assert reference(task, False)["values"][task.root] == reference(original, False)["values"][original.root]
        assert reference(task, True)["values"][task.root] == reference(original, True)["values"][original.root]
        output.append(task)
    return output, {**record, "cluster_id": cluster, "presentation": "opaque IDs / shuffled public nodes"}


def build():
    tasks, generation = [], []
    for template in ("relative", "parity"):
        for depth in (2, 4):
            for seed in (71017, 71033, 71059, 71081):
                variants, record = paired_tasks(template, depth, seed)
                transformed, record = transform(variants, record)
                tasks.extend(transformed)
                generation.append(record)
    random.Random(8043).shuffle(tasks)
    conditions = ["none", "static_system", "binding_system", "unbound_system"]
    return {"experiment_id": "structural-transfer-v1", "runner": "run_transfer_model.py", "seed": 1701,
            "models": ["Qwen3.5-4B", "Qwen3.5-9B"], "batch_size": 2,
            "context_tokens": 16384, "max_new_tokens": 256, "turn_budget": 64,
            "request_timeout_seconds": 300, "task_timeout_seconds": 3600, "sampling": "greedy", "thinking": False,
            "conditions": conditions, "tasks": [asdict(t) for t in tasks], "generator_records": generation,
            "planned_episodes": len(tasks) * len(conditions) * 2,
            "independent_graph_clusters": len(generation),
            "design": "Independent seeds, new depths 2/4, opaque source/node IDs and non-topological PUBLIC node ordering. Evaluator, private graph order, tools, generic skills and runtime renderers unchanged.",
            "launch_policy": "Assess only each completed 252-episode primary model. Launch all 384 transfer episodes on BOTH models if on either completed primary model absolute joined-minus-unjoined TSR >=0.10, or max(joined,unjoined) TSR minus system-static TSR >=0.10. GPU-wise handoff is allowed only after that model's primary worker exits and releases its GPU. If neither completed model triggers, skip transfer and reconsider the mechanism. No primary outcome subset, model selection or per-cell reruns.",
            "analysis_unit": "16 generated graph clusters, each with paired none/stable/flip variants; no outcome-selected subset or reruns.",
            "primary_contrasts": ["binding_system vs unbound_system", "binding_system vs static_system", "unbound_system vs static_system", "static_system vs none"],
            "selection_limit": "Same pre-inference generator eligibility selection as heldout-binding-v1; root numeric changes required. Structural synthetic transfer, not real-world benchmark validation."}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    config = build()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"tasks": len(config["tasks"]), "clusters": config["independent_graph_clusters"], "planned_episodes": config["planned_episodes"]}))
