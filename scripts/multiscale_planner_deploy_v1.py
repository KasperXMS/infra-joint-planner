"""Bounded independent Manager service and official pulls; never changes Executor."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path("/home/super/xiaoming/multiscale-planner-evaluation-v1/run-001")
BINARY = "/home/super/heterogeneous-v1/runtime/ollama-0.34.0/bin/ollama"


def write(path, data):
    with path.open("x") as f:
        json.dump(data, f, indent=2)


def api(route, body=None, timeout=30):
    req = urllib.request.Request(
        "http://127.0.0.1:11450/api/" + route,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    assert sys.platform == "linux"
    ROOT.mkdir(parents=True, exist_ok=True)
    plan = json.loads(
        (ROOT / "app/configs/experiments/multiscale-planner-execution-v1.json").read_text()
    )
    assert shutil.disk_usage(ROOT).free > 30 * 1024**3
    s = socket.socket()
    s.bind(("127.0.0.1", 11450))
    s.close()
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("OLLAMA_") and k != "CUDA_VISIBLE_DEVICES"
    }
    env.update(
        OLLAMA_HOST="127.0.0.1:11450",
        OLLAMA_MODELS=str(ROOT / "models"),
        OLLAMA_KEEP_ALIVE="-1",
        OLLAMA_NUM_PARALLEL="1",
        OLLAMA_MAX_LOADED_MODELS="1",
        OLLAMA_KV_CACHE_TYPE="q8_0",
        OLLAMA_FLASH_ATTENTION="1",
        OLLAMA_VULKAN="0",
        OLLAMA_NO_CLOUD="1",
        CUDA_VISIBLE_DEVICES="GPU-bf1b70c4-b2d7-ed3b-54d5-95685863f06d",
    )
    p = subprocess.Popen(
        [BINARY, "serve"],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=(ROOT / "planner-server.log").open("x"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    write(
        ROOT / "planner-server.json",
        {
            "pid": p.pid,
            "binary_sha256": hashlib.sha256(Path(BINARY).read_bytes()).hexdigest(),
            "port": 11450,
            "environment": {
                k: v
                for k, v in env.items()
                if k.startswith("OLLAMA_") or k == "CUDA_VISIBLE_DEVICES"
            },
        },
    )
    for _ in range(30):
        try:
            api("version")
            break
        except Exception:
            time.sleep(1)
    write(ROOT / "deployment-freeze.json", plan)
    for name, tag in plan["downloads"].items():
        begin = time.monotonic()
        try:
            receipt = api(
                "pull",
                {"model": tag, "stream": False},
                timeout=plan["download_timeout_seconds_per_candidate"],
            )
            show = api("show", {"model": tag})
            manifest = (
                ROOT
                / "models/manifests/registry.ollama.ai/library"
                / tag.split(":")[0]
                / tag.split(":")[1]
            )
            layers = json.loads(manifest.read_text())["layers"]
            total = sum(x["size"] for x in layers)
            assert total <= plan["maximum_download_bytes"]
            write(
                ROOT / (name + "-download.json"),
                {
                    "tag": tag,
                    "official_source": "https://ollama.com/library/" + tag,
                    "status": receipt,
                    "elapsed_seconds": time.monotonic() - begin,
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "layers": layers,
                    "show": show,
                    "version": api("version"),
                },
            )
            print(
                json.dumps(
                    {"downloaded": name, "seconds": time.monotonic() - begin, "bytes": total}
                ),
                flush=True,
            )
        except Exception as exc:
            write(
                ROOT / (name + "-download-error.json"),
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "elapsed_seconds": time.monotonic() - begin,
                },
            )
            print(json.dumps({"download_failed": name, "type": type(exc).__name__}), flush=True)
    write(ROOT / "downloads-finished.json", {"done": True})


if __name__ == "__main__":
    main()
