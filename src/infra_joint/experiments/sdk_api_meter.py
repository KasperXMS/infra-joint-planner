"""Pass-through, recipient-scoped raw HTTP accounting for frozen SDK experiments.

This module never builds Agent inputs or changes an SDK response. Raw payloads
are sent only to an experiment-owned private sink; credentials/headers are not
persisted. ContextVar scopes correlate concurrent specialists without relying on
request completion order. SDK defaults are never a source of provider usage.
"""

import json
from collections.abc import AsyncIterator, Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx
from agents import Model

from infra_joint.experiments.api_cost import (
    APICostReceipt,
    APIPriceCard,
    FXReference,
    Recipient,
    estimate_api_cost,
    summarize_api_costs,
)

PrivateSink = Callable[[str, str, object], None]


@dataclass
class _Scope:
    scope_id: str
    recipient: Recipient
    agent_name: str
    requested_model: str
    requests: dict[str, httpx.Request] = field(default_factory=lambda: dict[str, httpx.Request]())
    completed: set[str] = field(default_factory=lambda: set[str]())


def _mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


class RawSDKAPIMeter:
    """One meter per run, shared by both exact models and all SDK recipients."""

    def __init__(
        self, *, provider: str, region: str, prices: Mapping[str, APIPriceCard],
        fx: FXReference | None, private_sink: PrivateSink,
    ) -> None:
        self.provider, self.region = provider, region
        self.prices, self.fx = dict(prices), fx
        self._sink = private_sink
        self._scope: ContextVar[_Scope | None] = ContextVar("sdk_api_meter_scope", default=None)
        self.receipts: list[APICostReceipt] = []
        self.model_attempts: list[dict[str, object]] = []

    def model(self, delegate: object, *, recipient: Recipient, agent_name: str,
              requested_model: str) -> Model:
        return _ScopedSDKModel(delegate, self, recipient, agent_name, requested_model)

    async def request_hook(self, request: httpx.Request) -> None:
        scope = self._scope.get()
        if scope is None:
            raise RuntimeError("unscoped SDK API request: recipient accounting unavailable")
        call_id = f"{scope.scope_id}-{len(scope.requests) + 1}"
        scope.requests[call_id] = request
        request.extensions["raw_sdk_api_meter"] = {
            "scope": scope, "call_id": call_id, "started": perf_counter(),
            "started_utc": datetime.now(UTC).isoformat(),
        }
        # Do not store headers, auth, URL query strings or an exception's text.
        self._sink("request", call_id, json.loads(request.content))

    async def response_hook(self, response: httpx.Response) -> None:
        await response.aread()  # Frozen non-streaming path; SDK receives the same bytes.
        try:
            payload: object = response.json()
        except ValueError:
            payload = {"non_json_response": response.text}
        self._record(response.request, response=response, payload=payload)

    def _record(
        self, request: httpx.Request, *, response: httpx.Response | None = None,
        payload: object = None, error_type: str | None = None,
    ) -> None:
        metadata = cast(dict[str, Any], request.extensions["raw_sdk_api_meter"])
        scope = cast(_Scope, metadata["scope"])
        call_id = str(metadata["call_id"])
        if call_id in scope.completed:
            raise RuntimeError("duplicate provider receipt")
        body = _mapping(payload)
        response_model = body.get("model") if body is not None else None
        raw_usage = _mapping(body.get("usage")) if body is not None else None
        request_body = _mapping(json.loads(request.content))
        request_model = request_body.get("model") if request_body is not None else None
        # Model identity drift remains explicit, never priced as the intended model.
        actual_request_model = request_model if isinstance(request_model, str) else "unreported"
        cost = estimate_api_cost(
            raw_usage, self.prices.get(scope.requested_model), self.fx,
            provider=self.provider, region=self.region, requested_model=actual_request_model,
            response_model=response_model if isinstance(response_model, str) else None,
        )
        receipt = APICostReceipt(call_id=call_id, recipient=scope.recipient, cost=cost)
        self._sink("response", call_id, payload)
        self._sink("usage", call_id, {
            "scope_id": scope.scope_id, "call_id": call_id, "recipient": scope.recipient,
            "agent_name": scope.agent_name, "intended_model": scope.requested_model,
            "requested_model": actual_request_model, "response_model": response_model,
            "started_utc": metadata["started_utc"],
            "finished_utc": datetime.now(UTC).isoformat(),
            "latency_ms": (perf_counter() - float(metadata["started"])) * 1000,
            "status": response.status_code if response is not None else None,
            "request_id": response.headers.get("x-request-id") if response is not None else None,
            "usage": raw_usage, "error_type": error_type,
            "cost_receipt": receipt.model_dump(mode="json"),
        })
        self.receipts.append(receipt)
        scope.completed.add(call_id)

    def summary(self) -> dict[str, object]:
        return {"roles": {role: row.model_dump(mode="json")
                          for role, row in summarize_api_costs(self.receipts).items()},
                "model_attempts": list(self.model_attempts),
                "usage_source": "raw_provider_HTTP_response",
                "logical_feedback": False}

    async def scoped_response(
        self, delegate: Any, recipient: Recipient, agent_name: str, requested_model: str,
        *args: Any, **kwargs: Any,
    ) -> Any:
        scope = _Scope(uuid4().hex, recipient, agent_name, requested_model)
        token = self._scope.set(scope)
        started = perf_counter()
        error_type = None
        try:
            return await delegate.get_response(*args, **kwargs)
        except BaseException as error:
            error_type = type(error).__name__
            raise
        finally:
            self._scope.reset(token)
            for call_id, request in scope.requests.items():
                if call_id not in scope.completed:
                    self._record(request, error_type=error_type or "response_unobserved")
            attempt: dict[str, object] = {
                "scope_id": scope.scope_id, "recipient": scope.recipient,
                "agent_name": scope.agent_name, "requested_model": scope.requested_model,
                "http_calls": len(scope.requests), "error_type": error_type,
                "latency_ms": (perf_counter() - started) * 1000,
            }
            self._sink("model-attempt", scope.scope_id, attempt)
            self.model_attempts.append(attempt)


class _ScopedSDKModel(Model):
    def __init__(self, delegate: object, meter: RawSDKAPIMeter, recipient: Recipient,
                 agent_name: str, requested_model: str) -> None:
        self._delegate = cast(Any, delegate)
        self._meter = meter
        self._recipient: Recipient = recipient
        self._agent_name, self._requested_model = agent_name, requested_model

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        return await self._meter.scoped_response(
            self._delegate, self._recipient, self._agent_name, self._requested_model,
            *args, **kwargs,
        )

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        del args, kwargs
        raise RuntimeError("raw SDK accounting requires the frozen non-streaming path")
        yield  # pragma: no cover


def metered_sdk(
    sdk: object, meter: RawSDKAPIMeter, *, manager_model: str, root_agent_name: str = "manager",
) -> object:
    """SDK construction facade, not a replacement runner or logical runtime.

    All original SDK objects except the Agent constructor are identical. Existing
    method wrappers can still wrap the scoped model; accounting does not modify
    tools, instructions, model settings, hooks or method-specific input filters.
    Construct the fixed Verifier independently with meter.model(..., verifier).
    """
    original_constructor = sdk.__dict__["Agent"]

    def construct_agent(*args: Any, **kwargs: Any) -> object:
        name = str(kwargs["name"])
        if name not in {root_agent_name, "bounded_specialist"}:
            raise ValueError("unexpected native Agent recipient; cannot silently assign cost")
        result = original_constructor(*args, **kwargs)
        result.model = meter.model(
            result.model, recipient="manager" if name == root_agent_name else "specialist",
            agent_name=name, requested_model=manager_model,
        )
        return result

    attributes = dict(sdk.__dict__)
    attributes["Agent"] = construct_agent
    return SimpleNamespace(**attributes)
