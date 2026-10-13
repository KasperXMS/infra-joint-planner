"""Read-only infrastructure probe; no task execution or instance lifecycle actions."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def run(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        return {"argv": argv, "returncode": result.returncode,
                "stdout": result.stdout[-12000:], "stderr": result.stderr[-2000:]}
    except Exception as exc:
        return {"argv": argv, "error": type(exc).__name__, "detail": str(exc)}


result = {"epoch": time.time(), "tools": {name: shutil.which(name) for name in
          ("docker", "dockerd", "podman", "unshare", "bwrap", "runc", "containerd", "systemd-detect-virt")}}
result["checks"] = [run(argv) for argv in (
    ["id"], ["cat", "/proc/self/status"], ["cat", "/proc/self/cgroup"],
    ["findmnt", "-n", "-o", "TARGET,FSTYPE", "/sys/fs/cgroup"],
    ["unshare", "--user", "--map-root-user", "--mount", "true"],
    ["unshare", "--mount", "true"], ["docker", "info", "--format", "{{json .}}"],
    ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
    ["ps", "-eo", "comm="], ["ss", "-H", "-ltn"], ["uptime", "-s"],
)]
result["docker_socket_present"] = Path("/var/run/docker.sock").exists()
result["docker_env_present"] = {name: bool(os.environ.get(name)) for name in
                                ("DOCKER_HOST", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "DAYTONA_API_KEY")}
result["cloud_config_present"] = {name: (Path.home() / name).exists() for name in
                                  (".modal.toml", ".config/daytona/config.json")}
result["lifecycle_jobs"] = [run(["crontab", "-l"]), run(["systemctl", "list-timers", "--no-pager"])]
print(json.dumps(result, indent=2))
