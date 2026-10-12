"""Persistent lease budget, telemetry and owned-process protection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


def append(path: Path, value: dict) -> None:
    data = (json.dumps(value, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def identity(pid: int) -> dict:
    proc = Path("/proc") / str(pid)
    return {"pid": pid, "start_ticks": proc.joinpath("stat").read_text().rsplit(")", 1)[1].split()[19]}


def register(root: Path, purpose: str) -> None:
    append(root / "owned-processes.jsonl", {**identity(os.getpid()), "purpose": purpose})


def stop_owned(root: Path) -> None:
    ledger = root / "owned-processes.jsonl"
    if not ledger.exists():
        return
    for line in ledger.read_text().splitlines():
        record = json.loads(line)
        if record["pid"] == os.getpid():
            continue
        try:
            if identity(record["pid"]) == {k: record[k] for k in ("pid", "start_ticks")}:
                if record.get("process_group") and os.getpgid(record["pid"]) == record["pid"]:
                    os.killpg(record["pid"], signal.SIGTERM)
                else:
                    os.kill(record["pid"], signal.SIGTERM)
        except (FileNotFoundError, ProcessLookupError):
            pass


def main(root: Path, backup: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)
    budget_path = root / "resource-budget.json"
    if not budget_path.exists():
        with budget_path.open("x") as stream:
            json.dump({"start_epoch": time.time(), "soft_seconds": 36000, "hard_seconds": 72000,
                       "lease_cny_per_hour": 6.06, "hard_limit_action": "owned_jobs_stop_then_autodl_shutdown"}, stream, indent=2)
    budget = json.loads(budget_path.read_text())
    register(root, "resource_guard")
    shutil.copy2(budget_path, backup / budget_path.name)
    while True:
        now = time.time()
        elapsed = now - budget["start_epoch"]
        try:
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu,power.draw",
                                  "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
            gpu_csv, gpu_returncode = gpu.stdout.strip(), gpu.returncode
        except subprocess.TimeoutExpired:
            gpu_csv, gpu_returncode = "", "telemetry_timeout"
        memory = Path("/sys/fs/cgroup/memory.current")
        append(root / "resources.jsonl", {"epoch": now, "elapsed_seconds": elapsed,
               "lease_cny_estimate": elapsed / 3600 * budget["lease_cny_per_hour"],
               "gpu_csv": gpu_csv, "gpu_query_returncode": gpu_returncode,
               "cgroup_memory_bytes": int(memory.read_text()) if memory.exists() else None})
        # Copy small evidence/checkpoints, never models, caches or virtual environments.
        for file in root.glob("*.json*"):
            shutil.copy2(file, backup / file.name)
        for dirname in ("results", "configs", "traces", "checkpoints"):
            if root.joinpath(dirname).exists():
                shutil.copytree(root / dirname, backup / dirname, dirs_exist_ok=True)
        if elapsed >= budget["soft_seconds"]:
            (root / "SOFT_TIME_TARGET_REACHED").touch(exist_ok=True)
        if elapsed >= budget["hard_seconds"]:
            (root / "STOP").touch(exist_ok=True)
            stop_owned(root)
            append(root / "administration.jsonl", {"epoch": now, "event": "20h_safety_limit_shutdown"})
            for name in ("resources.jsonl", "administration.jsonl", "owned-processes.jsonl"):
                if (root / name).exists():
                    shutil.copy2(root / name, backup / name)
            os.sync()
            subprocess.run(["/usr/bin/shutdown"], check=True)
            return
        time.sleep(min(60, max(1, budget["hard_seconds"] - elapsed)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    main(args.root, args.backup)
