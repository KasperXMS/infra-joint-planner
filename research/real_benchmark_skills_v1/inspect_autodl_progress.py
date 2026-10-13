import json
import subprocess
from pathlib import Path

root = Path("/root/autodl-tmp/real-benchmark-skills-v1")
result = {}
for name in ("evidence/ranged-model-materialization.json", "evidence/large-wheel-materialization.json", "evidence/inference-environment-repair.json", "logs/ranged-models-resumed.log", "logs/large-wheels-small-ranges.log", "logs/wheel-install-0.log", "logs/wheel-install-1.log", "logs/wheel-install-2.log"):
    path = root / name
    if path.exists():
        if path.suffix == ".json":
            state = json.loads(path.read_bytes())
            result[name] = {k: v for k, v in state.items() if k not in ("verified_files", "verified_wheels")}
            for collection in ("verified_files", "verified_wheels"):
                if collection in state:
                    result[name][collection + "_count"] = len(state[collection])
                    result[name][collection + "_bytes"] = sum(f["bytes"] for f in state[collection])
        else:
            result[name] = path.read_text(errors="replace")[-700:]
result["active_chunks"] = [{"file": str(p.relative_to(root)), "completed_chunks": len(json.loads(p.read_bytes()))}
                            for p in root.glob("models/*/*.parts.json")]
result["wheel_chunks"] = [{"file": p.name, "completed_chunks": len(json.loads(p.read_bytes()))}
                          for p in (root / "wheelhouse").glob("*.parts-*.json")]
result["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout
result["process_names"] = subprocess.run(["ps", "-eo", "pid,ppid,etime,comm"], capture_output=True, text=True).stdout
print(json.dumps(result))
