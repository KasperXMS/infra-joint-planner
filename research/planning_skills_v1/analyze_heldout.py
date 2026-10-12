"""Frozen-task replay and exploratory graph-cluster paired analysis; no inference."""
import argparse
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from analyze import inspect_episode, jsonl
from microbench import Environment, Task


CONTRASTS = [
    ("unbound_system", "binding_system"),
    ("static_system", "binding_system"),
    ("static", "static_system"),
    ("static_system", "ledger_system"),
    ("static_system", "local"),
]


def correct_operation(node, values):
    predicate = node["predicate"]
    yes = {"greater": values[0] > node["threshold"],
           "less_second": values[0] < values[1],
           "even": values[0] % 2 == 0, "always": True}[predicate]
    return node["choices"][0 if yes else 1]


def details(directory):
    row = inspect_episode(directory)
    task = Task(**json.loads((directory / "started.json").read_text())["task"])
    env = Environment(task)
    nodes = {n["node"]: n for n in task.nodes}
    before = {}
    counts = Counter()
    errors = Counter()
    decisions = []
    maximum_prompt = 0
    support_total = 0
    initial_prefix = []
    trace_records = jsonl(directory / "trace.jsonl")
    for record in trace_records:
        maximum_prompt = max(maximum_prompt, record.get("prompt_tokens", 0))
        support_total += record.get("support_tokens", 0)
        if record["event"] != "inference":
            continue
        category = record["category"]
        counts["raw_actions"] += 1
        counts["schema_valid_actions"] += category not in ("json_parse_failed", "schema_validation_failed")
        if category and category not in ("source_updated", "transient_unavailable"):
            errors[category] += 1
        action = record["action"]
        if not env.changed:
            initial_prefix.append({"raw_output": record["raw_output"], "observation": record["observation"]})
        if (isinstance(action, dict) and action.get("name") == "compute"
                and category is None and record["observation"].get("status") == "computed"):
            args = action["arguments"]
            node = nodes.get(args["node"])
            handles = args["inputs"]
            if (node and all(env.valid(h) for h in handles)
                    and [env.artifacts[h]["node"] for h in handles] == node["parents"]
                    and node["predicate"] != "always"):
                values = [env.artifacts[h]["value"] for h in handles]
                gold = correct_operation(node, values)
                correct = args["operation"] == gold
                phase = "post" if env.changed else "pre"
                counts[f"{phase}_conditional_decisions"] += 1
                counts[f"{phase}_conditional_correct"] += correct
                prior = before.get(node["node"])
                changed_inputs = bool(prior and prior["values"] != values)
                changed_policy = bool(prior and prior["gold"] != gold)
                stale_old_operation = bool(env.changed and changed_inputs and changed_policy
                    and prior["chosen"] == prior["gold"] and args["operation"] == prior["chosen"])
                if env.changed and changed_inputs:
                    counts["post_changed_input_decisions"] += 1
                    counts["post_changed_input_correct"] += correct
                    if changed_policy:
                        counts["post_changed_policy_decisions"] += 1
                        counts["post_changed_policy_correct"] += correct
                    counts["stale_old_operation_decisions"] += stale_old_operation
                decision = {"turn": record["turn"], "node": node["node"], "values": values,
                            "gold": gold, "chosen": args["operation"], "correct": correct,
                            "phase": phase, "changed_inputs": changed_inputs,
                            "changed_policy": changed_policy, "stale_old_operation": stale_old_operation}
                decisions.append(decision)
                if not env.changed:
                    before[node["node"]] = decision
        observation, replay_category = env.step(record["raw_output"])
        if observation != record["observation"] or replay_category != category:
            raise RuntimeError("Independent replay mismatch")
    # Artifact values never mutate: updates invalidate old handles and create
    # fresh ones. Actual executed decisions can therefore be scored against the
    # immutable parent values after replay, including unconditional/root rules.
    executed = []
    for event, record in zip(env.events, (r for r in trace_records if r["event"] == "inference")):
        if event["observation"].get("status") != "computed":
            continue
        args = event["action"]["arguments"]
        node = nodes[args["node"]]
        values = [env.artifacts[handle]["value"] for handle in args["inputs"]]
        gold = correct_operation(node, values)
        executed.append({"turn": record["turn"], "artifact": event["observation"]["artifact"],
                         "node": node["node"], "parents": args["inputs"], "values": values,
                         "chosen": args["operation"], "gold": gold, "correct": args["operation"] == gold,
                         "conditional": node["predicate"] != "always"})
    all_executed_correct = all(d["correct"] for d in executed)
    counts["executed_policy_decisions"] = len(executed)
    counts["executed_policy_correct"] = sum(d["correct"] for d in executed)
    counts["unconditional_policy_decisions"] = sum(not d["conditional"] for d in executed)
    counts["unconditional_policy_correct"] = sum(not d["conditional"] and d["correct"] for d in executed)
    submitted_handle = None
    if env.completed:
        terminal = next(event for event in reversed(env.events) if event["observation"].get("status") == "submitted")
        submitted_handle = terminal["action"]["arguments"]["artifact"]
    used = set()
    stack = [submitted_handle] if submitted_handle else []
    while stack:
        handle = stack.pop()
        if handle in used:
            continue
        used.add(handle)
        stack.extend(env.artifacts[handle]["parents"])
    final_errors = [d for d in executed if d["artifact"] in used and not d["correct"]]
    final_compliant = not final_errors if env.completed else None
    if env.completed:
        if not all(env.valid(handle) for handle in used):
            raise RuntimeError("Submitted provenance contains an invalid artifact")
        if final_compliant and not env.success:
            raise RuntimeError("Numeric evaluator conflicts with policy-compliant submitted provenance")
    affected = {task.changed_source}
    for node in task.nodes:
        if any(parent in affected for parent in node["parents"]):
            affected.add(node["node"])
    minimum = len(task.sources) + len(task.nodes) + 2
    if task.refresh:
        minimum += len(affected) + 1  # refetch source, recompute descendants, second verify
    if task.transient:
        minimum += 1
    return {**row, "cluster_id": task.cluster_id, "update_mode": task.update_mode,
            "conditional_counts": dict(counts), "unexpected_errors": dict(errors),
            "recovered_after_unexpected_error": bool(errors) and row["completion"],
            "succeeded_after_unexpected_error": bool(errors) and row["success"],
            "required_verify_attempts_for_correct_path": 1 + int(task.refresh) + int(task.transient),
            "minimum_successful_calls": minimum,
            "excess_turns_over_minimum": row["turns"] - minimum,
            "max_prompt_tokens": maximum_prompt, "support_tokens": support_total,
            "policy_decisions": len(executed), "policy_correct": sum(d["correct"] for d in executed),
            "all_executed_policy_choices_correct": all_executed_correct,
            "first_policy_error_turn": next((d["turn"] for d in executed if not d["correct"]), None),
            "submitted_artifact": submitted_handle,
            "submitted_provenance_policy_compliant": final_compliant,
            "submitted_provenance_policy_errors": len(final_errors) if env.completed else None,
            "submitted_provenance_error_decisions": final_errors,
            "numeric_success_with_policy_violation": row["success"] and final_compliant is False,
            "recovered_policy_provenance": not all_executed_correct and final_compliant is True,
            "executed_policy_decisions": executed,
            "initial_through_update_prefix_sha256": hashlib.sha256(json.dumps(initial_prefix, sort_keys=True).encode()).hexdigest(),
            "initial_through_update_turns": len(initial_prefix),
            "decisions": decisions}


def aggregate(rows):
    n = len(rows)
    errors, counts, finishes, tools = Counter(), Counter(), Counter(), Counter()
    for r in rows:
        errors.update(r["unexpected_errors"])
        counts.update(r["conditional_counts"])
        tools.update(r["tool_counts"])
        finishes[r["finish_reason"]] += 1
    return {"n": n, "clusters": len({r["cluster_id"] for r in rows}),
            "completion_count": sum(r["completion"] for r in rows),
            "success_count": sum(r["success"] for r in rows),
            "completion": sum(r["completion"] for r in rows) / n,
            "tsr": sum(r["success"] for r in rows) / n,
            "turns": sum(r["turns"] for r in rows),
            "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
            "completion_tokens": sum(r["completion_tokens"] for r in rows),
            "support_tokens": sum(r["support_tokens"] for r in rows),
            "tool_seconds": sum(r["tool_seconds"] for r in rows),
            "e2e_median_seconds": statistics.median(r["e2e_seconds"] for r in rows),
            "max_prompt_tokens": max(r["max_prompt_tokens"] for r in rows),
            "errors": dict(errors), "finish_reasons": dict(finishes),
            "counts": dict(counts), "tool_counts": dict(tools),
            "recovered_after_unexpected_error": sum(r["recovered_after_unexpected_error"] for r in rows),
            "succeeded_after_unexpected_error": sum(r["succeeded_after_unexpected_error"] for r in rows),
            "completed_after_source_update": sum(r["source_update_observed"] and r["completion"] for r in rows),
            "completed_verify_attempts": sum(r["tool_counts"].get("verify", 0) for r in rows if r["completion"]),
            "completed_required_verify_attempts": sum(r["required_verify_attempts_for_correct_path"] for r in rows if r["completion"]),
            "policy_compliant_completion_count": sum(r["submitted_provenance_policy_compliant"] is True for r in rows),
            "numeric_success_with_policy_violation": sum(r["numeric_success_with_policy_violation"] for r in rows),
            "policy_provenance_recoveries": sum(r["recovered_policy_provenance"] for r in rows),
            "success_despite_policy_error": sum(r["success"] and not r["all_executed_policy_choices_correct"] for r in rows)}


def interval(values):
    """Resample independent graphs, retaining all paired variants in each graph."""
    rng = random.Random(714203)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(5000))
    return {"mean": statistics.mean(values), "cluster_bootstrap_percentile95": [samples[124], samples[4874]],
            "graph_clusters": len(values), "bootstrap_replicates": 5000}


def paired(rows):
    by_task = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["condition"]] = row
    output = []
    for a, b in CONTRASTS:
        for mode in ("all", "none", "stable", "flip"):
            pairs = [(v[a], v[b]) for v in by_task.values() if a in v and b in v
                     and (mode == "all" or v[a]["update_mode"] == mode)]
            if not pairs:
                continue
            effects = {}
            for metric in ("success", "completion", "turns", "prompt_tokens", "completion_tokens"):
                clusters = defaultdict(list)
                for left, right in pairs:
                    clusters[left["cluster_id"]].append(right[metric] - left[metric])
                effects[metric] = interval([statistics.mean(v) for _, v in sorted(clusters.items())])
            output.append({"baseline": a, "treatment": b, "update_mode": mode,
                           "paired_variants": len(pairs),
                           "rescues": sum(not a_["success"] and b_["success"] for a_, b_ in pairs),
                           "regressions": sum(a_["success"] and not b_["success"] for a_, b_ in pairs),
                           "effects": effects})
    return output


def capacity_interactions(rows):
    indexed = {(r["model"], r["task_id"], r["condition"]): r for r in rows}
    models = sorted({r["model"] for r in rows})
    if len(models) != 2:
        return []
    small, large = models
    output = []
    for baseline, treatment in CONTRASTS:
        differences = defaultdict(list)
        for task in sorted({r["task_id"] for r in rows}):
            keys = [(model, task, condition) for model in models for condition in (baseline, treatment)]
            if not all(key in indexed for key in keys):
                continue
            left = int(indexed[(small, task, treatment)]["success"]) - int(indexed[(small, task, baseline)]["success"])
            right = int(indexed[(large, task, treatment)]["success"]) - int(indexed[(large, task, baseline)]["success"])
            differences[indexed[(small, task, baseline)]["cluster_id"]].append(right - left)
        if differences:
            output.append({"baseline": baseline, "treatment": treatment,
                           "orientation": f"({large} treatment-baseline) - ({small} treatment-baseline)",
                           **interval([statistics.mean(v) for _, v in sorted(differences.items())])})
    return output


def counterfactual_prefixes(rows):
    pairs = defaultdict(dict)
    for row in rows:
        if row["update_mode"] in ("stable", "flip"):
            pairs[(row["model"], row["condition"], row["cluster_id"])][row["update_mode"]] = row
    counts = defaultdict(Counter)
    for (model, condition, cluster), variants in pairs.items():
        if set(variants) != {"stable", "flip"}:
            continue
        a, b = variants["stable"], variants["flip"]
        group = counts[(model, condition)]
        group["paired_graphs"] += 1
        group["both_reached_update"] += a["source_update_observed"] and b["source_update_observed"]
        group["exact_initial_prefix_matches"] += a["initial_through_update_prefix_sha256"] == b["initial_through_update_prefix_sha256"]
    return [{"model": key[0], "condition": key[1], **dict(value)} for key, value in sorted(counts.items())]


def analyze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    rows, integrity, batches = [], [], []
    for manifest_path in sorted(root.glob("*/frozen-manifest.json")):
        stage = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        config = manifest["config"]
        expected = {task["task_id"] + "__" + condition for task in config["tasks"] for condition in config["conditions"]}
        directories = sorted((stage / "episodes").iterdir())
        actual = {d.name for d in directories if (d / "result.json").exists()}
        if actual != expected or not (stage / "complete.json").exists():
            raise RuntimeError(f"Incomplete or extra episodes: {stage.name}, {len(actual)}/{len(expected)}")
        if len(jsonl(stage / "results.jsonl")) != len(expected):
            raise RuntimeError("Duplicate/missing result index records")
        for name, expected_sha in manifest["source_sha256"].items():
            source = stage / "frozen-source" / name
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected_sha:
                raise RuntimeError(f"Frozen source mismatch: {name}")
        integrity.append({"model": stage.name, "expected": len(expected), "finished": len(actual),
                          "config_sha256": manifest["config_sha256"],
                          "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                          "frozen_source_verified": True})
        rows.extend(details(d) for d in directories)
        batches.extend({**b, "model": stage.name} for b in jsonl(stage / "service-batches.jsonl"))
    groups = defaultdict(list)
    strata = defaultdict(list)
    by_model = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["condition"])].append(row)
        strata[(row["model"], row["condition"], row["update_mode"], row["depth"], row["template"])].append(row)
        by_model[row["model"]].append(row)
    summary = {"integrity": integrity, "episodes": len(rows),
               "groups": [{"group": list(k), **aggregate(v)} for k, v in sorted(groups.items())],
               "strata": [{"group": list(k), **aggregate(v)} for k, v in sorted(strata.items())],
               "paired": {model: paired(v) for model, v in sorted(by_model.items())},
               "capacity_interactions": capacity_interactions(rows),
               "counterfactual_prefix_checks": counterfactual_prefixes(rows),
               "service": {"batches": len(batches), "requests": sum(b["requests"] for b in batches),
                           "model_batch_wall_seconds": sum(b["provider_seconds"] for b in batches),
                           "first_request_epoch": min(b["started_epoch"] for b in batches),
                           "last_request_epoch": max(b["finished_epoch"] for b in batches),
                           "peak_allocated_gpu_bytes": {model: max(b["allocated_gpu_bytes"] for b in batches if b["model"] == model) for model in by_model},
                           "note": "Batch wall counted once; neither summed overlapping request latency nor GPU kernel time."},
               "cloud_api_usd": 0.0, "local_gpu_usd": None,
               "statistical_note": "Exploratory paired graph-cluster bootstrap; 12 graphs, diagnostic synthetic distribution, no universal significance claim."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (output / "episode-results.json").write_text(json.dumps(rows, indent=2, sort_keys=True))
    index = [{k: r[k] for k in ("model", "episode_id", "task_id", "cluster_id", "condition", "trace_sha256")} for r in rows]
    (output / "trace-index.json").write_text(json.dumps(index, indent=2, sort_keys=True))
    print(json.dumps({"episodes": len(rows), "groups": [{k: g[k] for k in ("group", "completion_count", "success_count", "turns", "errors")} for g in summary["groups"]]}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    analyze(args.root, args.output)
