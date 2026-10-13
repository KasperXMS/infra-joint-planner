"""Start one verified BF16 model on AutoDL; refuse an occupied study port."""
import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")


def main(model):
    lock = json.loads((ROOT / "models.lock.json").read_bytes())[model]
    receipt = json.loads((ROOT / "evidence/ranged-model-materialization.json").read_bytes())
    verified = {(f["model"], f["file"], f["sha256"]) for f in receipt["verified_files"]}
    if any((model, name, info["sha256"]) not in verified for name, info in lock["files"].items()):
        raise RuntimeError("Model byte verification incomplete")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 18000)) == 0:
            raise RuntimeError("Study port occupied; do not replace another service")
    env = os.environ.copy()
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8",
               TOKENIZERS_PARALLELISM="false", VLLM_WORKER_MULTIPROC_METHOD="spawn")
    argv = [str(ROOT / "venv/bin/vllm"), "serve", str(ROOT / "models" / model),
            "--served-model-name", model, "--host", "127.0.0.1", "--port", "18000",
            "--dtype", "bfloat16", "--max-model-len", "32768", "--max-num-seqs", "4",
            "--gpu-memory-utilization", "0.85", "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_coder",
            "--reasoning-parser", "qwen3", "--generation-config", "vllm", "--api-key", "local-study"]
    with (ROOT / "logs" / (model + "-vllm.log")).open("w") as log:
        process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, start_new_session=True)
    result = {"model": model, "pid": process.pid, "started_epoch": time.time(), "argv": argv,
              "status": "starting", "revision": lock["revision"]}
    (ROOT / "evidence/model-service.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["Qwen3.5-4B", "Qwen3.5-9B"], required=True)
    main(parser.parse_args().model)
