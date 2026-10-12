"""Final CPU-only completion checks for the original development evidence.

Load each stage's actual frozen core modules. Never regenerate model outputs.
The already-audited placement stage is not repeated.
"""
import argparse
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root, stage_name, output):
    if output.exists():
        raise RuntimeError("Existing development check; never overwrite")
    stage = root / "results" / stage_name
    frozen = stage / "Qwen3.5-4B/frozen-source"
    # Actual historical modules precede current analysis utilities on sys.path.
    sys.path[:0] = [str(frozen), str(root / "code")]
    for model in ("Qwen3.5-4B", "Qwen3.5-9B"):
        manifest = json.loads((stage / model / "frozen-manifest.json").read_text())
        assert (stage / model / "complete.json").exists()
        for name, expected in manifest["source_sha256"].items():
            assert sha(stage / model / "frozen-source" / name) == expected
        for name in ("microbench.py", "skills.py"):
            assert sha(frozen / name) == manifest["source_sha256"][name]
    if stage_name == "diagnostic-v2":
        import audit_frozen_prompts as checker
        old_support = checker.support
        if "tokenizer" not in inspect.signature(old_support).parameters:
            # The historical function has no token-matched conditions; pass
            # precisely its original two arguments and preserve its outputs.
            checker.support = lambda condition, env, tokenizer=None: old_support(condition, env)
        checker.audit(stage, output)
        return
    if stage_name != "decision-context-probe-v1":
        raise RuntimeError("Only the declared legacy development stages are eligible")
    from transformers import AutoTokenizer
    from jsonschema import Draft202012Validator
    from microbench import ACTION_SCHEMA
    from audit_generalization_probe import prompt_messages
    config_path = root / "configs/decision-context-probe-v1.json"
    config = json.loads(config_path.read_text())
    queries = {q["query_id"]: q for q in config["queries"]}
    expected = {(q, c) for q in queries for c in config["conditions"]}
    for query in queries.values():
        match = re.fullmatch(r"Use (\w+) if the first input is greater than (-?\d+); otherwise use (\w+)\.", query["card"]["policy"])
        assert match
        first = query["card"]["ordered_inputs"][0]["value"]
        assert query["gold_operation"] == match.group(1 if first > int(match.group(2)) else 3)
    models = []
    for model in config["models"]:
        model_stage = stage / model
        manifest = json.loads((model_stage / "frozen-manifest.json").read_text())
        assert manifest["config_sha256"] == sha(config_path) and manifest["config"] == config
        tokenizer = AutoTokenizer.from_pretrained(manifest["model_identity"]["local_path"], local_files_only=True, padding_side="left")
        stops = set(json.loads((model_stage / "deployment.json").read_text())["generation_config"]["eos_token_id"])
        rows = [json.loads(line) for line in (model_stage / "raw-decisions.jsonl").read_text().splitlines()]
        assert len(rows) == len(expected) and {(r["query_id"], r["condition"]) for r in rows} == expected
        for row in rows:
            query = queries[row["query_id"]]
            prompt = tokenizer.apply_chat_template(prompt_messages(query, row["condition"]), tokenize=False, add_generation_prompt=True, enable_thinking=False)
            assert hashlib.sha256(prompt.encode()).hexdigest() == row["prompt_sha256"]
            assert len(tokenizer.encode(prompt, add_special_tokens=False)) == row["prompt_tokens"]
            assert row["prompt_tokens"] + config["max_new_tokens"] <= config["context_tokens"]
            ids = row["raw_token_ids"]
            payload = ids[:-1] if ids and ids[-1] in stops else ids
            assert tokenizer.decode(payload, skip_special_tokens=False) == row["raw_output"]
            assert len(ids) == row["completion_tokens"] <= config["max_new_tokens"]
            category, action = None, None
            if row["category"] in ("request_timeout", "stop_requested"):
                category = row["category"]
            else:
                try:
                    action = json.loads(row["raw_output"])
                except json.JSONDecodeError:
                    category = "json_parse_failed"
                else:
                    if not Draft202012Validator(ACTION_SCHEMA).is_valid(action):
                        category = "schema_validation_failed"
            valid = category is None and action["name"] == "compute"
            operation = bool(valid and action["arguments"]["operation"] == query["gold_operation"])
            target = bool(valid and all(action["arguments"][k] == query["target"][k] for k in ("node", "inputs")))
            assert (category, action, category is None, operation, target, operation and target) == (
                row["category"], row["action"], row["schema_valid"], row["operator_correct"], row["target_correct"], row["decision_correct"])
            assert row["actual_tool_executions"] == 0
        models.append({"model": model, "requests": len(rows), "raw_decisions_sha256": sha(model_stage / "raw-decisions.jsonl")})
    receipt = {"status": "pass", "stage": stage_name, "queries": len(queries), "requests": sum(m["requests"] for m in models),
               "models": models, "config_sha256": sha(config_path), "actual_model_directed_tool_executions": 0,
               "note": "Final once-only exact prompt/token/output/public-policy/schema/target audit; frozen historical core modules, no model inference."}
    with output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--stage", choices=("diagnostic-v2", "decision-context-probe-v1"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.root, args.stage, args.output)
