"""Resume verified artifacts after accepting full HTTP 200 for single-chunk files."""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
started = []
for stem, script in (("ranged-models", "materialize_models_ranged.py"), ("large-wheels", "materialize_large_wheels.py")):
    pid_path = root / (stem + ".pid")
    if pid_path.exists():
        pid = int(pid_path.read_text())
        command_path = Path(f"/proc/{pid}/cmdline")
        if command_path.exists() and command_path.read_bytes():
            if str(root / script).encode() not in command_path.read_bytes():
                raise RuntimeError("Unrelated PID; refusing to stop it")
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):
                if not command_path.exists() or not command_path.read_bytes():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Previous downloader did not exit")
    evidence_name = "ranged-model-materialization.json" if stem == "ranged-models" else "large-wheel-materialization.json"
    evidence = root / "evidence" / evidence_name
    if evidence.exists():
        shutil.copy2(evidence, evidence.with_name(evidence.stem + f"-attempt-{int(time.time())}.json"))
    log_path = root / "logs" / (stem + "-resumed.log")
    with log_path.open("w") as log:
        process = subprocess.Popen([sys.executable, str(root / script)], stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, start_new_session=True)
    pid_path.write_text(str(process.pid))
    started.append({"job": stem, "pid": process.pid})
print(json.dumps({"started": started}), flush=True)
