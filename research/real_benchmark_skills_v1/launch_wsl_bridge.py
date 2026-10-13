import json
import subprocess
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
script = Path("/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner/research/real_benchmark_skills_v1/model_bridge.py")
argv = [str(root / "venv/bin/python"), str(script), "--credentials",
        "/mnt/d/Codes/infra-aware-mas-new/device_info.txt", "--known-hosts",
        "/mnt/c/Users/38058/.ssh/known_hosts"]
with (root / "logs/model-bridge.log").open("w") as log:
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
(root / "bridge.pid").write_text(str(process.pid))
print(json.dumps({"pid": process.pid, "log": str(root / "logs/model-bridge.log")}))
