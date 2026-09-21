import asyncio
from pathlib import Path
from typing import Annotated

import httpx
import typer
import uvicorn

from infra_joint.config import build_model_backend, load_planner_config, load_worker_config
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.operators.media import FfmpegMediaBackend, probe_ffmpeg
from infra_joint.planning.planner import BlindPlannerContext, LLMBlindPlanner
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


async def _plan_once(config: Path, objective: str) -> str:
    settings = load_planner_config(config)
    backend, openai_client = build_model_backend(settings.model)
    planner = LLMBlindPlanner(backend, build_operator_catalog())
    task = TaskContract(
        task_id="blind-plan-once",
        benchmark_id="manual-smoke",
        objective=objective,
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="manual",
    )
    try:
        decision = await planner.decide(
            BlindPlannerContext(
                task=task,
                decisions=(),
                observations=(),
                remaining_steps=1,
            )
        )
        return decision.model_dump_json()
    finally:
        if openai_client is not None:
            await openai_client.close()


@app.command("blind-plan-once")
def blind_plan_once(
    config: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    objective: Annotated[str, typer.Option(help="Logical task objective.")],
) -> None:
    """Request one infrastructure-blind decision from the configured model."""

    typer.echo(asyncio.run(_plan_once(config, objective)))


if __name__ == "__main__":
    app()
