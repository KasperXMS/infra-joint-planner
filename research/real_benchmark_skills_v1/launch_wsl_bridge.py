import json
import os
import signal
import subprocess
import time
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
if (root / "bridge.pid").exists():
    pid = int((root / "bridge.pid").read_text())
    command_path = Path(f"/proc/{pid}/cmdline")
    if command_path.exists() and command_path.read_bytes():
        if b"real_benchmark_skills_v1/model_bridge.py" not in command_path.read_bytes():
            raise RuntimeError("Unrelated bridge PID")
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            if not command_path.exists() or not command_path.read_bytes():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Old model bridge did not exit")
script = Path("/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1/model_bridge.py")
argv = [str(root / "venv/bin/python"), str(script), "--credentials",
        "/mnt/d/Codes/infra-aware-mas-new/device_info.txt", "--known-hosts",
        "/mnt/c/Users/38058/.ssh/known_hosts", "--backend", "transformers"]
with (root / "logs/model-bridge.log").open("w") as log:
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "bridge.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "log": str(root / "logs/model-bridge.log")}))
