"""Focused tokenizer/control checks; no model generation or ability gate."""
import argparse
import json
from pathlib import Path

from microbench import Environment, Task
from runtime_binding import fact_inventory, matched_texts, structures
from skills import support
from test_microbench import action, reference_execution

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
from transformers import AutoTokenizer
config = json.loads(args.config.read_text())
counts = {}
for model in config["models"]:
    identity = json.loads((args.root / f"{model}-identity.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(identity["local_path"], local_files_only=True)
    states = maximum = 0
    for task_spec in config["tasks"]:
        task = Task(**task_spec)
        env = Environment(task)
        def check():
            global states, maximum
            joined, unjoined = structures(env)
            assert fact_inventory(joined, True) == fact_inventory(unjoined, False)
            a, b, target = matched_texts(env, tokenizer)
            assert len(tokenizer.encode(a, add_special_tokens=False)) == target
            assert len(tokenizer.encode(b, add_special_tokens=False)) == target
            states += 1
            maximum = max(maximum, target)
        check()
        root_handle = reference_execution(env)
        check()
        obs = action(env, "verify", artifact=root_handle)
        if task.refresh:
            assert obs["error"] == "source_updated"
            check()
            root_handle = reference_execution(env)
            check()
            obs = action(env, "verify", artifact=root_handle)
        assert obs["status"] == "verified"
        terminal = [support(c, env, tokenizer)[0] for c in ("ledger_system", "binding_system", "unbound_system")]
        assert terminal[0] == terminal[1] == terminal[2]
        states += 1
    counts[model] = {"checked_states": states, "maximum_dynamic_support_tokens": maximum}
result = {"actual_model_inference_calls": 0, "tasks": len(config["tasks"]), "models": counts,
          "checks": ["same current facts/policies/repetition counts", "exact per-state token match",
                     "no hidden update regime in public task", "same observed terminal-state delivery"]}
target = args.output or args.root / "configs" / "heldout-control-check.json"
with target.open("x") as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
