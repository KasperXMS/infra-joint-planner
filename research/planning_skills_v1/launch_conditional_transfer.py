"""Predeclared next-study trigger, GPU-wise handoff, no model/outcome cherry-picking."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from runtime_guard import append, identity, register


def trigger(rows):
    successes = Counter()
    totals = Counter()
    for row in rows:
        totals[row["condition"]] += 1
        successes[row["condition"]] += int(row["success"])
    n = totals["binding_system"]
    if not n or any(totals[c] != n for c in ("unbound_system", "static_system")):
        raise RuntimeError("Missing matched primary groups")
    joined_gap = abs(successes["binding_system"] - successes["unbound_system"])
    runtime_gain = max(successes["binding_system"], successes["unbound_system"]) - successes["static_system"]
    return joined_gap * 10 >= n or runtime_gain * 10 >= n, {"n_per_condition": n, "success_counts": dict(successes),
                                                          "absolute_joined_unjoined_gap": joined_gap / n,
                                                          "best_runtime_minus_static": runtime_gain / n}


def primary_worker_live(root, model):
    starts = [json.loads(line) for line in (root / "administration.jsonl").read_text().splitlines()]
    start = next(row for row in reversed(starts) if row.get("event") == "experiment_started"
                 and row.get("experiment_id") == "heldout-binding-v1" and row.get("model") == model)
    pid = start["pid"]
    owned = [json.loads(line) for line in (root / "owned-processes.jsonl").read_text().splitlines()]
    owner = next(row for row in reversed(owned) if row["pid"] == pid and row.get("process_group"))
    try:
        if identity(pid) != {k: owner[k] for k in ("pid", "start_ticks")}:
            return False
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def main(root):
    register(root, "conditional_structural_transfer_supervisor")
    config_path = root / "configs/structural-transfer-v1.json"
    config = json.loads(config_path.read_text())
    with (root / "structural-transfer-v1-launch-policy.json").open("x") as stream:
        json.dump({"epoch": time.time(), "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                   "policy": config["launch_policy"], "controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, stream, indent=2)
    assessed, eligible, running, finished, frozen = {}, False, {}, set(), set()
    stage = root / "results/structural-transfer-v1"
    while True:
        if (root / "SYSTEM_ISSUE").exists():
            (root / "STOP").touch(exist_ok=True)
        if (root / "STOP").exists():
            raise SystemExit("System integrity/STOP: no automatic reruns")
        for model in config["models"]:
            primary = root / "results/heldout-binding-v1" / model
            if model not in assessed and (primary / "complete.json").exists():
                rows = [json.loads(line) for line in (primary / "results.jsonl").read_text().splitlines()]
                primary_config = json.loads((primary / "frozen-manifest.json").read_text())["config"]
                expected = {t["task_id"] + "__" + c for t in primary_config["tasks"] for c in primary_config["conditions"]}
                if len(rows) != 252 or {r["episode_id"] for r in rows} != expected:
                    raise RuntimeError("Incomplete/duplicate primary model results")
                enabled, evidence = trigger(rows)
                assessed[model] = evidence
                eligible |= enabled
                append(root / "administration.jsonl", {"epoch": time.time(), "event": "conditional_transfer_assessed", "model": model, "eligible": enabled, **evidence})
        if len(assessed) == len(config["models"]) and not eligible:
            with (root / "structural-transfer-v1-not-launched.json").open("x") as stream:
                json.dump({"epoch": time.time(), "reason": "Neither primary model met the frozen information-value trigger", "evidence": assessed}, stream, indent=2)
            return
        for gpu, model in enumerate(config["models"]):
            if not eligible or model not in assessed or model in running or model in finished or primary_worker_live(root, model):
                continue
            memory = subprocess.check_output(["nvidia-smi", "--id", str(gpu), "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
            if int(memory.strip()) > 512:
                continue  # Wait for original CUDA context release; never touch other processes.
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                       OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false", HF_HOME=str(root / "cache/huggingface"))
            log = (root / f"structural-transfer-v1-{model}.log").open("ab")
            process = subprocess.Popen([str(root / ".venv/bin/python"), str(root / "code/run_transfer_model.py"),
                                        "--root", str(root), "--config", str(config_path), "--model", model],
                                       stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            append(root / "owned-processes.jsonl", {**identity(process.pid), "purpose": f"structural_transfer_{model}", "process_group": True})
            append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_started", "experiment_id": "structural-transfer-v1", "model": model, "gpu": gpu, "pid": process.pid})
            running[model] = process
        for model, process in list(running.items()):
            manifest = stage / model / "frozen-manifest.json"
            if model not in frozen and manifest.exists():
                try:
                    expected = json.loads(manifest.read_text())["source_sha256"]
                except json.JSONDecodeError:
                    continue  # Writer may have just created its manifest; no restart.
                shutil.copytree(root / "code", stage / model / "frozen-source", ignore=shutil.ignore_patterns("__pycache__"))
                for name, sha in expected.items():
                    if hashlib.sha256((stage / model / "frozen-source" / name).read_bytes()).hexdigest() != sha:
                        raise RuntimeError("Transfer source changed during launch")
                frozen.add(model)
            code = process.poll()
            if code is not None:
                append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_exited", "experiment_id": "structural-transfer-v1", "model": model, "returncode": code})
                if code:
                    (root / "SYSTEM_ISSUE").touch()
                    (root / "STOP").touch()
                    raise SystemExit("Transfer worker system failure; no rerun")
                finished.add(model)
                del running[model]
        if len(finished) == len(config["models"]):
            output = stage / "analysis"
            output.mkdir(parents=True, exist_ok=True)
            subprocess.run([str(root / ".venv/bin/python"), str(root / "code/analyze_transfer.py"), "--root", str(stage), "--output", str(output)], check=True)
            with (output / "postprocess-complete.json").open("x") as stream:
                json.dump({"epoch": time.time(), "status": "pass", "launch_evidence": assessed}, stream, indent=2)
            return
        time.sleep(20)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    args = p.parse_args()
    try:
        main(args.root)
    except Exception:
        (args.root / "SYSTEM_ISSUE").touch(exist_ok=True)
        (args.root / "STOP").touch(exist_ok=True)
        raise
