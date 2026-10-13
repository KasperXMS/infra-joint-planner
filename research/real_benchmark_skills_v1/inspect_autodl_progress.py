import json
import subprocess
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
result = {}
for name in ("evidence/preparation.json", "evidence/ranged-model-materialization.json", "logs/preparation.log", "logs/ranged-models.log", "logs/install-2.log", "logs/install-3.log"):
    path = root / name
    if path.exists():
        result[name] = path.read_text(errors="replace")[-1500:]
result["models"] = [{"file": str(p.relative_to(root)), "bytes": p.stat().st_size} for p in (root / "models").rglob("*") if p.is_file()]
result["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout
result["process_names"] = subprocess.run(["ps", "-eo", "pid,ppid,etime,comm"], capture_output=True, text=True).stdout
print(json.dumps(result))
