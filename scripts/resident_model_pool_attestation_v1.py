"""Read-only, private residency checks; never loads or repairs a model."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from resident_model_pool_service_v1 import api, manifest_path, targets


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_resident(state: dict[str, Any], tag: str, digest: str) -> None:
    models = state.get("models", [])
    if (len(models) != 1 or models[0].get("name") != tag + ":latest"
            or models[0].get("digest") != digest
            or models[0].get("context_length") != 32768
            or models[0].get("size_vram", 0) <= 0
            or not str(models[0].get("expires_at", "")).startswith("2319-")):
        raise RuntimeError("resident model identity/context/memory/keep-alive drift")


def process_identity(pid: int) -> dict[str, Any]:
    proc = Path(f"/proc/{pid}")
    command = (proc / "cmdline").read_bytes().decode().split("\0")
    # Return only relevant nonsecret settings, never the full inherited environment.
    values = dict(item.split("=", 1) for item in (proc / "environ").read_bytes().decode()
                  .split("\0") if "=" in item)
    keys = {"CUDA_VISIBLE_DEVICES", "OLLAMA_HOST", "OLLAMA_MODELS", "OLLAMA_KEEP_ALIVE",
            "OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_KV_CACHE_TYPE",
            "OLLAMA_FLASH_ATTENTION", "OLLAMA_VULKAN", "OLLAMA_NO_CLOUD"}
    return {"pid": pid, "command": command,
            "start_ticks": (proc / "stat").read_text().rsplit(")", 1)[1].split()[19],
            "environment": {key: values[key] for key in sorted(keys) if key in values}}


def is_model_runner(command: bytes) -> bool:
    argv = command.decode().split("\0")
    name = Path(argv[0]).name
    return name == "llama-server" or (name == "ollama" and argv[1:2] == ["runner"])


def node_attestation(node: str) -> dict[str, Any]:
    if sys.platform != "linux":
        raise RuntimeError("physical attestations must run on the actual experiment nodes")
    pool = (Path("/home/super/xiaoming/resident-model-pool-v1") if node == "strong-4090"
            else Path("/mnt/ssd/resident-model-pool-v1"))
    services = pool / "services" / ("start-004" if node == "strong-4090" else "start-003")
    instances = []
    for target in targets(node):
        name = target["instance"]
        receipt = json.loads((services / (name + "-receipt.json")).read_text())
        original = json.loads((services / (name + "-process.json")).read_text())
        if (receipt["target"] != target or original["target"] != target
                or sha256(Path(target["binary"])) != original["binary_sha256"]
                or sha256(manifest_path(Path(target["store"]), target["derived_tag"]))
                != receipt["derived_manifest_sha256"]):
            raise RuntimeError("actual server/model/binary differs from calibration")
        server = process_identity(receipt["pid"])
        if any(server["environment"].get(key) != value
               for key, value in original["environment"].items()
               if key in server["environment"] or key.startswith("OLLAMA_")
               or key == "CUDA_VISIBLE_DEVICES"):
            raise RuntimeError("server resident settings drift")
        children = []
        for child in Path("/proc").iterdir():
            if not child.name.isdigit():
                continue
            try:
                status = (child / "status").read_text()
                parent = next(line.split()[1] for line in status.splitlines()
                              if line.startswith("PPid:"))
                cmd = (child / "cmdline").read_bytes()
                if parent == str(receipt["pid"]) and is_model_runner(cmd):
                    children.append(process_identity(int(child.name)))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        if len(children) != 1:
            raise RuntimeError("one stable loaded runner per resident server is required")
        state = api(target["port"], "ps")
        validate_resident(state, target["derived_tag"], receipt["derived_manifest_sha256"])
        log = services / (name + "-server.log")
        data = log.read_bytes()
        instances.append({"target": target, "server": server, "runner": children[0],
                          "resident": state, "log_path": str(log), "log_bytes": len(data),
                          "log_prefix_sha256": hashlib.sha256(data).hexdigest()})
    gpu_processes: list[dict[str, Any]] | None = None
    if node == "strong-4090":
        output = subprocess.run([
            "nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ], check=True, capture_output=True, text=True).stdout
        gpu_processes = []
        for line in output.splitlines():
            gpu, pid, memory = (item.strip() for item in line.split(","))
            comm = Path(f"/proc/{pid}/comm").read_text().strip()
            gpu_processes.append({"gpu_uuid": gpu, "pid": int(pid), "used_mib": int(memory),
                                  "command_name": comm})
        for item in instances:
            matching = [p for p in gpu_processes if p["pid"] == item["runner"]["pid"]]
            if len(matching) != 1 or matching[0]["gpu_uuid"] != item["target"]["gpu"]:
                raise RuntimeError("actual CUDA runner is not on its calibrated GPU UUID")
    return {"node": node, "captured_at": time.time(), "instances": instances,
            "gpu_compute_processes": gpu_processes, "model_calls": 0, "pid": os.getpid()}


def compare_residency(before: dict[str, Any], after: dict[str, Any]) -> None:
    if before["node"] != after["node"]:
        raise RuntimeError("resident node identity changed")
    old = {row["target"]["instance"]: row for row in before["instances"]}
    new = {row["target"]["instance"]: row for row in after["instances"]}
    if old.keys() != new.keys():
        raise RuntimeError("resident instance surface changed")
    for name, row in old.items():
        now = new[name]
        if (row["server"] != now["server"] or row["runner"] != now["runner"]
                or row["target"] != now["target"]):
            raise RuntimeError("resident server/runner reloaded or drifted during the cell")
    old_gpu = before.get("gpu_compute_processes")
    new_gpu = after.get("gpu_compute_processes")
    if old_gpu is not None and (
        {(row["gpu_uuid"], row["pid"]) for row in old_gpu}
        != {(row["gpu_uuid"], row["pid"]) for row in new_gpu}
    ):
        raise RuntimeError("external GPU compute contention changed during the cell")


def audit_log_interval(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Run on the same node; preserve raw interval text only in private evidence."""
    compare_residency(before, after)
    logs = {}
    for row in before["instances"]:
        data = Path(row["log_path"]).read_bytes()
        prefix, interval = data[:row["log_bytes"]], data[row["log_bytes"]:]
        if hashlib.sha256(prefix).hexdigest() != row["log_prefix_sha256"]:
            raise RuntimeError("resident log was rotated or rewritten")
        text = interval.decode(errors="replace")
        if any(marker in text.lower() for marker in (
            "starting runner", "out of memory",
            "truncating input prompt",
        )) or any(int(value) > 0 for value in re.findall(r"truncated\s*=\s*(\d+)", text)):
            raise RuntimeError("model reload/OOM/truncation in measured cell interval")
        logs[row["target"]["instance"]] = {"text": text, "bytes": len(interval),
                                              "sha256": hashlib.sha256(interval).hexdigest()}
    return {"passed": True, "intervals": logs, "model_calls": 0}
