import httpx
import pytest

from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import ModelDeployment, StaticModelBackend
from infra_joint.worker.server import create_worker_app


def deployment(deployment_id: str = "known") -> ModelDeployment:
    return ModelDeployment(
        deployment_id=deployment_id,
        model_id="static-model",
        backend=StaticModelBackend("A"),
        modalities=frozenset({"text"}),
        context_window=4096,
        reserved_output_tokens=512,
        image_token_cost=4096,
    )


@pytest.mark.asyncio
async def test_worker_rejects_unknown_deployment() -> None:
    app = create_worker_app(
        "worker",
        {"known": deployment()},
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "invoke_model",
                    "inputs": [],
                    "arguments": {"prompt": "hello"},
                },
                "deployment_id": "missing",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "deployment_required"


@pytest.mark.asyncio
async def test_worker_reports_missing_local_artifact() -> None:
    app = create_worker_app("worker", {})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "read_artifact",
                    "inputs": ["missing"],
                    "arguments": {},
                }
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "missing_artifact"


@pytest.mark.asyncio
async def test_worker_rejects_action_that_violates_registry_schema() -> None:
    app = create_worker_app("worker", {})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "invoke_model",
                    "inputs": [],
                    "arguments": {},
                }
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_failed"
    assert "required property" in response.json()["detail"]["message"]


@pytest.mark.asyncio
async def test_read_artifact_fails_closed_above_explicit_limit() -> None:
    store = InMemoryArtifactStore((StoredArtifact.create("large", "text/plain", b"12345"),))
    app = create_worker_app(
        "worker",
        {},
        artifact_store=store,
        max_read_artifact_bytes=4,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "read_artifact",
                    "inputs": ["large"],
                    "arguments": {},
                }
            },
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "artifact_too_large"
