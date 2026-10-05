"""Remote-only synthetic calibration through the unchanged formal model backend."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from PIL import Image
from resident_model_pool_service_v1 import EDGE_POOL, POOL, targets, write_new

from infra_joint.worker.model_backend import (
    ModelArtifact,
    ModelRequest,
    OpenAICompatibleModelBackend,
    preflight_model_request,
)

CONTEXT = 32768
OUTPUT = 2048
IMAGE_COST = 2048  # Existing contract; verify image accounting, do not infer it from model size.


def fixtures(probe_set: str = "core") -> tuple[tuple[str, ModelRequest], ...]:
    if probe_set == "image-boundary":
        boundary = io.BytesIO()
        Image.new("RGB", (2048, 2048), color=(0, 0, 200)).save(boundary, format="PNG")
        return (("warm-image-boundary", ModelRequest(
            prompt="Name the single dominant color of the synthetic image. One word only.",
            artifacts=(ModelArtifact(artifact_id="synthetic-boundary", media_type="image/png",
                                     content=boundary.getvalue()),),
            max_output_tokens=OUTPUT,
        )),)
    if probe_set != "core":
        raise ValueError("unknown calibration probe set")
    text = ("0123456789abcdef " * 1800)[:30000] + "\nEND-CALIBRATION-731"
    buffer = io.BytesIO()
    Image.new("RGB", (1920, 1080), color=(0, 200, 0)).save(buffer, format="PNG")
    sheet = io.BytesIO()
    Image.new("RGB", (1280, 1440), color=(200, 0, 0)).save(sheet, format="PNG")
    return (
        ("setup-load-text", ModelRequest(
            prompt="Synthetic service calibration. Reply only CALIBRATION-OK.",
            max_output_tokens=OUTPUT,
        )),
        ("warm-text-envelope", ModelRequest(
            prompt="Read the synthetic text artifact and repeat its final END marker only.",
            artifacts=(ModelArtifact(artifact_id="synthetic-text", media_type="text/plain",
                                     content=text.encode()),),
            max_output_tokens=OUTPUT,
        )),
        ("warm-image-frame", ModelRequest(
            prompt="Name the single dominant color of the synthetic image. One word only.",
            artifacts=(ModelArtifact(artifact_id="synthetic-image", media_type="image/png",
                                     content=buffer.getvalue()),),
            max_output_tokens=OUTPUT,
        )),
        ("warm-image-sheet", ModelRequest(
            prompt="Name the single dominant color of the synthetic image. One word only.",
            artifacts=(ModelArtifact(artifact_id="synthetic-sheet", media_type="image/png",
                                     content=sheet.getvalue()),),
            max_output_tokens=OUTPUT,
        )),
    )


def resident_state(port: int) -> dict[str, Any]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ps", timeout=10) as response:
        return json.load(response)


def memory_state() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for name, command in (
        ("memory", ["free", "-b"]),
        ("gpu", ["nvidia-smi", "--query-gpu=index,uuid,memory.total,memory.used",
                 "--format=csv"]),
    ):
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            rows[name] = {"returncode": completed.returncode, "stdout": completed.stdout,
                          "stderr": completed.stderr}
        except OSError as error:
            rows[name] = {"unavailable": type(error).__name__}
    return rows


async def calibrate_target(
    target: dict[str, Any], evidence: Path, *, probe_set: str = "core",
    image_token_cost: int = IMAGE_COST,
) -> dict[str, Any]:
    directory = evidence / target["instance"]
    directory.mkdir(exist_ok=False)
    client = AsyncOpenAI(api_key="local-calibration", max_retries=0, timeout=1200,
                         base_url=f"http://127.0.0.1:{target['port']}/v1")
    backend = OpenAICompatibleModelBackend(client, target["derived_tag"],
                                           reasoning_effort="none", temperature=None)
    rows: list[dict[str, Any]] = []
    try:
        for name, request in fixtures(probe_set):
            row: dict[str, Any] = {
                "probe": name, "setup_outside_benchmark_clock": name.startswith("setup-"),
                "context_window": CONTEXT, "reserved_output_tokens": OUTPUT,
                "image_token_cost": image_token_cost, "temperature_override": None,
                "reasoning_effort": "none", "automatic_retries": 0,
                "ttft_ms": None, "peak_memory_bytes": None,
                "truncation_status": "requires_server_log_audit",
                "resident_before": resident_state(target["port"]),
                "memory_before": memory_state(), "started_at": time.time(),
            }
            write_new(directory / f"{name}-request.json",
                      request.model_dump(mode="json", exclude={"artifacts"}))
            for artifact in request.artifacts:
                with (directory / f"{name}-{artifact.artifact_id}.bin").open("xb") as handle:
                    handle.write(artifact.content)
            row["artifacts"] = [{"id": item.artifact_id, "media_type": item.media_type,
                                 "bytes": len(item.content),
                                 "sha256": hashlib.sha256(item.content).hexdigest()}
                                for item in request.artifacts]
            try:
                row["preflight_estimated_input"] = preflight_model_request(
                    request, modalities=frozenset({"text", "image"}), context_window=CONTEXT,
                    reserved_output_tokens=OUTPUT, image_token_cost=image_token_cost,
                )
                row["preflight"] = "pass"
                row["inference_submitted"] = True
                response = await backend.invoke(request)
                row["completion"] = response.model_dump(mode="json")
                row["status"] = "pass" if response.text.strip() else "empty_output"
            except Exception as error:
                row.update(status="failure", error_type=type(error).__name__, error=str(error))
            row["finished_at"] = time.time()
            row["resident_after"] = resident_state(target["port"])
            row["memory_after"] = memory_state()
            rows.append(row)
            write_new(directory / f"{name}-result.json", row)
            if row["status"] != "pass":
                break
    finally:
        await client.close()
    result = {"target": target, "probes": rows,
              "all_probes_passed": len(rows) == len(fixtures(probe_set))
              and all(item["status"] == "pass" for item in rows),
              "residency_and_truncation_audit_pending": True, "benchmark_cells": 0,
              "planner_calls": 0}
    write_new(directory / "completion.json", result)
    return result


async def calibrate(
    node: str, *, attempt: str = "synthetic-001", probe_set: str = "core",
    image_token_cost: int = IMAGE_COST,
) -> None:
    if sys.platform != "linux":
        raise RuntimeError("calibration must execute on the remote experiment nodes")
    if re.fullmatch(r"synthetic-[0-9]{3}", attempt) is None:
        raise ValueError("invalid calibration evidence namespace")
    if image_token_cost < 1:
        raise ValueError("image context envelope must be positive")
    fixtures(probe_set)
    base = POOL if node == "strong-4090" else EDGE_POOL
    evidence = base / "calibration" / attempt
    evidence.mkdir(parents=True, exist_ok=False)
    write_new(evidence / "process.json", {"pid": os.getpid(), "node": node,
              "started_at": time.time(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "formal_model_backend_source": __import__(OpenAICompatibleModelBackend.__module__,
              fromlist=["__file__"]).__file__, "benchmark_cells": 0, "planner_calls": 0})
    results = await asyncio.gather(
        *(calibrate_target(target, evidence, probe_set=probe_set,
                           image_token_cost=image_token_cost) for target in targets(node))
    )
    result = {"node": node, "instances": [{"instance": item["target"]["instance"],
               "all_probes_passed": item["all_probes_passed"]} for item in results],
              "benchmark_cells": 0, "planner_calls": 0, "audit_pending": True}
    write_new(evidence / "completion.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", choices=["A4", "A5", "A28", "strong-4090"], required=True)
    parser.add_argument("--attempt", default="synthetic-001")
    parser.add_argument("--probe-set", choices=["core", "image-boundary"], default="core")
    parser.add_argument("--image-token-cost", type=int, default=IMAGE_COST)
    args = parser.parse_args()
    asyncio.run(calibrate(args.node, attempt=args.attempt, probe_set=args.probe_set,
                          image_token_cost=args.image_token_cost))
