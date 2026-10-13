import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
previous = int((root / "model-repair.pid").read_text())
command_file = Path(f"/proc/{previous}/cmdline")
if command_file.exists():
    command = command_file.read_bytes()
    if b"prepare_real_benchmark_inference_repair.py" not in command or b"--models-only" not in command:
        raise RuntimeError("Refusing to stop an unrelated process")
    os.kill(previous, signal.SIGTERM)
    for _ in range(20):
        if not command_file.exists() or not command_file.read_bytes():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Previous model downloader did not exit")
with (root / "logs/ranged-models.log").open("w") as log:
    process = subprocess.Popen([sys.executable, str(root / "materialize_models_ranged.py")],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "ranged-models.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "reason": "Use bounded resumable ranges for slow weight transfers; unchanged official file hashes."}))
