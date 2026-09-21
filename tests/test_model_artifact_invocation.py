import base64
import json

import httpx
import pytest
from openai import AsyncOpenAI

from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import (
    ModelArtifact,
    ModelCallTelemetry,
    ModelCompletion,
    ModelDeployment,
    ModelInputLimitError,
    ModelRequest,
    OpenAICompatibleModelBackend,
    preflight_model_request,
)
from infra_joint.worker.server import create_worker_app


class RecordingBackend:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        return ModelCompletion(
            text="artifact answer",
            telemetry=ModelCallTelemetry(
                service_latency_ms=2,
                input_tokens=12,
                output_tokens=3,
                finish_reason="stop",
            ),
        )

    async def complete(self, prompt: str) -> str:
        return (await self.invoke(ModelRequest(prompt=prompt))).text


def deployment(backend: RecordingBackend) -> ModelDeployment:
    return ModelDeployment(
        deployment_id="vision-reader",
        model_id="vision-model",
        backend=backend,
        modalities=frozenset({"text", "image"}),
        context_window=8192,
        reserved_output_tokens=512,
        image_token_cost=1024,
    )


@pytest.mark.asyncio
async def test_worker_model_consumes_local_text_and_image_artifacts() -> None:
    backend = RecordingBackend()
    store = InMemoryArtifactStore(
        (
            StoredArtifact.create("notes", "text/plain", b"important evidence"),
            StoredArtifact.create("frame", "image/png", b"fake-png"),
        )
    )
    app = create_worker_app(
        "worker",
        {"vision-reader": deployment(backend)},
        artifact_store=store,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/execute/operator",
            json={
                "action": {
                    "operator": "invoke_model",
                    "inputs": ["notes", "frame"],
                    "arguments": {"prompt": "Answer from both artifacts."},
                },
                "deployment_id": "vision-reader",
            },
        )

    assert response.status_code == 200
    assert response.json()["output"] == {"text": "artifact answer"}
    assert response.json()["model_telemetry"]["input_tokens"] == 12
    assert len(backend.requests) == 1
    assert [item.artifact_id for item in backend.requests[0].artifacts] == [
        "notes",
        "frame",
    ]


def test_context_preflight_fails_before_model_request() -> None:
    request = ModelRequest(
        prompt="question",
        artifacts=(ModelArtifact(artifact_id="large", media_type="text/plain", content=b"x" * 20),),
    )

    with pytest.raises(ModelInputLimitError, match="before request"):
        preflight_model_request(
            request,
            modalities=frozenset({"text"}),
            context_window=24,
            reserved_output_tokens=4,
            image_token_cost=1024,
        )


@pytest.mark.asyncio
async def test_openai_backend_builds_real_multimodal_request_and_records_usage() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-mm",
                "object": "chat.completion",
                "created": 1,
                "model": "vision-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 2, "total_tokens": 22},
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = AsyncOpenAI(
        api_key="test",
        base_url="http://model.test/v1",
        http_client=http_client,
    )
    backend = OpenAICompatibleModelBackend(client, "vision-model")
    try:
        completion = await backend.invoke(
            ModelRequest(
                prompt="question",
                artifacts=(
                    ModelArtifact(
                        artifact_id="doc",
                        media_type="application/json",
                        content=b'{"fact":"value"}',
                    ),
                    ModelArtifact(
                        artifact_id="image",
                        media_type="image/png",
                        content=b"png",
                    ),
                ),
                max_output_tokens=64,
            )
        )
    finally:
        await client.close()

    body = json.loads(requests[0].content)
    content = body["messages"][0]["content"]
    assert content[1]["text"].endswith('{"fact":"value"}')
    assert content[2]["image_url"]["url"] == (
        "data:image/png;base64," + base64.b64encode(b"png").decode("ascii")
    )
    assert body["max_tokens"] == 64
    assert completion.telemetry.input_tokens == 20
    assert completion.telemetry.output_tokens == 2
    assert completion.telemetry.finish_reason == "stop"
