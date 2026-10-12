"""One launch receipt per experiment, exclusive GPUs, no automatic reruns."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from runtime_guard import append, identity, register

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--config", type=Path, required=True)
args = parser.parse_args()
root, config = args.root, json.loads(args.config.read_text())
register(root, f"supervisor_{config['experiment_id']}")
with (root / f"{config['experiment_id']}-launch.json").open("x") as stream:
    json.dump({"epoch": time.time(), "supervisor": identity(os.getpid()), "config": str(args.config)}, stream)
models = {model: str(i) for i, model in enumerate(config["models"])}
running = {}
failed = False
while models or running:
    if (root / "STOP").exists():
        raise SystemExit("STOP requested")
    for model, gpu in list(models.items()):
        if not (root / f"{model}-identity.json").exists():
            continue
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                   OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false", HF_HOME=str(root / "cache/huggingface"))
        log = (root / f"{config['experiment_id']}-{model}.log").open("ab")
        process = subprocess.Popen([str(root / ".venv/bin/python"), str(root / "code" / config.get("runner", "run_model.py")),
                                    "--root", str(root), "--config", str(args.config), "--model", model],
                                   env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        append(root / "owned-processes.jsonl", {**identity(process.pid), "purpose": f"inference_group_{model}",
                                               "process_group": True})
        append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_started",
                                               "experiment_id": config["experiment_id"], "model": model,
                                               "gpu": gpu, "pid": process.pid})
        running[model] = process
        del models[model]
    for model, process in list(running.items()):
        code = process.poll()
        if code is not None:
            append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_exited",
                                                   "experiment_id": config["experiment_id"], "model": model,
                                                   "returncode": code})
            if code:
                (root / "SYSTEM_ISSUE").touch()
                failed = True
            del running[model]
    time.sleep(10)
raise SystemExit(1 if failed else 0)
