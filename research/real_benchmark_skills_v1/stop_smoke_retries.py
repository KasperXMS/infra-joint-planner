"""Stop only infrastructure-smoke attempts after detecting default rollout retries."""
import json
import os
import signal
import subprocess
from pathlib import Path

root = Path("/root/skillsbench-local-20261013")
stopped = []
for process in Path("/proc").iterdir():
    if not process.name.isdigit():
        continue
    try:
        argv = (process / "cmdline").read_bytes().split(b"\0")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(b"bench_with_frozen_openhands.py" in arg for arg in argv) and any(
            arg.startswith(str(root / "jobs/agent-smoke").encode()) for arg in argv):
        os.kill(int(process.name), signal.SIGTERM)
        stopped.append(int(process.name))
env = os.environ.copy()
env.update(DOCKER_HOST=f"unix://{root}/run/docker.sock", DOCKER_CONFIG=str(root / "docker-config"))
docker = str(root / "bin/docker")
ids = subprocess.check_output([docker, "ps", "-q", "--filter", "label=benchflow.owned=true"], env=env, text=True).split()
containers = []
for container in ids:
    details = json.loads(subprocess.check_output([docker, "inspect", container], env=env, text=True))[0]
    project = details["Config"]["Labels"].get("com.docker.compose.project", "")
    if project.startswith("dialogue-parser__"):
        subprocess.run([docker, "stop", "--time", "5", container], env=env, check=True, capture_output=True)
        containers.append(container)
print(json.dumps({"stopped_smoke_runners": stopped, "stopped_smoke_containers": containers,
                  "reason": "BenchFlow rollout retries default to two; switch to explicit max_retries=0 config before formal cells."}))
