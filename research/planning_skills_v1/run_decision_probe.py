"""Counterfactual observed-value binding probe; no tool execution or TSR claim."""
import argparse
import copy
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

from microbench import ACTION_SCHEMA
from runtime_guard import append, register


def run(root, config_path, model_name):
    import torch
    import transformers
    from jsonschema import Draft202012Validator
    from transformers import AutoModelForImageTextToText, AutoTokenizer, StoppingCriteria, StoppingCriteriaList

    register(root, f"decision_probe_{model_name}")
    config = json.loads(config_path.read_text())
    stage = root / "results" / config["experiment_id"] / model_name
    stage.mkdir(parents=True, exist_ok=True)
    identity = json.loads((root / f"{model_name}-identity.json").read_text())
    with (stage / "frozen-manifest.json").open("x") as stream:
        json.dump({"config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "config": config,
                   "model_identity": identity, "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in Path(__file__).parent.glob("*.py")}, "torch": torch.__version__,
                   "transformers": transformers.__version__, "started_epoch": time.time(),
                   "backend": "transformers_direct", "dtype": "bfloat16", "quantization": None,
                   "thinking": False, "constrained_decoding": False, "actual_tool_executions": 0}, stream, indent=2)
    torch.manual_seed(config["seed"])
    tokenizer = AutoTokenizer.from_pretrained(identity["local_path"], local_files_only=True, padding_side="left")
    model = AutoModelForImageTextToText.from_pretrained(identity["local_path"], local_files_only=True,
                                                      dtype=torch.bfloat16, device_map={"": "cuda:0"}, attn_implementation="sdpa")
    model.eval()
    generation = copy.deepcopy(model.generation_config)
    generation.do_sample = False
    generation.temperature = generation.top_p = generation.top_k = None
    generation.repetition_penalty = 1.0
    generation.no_repeat_ngram_size = 0
    generation.max_new_tokens = config["max_new_tokens"]
    generation.use_cache = True
    generation.pad_token_id = tokenizer.pad_token_id
    eos = generation.eos_token_id
    generation.eos_token_id = sorted(set((eos if isinstance(eos, list) else [eos]) + [tokenizer.eos_token_id]) - {None})
    with (stage / "deployment.json").open("x") as stream:
        json.dump({"generation_config": generation.to_dict(), "model_class": type(model).__name__}, stream, indent=2)

    class BudgetStop(StoppingCriteria):
        def __init__(self):
            self.deadline = time.monotonic() + config["request_timeout_seconds"]
            self.reason = None
        def __call__(self, input_ids, scores, **kwargs):
            if (root / "STOP").exists():
                self.reason = "stop_requested"
            elif time.monotonic() >= self.deadline:
                self.reason = "request_timeout"
            return torch.full((input_ids.shape[0],), self.reason is not None, dtype=torch.bool, device=input_ids.device)

    jobs = []
    for index, query in enumerate(config["queries"]):
        conditions = config["conditions"]
        conditions = conditions[index % len(conditions):] + conditions[:index % len(conditions)]
        for condition in conditions:
            jobs.append((query, condition))
    results = []
    for start in range(0, len(jobs), config["batch_size"]):
        if (root / "STOP").exists():
            raise RuntimeError("STOP requested")
        batch = jobs[start:start + config["batch_size"]]
        prompts = []
        for query, condition in batch:
            messages = copy.deepcopy(query["messages"] if condition != "isolated_card" else query["messages"][:1])
            target = ("This is one requested compute decision, not the whole workflow. "
                      "Return exactly one compute action for this target, preserving its ordered input handles: "
                      + json.dumps(query["target"], sort_keys=True))
            if condition != "full_target":
                target += "\nObserved input/policy card (no operation selected): " + json.dumps(query["card"], sort_keys=True)
            messages.append({"role": "user", "content": target})
            prompts.append(tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False))
        inputs = tokenizer(prompts, padding=True, return_tensors="pt", add_special_tokens=False, truncation=False).to("cuda:0")
        lengths = inputs["attention_mask"].sum(dim=1).tolist()
        if max(lengths) + config["max_new_tokens"] > config["context_tokens"]:
            raise RuntimeError("Context preflight rejected probe batch; no model call forwarded")
        stop = BudgetStop()
        torch.cuda.synchronize()
        begun = time.time()
        with torch.inference_mode():
            outputs = model.generate(**inputs, generation_config=generation, stopping_criteria=StoppingCriteriaList([stop]))
        torch.cuda.synchronize()
        finished = time.time()
        append(stage / "service-batches.jsonl", {"batch_index": start // config["batch_size"], "started_epoch": begun,
               "finished_epoch": finished, "provider_seconds": finished - begun, "requests": len(batch),
               "input_lengths": lengths, "allocated_gpu_bytes": torch.cuda.max_memory_allocated()})
        ids_batch = outputs[:, inputs["input_ids"].shape[1]:].tolist()
        for (query, condition), ids, prompt, tokens in zip(batch, ids_batch, prompts, lengths):
            count = next((i + 1 for i, token in enumerate(ids) if token in generation.eos_token_id), len(ids))
            kept = ids[:count]
            payload = kept[:-1] if kept and kept[-1] in generation.eos_token_id else kept
            raw = tokenizer.decode(payload, skip_special_tokens=False)
            category = stop.reason
            action = None
            if category is None:
                try:
                    action = json.loads(raw)
                except json.JSONDecodeError:
                    category = "json_parse_failed"
                else:
                    if not Draft202012Validator(ACTION_SCHEMA).is_valid(action):
                        category = "schema_validation_failed"
            valid_compute = category is None and action["name"] == "compute"
            operator_correct = valid_compute and action["arguments"]["operation"] == query["gold_operation"]
            target_correct = valid_compute and all(action["arguments"][key] == query["target"][key] for key in ("node", "inputs"))
            result = {"query_id": query["query_id"], "task_id": query["task_id"], "condition": condition,
                      "model": model_name, "after_update": query["after_update"], "category": category,
                      "schema_valid": category is None, "operator_correct": operator_correct,
                      "target_correct": target_correct, "decision_correct": operator_correct and target_correct,
                      "raw_output": raw, "raw_token_ids": kept, "action": action,
                      "prompt_tokens": tokens, "completion_tokens": len(kept), "context_preflight": "allow",
                      "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                      "request_started_epoch": begun, "request_finished_epoch": finished,
                      "provider_latency_seconds": finished - begun, "actual_tool_executions": 0,
                      "cloud_api_usd": 0, "local_gpu_usd": None}
            results.append(result)
            append(stage / "raw-decisions.jsonl", result)
    groups = defaultdict(list)
    for result in results:
        groups[(result["condition"], result["after_update"])].append(result)
    summary = [{"condition": key[0], "after_update": key[1], "n": len(rows),
                "schema_valid": sum(r["schema_valid"] for r in rows),
                "operator_correct": sum(r["operator_correct"] for r in rows),
                "target_correct": sum(r["target_correct"] for r in rows),
                "decision_correct": sum(r["decision_correct"] for r in rows),
                "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
                "completion_tokens": sum(r["completion_tokens"] for r in rows),
                "categories": dict(Counter(r["category"] for r in rows))} for key, rows in sorted(groups.items())]
    with (stage / "complete.json").open("x") as stream:
        json.dump({"expected_requests": len(jobs), "finished_epoch": time.time(), "groups": summary}, stream, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    run(args.root, args.config, args.model)
