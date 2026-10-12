"""Freeze outcome-independent first observed decisions from the complete primary.

Post-hoc mechanism diagnosis, not another held-out workflow success claim.
Private history-bearing config stays with raw traces; public freeze has hashes.
"""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from microbench import BASE_PROMPT, Environment, Task, task_text


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make(source, output, public_output):
    if output.exists() or public_output.exists():
        raise RuntimeError("Existing frozen probe config; never overwrite")
    if source.name != "Qwen3.5-9B" or source.parent.name != "heldout-binding-v1":
        raise RuntimeError("Only the declared complete 9B primary source is eligible")
    for path in (source / "complete.json", source.parent / "analysis/postprocess-complete.json",
                 source.parent / "analysis-v2/postprocess-complete.json"):
        if not path.exists():
            raise RuntimeError("Primary source or unified audit unfinished")
    manifest = json.loads((source / "frozen-manifest.json").read_text())
    queries, coverage, exclusions = [], [], Counter()
    for directory in sorted((source / "episodes").iterdir()):
        started = json.loads((directory / "started.json").read_text())
        if started["condition"] != "none":
            continue
        task = Task(**started["task"])
        env, history, seen = Environment(task), [], set()
        trace_hash = sha(directory / "trace.jsonl")
        count = 0
        for line in (directory / "trace.jsonl").read_text().splitlines():
            record = json.loads(line)
            if record["event"] != "inference":
                continue
            action = record["action"]
            if (action and action.get("name") == "compute" and record["category"] is None
                    and record["observation"].get("status") == "computed"):
                node = next(n for n in task.nodes if n["node"] == action["arguments"]["node"])
                if node["predicate"] != "always":
                    key = (node["node"], env.changed)
                    if key in seen:
                        exclusions["later_duplicate_node_phase"] += 1
                    else:
                        seen.add(key)
                        handles = action["arguments"]["inputs"]
                        assert all(env.valid(h) for h in handles)
                        assert [env.artifacts[h]["node"] for h in handles] == node["parents"]
                        values = [env.artifacts[h]["value"] for h in handles]
                        yes = values[0] < values[1] if node["predicate"] == "less_second" else values[0] % 2 == 0
                        assert node["predicate"] in ("less_second", "even")
                        queries.append({"query_id": task.task_id + f"-turn{record['turn']}",
                                        "task_id": task.task_id, "cluster_id": task.cluster_id,
                                        "after_update": env.changed, "update_mode": task.update_mode,
                                        "depth": task.depth, "template": task.template,
                                        "source_episode": directory.name, "source_trace_sha256": trace_hash,
                                        "source_turn": record["turn"],
                                        "messages": [{"role": "system", "content": BASE_PROMPT},
                                                     {"role": "user", "content": task_text(task)}] + copy.deepcopy(history),
                                        "target": {"node": node["node"], "inputs": handles},
                                        "card": {"node": node["node"], "policy": node["policy"], "ordered_inputs": [
                                            {"artifact": h, "node": env.artifacts[h]["node"], "value": env.artifacts[h]["value"]} for h in handles]},
                                        "gold_operation": node["choices"][0 if yes else 1],
                                        "original_operation": action["arguments"]["operation"]})
                        count += 1
            observation, category = env.step(record["raw_output"])
            assert observation == record["observation"] and category == record["category"]
            history += [{"role": "assistant", "content": record["raw_output"]},
                        {"role": "user", "content": "TOOL_RESULT=" + json.dumps(observation, sort_keys=True)}]
        result = json.loads((directory / "result.json").read_text())
        assert (env.completed, env.success) == (result["completion"], result["success"])
        coverage.append({"task_id": task.task_id, "cluster_id": task.cluster_id, "depth": task.depth,
                         "template": task.template, "update_mode": task.update_mode,
                         "source_trace_sha256": trace_hash, "source_completion": env.completed,
                         "eligible_queries": count, "reached_update": env.changed,
                         "conditional_nodes_in_graph": len(task.nodes) - 1,
                         "observed_pre_node_phases": sum(not phase for _, phase in seen),
                         "observed_post_node_phases": sum(phase for _, phase in seen)})
    if len(coverage) != len(manifest["config"]["tasks"]) or not queries:
        raise RuntimeError("Missing source task coverage or no eligible observations")
    config = {"experiment_id": "decision-generalization-v1", "source_model": source.name,
              "source_stage": source.parent.name, "source_condition": "none",
              "split": "posthoc_mechanism_diagnostic", "models": ["Qwen3.5-4B", "Qwen3.5-9B"],
              "seed": 1701, "batch_size": 2, "max_new_tokens": 256, "context_tokens": 16384,
              "request_timeout_seconds": 300, "conditions": ["full_target", "full_card", "isolated_card"],
              "selection": "First actually executed conditional computation per task/node/pre-or-post-update phase from EVERY primary 9B no-skill trajectory, regardless of operation correctness or final outcome. Later repeats excluded by first-occurrence rule only.",
              "interpretation": "One-step operation/target accuracy; zero model-directed tool executions, never workflow TSR or independent held-out performance validation.",
              "prompt_change": "None relative to the frozen development decision probe; new source templates/values/history only.",
              "source_manifest_sha256": sha(source / "frozen-manifest.json"),
              "source_audit_sha256": sha(source.parent / "analysis/exact-prompt-audit.json"),
              "coverage": coverage, "exclusions": dict(exclusions), "queries": queries}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
    public = {k: v for k, v in config.items() if k != "queries"}
    public["private_config_sha256"] = sha(output)
    public["generator_sha256"] = sha(Path(__file__))
    public["queries"] = [{k: q[k] for k in ("query_id", "task_id", "cluster_id", "after_update", "update_mode", "depth", "template", "source_episode", "source_trace_sha256", "source_turn")}
                         | {"query_payload_sha256": hashlib.sha256(json.dumps(q, sort_keys=True).encode()).hexdigest()} for q in queries]
    public["note"] = "Public freeze metadata. Exact source histories/card values/scoring labels are retained in the private archive; reconstruct with the generator and indexed source traces. These hashes identify the actual inference config, not this redacted metadata's bytes."
    public_output.parent.mkdir(parents=True, exist_ok=True)
    with public_output.open("x") as stream:
        json.dump(public, stream, indent=2, sort_keys=True)
    print(json.dumps({"queries": len(queries), "source_tasks": len(coverage), "clusters": len({q['cluster_id'] for q in queries}),
                      "requests_per_model": len(queries) * len(config["conditions"]),
                      "private_config_sha256": public["private_config_sha256"], "exclusions": dict(exclusions)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()
    make(args.source, args.output, args.public_output)
