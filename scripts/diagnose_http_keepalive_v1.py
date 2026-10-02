"""Synthetic loopback transport counterexample, never a benchmark or Worker retry."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
from pathlib import Path
from typing import Any

import httpx
import uvicorn


async def healthy_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    del receive
    if scope["type"] != "http":
        raise ValueError("HTTP-only diagnostic")
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": b'{"healthy":true}'})


async def probe_pair(*, client_expiry: float) -> dict[str, Any]:
    """Compare idle reuse with/without client expiry; delayed write is explicit."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.setblocking(False)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        healthy_app, lifespan="off", access_log=False, log_level="error",
        timeout_keep_alive=5,
    ))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    trace: list[str] = []
    try:
        for _ in range(200):
            if server.started:
                break
            await asyncio.sleep(0.01)
        if not server.started:
            raise RuntimeError("diagnostic server did not start")
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2,
            limits=httpx.Limits(keepalive_expiry=client_expiry),
        ) as client:
            first = await client.get("/state")
            first.raise_for_status()
            await asyncio.sleep(4.8)

            async def delayed_headers(name: str, info: dict[str, Any]) -> None:
                del info
                trace.append(name)
                if name == "http11.send_request_headers.started":
                    # Counterexample only: make the peer expire after pool checkout.
                    # This is not tc shaping, measured production RTT, or a retry.
                    await asyncio.sleep(0.4)

            try:
                second = await client.get("/state", extensions={"trace": delayed_headers})
                second.raise_for_status()
                outcome = "PASS"
                error = None
            except httpx.HTTPError as exc:
                outcome = type(exc).__name__
                error = str(exc)
        return {"client_keepalive_expiry_seconds": client_expiry,
                "server_keepalive_seconds": 5, "idle_wait_seconds": 4.8,
                "injected_header_write_delay_seconds": 0.4,
                "first_request_status": first.status_code, "second_request": outcome,
                "error": error, "second_request_tcp_connect_count": trace.count(
                    "connection.connect_tcp.started"), "trace_events": trace}
    finally:
        server.should_exit = True
        await task
        sock.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("diagnostic evidence must not be overwritten")
    results = [await probe_pair(client_expiry=value) for value in (5, 4)]
    evidence = {"classification": "synthetic mechanism diagnostic, not historical root-cause proof",
                "real_network_shaping": False, "benchmark_calls": 0,
                "model_calls": 0, "formal_attempts": 0, "results": results,
                "httpx_version": httpx.__version__, "uvicorn_version": uvicorn.__version__}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    print(json.dumps(evidence))


if __name__ == "__main__":
    asyncio.run(main())
