"""Freeze every eligible observed development decision, not just failures."""
import argparse
import copy
import json
from pathlib import Path

from microbench import BASE_PROMPT, Environment, Task, task_text

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
queries = []
for directory in sorted((args.source / "episodes").iterdir()):
    started = json.loads((directory / "started.json").read_text())
    if started["condition"] != "none":
        continue
    task = Task(**started["task"])
    env = Environment(task)
    history = []
    for line in (directory / "trace.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record["event"] != "inference":
            continue
        action = record["action"]
        if action and action.get("name") == "compute" and record["category"] is None:
            node = next(n for n in task.nodes if n["node"] == action["arguments"]["node"])
            if node["node"] != task.root:
                handles = action["arguments"]["inputs"]
                operands = [env.artifacts[h]["value"] for h in handles]
                selected = {"greater": operands[0] > node["threshold"], "less_second": operands[0] < operands[1],
                            "even": operands[0] % 2 == 0, "always": True}[node["predicate"]]
                target = {"node": node["node"], "inputs": handles}
                card = {"node": node["node"], "policy": node["policy"], "ordered_inputs": [
                    {"artifact": h, "node": env.artifacts[h]["node"], "value": env.artifacts[h]["value"]} for h in handles]}
                queries.append({"query_id": task.task_id + f"-turn{record['turn']}", "task_id": task.task_id,
                                "after_update": env.changed, "depth": task.depth, "template": task.template,
                                "messages": [{"role": "system", "content": BASE_PROMPT},
                                             {"role": "user", "content": task_text(task)}] + copy.deepcopy(history),
                                "target": target, "card": card,
                                "gold_operation": node["choices"][0 if selected else 1],
                                "original_operation": action["arguments"]["operation"]})
        observation, category = env.step(record["raw_output"])
        assert observation == record["observation"] and category == record["category"]
        history += [{"role": "assistant", "content": record["raw_output"]},
                    {"role": "user", "content": "TOOL_RESULT=" + json.dumps(observation, sort_keys=True)}]
config = {"experiment_id": "decision-context-probe-v1", "source_model": "Qwen3.5-9B",
          "source_stage": "diagnostic-v2", "source_condition": "none", "split": "development",
          "models": ["Qwen3.5-4B", "Qwen3.5-9B"], "seed": 1701, "batch_size": 4,
          "max_new_tokens": 256, "context_tokens": 16384, "request_timeout_seconds": 300,
          "conditions": ["full_target", "full_card", "isolated_card"], "queries": queries,
          "selection": "Every valid non-root compute from all eight source trajectories, irrespective of correctness.",
          "interpretation": "One-step decision probe, not workflow completion/TSR. Gold operations never enter prompts."}
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x") as stream:
    json.dump(config, stream, indent=2, sort_keys=True)
print(json.dumps({"queries": len(queries), "requests_per_model": len(queries) * len(config["conditions"])}))
