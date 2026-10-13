"""Replace stalled dependency acquisition, keeping the exact same hashed lock."""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
stopped = []
for process in Path("/proc").iterdir():
    if process.name.isdigit():
        try:
            command = (process / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if b"uv\0pip\0install\0" in command and str(root / "inference.lock.txt").encode() in command:
            os.kill(int(process.name), signal.SIGTERM)
            stopped.append(int(process.name))
with (root / "logs/large-wheels.log").open("w") as log:
    process = subprocess.Popen([sys.executable, str(root / "materialize_large_wheels.py")],
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "large-wheels.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "stopped_owned_installers": stopped,
                  "reason": "Large single-stream package downloads repeatedly stalled; preserve lock and fetch hashed official wheels with HTTP ranges."}))
