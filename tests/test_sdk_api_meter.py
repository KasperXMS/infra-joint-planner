import asyncio
import json
from decimal import Decimal
from typing import Any

import agents
import httpx
import pytest
from openai import AsyncOpenAI
from test_api_cost import fx, price
from test_native_predecision import SyntheticSDKModel

from infra_joint.experiments.sdk_api_meter import RawSDKAPIMeter, metered_sdk


def usage(count: int = 100) -> dict[str, Any]:
    return {"prompt_tokens": count, "completion_tokens": 2, "total_tokens": count + 2,
            "prompt_tokens_details": {"cached_tokens": 0}}


def build_meter() -> tuple[RawSDKAPIMeter, dict[tuple[str, str], Any]]:
    writes: dict[tuple[str, str], Any] = {}

    def sink(kind: str, identifier: str, value: object) -> None:
        assert (kind, identifier) not in writes
        writes[kind, identifier] = value

    qwen = price().model_copy(update={"model_id": "qwen3.8-max"})
    deepseek = price().model_copy(update={"model_id": "deepseek-v4-pro"})
    return RawSDKAPIMeter(provider=qwen.provider, region=qwen.region,
                         prices={qwen.model_id: qwen, deepseek.model_id: deepseek},
                         fx=fx(), private_sink=sink), writes


class HTTPDelegate:
    def __init__(self, client: httpx.AsyncClient, identifier: str,
                 result: object, count: int = 100) -> None:
        self.client, self.identifier, self.result, self.count = client, identifier, result, count
        self.arguments: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        self.arguments.append((args, kwargs))
        response = await self.client.post("https://synthetic.invalid/v1/chat/completions",
                                          json={"model": self.identifier, "count": self.count},
                                          headers={"Authorization": "Bearer DO-NOT-STORE"})
        response.raise_for_status()
        return self.result


@pytest.mark.asyncio
async def test_parallel_recipient_usage_correlates_requests_not_completion_order() -> None:
    meter, writes = build_meter()
    first_started, second_finished = asyncio.Event(), asyncio.Event()

    async def transport(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["count"] == 111:
            first_started.set()
            await second_finished.wait()
        elif body["count"] == 222:
            await first_started.wait()
            second_finished.set()
        return httpx.Response(200, json={"model": body["model"], "usage": usage(body["count"])})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), event_hooks={
        "request": [meter.request_hook], "response": [meter.response_hook],
    }) as client:
        results = [object(), object(), object(), object()]
        models = [meter.model(HTTPDelegate(client, identifier, result, count),
                              recipient=recipient, agent_name=name, requested_model=identifier)
                  for identifier, result, count, recipient, name in [
                      ("deepseek-v4-pro", results[0], 111, "specialist", "one"),
                      ("deepseek-v4-pro", results[1], 222, "specialist", "two"),
                      ("deepseek-v4-pro", results[2], 333, "manager", "manager"),
                      ("qwen3.8-max", results[3], 444, "verifier", "blind_evidence_verifier")]]
        actual = await asyncio.gather(*(model.get_response(
            system_instructions="unchanged", input="synthetic", model_settings=None, tools=[],
            output_schema=None, handoffs=[], tracing=None, previous_response_id=None,
            conversation_id=None, prompt=None,
        ) for model in models))
    assert all(before is after for before, after in zip(results, actual, strict=True))
    rows = [row for (kind, _), row in writes.items() if kind == "usage"]
    assert next(row for row in rows if row["agent_name"] == "one")["usage"]["prompt_tokens"] == 111
    assert next(row for row in rows if row["agent_name"] == "two")["usage"]["prompt_tokens"] == 222
    assert len({row["call_id"] for row in rows}) == 4
    assert meter.summary()["roles"]["specialist"]["calls"] == 2
    assert meter.summary()["roles"]["verifier"]["calls"] == 1
    assert meter.summary()["roles"]["all"]["known_usd_calls"] == 4
    assert "DO-NOT-STORE" not in json.dumps(list(writes.values()))


@pytest.mark.asyncio
async def test_real_chat_completions_model_gets_unmodified_response_and_raw_usage() -> None:
    meter, writes = build_meter()

    def transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "chat-synthetic", "object": "chat.completion",
            "created": 1, "model": "qwen3.8-max", "usage": usage(),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "Seven"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), event_hooks={
        "request": [meter.request_hook], "response": [meter.response_hook],
    }) as http_client, AsyncOpenAI(api_key="synthetic-secret", base_url="https://synthetic.invalid/v1",
                                 max_retries=0, http_client=http_client) as client:
        model = meter.model(agents.OpenAIChatCompletionsModel(model="qwen3.8-max",
                                                            openai_client=client),
                            recipient="manager", agent_name="manager",
                            requested_model="qwen3.8-max")
        result = await agents.Runner.run(agents.Agent(name="manager", instructions="Return seven.",
                                                     model=model), input="Synthetic input",
                                         max_turns=1)
    assert result.final_output == "Seven"
    assert meter.receipts[0].cost.usage.cached_input_tokens == 0
    assert len([kind for kind, _ in writes if kind == "request"]) == 1
    assert "synthetic-secret" not in json.dumps(list(writes.values()))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["transport", "http", "missing_usage", "identity"])
async def test_failed_or_missing_provider_usage_is_unknown_not_zero(kind: str) -> None:
    meter, writes = build_meter()

    def transport(request: httpx.Request) -> httpx.Response:
        if kind == "transport":
            raise httpx.ReadTimeout("secret must not be copied", request=request)
        if kind == "http":
            return httpx.Response(503, json={"error": {"type": "unavailable"}})
        return httpx.Response(200, json={"model": "changed-model" if kind == "identity"
                                        else "qwen3.8-max",
                                        **({"usage": usage()} if kind == "identity" else {})})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), event_hooks={
        "request": [meter.request_hook], "response": [meter.response_hook],
    }) as client:
        model = meter.model(HTTPDelegate(client, "qwen3.8-max", object()), recipient="manager",
                            agent_name="manager", requested_model="qwen3.8-max")
        if kind in {"transport", "http"}:
            with pytest.raises(httpx.HTTPError):
                await model.get_response()
        else:
            await model.get_response()
    assert len(meter.receipts) == 1 and meter.receipts[0].cost.usd_amount is None
    assert meter.summary()["roles"]["all"]["complete_usd_total"] is None
    assert meter.summary()["roles"]["all"]["known_usd_subtotal"] == str(Decimal(0))
    assert "secret must not be copied" not in json.dumps(list(writes.values()))


@pytest.mark.asyncio
async def test_no_http_failure_is_not_counted_as_an_api_call_and_scope_resets() -> None:
    meter, writes = build_meter()

    class Failing:
        async def get_response(self) -> None:
            raise ValueError("synthetic validation failure")

    model = meter.model(Failing(), recipient="manager", agent_name="manager",
                        requested_model="qwen3.8-max")
    with pytest.raises(ValueError):
        await model.get_response()
    assert not meter.receipts and meter.model_attempts[0]["http_calls"] == 0
    with pytest.raises(RuntimeError, match="unscoped"):
        await meter.request_hook(httpx.Request("POST", "https://synthetic.invalid", json={}))
    assert len(writes) == 1


def test_sdk_facade_preserves_tools_settings_instructions_and_rejects_unknown_recipient() -> None:
    meter, _ = build_meter()
    sdk = metered_sdk(agents, meter, manager_model="deepseek-v4-pro")
    assert sdk.Runner is agents.Runner and sdk.FunctionTool is agents.FunctionTool
    settings = agents.ModelSettings(parallel_tool_calls=True)
    agent = sdk.Agent(name="manager", instructions="FROZEN", model=SyntheticSDKModel(),
                      tools=[], model_settings=settings)
    assert agent.instructions == "FROZEN" and agent.model_settings is settings
    assert agent.tools == []
    with pytest.raises(ValueError, match="unexpected native Agent"):
        sdk.Agent(name="unknown", model=SyntheticSDKModel())
