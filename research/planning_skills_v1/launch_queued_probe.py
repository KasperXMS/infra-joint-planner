"""Frozen follow-up probe, GPU-wise handoff after transfer; no outcome trigger."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from runtime_guard import append, identity, register


def transfer_worker_live(root, model):
    starts = [json.loads(line) for line in (root / "administration.jsonl").read_text().splitlines()]
    start = next(row for row in reversed(starts) if row.get("event") == "experiment_started"
                 and row.get("experiment_id") == "structural-transfer-v1" and row.get("model") == model)
    pid = start["pid"]
    owners = [json.loads(line) for line in (root / "owned-processes.jsonl").read_text().splitlines()]
    owner = next(row for row in reversed(owners) if row["pid"] == pid and row.get("process_group"))
    try:
        if identity(pid) != {k: owner[k] for k in ("pid", "start_ticks")}:
            return False
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def main(root, config_path):
    register(root, "decision_generalization_queue")
    source = Path(__file__).parent
    config = json.loads(config_path.read_text())
    assert config["experiment_id"] == "decision-generalization-v1"
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    with (root / "decision-generalization-v1-launch-policy.json").open("x") as stream:
        json.dump({"epoch": time.time(), "config_sha256": config_sha,
                   "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.py")},
                   "policy": "Run ALL frozen queries and three conditions on BOTH models, irrespective of primary/transfer success. Each model starts only after its transfer worker actually exits with complete.json present and releases CUDA. No per-query reruns or prompt/model changes. Single unified probe audit after both models finish."}, stream, indent=2)
    running, finished, frozen = {}, set(), set()
    stage = root / "results" / config["experiment_id"]
    while True:
        if (root / "SYSTEM_ISSUE").exists():
            (root / "STOP").touch(exist_ok=True)
        if (root / "STOP").exists():
            raise SystemExit("STOP/system integrity; no further probe requests")
        for gpu, model in enumerate(config["models"]):
            if model in running or model in finished:
                continue
            if transfer_worker_live(root, model):
                continue
            if not (root / "results/structural-transfer-v1" / model / "complete.json").exists():
                raise RuntimeError("Transfer worker disappeared without a complete result; never restart from observation timeout")
            memory = subprocess.check_output(["nvidia-smi", "--id", str(gpu), "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True)
            if int(memory.strip()) > 512:
                continue
            assert hashlib.sha256(config_path.read_bytes()).hexdigest() == config_sha
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                       OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false", HF_HOME=str(root / "cache/huggingface"))
            log = (root / f"decision-generalization-v1-{model}.log").open("ab")
            process = subprocess.Popen([str(root / ".venv/bin/python"), str(source / "run_decision_probe.py"),
                                        "--root", str(root), "--config", str(config_path), "--model", model],
                                       stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            append(root / "owned-processes.jsonl", {**identity(process.pid), "purpose": f"decision_generalization_{model}", "process_group": True})
            append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_started", "experiment_id": config["experiment_id"], "model": model, "gpu": gpu, "pid": process.pid})
            running[model] = process
        for model, process in list(running.items()):
            manifest_path = stage / model / "frozen-manifest.json"
            if model not in frozen and manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                except json.JSONDecodeError:
                    continue
                shutil.copytree(source, stage / model / "frozen-source", ignore=shutil.ignore_patterns("__pycache__"))
                for name, digest in manifest["source_sha256"].items():
                    assert hashlib.sha256((stage / model / "frozen-source" / name).read_bytes()).hexdigest() == digest
                assert manifest["config_sha256"] == config_sha
                frozen.add(model)
            code = process.poll()
            if code is not None:
                append(root / "administration.jsonl", {"epoch": time.time(), "event": "experiment_exited", "experiment_id": config["experiment_id"], "model": model, "returncode": code})
                if code:
                    raise RuntimeError("Probe worker system failure; no selective rerun")
                finished.add(model)
                del running[model]
        if len(finished) == len(config["models"]):
            output = stage / "analysis"
            with (root / "decision-generalization-v1-final-audit.log").open("ab") as log:
                subprocess.run([str(root / ".venv/bin/python"), str(source / "audit_generalization_probe.py"),
                                "--root", str(stage), "--config", str(config_path), "--output", str(output)],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            return
        time.sleep(20)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        main(args.root, args.config)
    except Exception:
        (args.root / "SYSTEM_ISSUE").touch(exist_ok=True)
        (args.root / "STOP").touch(exist_ok=True)
        raise
