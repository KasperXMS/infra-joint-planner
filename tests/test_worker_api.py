import httpx
import pytest

from infra_joint.operators.media import MediaExecutionError
from infra_joint.runtime.client import HttpWorkerClient
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
async def test_worker_artifact_delete_is_idempotent() -> None:
    store = InMemoryArtifactStore(
        (StoredArtifact.create("temporary", "text/plain", b"payload"),)
    )
    app = create_worker_app("worker", {}, artifact_store=store)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as http_client:
        client = HttpWorkerClient("worker", http_client)
        assert await client.delete_artifact("temporary") is True
        assert await client.delete_artifact("temporary") is False

    assert store.ids() == ()


@pytest.mark.asyncio
async def test_worker_artifact_routes_preserve_ids_with_path_separators() -> None:
    artifact_id = "clipframe/frame-000001.jpg"
    store = InMemoryArtifactStore(
        (StoredArtifact.create(artifact_id, "image/jpeg", b"jpeg"),)
    )
    app = create_worker_app("worker", {}, artifact_store=store)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as http_client:
        client = HttpWorkerClient("worker", http_client)
        response = await http_client.get("/artifact/clipframe%2Fframe-000001.jpg")
        assert response.status_code == 200
        assert response.content == b"jpeg"
        assert await client.delete_artifact(artifact_id) is True

    assert store.ids() == ()


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


@pytest.mark.asyncio
async def test_media_failure_returns_typed_operator_reason() -> None:
    class FailingMediaBackend:
        async def sample_frames(self, *_args, **_kwargs) -> None:
            raise MediaExecutionError("decoder unavailable")

        async def extract_clip(self, *_args, **_kwargs) -> None:
            raise MediaExecutionError("decoder unavailable")

    store = InMemoryArtifactStore((StoredArtifact.create("video", "video/mp4", b"x"),))
    app = create_worker_app(
        "worker",
        {},
        artifact_store=store,
        media_backend=FailingMediaBackend(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "sample_frames",
                    "inputs": ["video"],
                    "arguments": {
                        "every_seconds": 1,
                        "max_frames": 1,
                        "output_prefix": "frames",
                    },
                }
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "operator_failed",
        "message": "decoder unavailable",
    }


@pytest.mark.asyncio
async def test_model_backend_failure_returns_typed_reason_without_backend_detail() -> None:
    class FailingModelBackend:
        async def invoke(self, _request):
            raise RuntimeError("secret backend detail")

        async def complete(self, _prompt):
            raise RuntimeError("secret backend detail")

    failing_deployment = deployment()
    object.__setattr__(failing_deployment, "backend", FailingModelBackend())
    app = create_worker_app("worker", {"known": failing_deployment})
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
                "deployment_id": "known",
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "model_service_error",
        "message": "model backend request failed: RuntimeError",
    }
