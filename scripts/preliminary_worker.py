"""No-retry worker entry point for preliminary experiment v0."""

import argparse
import asyncio
from pathlib import Path

import httpx
import uvicorn

from infra_joint.config import load_worker_config
from infra_joint.experiments.preliminary import build_no_retry_model_backend
from infra_joint.operators.media import FfmpegMediaBackend, probe_ffmpeg
from infra_joint.worker.artifact_fetcher import HttpArtifactFetcher
from infra_joint.worker.artifact_store import FileArtifactStore
from infra_joint.worker.model_backend import ModelDeployment
from infra_joint.worker.server import create_worker_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    settings = load_worker_config(arguments.config)

    clients = []
    deployments = {}
    for deployment_id, deployment_config in settings.deployments.items():
        backend, client = build_no_retry_model_backend(deployment_config.model)
        if client is not None:
            clients.append(client)
        deployments[deployment_id] = ModelDeployment(
            deployment_id=deployment_id,
            model_id=deployment_config.model_id,
            backend=backend,
            modalities=deployment_config.modalities,
            context_window=deployment_config.context_window,
            reserved_output_tokens=deployment_config.reserved_output_tokens,
            image_token_cost=deployment_config.image_token_cost,
        )

    fetch_client = None
    fetcher = None
    if settings.allowed_artifact_hosts:
        fetch_client = httpx.AsyncClient(timeout=900.0)
        fetcher = HttpArtifactFetcher(fetch_client, settings.allowed_artifact_hosts)
    ffmpeg = asyncio.run(probe_ffmpeg(settings.ffmpeg_executable))
    media_backend = (
        FfmpegMediaBackend(ffmpeg.executable)
        if ffmpeg.available and ffmpeg.executable is not None
        else None
    )
    app = create_worker_app(
        settings.agent_id,
        deployments,
        artifact_store=FileArtifactStore(settings.artifact_root),
        artifact_fetcher=fetcher,
        media_backend=media_backend,
        max_read_artifact_bytes=settings.max_read_artifact_bytes,
    )
    try:
        uvicorn.run(app, host=settings.host, port=settings.port)
    finally:
        if fetch_client is not None:
            asyncio.run(fetch_client.aclose())
        for client in clients:
            asyncio.run(client.close())


if __name__ == "__main__":
    main()
