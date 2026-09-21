import httpx
import pytest

from infra_joint.core.errors import ExecutionErrorCode, TypedExecutionError
from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.worker.model_backend import ModelDeployment, StaticModelBackend
from infra_joint.worker.server import create_worker_app


def model_deployment() -> ModelDeployment:
    return ModelDeployment(
        deployment_id="reader",
        model_id="reader-model",
        backend=StaticModelBackend("A"),
        modalities=frozenset({"text"}),
        context_window=4096,
        reserved_output_tokens=512,
        image_token_cost=4096,
    )


def environment(model_id: str = "reader-model") -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="worker",
                device="test",
                capabilities=frozenset({"model", "structured", "retrieval", "media.image"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="reader",
                agent_id="worker",
                model_id=model_id,
                context_window=4096,
                reserved_output_tokens=512,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_surface_validation_accepts_exact_operator_and_deployment_contract() -> None:
    app = create_worker_app("worker", {"reader": model_deployment()})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        states = await validate_worker_surfaces(
            environment(),
            build_operator_catalog(),
            {"worker": HttpWorkerClient("worker", client)},
        )

    assert states["worker"].deployments[0].model_id == "reader-model"


@pytest.mark.asyncio
async def test_surface_validation_rejects_deployment_contract_mismatch() -> None:
    app = create_worker_app("worker", {"reader": model_deployment()})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        with pytest.raises(TypedExecutionError) as error:
            await validate_worker_surfaces(
                environment(model_id="another-model"),
                build_operator_catalog(),
                {"worker": HttpWorkerClient("worker", client)},
            )

    assert error.value.code == ExecutionErrorCode.SURFACE_MISMATCH
