"""Start a frozen development experiment once; wait for official byte manifests."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from runtime_guard import append, identity, register

root = Path("/root/autodl-tmp/xiaoming/planning-skills-research-v1/run-001")
register(root, "diagnostic_supervisor")
receipt = root / "diagnostic-launch.json"
with receipt.open("x") as stream:
    json.dump({"epoch": time.time(), "supervisor": identity(os.getpid()), "state": "waiting_for_weights"}, stream)
models = {"Qwen3.5-4B": "0", "Qwen3.5-9B": "1"}
running = {}
while models or running:
    if (root / "STOP").exists():
        raise SystemExit("STOP requested")
    for model, gpu in list(models.items()):
        if not (root / f"{model}-identity.json").exists():
            continue
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                   OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false", HF_HOME=str(root / "cache/huggingface"))
        log = (root / f"diagnostic-{model}.log").open("ab")
        process = subprocess.Popen([str(root / ".venv/bin/python"), str(root / "code/run_model.py"),
                                    "--root", str(root), "--config", str(root / "configs/diagnostic-v1.json"),
                                    "--model", model], env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        append(root / "owned-processes.jsonl", {**identity(process.pid), "purpose": f"inference_group_{model}",
                                               "process_group": True})
        append(root / "administration.jsonl", {"epoch": time.time(), "event": "diagnostic_started", "model": model,
                                               "gpu": gpu, "pid": process.pid})
        running[model] = process
        del models[model]
    for model, process in list(running.items()):
        code = process.poll()
        if code is not None:
            append(root / "administration.jsonl", {"epoch": time.time(), "event": "diagnostic_exited",
                                                   "model": model, "returncode": code})
            if code:
                (root / "SYSTEM_ISSUE").touch()
            del running[model]
    time.sleep(10)
