"""Launch once in an isolated namespace; receipts prevent accidental duplicates."""
import json
import subprocess
import sys
import time
from pathlib import Path

from runtime_guard import append, identity

root = Path("/root/autodl-tmp/xiaoming/planning-skills-research-v1/run-001")
backup = Path("/root/autodl-fs/xiaoming/planning-skills-research-v1")
root.mkdir(parents=True, exist_ok=True)
backup.mkdir(parents=True, exist_ok=True)
receipt = root / "preparation-launch.json"
if receipt.exists():
    print(receipt.read_text())
    raise SystemExit("Already launched; inspect processes and logs rather than duplicate work")
guard_log = (root / "guard.log").open("ab")
guard = subprocess.Popen([sys.executable, str(root / "code/runtime_guard.py"), "--root", str(root),
                          "--backup", str(backup)], stdout=guard_log, stderr=subprocess.STDOUT,
                         start_new_session=True)
time.sleep(1)
if guard.poll() is not None:
    raise SystemExit("Resource guard failed to start")
log = (root / "preparation.log").open("ab")
prepare = subprocess.Popen(["bash", str(root / "code/bootstrap.sh")], stdout=log,
                           stderr=subprocess.STDOUT, start_new_session=True)
append(root / "owned-processes.jsonl", {**identity(prepare.pid), "purpose": "preparation",
                                       "process_group": True})
record = {"epoch": time.time(), "guard": identity(guard.pid), "preparation": identity(prepare.pid)}
with receipt.open("x") as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(record))
