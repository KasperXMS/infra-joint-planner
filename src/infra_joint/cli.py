import asyncio
from pathlib import Path
from typing import Annotated

import httpx
import typer
import uvicorn

from infra_joint.config import build_model_backend, load_worker_config
from infra_joint.operators.media import FfmpegMediaBackend, probe_ffmpeg
from infra_joint.worker.artifact_fetcher import HttpArtifactFetcher
from infra_joint.worker.artifact_store import FileArtifactStore
from infra_joint.worker.server import create_worker_app

app = typer.Typer(no_args_is_help=True, help="Infra-Aware Joint Planner utilities.")


@app.callback()
def main() -> None:
    """Run controller and worker utilities."""


@app.command()
def worker(
    config: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Start a worker from a YAML configuration file."""

    settings = load_worker_config(config)
    backend, openai_client = build_model_backend(settings.model)
    fetch_client: httpx.AsyncClient | None = None
    fetcher = None
    if settings.allowed_artifact_hosts:
        fetch_client = httpx.AsyncClient(timeout=60.0)
        fetcher = HttpArtifactFetcher(fetch_client, settings.allowed_artifact_hosts)
    ffmpeg = asyncio.run(probe_ffmpeg(settings.ffmpeg_executable))
    media_backend = (
        FfmpegMediaBackend(ffmpeg.executable)
        if ffmpeg.available and ffmpeg.executable is not None
        else None
    )
    if not ffmpeg.available:
        typer.echo(f"FFmpeg media operators disabled: {ffmpeg.reason}", err=True)
    worker_app = create_worker_app(
        settings.agent_id,
        backend,
        artifact_store=FileArtifactStore(settings.artifact_root),
        artifact_fetcher=fetcher,
        deployment_ids=settings.deployment_ids,
        media_backend=media_backend,
    )
    try:
        uvicorn.run(worker_app, host=settings.host, port=settings.port)
    finally:
        if fetch_client is not None:
            asyncio.run(fetch_client.aclose())
        if openai_client is not None:
            asyncio.run(openai_client.close())


if __name__ == "__main__":
    app()
