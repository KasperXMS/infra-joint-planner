"""Isolated, remote-only Ollama service bootstrap; no inference or benchmark calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

POOL = Path("/home/super/xiaoming/resident-model-pool-v1")
EDGE_POOL = Path("/mnt/ssd/resident-model-pool-v1")
GPU0 = "GPU-eba0a381-9ae1-4752-9171-6616ee9a0880"
GPU1 = "GPU-bf1b70c4-b2d7-ed3b-54d5-95685863f06d"


def targets(node: str) -> tuple[dict[str, Any], ...]:
    if node in {"A4", "A5"}:
        small = "4b" if node == "A4" else "8b"
        return ({
            "instance": f"resident-{node.lower()}-vl{small}-v1",
            "port": 11436,
            "store": str(EDGE_POOL / "models"),
            "binary": str(EDGE_POOL / "runtime/ollama-0.34.0/bin/ollama"),
            "source_tag": f"qwen3-vl:{small}-instruct",
            "derived_tag": f"qwen-vl{small}-resident-32k-v1",
            "gpu": None,
        },)
    if node == "A28":
        return ({
            "instance": "resident-a28-qwen35-27b-v1", "port": 11436,
            "store": str(EDGE_POOL / "models"),
            "binary": "/mnt/ssd/heterogeneous-v1/runtime/ollama-0.34.0/bin/ollama",
            "source_tag": "qwen3.8-27b-v1", "derived_tag": "qwen35-27b-resident-32k-v1",
            "gpu": None,
        },)
    if node == "strong-4090":
        binary = "/home/super/heterogeneous-v1/runtime/ollama-0.34.0/bin/ollama"
        return (
            {"instance": "resident-4090-gpu0-qwen35-27b-v1", "port": 11436,
             "store": str(POOL / "instance-stores/gpu0/models"), "binary": binary,
             "source_tag": "qwen3.8-27b-v1", "derived_tag": "qwen35-27b-resident-32k-v1",
             "gpu": GPU0},
            {"instance": "resident-4090-gpu1-vl8b-v1", "port": 11437,
             "store": str(POOL / "instance-stores/gpu1/models"), "binary": binary,
             "source_tag": "qwen3-vl:8b-instruct", "derived_tag": "qwen-vl8b-resident-32k-v1",
             "gpu": GPU1},
        )
    raise ValueError("unknown resident-pool node")


def server_environment(target: dict[str, Any], inherited: dict[str, str]) -> dict[str, str]:
    result = dict(inherited)
    # Do not inherit a different server's model/context/device configuration.
    for key in tuple(result):
        if key.startswith("OLLAMA_") or key in {"CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES"}:
            del result[key]
    result.update({
        "OLLAMA_HOST": f"127.0.0.1:{target['port']}",
        "OLLAMA_MODELS": target["store"], "OLLAMA_KEEP_ALIVE": "-1",
        "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0", "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_NO_CLOUD": "1",
    })
    if target["gpu"] is not None:
        result["CUDA_VISIBLE_DEVICES"] = target["gpu"]
    return result


def manifest_path(store: Path, tag: str) -> Path:
    if "/" in tag or tag.count(":") > 1 or not tag:
        raise ValueError("bootstrap accepts only fixed local library tags")
    name, _, version = tag.partition(":")
    if name in {".", ".."} or version in {".", ".."}:
        raise ValueError("unsafe model tag")
    return store / "manifests/registry.ollama.ai/library" / name / (version or "latest")


def manifest_parameters(store: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    entries = [item for item in manifest["layers"] if item["mediaType"].endswith(".params")]
    if not entries:
        return {}
    if len(entries) != 1:
        raise ValueError("ambiguous parameter layers")
    digest = entries[0]["digest"]
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError("invalid parameter-layer digest")
    data = (store / "blobs" / digest.replace(":", "-")).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest.removeprefix("sha256:"):
        raise ValueError("parameter-layer content drift")
    return json.loads(data)


def verify_derived_build(
    source: dict[str, Any], derived: dict[str, Any],
    source_parameters: dict[str, Any], derived_parameters: dict[str, Any],
    source_show: dict[str, Any], derived_show: dict[str, Any],
) -> None:
    unchanged = lambda value: [  # noqa: E731
        item for item in value["layers"] if not item["mediaType"].endswith(".params")
    ]
    if unchanged(source) != unchanged(derived):
        raise ValueError("derived model changes source weights/template/projector/license")
    if derived_parameters != {**source_parameters, "num_ctx": 32768}:
        raise ValueError("derived parameters differ beyond num_ctx")
    for field in ("template", "system", "messages", "model_info", "details", "capabilities"):
        if source_show.get(field) != derived_show.get(field):
            raise ValueError(f"derived show metadata drift: {field}")


def api(port: int, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/{endpoint}", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)


def bootstrap(node: str) -> dict[str, Any]:
    if sys.platform != "linux":
        raise RuntimeError("resident service bootstrap must execute on the remote nodes")
    root = POOL if node == "strong-4090" else EDGE_POOL
    evidence = root / "services/start-001"
    evidence.mkdir(parents=True, exist_ok=False)
    started: list[subprocess.Popen[bytes]] = []
    receipts: list[dict[str, Any]] = []
    try:
        for target in targets(node):
            port, store = target["port"], Path(target["store"])
            with socket.socket() as probe:
                probe.settimeout(1)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError("new resident port already occupied; refusing reuse")
            source_file = manifest_path(store, target["source_tag"])
            derived_file = manifest_path(store, target["derived_tag"])
            if not source_file.is_file() or derived_file.exists():
                raise RuntimeError("source missing or derived tag already exists")
            original_bytes = source_file.read_bytes()
            source = json.loads(original_bytes)
            original_parameters = manifest_parameters(store, source)
            environment = server_environment(target, dict(os.environ))
            log_path = evidence / f"{target['instance']}-server.log"
            with log_path.open("xb") as log:
                process = subprocess.Popen(
                    [target["binary"], "serve"], env=environment,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                )
            started.append(process)
            write_new(evidence / f"{target['instance']}-process.json", {
                "pid": process.pid, "target": target,
                "binary_sha256": hashlib.sha256(Path(target["binary"]).read_bytes()).hexdigest(),
                "environment": {key: value for key, value in environment.items()
                                if key.startswith("OLLAMA_") or key == "CUDA_VISIBLE_DEVICES"},
                "source_manifest_sha256": hashlib.sha256(original_bytes).hexdigest(),
                "bootstrap_inference_calls": 0,
            })
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError("new server exited during bootstrap")
                try:
                    version = api(port, "version")
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("server readiness deadline exceeded") from None
                    time.sleep(0.2)
            if version.get("version") != "0.34.0" or api(port, "ps").get("models") != []:
                raise RuntimeError("unexpected server version or loaded model")
            source_show = api(port, "show", {"model": target["source_tag"]})
            write_new(evidence / f"{target['instance']}-source-show.json", source_show)
            create = api(port, "create", {
                "model": target["derived_tag"], "from": target["source_tag"],
                "parameters": {"num_ctx": 32768}, "stream": False,
            })
            if create.get("status") != "success":
                raise RuntimeError("derived model creation did not succeed")
            derived_show = api(port, "show", {"model": target["derived_tag"]})
            derived_bytes = derived_file.read_bytes()
            derived = json.loads(derived_bytes)
            verify_derived_build(source, derived, original_parameters,
                                 manifest_parameters(store, derived), source_show, derived_show)
            if source_file.read_bytes() != original_bytes:
                raise RuntimeError("source tag was overwritten")
            write_new(evidence / f"{target['instance']}-derived-show.json", derived_show)
            row = {"target": target, "pid": process.pid, "server_version": version,
                   "source_manifest_sha256": hashlib.sha256(original_bytes).hexdigest(),
                   "derived_manifest_sha256": hashlib.sha256(derived_bytes).hexdigest(),
                   "derived_parameters": manifest_parameters(store, derived),
                   "source_identity_preserved": True, "inference_calls": 0,
                   "loaded_models": api(port, "ps")["models"], "validated_contract": None}
            write_new(evidence / f"{target['instance']}-receipt.json", row)
            receipts.append(row)
        result = {"node": node, "instances": receipts, "benchmark_cells": 0,
                  "planner_calls": 0, "inference_calls": 0, "calibration_pending": True}
        write_new(evidence / "completion.json", result)
        return result
    except Exception as error:
        stopped = []
        for process in started:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
                stopped.append(process.pid)
        write_new(evidence / "failure.json", {
            "type": type(error).__name__, "message": str(error),
            "only_new_bootstrap_servers_stopped": stopped,
            "source_tags_not_intentionally_modified": True, "benchmark_cells": 0,
        })
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", choices=["A4", "A5", "A28", "strong-4090"], required=True)
    print(json.dumps(bootstrap(parser.parse_args().node), sort_keys=True))
