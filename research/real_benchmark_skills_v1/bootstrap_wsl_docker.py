"""Provision a dedicated official Docker daemon in WSL, without a system service.

Runs as WSL root. Does not change or stop any existing Docker daemon, install
cloud services, or perform instance lifecycle actions.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path("/root/skillsbench-local-20261013")
DOCKER_VERSION = "29.9.0"
COMPOSE_VERSION = "v5.6.0"
COMPOSE_SHA256 = "40343e21ca777173e69cff5dbafeb37c6f81f3b0d57d9e597f036e95eb63e76a"


def download(url, path, expected=None):
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected and digest != expected:
        raise ValueError("Downloaded checksum differs: " + path.name)
    return {"url": url, "sha256": digest, "bytes": path.stat().st_size}


def main():
    if os.geteuid() != 0:
        raise RuntimeError("WSL root required")
    for name in ("downloads", "bin", "run", "logs", "evidence", "docker-config/cli-plugins"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    receipt = {"started_epoch": time.time(), "root": str(ROOT), "status": "running"}
    archive = ROOT / "downloads" / f"docker-{DOCKER_VERSION}.tgz"
    receipt["docker"] = download(f"https://download.docker.com/linux/static/stable/x86_64/{archive.name}", archive)
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile() and Path(member.name).parent == Path("docker"):
                target = ROOT / "bin" / Path(member.name).name
                with bundle.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755)
    compose = ROOT / "docker-config/cli-plugins/docker-compose"
    receipt["compose"] = download(
        f"https://github.com/docker/compose/releases/download/{COMPOSE_VERSION}/docker-compose-linux-x86_64",
        compose, COMPOSE_SHA256)
    compose.chmod(0o755)
    env = os.environ.copy()
    env.update(PATH=str(ROOT / "bin") + ":" + env["PATH"],
               DOCKER_HOST="unix://" + str(ROOT / "run/docker.sock"),
               DOCKER_CONFIG=str(ROOT / "docker-config"))
    (ROOT / "docker-env.sh").write_text(
        f"export PATH={ROOT}/bin:$PATH\nexport DOCKER_HOST={env['DOCKER_HOST']}\n"
        f"export DOCKER_CONFIG={env['DOCKER_CONFIG']}\n")
    if not (ROOT / "run/docker.sock").exists():
        argv = [str(ROOT / "bin/dockerd"), "--host", env["DOCKER_HOST"],
                "--data-root", str(ROOT / "docker-data"), "--exec-root", str(ROOT / "docker-exec"),
                "--pidfile", str(ROOT / "run/dockerd.pid")]
        with (ROOT / "logs/dockerd.log").open("ab") as log:
            process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        receipt["daemon_pid"] = process.pid
    docker = str(ROOT / "bin/docker")
    for _ in range(30):
        result = subprocess.run([docker, "info", "--format", "{{json .}}"], env=env,
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            receipt["info"] = json.loads(result.stdout)
            break
        time.sleep(1)
    else:
        raise RuntimeError("Dedicated Docker daemon not ready; inspect logs/dockerd.log")
    for name, argv in (("compose_version", [docker, "compose", "version"]),
                       ("hello_world", [docker, "run", "--rm", "hello-world"])):
        result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=180)
        receipt[name] = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        if result.returncode:
            receipt["status"] = "failed"
            break
    else:
        receipt["status"] = "pass"
    receipt["finished_epoch"] = time.time()
    (ROOT / "evidence/docker-bootstrap.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "root": str(ROOT),
                      "docker_version": DOCKER_VERSION, "compose_version": COMPOSE_VERSION}))


if __name__ == "__main__":
    main()
