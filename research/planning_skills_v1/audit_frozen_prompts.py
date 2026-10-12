"""One post-batch CPU-only audit: exact prompts/tokens/observation-only support."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from microbench import BASE_PROMPT, Environment, Task, task_text
from runtime_binding import fact_inventory, structures
from skills import STATIC, support


def audit(root, output):
    from transformers import AutoTokenizer
    counts = Counter()
    per_model = {}
    for manifest_path in sorted(root.glob("*/frozen-manifest.json")):
        stage = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        config = manifest["config"]
        tokenizer = AutoTokenizer.from_pretrained(manifest["model_identity"]["local_path"],
                                                   local_files_only=True, padding_side="left")
        deployment = json.loads((stage / "deployment.json").read_text())
        stops = set(deployment["generation_config"]["eos_token_id"])
        model_counts = Counter()
        for started_path in sorted(stage.glob("episodes/*/started.json")):
            started = json.loads(started_path.read_text())
            env = Environment(Task(**started["task"]))
            history = []
            for line in (started_path.parent / "trace.jsonl").read_text().splitlines():
                record = json.loads(line)
                text, metadata = support(started["condition"], env, tokenizer=tokenizer)
                system_text = STATIC if metadata.get("system_skill") else text if metadata.get("placement") == "system" else ""
                messages = [{"role": "system", "content": BASE_PROMPT + ("\n" + system_text if system_text else "")},
                            {"role": "user", "content": task_text(env.task)}] + history
                if text and metadata.get("placement") != "system":
                    messages.append({"role": "user", "content": text})
                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
                tokens = len(tokenizer.encode(prompt, add_special_tokens=False))
                assert tokens == record["prompt_tokens"], (started_path, record.get("turn"), "prompt tokens")
                if record["event"] == "context_preflight_rejected":
                    assert tokens + config["max_new_tokens"] > config["context_tokens"]
                    model_counts["context_rejections"] += 1
                    continue
                assert hashlib.sha256(prompt.encode()).hexdigest() == record["prompt_sha256"]
                assert tokens + config["max_new_tokens"] <= config["context_tokens"]
                for key, value in metadata.items():
                    assert record[key] == value, (started_path, key)
                if started["condition"] in ("binding_system", "unbound_system"):
                    joined, unjoined = structures(env)
                    assert fact_inventory(joined, True) == fact_inventory(unjoined, False)
                    model_counts["matched_fact_inventories"] += 1
                ids = record["raw_token_ids"]
                payload = ids[:-1] if ids and ids[-1] in stops else ids
                assert tokenizer.decode(payload, skip_special_tokens=False) == record["raw_output"]
                model_counts["exact_prompt_token_output_checks"] += 1
                if record["event"] == "inference_budget_rejected":
                    assert not record["action_executed"]
                    continue
                observation, category = env.step(record["raw_output"])
                assert observation == record["observation"] and category == record["category"]
                history += [{"role": "assistant", "content": record["raw_output"]},
                            {"role": "user", "content": "TOOL_RESULT=" + json.dumps(observation, sort_keys=True)}]
            model_counts["episodes"] += 1
        per_model[stage.name] = dict(model_counts)
        counts.update(model_counts)
    receipt = {"status": "pass", "counts": dict(counts), "models": per_model,
               "note": "No model inference. Full prompt SHA/tokenization, raw output decoding, support facts and event replay checked once after batch."}
    with output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    audit(args.root, args.output)
