"""Stop only the study's package downloader after validating the official fallback API."""
import json
import os
import signal
import time
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
smoke = json.loads((root / "evidence/guarded-api-smoke.json").read_bytes())
assert smoke["pass"] is True
pid = int((root / "large-wheels.pid").read_text())
command = Path(f"/proc/{pid}/cmdline")
stopped = False
if command.exists() and command.read_bytes():
    assert str(root / "materialize_large_wheels.py").encode() in command.read_bytes()
    os.kill(pid, signal.SIGTERM)
    stopped = True
receipt = {"epoch": time.time(), "stopped_owned_downloader": stopped, "pid": pid,
           "reason": "Official Transformers BF16 tool API and context protection validated before formal cells; vLLM dependency acquisition remains incomplete.",
           "instance_lifecycle_action": False, "formal_agent_runs": 0}
(root / "evidence/backend-fallback-selection.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
