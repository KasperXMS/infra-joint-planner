"""Derive a fresh Worker config for the calibrated pool, without runtime changes."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from infra_joint.config import WorkerConfig
from infra_joint.core.state import EnvironmentSpec

ARM_FFMPEG = "/mnt/ssd/large-scale-cost-guidance-v1/environment-repair-001/" \
             "ffmpeg-av1-h264-sw-v8.0.1/bin/ffmpeg"


def worker_config(
    pool: dict[str, Any], original: dict[str, Any], agent_id: str, artifact_root: Path,
) -> WorkerConfig:
    environment = EnvironmentSpec.model_validate(pool["environment"])
    agents = {item.agent_id for item in environment.agents}
    if agent_id not in agents or original.get("agent_id") != agent_id:
        raise ValueError("unknown Worker or source identity mismatch")
    if set(pool["resident_backends"]) != {d.deployment_id for d in environment.deployments}:
        raise ValueError("resident backend mapping does not exactly match the environment")
    if pool["model_request"]["max_retries"] != 0:
        raise ValueError("resident Worker cannot add backend retries")
    url = urlparse(pool["worker_urls"][agent_id])
    if url.scheme != "http" or url.port is None:
        raise ValueError("resident Worker endpoint requires an explicit HTTP port")
    config = deepcopy(original)
    config.update(port=url.port, artifact_root=artifact_root, deployments={})
    if agent_id != "strong-4090":
        config["ffmpeg_executable"] = ARM_FFMPEG
    seen_backends: set[str] = set()
    for deployment in environment.deployments:
        if deployment.agent_id != agent_id:
            continue
        backend = pool["resident_backends"][deployment.deployment_id]
        if backend["base_url"] in seen_backends:
            raise ValueError("same Worker deployments must have distinct resident servers")
        seen_backends.add(backend["base_url"])
        config["deployments"][deployment.deployment_id] = {
            "model_id": deployment.model_id, "modalities": sorted(deployment.modalities),
            "context_window": deployment.context_window,
            "reserved_output_tokens": deployment.reserved_output_tokens,
            "image_token_cost": deployment.image_token_cost,
            "model": {**{key: value for key, value in pool["model_request"].items()
                         if key != "max_retries"}, **backend},
        }
    return WorkerConfig.model_validate(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pool = yaml.safe_load(args.pool.read_text(encoding="utf-8"))
    original = yaml.safe_load(args.original.read_text(encoding="utf-8"))
    config = worker_config(pool, original, args.agent, args.store)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        yaml.safe_dump(config.model_dump(mode="json"), handle, sort_keys=False)
