"""Launch the verified fallback path, preserving provisioning failures as evidence."""
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
model = "Qwen3.5-4B"
verified = json.loads((root / "evidence/ranged-model-materialization.json").read_bytes())["verified_files"]
lock = json.loads((root / "models.lock.json").read_bytes())[model]
seen = {(f["model"], f["file"], f["sha256"]) for f in verified}
assert all((model, name, info["sha256"]) in seen for name, info in lock["files"].items())
pid = int((root / "transformers-api-probe.pid").read_text())
command_path = Path(f"/proc/{pid}/cmdline")
if command_path.exists() and command_path.read_bytes():
    command = command_path.read_bytes()
    if b"transformers.cli.serve" not in command or str(root / "models" / model).encode() not in command:
        raise RuntimeError("Unrelated process; refuse to stop it")
    os.kill(pid, signal.SIGTERM)
with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 18000)) == 0:
        raise RuntimeError("Study service port already occupied")
env = os.environ.copy()
env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8", TOKENIZERS_PARALLELISM="false",
           PYTHONPATH="/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/project/lib/python3.12/site-packages")
python = "/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/venvs/inference/bin/python"
argv = [python, str(root / "guarded_transformers_server.py"), "--model", model]
with (root / "logs" / (model + "-transformers.log")).open("w") as log:
    process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
result = {"pid": process.pid, "model": model, "backend": "transformers-5.19.0", "epoch": time.time(),
          "argv": argv, "revision": lock["revision"], "status": "starting"}
(root / "evidence/model-service.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
