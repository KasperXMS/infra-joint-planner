"""One exclusive GPU, real unmasked BF16 generation, batched active workflows.

Raw tokens/actions are preserved. No native-provider tool parser, constrained
decoding, automatic action repair, reference action selection, or hidden LLM.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from microbench import BASE_PROMPT, Environment, Task, digest, task_text
from runtime_guard import append, register
from skills import STATIC, support


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path, config_path: Path, model_name: str):
    import torch
    import transformers
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    register(root, f"inference_{model_name}")
    config = json.loads(config_path.read_text())
    stage = root / "results" / config["experiment_id"] / model_name
    stage.mkdir(parents=True, exist_ok=True)
    manifest_path = stage / "frozen-manifest.json"
    if manifest_path.exists():
        raise RuntimeError("Existing experiment namespace: do not rerun or overwrite; inspect checkpoint first")
    identity = json.loads((root / f"{model_name}-identity.json").read_text())
    source_files = {p.name: file_hash(p) for p in Path(__file__).parent.glob("*.py")}
    write_json(manifest_path, {"config": config, "config_sha256": file_hash(config_path),
                              "source_sha256": source_files, "model_identity": identity,
                              "torch": torch.__version__, "transformers": transformers.__version__,
                              "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                              "backend": "transformers_direct", "dtype": "bfloat16", "quantization": None,
                              "constrained_decoding": False, "thinking": False,
                              "base_prompt_sha256": digest(BASE_PROMPT), "static_skill_sha256": digest(STATIC),
                              "started_epoch": time.time()})
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    torch.manual_seed(config["seed"])
    random.seed(config["seed"])
    model_path = identity["local_path"]
    begun = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, padding_side="left")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True,
                                                      dtype=torch.bfloat16, device_map={"": "cuda:0"},
                                                      attn_implementation="sdpa")
    model.eval()
    generation = copy.deepcopy(model.generation_config)
    generation.do_sample = False
    generation.temperature = None
    generation.top_p = None
    generation.top_k = None
    generation.max_new_tokens = config["max_new_tokens"]
    generation.use_cache = True
    generation.pad_token_id = tokenizer.pad_token_id
    write_json(stage / "deployment.json", {"load_seconds": time.time() - begun,
               "generation_config": generation.to_dict(), "model_class": type(model).__name__,
               "model_config": model.config.to_dict(),
               "skill_tokens": len(tokenizer.encode(STATIC)),
               "gpu_name": torch.cuda.get_device_name(0), "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory})
    specs = []
    # Task-major, rotated condition order was frozen before inference; avoids always
    # giving one condition the cold-start position. No accuracy-based reordering.
    for index, task_spec in enumerate(config["tasks"]):
        conditions = config["conditions"]
        rotated = conditions[index % len(conditions):] + conditions[:index % len(conditions)]
        for condition in rotated:
            specs.append((task_spec, condition))
    active = []
    next_index = 0
    batch_index = 0

    def admit():
        nonlocal next_index
        while len(active) < config["batch_size"] and next_index < len(specs):
            task_spec, condition = specs[next_index]
            task = Task(**task_spec)
            episode_id = task.task_id + "__" + condition
            state = {"id": episode_id, "env": Environment(task), "condition": condition,
                     "history": [], "started": time.time(), "turns": 0, "prompt_tokens": 0,
                     "completion_tokens": 0, "errors": Counter(), "tool_counts": Counter(),
                     "provider_latency_sum": 0.0, "tool_seconds": 0.0, "finish_reason": None}
            write_json(stage / "episodes" / episode_id / "started.json",
                       {"task": asdict(task), "condition": condition, "started_epoch": state["started"]})
            active.append(state)
            next_index += 1

    def finish(state):
        env = state["env"]
        directory = stage / "episodes" / state["id"]
        result = {"episode_id": state["id"], "model": model_name, "condition": state["condition"],
                  "task_id": env.task.task_id, "split": env.task.split, "depth": env.task.depth,
                  "width": env.task.width, "refresh": env.task.refresh, "transient": env.task.transient,
                  "template": env.task.template, "completion": env.completed, "success": env.success,
                  "turns": state["turns"], "prompt_tokens": state["prompt_tokens"],
                  "completion_tokens": state["completion_tokens"], "error_counts": dict(state["errors"]),
                  "tool_counts": dict(state["tool_counts"]), "tool_seconds": state["tool_seconds"],
                  "provider_latency_sum": state["provider_latency_sum"],
                  "e2e_seconds": time.time() - state["started"], "finish_reason": state["finish_reason"],
                  "submitted_value": env.submitted_value, "source_update_observed": env.changed,
                  "cloud_api_usd": 0.0, "cloud_calls": 0, "local_gpu_usd": None,
                  "cost_note": "Lease CNY recorded at whole-instance level; request waiting is not GPU inference time.",
                  "trace_sha256": file_hash(directory / "trace.jsonl") if (directory / "trace.jsonl").exists() else None}
        write_json(directory / "result.json", result)
        append(stage / "results.jsonl", result)

    admit()
    while active:
        if (root / "STOP").exists():
            raise RuntimeError("STOP requested; no further model calls")
        candidates, prompts, support_metadata = [], [], []
        for state in active:
            if time.time() - state["started"] > config["task_timeout_seconds"]:
                state["finish_reason"] = "task_timeout"
                continue
            text, metadata = support(state["condition"], state["env"])
            messages = [{"role": "system", "content": BASE_PROMPT},
                        {"role": "user", "content": task_text(state["env"].task)}]
            messages += state["history"]
            if text:
                messages.append({"role": "user", "content": text})
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                    enable_thinking=False)
            token_count = len(tokenizer.encode(prompt, add_special_tokens=False))
            if token_count + config["max_new_tokens"] > config["context_tokens"]:
                state["errors"]["context_preflight_rejected"] += 1
                state["finish_reason"] = "context_preflight_rejected"
                append(stage / "episodes" / state["id"] / "trace.jsonl",
                       {"event": "context_preflight_rejected", "prompt_tokens": token_count,
                        "reserved_output_tokens": config["max_new_tokens"], "context_tokens": config["context_tokens"]})
                continue
            candidates.append(state)
            prompts.append(prompt)
            support_metadata.append({**metadata, "support_tokens": len(tokenizer.encode(text, add_special_tokens=False)),
                                     "prompt_tokens": token_count})
        for state in list(active):
            if state["finish_reason"]:
                finish(state)
                active.remove(state)
        if not candidates:
            admit()
            continue
        inputs = tokenizer(prompts, padding=True, return_tensors="pt", add_special_tokens=False,
                           truncation=False).to("cuda:0")
        actual_counts = inputs["attention_mask"].sum(dim=1).tolist()
        if actual_counts != [m["prompt_tokens"] for m in support_metadata]:
            raise RuntimeError("Tokenizer/preflight context integrity mismatch")
        torch.cuda.synchronize()
        begun = time.time()
        with torch.inference_mode():
            outputs = model.generate(**inputs, generation_config=generation)
        torch.cuda.synchronize()
        finished = time.time()
        latency = finished - begun
        input_width = inputs["input_ids"].shape[1]
        generated = outputs[:, input_width:].tolist()
        eos = generation.eos_token_id
        stops = set(eos if isinstance(eos, list) else [eos])
        append(stage / "service-batches.jsonl", {"batch_index": batch_index, "started_epoch": begun,
               "finished_epoch": finished, "provider_seconds": latency, "requests": len(candidates),
               "episode_ids": [s["id"] for s in candidates], "input_lengths": actual_counts,
               "padded_input_width": input_width, "allocated_gpu_bytes": torch.cuda.max_memory_allocated()})
        for state, ids, metadata in zip(candidates, generated, support_metadata):
            count = next((i + 1 for i, token in enumerate(ids) if token in stops), len(ids))
            kept = ids[:count]
            payload = kept[:-1] if kept and kept[-1] in stops else kept
            raw = tokenizer.decode(payload, skip_special_tokens=False)
            state["turns"] += 1
            state["prompt_tokens"] += metadata["prompt_tokens"]
            state["completion_tokens"] += len(kept)
            state["provider_latency_sum"] += latency
            tool_start = time.perf_counter()
            observation, category = state["env"].step(raw)
            tool_seconds = time.perf_counter() - tool_start
            state["tool_seconds"] += tool_seconds
            if category:
                state["errors"][category] += 1
            event = state["env"].events[-1]
            if event["action"] and category not in ("schema_validation_failed", "json_parse_failed"):
                state["tool_counts"][event["action"]["name"]] += 1
            state["history"] += [{"role": "assistant", "content": raw},
                                  {"role": "user", "content": "TOOL_RESULT=" + json.dumps(observation, sort_keys=True)}]
            append(stage / "episodes" / state["id"] / "trace.jsonl", {
                "event": "inference", "turn": state["turns"], "batch_index": batch_index,
                "request_started_epoch": begun, "request_finished_epoch": finished,
                "provider_latency_seconds": latency, "queue_wait_seconds": 0.0,
                "queue_note": "Exclusive local synchronous batch; no provider queue. Admission waiting excluded.",
                "context_preflight": "allow", "raw_token_ids": kept, "raw_output": raw,
                "action": event["action"], "observation": observation, "category": category,
                "tool_seconds": tool_seconds, **metadata})
            if state["env"].completed:
                state["finish_reason"] = "completed" if state["env"].success else "wrong_answer"
            elif state["turns"] >= config["turn_budget"]:
                state["finish_reason"] = "turn_budget_exhausted"
            if state["finish_reason"]:
                finish(state)
                active.remove(state)
        batch_index += 1
        admit()
    write_json(stage / "complete.json", {"expected_episodes": len(specs), "finished_epoch": time.time(),
                                         "batches": batch_index})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    run(args.root, args.config, args.model)
