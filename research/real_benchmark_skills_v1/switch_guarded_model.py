"""Switch only this study's idle model service; never change the AutoDL instance lifecycle."""
import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path("/root/autodl-tmp/real-benchmark-skills-v1")


def main(model):
    lock = json.loads((ROOT / "models.lock.json").read_bytes())[model]
    state = json.loads((ROOT / "evidence/ranged-model-materialization.json").read_bytes())
    verified = {(f["model"], f["file"], f["sha256"]) for f in state["verified_files"]}
    if any((model, name, info["sha256"]) not in verified for name, info in lock["files"].items()):
        raise RuntimeError("Model byte verification is incomplete")
    receipt = ROOT / "evidence/model-service.json"
    if receipt.exists():
        previous = json.loads(receipt.read_bytes())
        command_path = Path(f"/proc/{previous['pid']}/cmdline")
        if command_path.exists() and command_path.read_bytes():
            assert str(ROOT / "guarded_transformers_server.py").encode() in command_path.read_bytes()
            try:
                with urllib.request.urlopen("http://127.0.0.1:18000/study/status", timeout=3) as response:
                    status = json.load(response)
                if status["pending_requests"] or status["running_generations"]:
                    raise RuntimeError("Model service is busy; wait before switching")
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
            os.kill(previous["pid"], signal.SIGTERM)
            for _ in range(100):
                if not command_path.exists() or not command_path.read_bytes():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Study service did not exit")
        with (ROOT / "evidence/model-service-history.jsonl").open("a") as output:
            output.write(json.dumps(previous) + "\n")
    for _ in range(50):
        with socket.socket() as probe:
            occupied = probe.connect_ex(("127.0.0.1", 18000)) == 0
        if not occupied:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Study port remains occupied")
    env = os.environ.copy()
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false",
               PYTHONPATH="/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/lib/python3.12/site-packages")
    python = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/inference/bin/python"
    script = ROOT / "guarded_transformers_server.py"
    argv = [python, str(script), "--model", model]
    epoch = time.time()
    log_path = ROOT / "logs" / f"{model}-transformers-{int(epoch)}.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    result = {"pid": process.pid, "model": model, "backend": "transformers-5.19.0", "epoch": epoch,
              "argv": argv, "revision": lock["revision"], "status": "starting", "log": str(log_path),
              "service_source_sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["Qwen3.5-4B", "Qwen3.5-9B"], required=True)
    main(parser.parse_args().model)
