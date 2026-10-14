"""Study-owned HTTP data-path shaper for bounded Worker artifact probes.

This proxy only forwards GET /artifact requests to a local source Worker.
It imposes configured RTT and response-byte pacing without changing host tc.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import StreamingResponse


def create_app(upstream: str, bandwidth_mbps: float, added_rtt_ms: float) -> FastAPI:
    if bandwidth_mbps <= 0 or added_rtt_ms < 0:
        raise ValueError("invalid link profile")
    app = FastAPI()

    @app.get("/artifact/{artifact_id:path}")
    async def artifact(artifact_id: str, request: Request) -> StreamingResponse:
        client = httpx.AsyncClient(timeout=60.0)
        upstream_request = client.build_request(
            "GET",
            upstream.rstrip("/") + "/artifact/" + artifact_id,
            headers={
                "x-source-access-token": request.headers.get("x-source-access-token", "")
            },
        )
        try:
            response = await client.send(upstream_request, stream=True)
        except Exception:  # noqa: BLE001 - close client before crossing HTTP boundary
            await client.aclose()
            raise
        if response.status_code != 200:
            await response.aclose()
            await client.aclose()
            raise HTTPException(
                status_code=response.status_code, detail="upstream source read failed"
            )

        async def paced() -> AsyncIterator[bytes]:
            try:
                await asyncio.sleep(added_rtt_ms / 1000)
                async for chunk in response.aiter_bytes(chunk_size=65_536):
                    await asyncio.sleep(len(chunk) * 8 / (bandwidth_mbps * 1_000_000))
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(
            paced(),
            media_type=response.headers.get("content-type", "application/octet-stream"),
            headers={"x-artifact-sha256": response.headers.get("x-artifact-sha256", "")},
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--upstream", default="http://127.0.0.1:63104")
    parser.add_argument("--bandwidth-mbps", type=float, required=True)
    parser.add_argument("--added-rtt-ms", type=float, required=True)
    args = parser.parse_args()
    uvicorn.run(
        create_app(args.upstream, args.bandwidth_mbps, args.added_rtt_ms),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
