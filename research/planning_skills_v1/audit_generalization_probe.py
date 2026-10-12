"""One final CPU audit of frozen one-step queries, scores and exact model inputs."""
import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from analyze_heldout import interval
from microbench import ACTION_SCHEMA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_policy_operation(query):
    text = query["card"]["policy"]
    values = [i["value"] for i in query["card"]["ordered_inputs"]]
    match = re.fullmatch(r"When the first input is smaller than the second, use (\w+); in all other cases use (\w+)\.", text)
    if match:
        return match.group(1 if values[0] < values[1] else 2)
    match = re.fullmatch(r"Choose (\w+) when the first input is an even integer\. Choose (\w+) when it is odd\.", text)
    if match:
        return match.group(1 if values[0] % 2 == 0 else 2)
    raise RuntimeError("Unrecognized frozen public policy; no silent scoring substitute")


def prompt_messages(query, condition):
    messages = copy.deepcopy(query["messages"] if condition != "isolated_card" else query["messages"][:1])
    text = ("This is one requested compute decision, not the whole workflow. "
            "Return exactly one compute action for this target, preserving its ordered input handles: "
            + json.dumps(query["target"], sort_keys=True))
    if condition != "full_target":
        text += "\nObserved input/policy card (no operation selected): " + json.dumps(query["card"], sort_keys=True)
    messages.append({"role": "user", "content": text})
    return messages


def audit(root, config_path, output):
    from jsonschema import Draft202012Validator
    from transformers import AutoTokenizer
    if output.exists():
        raise RuntimeError("Existing final probe audit; never overwrite")
    config = json.loads(config_path.read_text())
    queries = {q["query_id"]: q for q in config["queries"]}
    assert len(queries) == len(config["queries"])
    for query in queries.values():
        assert public_policy_operation(query) == query["gold_operation"]
    expected = {(q, c) for q in queries for c in config["conditions"]}
    rows, model_receipts, service = [], [], []
    for model in config["models"]:
        stage = root / model
        manifest = json.loads((stage / "frozen-manifest.json").read_text())
        assert manifest["config_sha256"] == sha(config_path) and manifest["config"] == config
        assert json.loads((stage / "complete.json").read_text())["expected_requests"] == len(expected)
        for name, digest in manifest["source_sha256"].items():
            assert sha(stage / "frozen-source" / name) == digest
        tokenizer = AutoTokenizer.from_pretrained(manifest["model_identity"]["local_path"], local_files_only=True, padding_side="left")
        stops = set(json.loads((stage / "deployment.json").read_text())["generation_config"]["eos_token_id"])
        records = [json.loads(line) for line in (stage / "raw-decisions.jsonl").read_text().splitlines()]
        assert len(records) == len(expected) and {(r["query_id"], r["condition"]) for r in records} == expected
        batches = [json.loads(line) for line in (stage / "service-batches.jsonl").read_text().splitlines()]
        assert sum(b["requests"] for b in batches) == len(records)
        batches_by_time = {(b["started_epoch"], b["finished_epoch"]): b for b in batches}
        observed_by_time = Counter()
        for record in records:
            query = queries[record["query_id"]]
            condition = record["condition"]
            assert record["model"] == model and record["actual_tool_executions"] == 0
            prompt = tokenizer.apply_chat_template(prompt_messages(query, condition), tokenize=False, add_generation_prompt=True, enable_thinking=False)
            assert hashlib.sha256(prompt.encode()).hexdigest() == record["prompt_sha256"]
            assert len(tokenizer.encode(prompt, add_special_tokens=False)) == record["prompt_tokens"]
            assert record["prompt_tokens"] + config["max_new_tokens"] <= config["context_tokens"]
            ids = record["raw_token_ids"]
            assert len(ids) == record["completion_tokens"] <= config["max_new_tokens"]
            payload = ids[:-1] if ids and ids[-1] in stops else ids
            assert tokenizer.decode(payload, skip_special_tokens=False) == record["raw_output"]
            category, action = None, None
            if record["category"] in ("request_timeout", "stop_requested"):
                category = record["category"]
            else:
                try:
                    action = json.loads(record["raw_output"])
                except json.JSONDecodeError:
                    category = "json_parse_failed"
                else:
                    if not Draft202012Validator(ACTION_SCHEMA).is_valid(action):
                        category = "schema_validation_failed"
            assert category == record["category"] and action == record["action"]
            valid = category is None and action["name"] == "compute"
            operator = bool(valid and action["arguments"]["operation"] == query["gold_operation"])
            target = bool(valid and all(action["arguments"][k] == query["target"][k] for k in ("node", "inputs")))
            assert (record["schema_valid"], record["operator_correct"], record["target_correct"], record["decision_correct"]) == (category is None, operator, target, operator and target)
            timing = (record["request_started_epoch"], record["request_finished_epoch"])
            assert timing in batches_by_time
            observed_by_time[timing] += 1
            rows.append({k: record[k] for k in ("model", "query_id", "task_id", "condition", "after_update", "category", "schema_valid", "operator_correct", "target_correct", "decision_correct", "prompt_tokens", "completion_tokens", "provider_latency_seconds", "prompt_sha256")}
                        | {k: query[k] for k in ("cluster_id", "depth", "template", "update_mode", "source_episode", "source_trace_sha256", "source_turn")}
                        | {"source_original_operator_correct": query["original_operation"] == query["gold_operation"]})
        assert all(observed_by_time[k] == b["requests"] for k, b in batches_by_time.items())
        service.extend({"model": model, **b} for b in batches)
        model_receipts.append({"model": model, "requests": len(records), "raw_decisions_sha256": sha(stage / "raw-decisions.jsonl"),
                               "manifest_sha256": sha(stage / "frozen-manifest.json"), "config_sha256": manifest["config_sha256"],
                               "frozen_source_files_verified": len(manifest["source_sha256"])})
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["condition"])].append(row)
    summaries = []
    for key, values in sorted(groups.items()):
        summaries.append({"model": key[0], "condition": key[1], "n": len(values),
                          **{metric: sum(r[metric] for r in values) for metric in ("schema_valid", "operator_correct", "target_correct", "decision_correct", "prompt_tokens", "completion_tokens")},
                          "categories": dict(Counter(str(r["category"]) for r in values)),
                          "original_wrong_rescued": sum(not r["source_original_operator_correct"] and r["decision_correct"] for r in values),
                          "original_correct_regressed": sum(r["source_original_operator_correct"] and not r["decision_correct"] for r in values),
                          "pre": {m: sum(r[m] for r in values if not r["after_update"]) for m in ("operator_correct", "decision_correct")}
                                 | {"n": sum(not r["after_update"] for r in values)},
                          "post": {m: sum(r[m] for r in values if r["after_update"]) for m in ("operator_correct", "decision_correct")}
                                  | {"n": sum(r["after_update"] for r in values)}})
    paired = []
    for model in config["models"]:
        indexed = {(r["query_id"], r["condition"]): r for r in rows if r["model"] == model}
        for baseline, treatment in (("full_target", "full_card"), ("full_target", "isolated_card"), ("isolated_card", "full_card")):
            clusters = defaultdict(list)
            for query in queries.values():
                clusters[query["cluster_id"]].append(int(indexed[(query["query_id"], treatment)]["decision_correct"]) - int(indexed[(query["query_id"], baseline)]["decision_correct"]))
            paired.append({"model": model, "baseline": baseline, "treatment": treatment,
                           "macro_graph_joint_accuracy_effect": interval([sum(v)/len(v) for _, v in sorted(clusters.items())])})
    observed_clusters = len({q["cluster_id"] for q in queries.values()})
    source_clusters = len({r["cluster_id"] for r in config["coverage"]})
    summary = {"status": "pass", "experiment_id": config["experiment_id"], "queries": len(queries), "requests": len(rows),
               "source_graph_clusters": source_clusters, "observed_query_graph_clusters": observed_clusters,
               "groups": summaries, "paired": paired, "models": model_receipts, "coverage": config["coverage"],
               "exclusions": config["exclusions"], "actual_model_directed_tool_executions": 0,
               "service": {"physical_generate_batches": len(service), "model_batch_wall_seconds": sum(b["provider_seconds"] for b in service),
                           "first_request_epoch": min(b["started_epoch"] for b in service), "last_request_epoch": max(b["finished_epoch"] for b in service)},
               "cloud_api_usd": 0.0, "local_gpu_usd": None,
               "statistical_note": f"Post-hoc mechanism diagnosis from the complete frozen primary source; not workflow TSR or independent held-out performance validation. Overall accuracy is query-weighted; paired effects average queries within each of {observed_clusters} observed graph clusters then weight those graphs equally. Source coverage contains {source_clusters} graphs; graphs/decisions never actually executed cannot enter this conditional probe and are not imputed. Batch wall is not kernel time."}
    output.mkdir(parents=True)
    for name, value in (("summary.json", summary), ("decision-results.json", rows),
                        ("postprocess-complete.json", {"status": "pass", "requests": len(rows), "queries": len(queries), "config_sha256": sha(config_path),
                                                      "executing_source_sha256": {p.name: sha(p) for p in Path(__file__).parent.glob('*.py')}})):
        with (output / name).open("x") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
    print(json.dumps({"status": "pass", "queries": len(queries), "requests": len(rows), "groups": summaries}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.root, args.config, args.output)
