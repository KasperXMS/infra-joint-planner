import hashlib
import json

import httpx
import pytest

from infra_joint.experiments.manager_context import (
    ManagerContextConfig,
    ManagerContextError,
    ManagerContextIntegrityError,
    ManagerContextLimitExceeded,
    OllamaManagerContextPreflight,
    native_text_messages,
    truncation_events,
)


def config():
    return ManagerContextConfig(
        model="manager",
        digest="digest",
        model_blob="weights",
        template_sha256=hashlib.sha256(b"template").hexdigest(),
        ollama_url="http://ollama",
        runner_url="http://tokenizer",
    )


def helper_transport(count=30720, *, drift=False, bad_debug=False):
    def handle(request):
        if request.url.path == "/api/ps":
            body = {
                "models": [
                    {
                        "name": "manager:latest",
                        "digest": "wrong" if drift else "digest",
                        "context_length": 32768,
                    }
                ]
            }
        elif request.url.path == "/props":
            body = {"default_generation_settings": {"n_ctx": 32768}, "model_path": "/weights"}
        elif request.url.path == "/api/show":
            body = {
                "template": "template",
                "modelfile": "RENDERER qwen3-vl-instruct\nPARSER qwen3-vl-instruct\n",
            }
        elif request.url.path == "/api/chat":
            wire = json.loads(request.content)
            assert wire["truncate"] is False
            assert wire["_debug_render_only"] is True
            assert wire["options"] == {"num_ctx": 32768, "num_predict": 2048}
            body = {"done": bad_debug, "_debug_info": {"rendered_template": "full prompt"}}
        elif request.url.path == "/tokenize":
            assert json.loads(request.content)["add_special"]
            body = {"tokens": [1] * count}
        else:
            raise AssertionError(request.url)
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handle)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,allowed",
    [(8192, True), (16384, True), (24576, True), (30720, True), (30721, False), (42272, False)],
)
async def test_context_budget_and_final_wire_preservation(count, allowed):
    calls = []
    raw = (
        b'{"model":"manager","messages":[{"role":"user","content":"unchanged"}],"max_tokens":2048}'
    )

    def infer(request):
        calls.append(request.content)
        return httpx.Response(200, json={"usage": {"prompt_tokens": count}})

    async with httpx.AsyncClient(transport=helper_transport(count)) as helper:
        guard = OllamaManagerContextPreflight(config(), helper)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(infer),
            event_hooks={"request": [guard.request_hook], "response": [guard.response_hook]},
        ) as client:
            if allowed:
                await client.post("http://ollama/v1/chat/completions", content=raw)
                assert calls == [raw]
                assert guard.receipts[0]["integrity_verified"]
            else:
                with pytest.raises(ManagerContextLimitExceeded, match="context_limit_exceeded"):
                    await client.post("http://ollama/v1/chat/completions", content=raw)
                assert calls == []
                assert not guard.receipts[0]["inference_forwarded"]


@pytest.mark.asyncio
@pytest.mark.parametrize("drift,bad_debug", [(True, False), (False, True)])
async def test_unknown_residency_or_accidental_generation_fails_closed(drift, bad_debug):
    async with httpx.AsyncClient(
        transport=helper_transport(drift=drift, bad_debug=bad_debug)
    ) as helper:
        guard = OllamaManagerContextPreflight(config(), helper)
        with pytest.raises(ManagerContextError):
            await guard.inspect(
                {
                    "model": "manager",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": "test"}],
                }
            )


@pytest.mark.asyncio
async def test_provider_usage_mismatch_never_reaches_sdk_consumer():
    async with httpx.AsyncClient(transport=helper_transport(24576)) as helper:
        guard = OllamaManagerContextPreflight(config(), helper)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"usage": {"prompt_tokens": 16386}})
            ),
            event_hooks={"request": [guard.request_hook], "response": [guard.response_hook]},
        ) as client:
            with pytest.raises(ManagerContextIntegrityError):
                await client.post(
                    "http://ollama/v1/chat/completions",
                    json={
                        "model": "manager",
                        "max_tokens": 2048,
                        "messages": [{"role": "user", "content": "test"}],
                    },
                )


def test_text_tool_history_conversion_preserves_call_identity_and_argument_values():
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}],
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "id1",
                    "type": "function",
                    "function": {"name": "read_artifact", "arguments": '{"inputs":["x"]}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "id1", "content": '{"succeeded":false}'},
    ]
    native = native_text_messages(messages)
    assert [m.get("content") for m in native[:2]] == ["one", "two"]
    assert native[2]["tool_calls"][0]["function"]["arguments"] == {"inputs": ["x"]}
    assert native[3]["tool_name"] == "read_artifact"
    assert native[3]["tool_call_id"] == "id1"
    assert messages[1]["tool_calls"][0]["function"]["arguments"] == '{"inputs":["x"]}'
    with pytest.raises(ManagerContextError, match="only supports text"):
        native_text_messages(
            [
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": "private://image"}}],
                }
            ]
        )


def test_log_parser_does_not_treat_zero_truncation_as_a_failure():
    normal = "slot release: n_tokens = 30766, truncated = 0"
    old_warning = 'level=WARN msg="truncating input prompt" limit=16386 prompt=42272'
    assert truncation_events(normal) == []
    assert truncation_events(normal + "\n" + old_warning) == [old_warning]
    assert truncation_events("slot release: truncated = 7") == ["slot release: truncated = 7"]
