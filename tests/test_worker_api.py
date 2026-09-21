import httpx
import pytest

from infra_joint.worker.model_backend import StaticModelBackend
from infra_joint.worker.server import create_worker_app


@pytest.mark.asyncio
async def test_worker_rejects_unknown_deployment() -> None:
    app = create_worker_app(
        "worker",
        StaticModelBackend("A"),
        deployment_ids=("known",),
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
    assert response.json()["detail"] == "deployment is not available"


@pytest.mark.asyncio
async def test_worker_reports_missing_local_artifact() -> None:
    app = create_worker_app("worker", StaticModelBackend("unused"))
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
    assert response.json()["detail"] == "input artifact not found"


@pytest.mark.asyncio
async def test_worker_rejects_action_that_violates_registry_schema() -> None:
    app = create_worker_app("worker", StaticModelBackend("unused"))
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
    assert "required property" in response.json()["detail"]
