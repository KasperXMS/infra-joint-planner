import hashlib
import json

import httpx
import pytest

from infra_joint.experiments.manager_context import (
    ManagerContextError,
    ManagerContextLimitExceeded,
)
from scripts.multiscale_planner_context_v1 import (
    MultiscaleContextConfig,
    MultiscaleContextPreflight,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("count,drift", [(30720, False), (30721, False), (100, True)])
async def test_native_reasoning_mapping_parser_pin_and_exact_inference_wire(count, drift):
    rendered = []
    forwarded = []

    def helper(request):
        path = request.url.path
        if path == "/api/ps":
            value = {
                "models": [{"name": "manager:latest", "digest": "pinned", "context_length": 32768}]
            }
        elif path == "/props":
            value = {"default_generation_settings": {"n_ctx": 32768}, "model_path": "/weights"}
        elif path == "/api/show":
            value = {
                "template": "template",
                "modelfile": "RENDERER qwen3.5\nPARSER " + ("wrong" if drift else "qwen3.5") + "\n",
            }
        elif path == "/api/chat":
            native = json.loads(request.content)
            assert native["think"] is False
            assert native["truncate"] is False
            assert native["_debug_render_only"] is True
            rendered.append(native)
            value = {"done": False, "_debug_info": {"rendered_template": "whole prompt"}}
        elif path == "/tokenize":
            value = {"tokens": [1] * count}
        else:
            raise AssertionError(path)
        return httpx.Response(200, json=value)

    def inference(request):
        forwarded.append(request.content)
        return httpx.Response(200, json={"usage": {"prompt_tokens": count}})

    config = MultiscaleContextConfig(
        model="manager",
        digest="pinned",
        model_blob="weights",
        template_sha256=hashlib.sha256(b"template").hexdigest(),
        ollama_url="http://ollama",
        runner_url="http://runner",
        renderer="qwen3.5",
        parser="qwen3.5",
        disable_thinking=True,
    )
    raw = (
        b'{"model":"manager","max_tokens":2048,"reasoning_effort":"none",'
        b'"messages":[{"role":"user","content":"unchanged"}]}'
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(helper)) as helpers:
        guard = MultiscaleContextPreflight(config, helpers)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(inference),
            event_hooks={
                "request": [guard.request_hook],
                "response": [guard.response_hook],
            },
        ) as client:
            if drift:
                with pytest.raises(ManagerContextError, match="parser changed"):
                    await client.post("http://ollama/v1/chat/completions", content=raw)
                assert not forwarded and not rendered
            elif count > 30720:
                with pytest.raises(ManagerContextLimitExceeded):
                    await client.post("http://ollama/v1/chat/completions", content=raw)
                assert not forwarded
            else:
                await client.post("http://ollama/v1/chat/completions", content=raw)
                assert forwarded == [raw]
                assert guard.receipts[0]["integrity_verified"]
