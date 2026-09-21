import inspect
from typing import Any, cast

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import Field
from starlette.responses import Response

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.operators.builtin import invoke_model_spec, read_artifact_spec
from infra_joint.operators.media import MediaBackend, MediaExecutionError, register_media_operators
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.operators.retrieval import register_retrieval_operators
from infra_joint.operators.structured import register_structured_operators
from infra_joint.worker.artifact_fetcher import ArtifactFetcher
from infra_joint.worker.artifact_store import (
    ArtifactNotFoundError,
    ArtifactStore,
    InMemoryArtifactStore,
    StoredArtifact,
)
from infra_joint.worker.model_backend import ModelBackend


class ExecuteOperatorRequest(ContractModel):
    action: SemanticAction
    deployment_id: str | None = None


class ExecuteOperatorResponse(ContractModel):
    operator: str
    output: dict[str, Any]


class WorkerStateResponse(ContractModel):
    agent_id: str = Field(min_length=1)
    available: bool
    in_flight: int = Field(ge=0)
    operators: tuple[str, ...]
    deployment_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]


class PullArtifactRequest(ContractModel):
    artifact_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PullArtifactResponse(ContractModel):
    artifact_id: str
    size_bytes: int = Field(ge=0)
    sha256_hex: str = Field(pattern=r"^[0-9a-f]{64}$")


def create_worker_app(
    agent_id: str,
    model_backend: ModelBackend,
    *,
    artifact_store: ArtifactStore | None = None,
    artifact_fetcher: ArtifactFetcher | None = None,
    deployment_ids: tuple[str, ...] = (),
    media_backend: MediaBackend | None = None,
) -> FastAPI:
    registry = OperatorRegistry()
    store = artifact_store or InMemoryArtifactStore()
    in_flight = 0

    async def invoke_model(action: SemanticAction) -> dict[str, str]:
        prompt = action.arguments.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("invoke_model requires a non-empty prompt")
        return {"text": await model_backend.complete(prompt)}

    def read_artifact(action: SemanticAction) -> dict[str, str]:
        if len(action.inputs) != 1:
            raise ValueError("read_artifact requires exactly one input")
        artifact = store.get(action.inputs[0])
        try:
            text = artifact.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("read_artifact only supports UTF-8 text in M2") from exc
        return {"text": text}

    registry.register(invoke_model_spec(), invoke_model)
    registry.register(read_artifact_spec(), read_artifact)
    register_structured_operators(registry, store)
    register_retrieval_operators(registry, store)
    register_media_operators(registry, store, media_backend)
    app = FastAPI(title=f"Infra Joint Worker: {agent_id}", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/state", response_model=WorkerStateResponse)
    async def state() -> WorkerStateResponse:
        return WorkerStateResponse(
            agent_id=agent_id,
            available=True,
            in_flight=in_flight,
            operators=tuple(sorted(registry)),
            deployment_ids=tuple(sorted(deployment_ids)),
            artifact_ids=store.ids(),
        )

    @app.get("/artifact/{artifact_id}")
    async def get_artifact(artifact_id: str) -> Response:
        try:
            artifact = store.get(artifact_id)
        except ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="artifact not found") from exc
        return Response(
            content=artifact.content,
            media_type=artifact.media_type,
            headers={"x-artifact-sha256": artifact.sha256_hex},
        )

    @app.post("/artifact/pull", response_model=PullArtifactResponse)
    async def pull_artifact(request: PullArtifactRequest) -> PullArtifactResponse:
        if artifact_fetcher is None:
            raise HTTPException(status_code=501, detail="artifact pulling is not configured")
        try:
            fetched = await artifact_fetcher.fetch(request.source_url)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        artifact = StoredArtifact.create(
            artifact_id=request.artifact_id,
            media_type=fetched.media_type,
            content=fetched.content,
        )
        expected = request.expected_sha256 or fetched.sha256_hex
        if expected is not None and artifact.sha256_hex != expected:
            raise HTTPException(status_code=409, detail="artifact checksum mismatch")
        store.put(artifact)
        return PullArtifactResponse(
            artifact_id=artifact.artifact_id,
            size_bytes=len(artifact.content),
            sha256_hex=artifact.sha256_hex,
        )

    @app.post("/execute/operator", response_model=ExecuteOperatorResponse)
    async def execute(request: ExecuteOperatorRequest) -> ExecuteOperatorResponse:
        nonlocal in_flight
        if request.deployment_id is not None and request.deployment_id not in deployment_ids:
            raise HTTPException(status_code=409, detail="deployment is not available")
        try:
            binding = registry.binding(request.action.operator)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        in_flight += 1
        try:
            result = binding.handler(request.action)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                raise TypeError("operator handler must return a dictionary")
            output = cast(dict[str, Any], result)
            return ExecuteOperatorResponse(operator=request.action.operator, output=output)
        except ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail="input artifact not found") from exc
        except MediaExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            in_flight -= 1

    return app
