"""Install locked BenchFlow tooling and copy exact frozen official task bytes."""
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
SOURCE = Path("/mnt/d/Codes/infra-aware-mas-new")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "evidence").mkdir(exist_ok=True)
    uv_archive = ROOT / "uv-0.12.7.tar.gz"
    if not uv_archive.exists():
        with urllib.request.urlopen("https://github.com/astral-sh/uv/releases/download/0.12.7/uv-x86_64-unknown-linux-gnu.tar.gz", timeout=60) as response, uv_archive.open("wb") as output:
            shutil.copyfileobj(response, output)
    with tarfile.open(uv_archive) as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith("/uv"))
        uv = ROOT / "uv"
        with archive.extractfile(member) as source, uv.open("wb") as output:
            shutil.copyfileobj(source, output)
        uv.chmod(0o755)
    env = os.environ.copy()
    env.update(UV_PYTHON_INSTALL_DIR=str(ROOT / "python"), UV_CACHE_DIR=str(ROOT / "uv-cache"))
    receipt = {"started_epoch": time.time(), "uv_archive_sha256": hashlib.sha256(uv_archive.read_bytes()).hexdigest()}
    commands = [
        [str(uv), "python", "install", "3.12"],
        [str(uv), "venv", "--python", "3.12", str(ROOT / "venv")],
        [str(uv), "pip", "compile", "--python", str(ROOT / "venv/bin/python"), "--generate-hashes",
         str(ROOT / "requirements.in"), "--output-file", str(ROOT / "requirements.lock.txt")],
        [str(uv), "pip", "install", "--python", str(ROOT / "venv/bin/python"), "--require-hashes",
         "--requirement", str(ROOT / "requirements.lock.txt")],
        [str(ROOT / "venv/bin/bench"), "--version"],
    ]
    (ROOT / "requirements.in").write_text("benchflow==0.6.3\nparamiko==4.0.0\n")
    for index, argv in enumerate(commands):
        with (ROOT / "logs" / f"tooling-{index}.log").open("w") as log:
            subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
    task_root = ROOT / "skillsbench"
    task_root.mkdir(exist_ok=True)
    with tarfile.open(SOURCE / ".code-staging/selected-skillsbench-v1.1.tar") as archive:
        archive.extractall(task_root, filter="data")
    for name in ("task-selection.lock.json", "freeze_tasks.py"):
        shutil.copy2(SOURCE / "infra-joint-planner/research/real_benchmark_skills_v1" / name, ROOT / name)
    shutil.copy2(SOURCE / ".code-staging/skillsbench-v1.1-task-manifest.json", ROOT / "release-manifest.json")
    receipt.update(status="pass", finished_epoch=time.time(),
                   requirements_sha256=hashlib.sha256((ROOT / "requirements.lock.txt").read_bytes()).hexdigest())
    (ROOT / "evidence/tooling.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
