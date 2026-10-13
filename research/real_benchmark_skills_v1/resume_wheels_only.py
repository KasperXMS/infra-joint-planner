import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
pid = int((root / "large-wheels.pid").read_text())
command_path = Path(f"/proc/{pid}/cmdline")
if command_path.exists() and command_path.read_bytes():
    if str(root / "materialize_large_wheels.py").encode() not in command_path.read_bytes():
        raise RuntimeError("Unrelated PID")
    os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        if not command_path.exists() or not command_path.read_bytes():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Old wheel downloader still running")
with (root / "logs/large-wheels-small-ranges.log").open("w") as log:
    process = subprocess.Popen([sys.executable, str(root / "materialize_large_wheels.py")],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "large-wheels.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "package_range_bytes": 1048576, "max_requests": 64,
                  "reason": "Package endpoints are slow per stream; smaller resumable chunks retain the same full-file hashes."}))
