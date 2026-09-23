import inspect
import json
from typing import Any, cast

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import Field
from starlette.responses import Response

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.core.errors import ExecutionErrorCode, FailureDetail
from infra_joint.operators.builtin import invoke_model_spec, read_artifact_spec
from infra_joint.operators.media import MediaBackend, MediaExecutionError, register_media_operators
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.operators.retrieval import register_retrieval_operators
from infra_joint.operators.structured import register_structured_operators
from infra_joint.worker.artifact_fetcher import ArtifactFetcher
from infra_joint.worker.artifact_store import (
    ArtifactMetadata,
    ArtifactNotFoundError,
    ArtifactStore,
    InMemoryArtifactStore,
    StoredArtifact,
)
from infra_joint.worker.model_backend import (
    ModelArtifact,
    ModelCallTelemetry,
    ModelDeployment,
    ModelInputLimitError,
    ModelRequest,
    UnsupportedModelArtifactError,
    preflight_model_request,
)


class ExecuteOperatorRequest(ContractModel):
    action: SemanticAction
    deployment_id: str | None = None


class ExecuteOperatorResponse(ContractModel):
    operator: str
    output: dict[str, Any]
    model_telemetry: ModelCallTelemetry | None = None


class WorkerDeploymentState(ContractModel):
    deployment_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    modalities: frozenset[str]
    context_window: int = Field(gt=0)
    reserved_output_tokens: int = Field(gt=0)
    image_token_cost: int = Field(gt=0)


class WorkerStateResponse(ContractModel):
    agent_id: str = Field(min_length=1)
    available: bool
    in_flight: int = Field(ge=0)
    operators: tuple[str, ...]
    operator_contract_digests: dict[str, str] = Field(default_factory=dict)
    deployments: tuple[WorkerDeploymentState, ...]
    artifacts: tuple[ArtifactMetadata, ...]


class PullArtifactRequest(ContractModel):
    artifact_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PullArtifactResponse(ContractModel):
    artifact_id: str
    size_bytes: int = Field(ge=0)
    sha256_hex: str = Field(pattern=r"^[0-9a-f]{64}$")


class PutArtifactResponse(PullArtifactResponse):
    pass


def _failure(code: ExecutionErrorCode, message: str, status_code: int = 422) -> HTTPException:
    detail = FailureDetail(code=code, message=message)
    return HTTPException(status_code=status_code, detail=detail.model_dump(mode="json"))


def _artifact_metadata(store: ArtifactStore) -> tuple[ArtifactMetadata, ...]:
    return tuple(
        ArtifactMetadata(
            artifact_id=artifact.artifact_id,
            media_type=artifact.media_type,
            size_bytes=len(artifact.content),
            sha256_hex=artifact.sha256_hex,
        )
        for artifact in (store.get(artifact_id) for artifact_id in store.ids())
    )


def create_worker_app(
    agent_id: str,
    deployments: dict[str, ModelDeployment],
    *,
    artifact_store: ArtifactStore | None = None,
    artifact_fetcher: ArtifactFetcher | None = None,
    media_backend: MediaBackend | None = None,
    max_read_artifact_bytes: int = 65_536,
) -> FastAPI:
    if max_read_artifact_bytes < 1:
        raise ValueError("max_read_artifact_bytes must be positive")
    if set(deployments) != {item.deployment_id for item in deployments.values()}:
        raise ValueError("deployment mapping keys must match deployment IDs")
    registry = OperatorRegistry()
    store = artifact_store or InMemoryArtifactStore()
    in_flight = 0

    def read_artifact(action: SemanticAction) -> dict[str, str]:
        if len(action.inputs) != 1:
            raise ValueError("read_artifact requires exactly one input")
        artifact = store.get(action.inputs[0])
        if len(artifact.content) > max_read_artifact_bytes:
            raise HTTPException(
                status_code=413,
                detail=FailureDetail(
                    code=ExecutionErrorCode.ARTIFACT_TOO_LARGE,
                    message=(
                        f"artifact has {len(artifact.content)} bytes; "
                        f"read limit is {max_read_artifact_bytes}"
                    ),
                ).model_dump(mode="json"),
            )
        try:
            text = artifact.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("read_artifact supports only UTF-8 text") from exc
        return {"text": text}

    def model_marker(_: SemanticAction) -> None:
        raise RuntimeError("invoke_model is dispatched through its deployment")

    registry.register(invoke_model_spec(), model_marker)
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
            operator_contract_digests=registry.contract_digests(),
            deployments=tuple(
                WorkerDeploymentState(
                    deployment_id=item.deployment_id,
                    model_id=item.model_id,
                    modalities=item.modalities,
                    context_window=item.context_window,
                    reserved_output_tokens=item.reserved_output_tokens,
                    image_token_cost=item.image_token_cost,
                )
                for item in sorted(deployments.values(), key=lambda value: value.deployment_id)
            ),
            artifacts=_artifact_metadata(store),
        )

    @app.get("/artifact/{artifact_id}")
    async def get_artifact(artifact_id: str) -> Response:
        try:
            artifact = store.get(artifact_id)
        except ArtifactNotFoundError as exc:
            raise _failure(
                ExecutionErrorCode.MISSING_ARTIFACT,
                "artifact not found",
                404,
            ) from exc
        return Response(
            content=artifact.content,
            media_type=artifact.media_type,
            headers={"x-artifact-sha256": artifact.sha256_hex},
        )

    @app.put("/artifact/{artifact_id}", response_model=PutArtifactResponse)
    async def put_artifact(artifact_id: str, request: Request) -> PutArtifactResponse:
        content = await request.body()
        media_type = request.headers.get("content-type", "application/octet-stream")
        media_type = media_type.split(";", maxsplit=1)[0]
        artifact = StoredArtifact.create(artifact_id, media_type, content)
        expected = request.headers.get("x-artifact-sha256")
        if expected is not None and artifact.sha256_hex != expected:
            raise HTTPException(status_code=409, detail="artifact checksum mismatch")
        store.put(artifact)
        return PutArtifactResponse(
            artifact_id=artifact_id,
            size_bytes=len(content),
            sha256_hex=artifact.sha256_hex,
        )

    @app.delete("/artifact/{artifact_id}")
    async def delete_artifact(artifact_id: str) -> dict[str, bool | str]:
        return {"artifact_id": artifact_id, "deleted": store.delete(artifact_id)}

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

    async def invoke_model(
        action: SemanticAction,
        deployment_id: str | None,
    ) -> tuple[dict[str, Any], ModelCallTelemetry]:
        if deployment_id is None:
            raise _failure(
                ExecutionErrorCode.DEPLOYMENT_REQUIRED,
                "invoke_model requires a concrete deployment",
            )
        deployment = deployments.get(deployment_id)
        if deployment is None:
            raise _failure(
                ExecutionErrorCode.DEPLOYMENT_REQUIRED,
                f"deployment is not available: {deployment_id}",
                409,
            )
        prompt = action.arguments.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("invoke_model requires a non-empty prompt")
        artifacts = tuple(
            ModelArtifact(
                artifact_id=artifact.artifact_id,
                media_type=artifact.media_type,
                content=artifact.content,
            )
            for artifact in (store.get(artifact_id) for artifact_id in action.inputs)
        )
        model_request = ModelRequest(
            prompt=prompt,
            artifacts=artifacts,
            max_output_tokens=deployment.reserved_output_tokens,
        )
        try:
            preflight_model_request(
                model_request,
                modalities=deployment.modalities,
                context_window=deployment.context_window,
                reserved_output_tokens=deployment.reserved_output_tokens,
                image_token_cost=deployment.image_token_cost,
            )
            completion = await deployment.backend.invoke(model_request)
        except ModelInputLimitError as exc:
            raise _failure(ExecutionErrorCode.CONTEXT_LIMIT_EXCEEDED, str(exc)) from exc
        except UnsupportedModelArtifactError as exc:
            raise _failure(ExecutionErrorCode.UNSUPPORTED_MODALITY, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - backend failures cross an API boundary
            raise _failure(
                ExecutionErrorCode.MODEL_SERVICE_ERROR,
                f"model backend request failed: {type(exc).__name__}",
                502,
            ) from exc
        output: dict[str, Any] = {"text": completion.text}
        output_artifact_id = action.arguments.get("output_artifact_id")
        if output_artifact_id is not None:
            if not isinstance(output_artifact_id, str) or not output_artifact_id:
                raise ValueError("output_artifact_id must be a non-empty string")
            output_media_type = action.arguments.get("output_media_type", "text/plain")
            if output_media_type not in {"text/plain", "application/json"}:
                raise ValueError("model output supports only text/plain or application/json")
            if output_media_type == "application/json":
                try:
                    json.loads(completion.text)
                except json.JSONDecodeError as exc:
                    raise ValueError("model output is not valid JSON") from exc
            materialized = StoredArtifact.create(
                output_artifact_id,
                output_media_type,
                completion.text.encode("utf-8"),
            )
            store.put(materialized)
            output["artifacts"] = [
                {
                    "artifact_id": materialized.artifact_id,
                    "media_type": materialized.media_type,
                    "size_bytes": len(materialized.content),
                    "sha256_hex": materialized.sha256_hex,
                }
            ]
        return output, completion.telemetry

    @app.post("/execute/operator", response_model=ExecuteOperatorResponse)
    async def execute(request: ExecuteOperatorRequest) -> ExecuteOperatorResponse:
        nonlocal in_flight
        try:
            binding = registry.binding(request.action.operator)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        in_flight += 1
        try:
            registry.validate_action(request.action)
            if request.action.operator == "invoke_model":
                output, telemetry = await invoke_model(request.action, request.deployment_id)
                return ExecuteOperatorResponse(
                    operator=request.action.operator,
                    output=output,
                    model_telemetry=telemetry,
                )
            if request.deployment_id is not None:
                raise _failure(
                    ExecutionErrorCode.VALIDATION_FAILED,
                    "non-model operators must not specify a deployment",
                )
            result = binding.handler(request.action)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                raise TypeError("operator handler must return a dictionary")
            output = cast(dict[str, Any], result)
            return ExecuteOperatorResponse(operator=request.action.operator, output=output)
        except ArtifactNotFoundError as exc:
            raise _failure(
                ExecutionErrorCode.MISSING_ARTIFACT,
                f"input artifact not found: {exc.args[0]}",
                404,
            ) from exc
        except MediaExecutionError as exc:
            raise _failure(
                ExecutionErrorCode.OPERATOR_FAILED,
                str(exc),
                502,
            ) from exc
        except ValueError as exc:
            raise _failure(ExecutionErrorCode.VALIDATION_FAILED, str(exc)) from exc
        finally:
            in_flight -= 1

    return app
