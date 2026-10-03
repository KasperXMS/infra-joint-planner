import sys
from contextlib import AsyncExitStack
from inspect import signature
from pathlib import Path
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from diagnose_http_keepalive_v1 import probe_pair  # noqa: E402
from resource_blind_live_validation_v1 import _clients  # noqa: E402

from infra_joint.runtime.client import (
    WORKER_HTTP_KEEPALIVE_EXPIRY_SECONDS,
    HttpWorkerClient,
    worker_http_limits,
)


def test_worker_idle_expiry_preserves_default_connection_concurrency() -> None:
    limits = worker_http_limits()
    default = signature(httpx.AsyncClient).parameters["limits"].default
    assert limits.max_connections == default.max_connections == 100
    assert limits.max_keepalive_connections == default.max_keepalive_connections == 20
    assert limits.keepalive_expiry == WORKER_HTTP_KEEPALIVE_EXPIRY_SECONDS == 4


@pytest.mark.asyncio
async def test_native_worker_client_factory_uses_shared_transport_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any]] = []
    original = httpx.AsyncClient

    def capture(**kwargs: Any) -> httpx.AsyncClient:
        captured.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr("resource_blind_live_validation_v1.httpx.AsyncClient", capture)
    async with AsyncExitStack() as stack:
        clients = await _clients(
            stack, {"one": "http://one", "two": "http://two"}, timeout_seconds=1200,
        )
        assert set(clients) == {"one", "two"}
    assert len(captured) == 2
    for kwargs in captured:
        assert kwargs["limits"].keepalive_expiry == 4
        assert kwargs["limits"].max_connections == 100
        assert kwargs["limits"].max_keepalive_connections == 20
        assert kwargs["timeout"] == 1200 and kwargs["trust_env"] is False


@pytest.mark.asyncio
async def test_transport_patch_does_not_retry_failed_worker_state_request() -> None:
    calls = 0

    async def fail(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.RemoteProtocolError("peer disconnected", request=request)

    async with httpx.AsyncClient(
        base_url="http://worker", transport=httpx.MockTransport(fail),
        limits=worker_http_limits(),
    ) as http:
        with pytest.raises(httpx.RemoteProtocolError):
            await HttpWorkerClient("worker", http).get_state()
    assert calls == 1


@pytest.mark.asyncio
async def test_real_worker_limits_expire_idle_connection_before_peer_timeout() -> None:
    result = await probe_pair(client_expiry=4, limits=worker_http_limits())
    assert result["second_request"] == "PASS"
    assert result["second_request_tcp_connect_count"] == 1
    assert result["trace_events"].count("http11.send_request_headers.started") == 1
