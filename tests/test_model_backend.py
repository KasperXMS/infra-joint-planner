import json

import httpx
import pytest
from openai import AsyncOpenAI

from infra_joint.worker.model_backend import (
    ModelInputLimitError,
    OpenAICompatibleModelBackend,
)


@pytest.mark.asyncio
async def test_openai_compatible_backend_uses_injected_client() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "local-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "A"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    openai_client = AsyncOpenAI(
        api_key="injected-test-key",
        base_url="http://local-llm/v1",
        http_client=http_client,
    )
    backend = OpenAICompatibleModelBackend(openai_client, "local-model")
    try:
        result = await backend.complete("Choose one")
    finally:
        await openai_client.close()

    assert result == "A"
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["model"] == "local-model"
    assert body["messages"] == [{"role": "user", "content": "Choose one"}]


@pytest.mark.asyncio
async def test_model_input_limit_fails_before_request() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500, request=request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    openai_client = AsyncOpenAI(api_key="test", http_client=http_client)
    backend = OpenAICompatibleModelBackend(
        openai_client,
        "local-model",
        max_input_tokens=2,
        token_counter=lambda text: len(text.split()),
    )
    try:
        with pytest.raises(ModelInputLimitError, match="input has 3 tokens"):
            await backend.complete("one two three")
    finally:
        await openai_client.close()

    assert request_count == 0
