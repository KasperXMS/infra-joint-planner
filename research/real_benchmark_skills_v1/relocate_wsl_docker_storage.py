"""Place only this study's Docker data on a dedicated ext4 image on D:.

The original data directory is preserved. No distro relocation or global Docker
service change occurs. Requires the dedicated study daemon to be idle.
"""
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path("/root/skillsbench-local-20261013")
IMAGE = Path("/mnt/d/Codes/infra-aware-mas-new/.code-staging/skillsbench-docker-data.ext4")
VOLUME = ROOT / "docker-volume"
env = os.environ.copy()
env.update(PATH=str(ROOT / "bin") + ":" + env["PATH"], DOCKER_HOST=f"unix://{ROOT}/run/docker.sock",
           DOCKER_CONFIG=str(ROOT / "docker-config"))
docker = str(ROOT / "bin/docker")
if subprocess.check_output([docker, "ps", "-q"], env=env, text=True).strip():
    raise RuntimeError("Study containers are active; refuse storage migration")
VOLUME.mkdir(exist_ok=True)
if not IMAGE.exists():
    with IMAGE.open("wb") as output:
        output.truncate(96 * 1024**3)
    subprocess.run(["mkfs.ext4", "-F", "-L", "skillsbench-data", str(IMAGE)], check=True, capture_output=True)
if not os.path.ismount(VOLUME):
    subprocess.run(["mount", "-o", "loop", str(IMAGE), str(VOLUME)], check=True)
pid = int((ROOT / "run/dockerd.pid").read_text())
command = Path(f"/proc/{pid}/cmdline").read_bytes()
if str(ROOT / "bin/dockerd").encode() not in command or str(ROOT / "docker-data").encode() not in command:
    raise RuntimeError("Unexpected daemon; refuse to stop it")
os.kill(pid, signal.SIGTERM)
for _ in range(300):
    process = Path(f"/proc/{pid}")
    if not process.exists() or not (process / "cmdline").read_bytes():
        break
    time.sleep(0.1)
else:
    raise RuntimeError("Dedicated Docker daemon did not exit")
destination = VOLUME / "data"
if destination.exists():
    raise RuntimeError("Destination already exists; audit before resuming")
subprocess.run(["cp", "-a", str(ROOT / "docker-data"), str(destination)], check=True)
argv = [str(ROOT / "bin/dockerd"), "--host", env["DOCKER_HOST"], "--data-root", str(destination),
        "--exec-root", str(ROOT / "docker-exec"), "--pidfile", str(ROOT / "run/dockerd.pid")]
with (ROOT / "logs/dockerd-d-volume.log").open("w") as log:
    daemon = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
for _ in range(30):
    info = subprocess.run([docker, "info", "--format", "{{json .}}"], env=env, capture_output=True, text=True)
    if info.returncode == 0:
        parsed = json.loads(info.stdout)
        if parsed["DockerRootDir"] != str(destination):
            raise RuntimeError("Docker is using the wrong data directory")
        break
    time.sleep(1)
else:
    raise RuntimeError("Migrated daemon not ready; inspect its log")
test = subprocess.run([docker, "run", "--rm", "hello-world"], env=env, capture_output=True, text=True, timeout=120)
receipt = {"epoch": time.time(), "disk_image": str(IMAGE), "image_capacity_bytes": IMAGE.stat().st_size,
           "docker_root": str(destination), "original_data_preserved": str(ROOT / "docker-data"),
           "daemon_pid": daemon.pid, "hello_world_returncode": test.returncode,
           "status": "pass" if test.returncode == 0 else "failed"}
(ROOT / "evidence/docker-storage.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
