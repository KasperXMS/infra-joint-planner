"""Replay synthetic traces, independently aggregate outcomes and paired differences.

No inference, result rewriting, best-run selection or hidden model-based judge.
Use the stage's frozen microbench version when evaluating an older stage.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from microbench import Environment, Task, digest


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def wilson(k, n):
    if not n:
        return [None, None]
    z = 1.959963984540054
    center = (k / n + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(k / n * (1 - k / n) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0, center - half), min(1, center + half)]


def inspect_episode(directory):
    started = json.loads((directory / "started.json").read_text())
    result = json.loads((directory / "result.json").read_text())
    env = Environment(Task(**started["task"]))
    errors = Counter()
    policy_total = policy_correct = 0
    first_error_turn = None
    update_turn = completion_turn = None
    for record in jsonl(directory / "trace.jsonl"):
        if record["event"] != "inference":
            continue
        action = record["action"]
        if isinstance(action, dict) and action.get("name") == "compute" and record["category"] not in ("schema_validation_failed", "json_parse_failed"):
            args = action["arguments"]
            node = next((n for n in env.task.nodes if n["node"] == args["node"]), None)
            handles = args["inputs"]
            if node and all(env.valid(h) for h in handles) and [env.artifacts[h]["node"] for h in handles] == node["parents"]:
                values = [env.artifacts[h]["value"] for h in handles]
                predicate = node["predicate"]
                selected = {"greater": values[0] > node["threshold"], "less_second": values[0] < values[1],
                            "even": values[0] % 2 == 0, "always": True}[predicate]
                policy_total += 1
                policy_correct += args["operation"] == node["choices"][0 if selected else 1]
        observation, category = env.step(record["raw_output"])
        if observation != record["observation"] or category != record["category"]:
            raise RuntimeError(f"Trace replay mismatch: {directory.name}, turn {record['turn']}")
        if category:
            errors[category] += 1
            if first_error_turn is None:
                first_error_turn = record["turn"]
        if category == "source_updated":
            update_turn = record["turn"]
        if env.completed:
            completion_turn = record["turn"]
    if (env.completed, env.success, env.submitted_value) != (result["completion"], result["success"], result["submitted_value"]):
        raise RuntimeError(f"Evaluator mismatch: {directory.name}")
    if hashlib.sha256((directory / "trace.jsonl").read_bytes()).hexdigest() != result["trace_sha256"]:
        raise RuntimeError(f"Trace hash mismatch: {directory.name}")
    return {**result, "policy_decisions": policy_total, "policy_correct": policy_correct,
            "recovered_after_error": first_error_turn is not None and env.completed,
            "recovered_after_update": update_turn is not None and env.completed,
            "post_update_turns": completion_turn - update_turn if update_turn and completion_turn else None}


def analyze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    rows, index, batches = [], [], []
    for manifest in sorted(root.rglob("frozen-manifest.json")):
        stage = manifest.parent
        expected = len(json.loads(manifest.read_text())["config"]["tasks"]) * len(json.loads(manifest.read_text())["config"]["conditions"])
        dirs = sorted((stage / "episodes").glob("*"))
        completed = [d for d in dirs if (d / "result.json").exists()]
        index.append({"model_stage": str(stage.relative_to(root)), "expected": expected,
                      "started": len(dirs), "finished": len(completed),
                      "incomplete": [d.name for d in dirs if not (d / "result.json").exists()],
                      "frozen_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()})
        rows.extend(inspect_episode(d) for d in completed)
        if (stage / "service-batches.jsonl").exists():
            batches.extend(jsonl(stage / "service-batches.jsonl"))
    grouped = defaultdict(list)
    stratified = defaultdict(list)
    for row in rows:
        grouped[(row["model"], row["condition"])].append(row)
        stratified[(row["model"], row["condition"], row["depth"], row["refresh"])].append(row)

    def aggregate(key, values):
        n = len(values)
        completed, success = sum(r["completion"] for r in values), sum(r["success"] for r in values)
        errors, tools = Counter(), Counter()
        for r in values:
            errors.update(r["error_counts"])
            tools.update(r["tool_counts"])
        return {"group": list(key), "n": n, "completion_count": completed, "success_count": success,
                "completion": completed / n, "tsr": success / n, "tsr_wilson95": wilson(success, n),
                "turns": sum(r["turns"] for r in values), "prompt_tokens": sum(r["prompt_tokens"] for r in values),
                "completion_tokens": sum(r["completion_tokens"] for r in values),
                "tool_counts": dict(tools), "errors": dict(errors),
                "finish_reasons": dict(Counter(r["finish_reason"] for r in values)),
                "policy_correct": sum(r["policy_correct"] for r in values),
                "policy_decisions": sum(r["policy_decisions"] for r in values),
                "recovery_count": sum(r["recovered_after_error"] for r in values),
                "update_recovery_count": sum(r["recovered_after_update"] for r in values)}
    summary = {"integrity": index, "groups": [aggregate(k, v) for k, v in sorted(grouped.items())],
               "strata": [aggregate(k, v) for k, v in sorted(stratified.items())],
               "total_episodes": len(rows), "real_model_requests": sum(r["turns"] for r in rows),
               "service_batches": len(batches), "model_service_seconds": sum(b["provider_seconds"] for b in batches),
               "service_note": "Whole batch wall time counted once; not GPU kernel time or summed request waiting.",
               "local_gpu_usd": None, "statistical_note": "Wilson intervals describe this small synthetic task sample; no population or novelty claim."}
    by_task = defaultdict(dict)
    for row in rows:
        by_task[(row["model"], row["task_id"])][row["condition"]] = row
    paired = defaultdict(Counter)
    for (model, task), conditions in by_task.items():
        for other in ("static", "local", "ledger"):
            if "none" not in conditions or other not in conditions:
                continue
            a, b = conditions["none"], conditions[other]
            pair = paired[(model, other)]
            pair["paired_tasks"] += 1
            pair["rescues"] += not a["success"] and b["success"]
            pair["regressions"] += a["success"] and not b["success"]
            pair["delta_turns"] += b["turns"] - a["turns"]
            pair["delta_prompt_tokens"] += b["prompt_tokens"] - a["prompt_tokens"]
    summary["paired_vs_none"] = [{"model": k[0], "condition": k[1], **dict(v)} for k, v in sorted(paired.items())]
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (output / "episode-results.json").write_text(json.dumps(rows, indent=2, sort_keys=True))
    with (output / "results.csv").open("w", newline="") as stream:
        fields = ["model", "condition", "task_id", "depth", "width", "refresh", "transient", "completion", "success", "turns",
                  "prompt_tokens", "completion_tokens", "finish_reason", "policy_correct", "policy_decisions", "post_update_turns"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"episodes": len(rows), "groups": [{k: r[k] for k in ("group", "n", "completion_count", "success_count", "turns", "errors")} for r in summary["groups"]]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.root, args.output)
