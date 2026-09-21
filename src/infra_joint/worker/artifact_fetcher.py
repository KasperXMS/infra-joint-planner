from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class FetchedArtifact:
    content: bytes
    media_type: str
    sha256_hex: str | None


class ArtifactFetcher(Protocol):
    async def fetch(self, source_url: str) -> FetchedArtifact: ...


class HttpArtifactFetcher:
    """HTTP fetcher with an explicit host allowlist to constrain worker-side pulls."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        allowed_hosts: frozenset[str],
    ) -> None:
        if not allowed_hosts:
            raise ValueError("allowed_hosts must not be empty")
        self._client = client
        self._allowed_hosts = allowed_hosts

    async def fetch(self, source_url: str) -> FetchedArtifact:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in self._allowed_hosts:
            raise ValueError("artifact source URL is not allowed")
        response = await self._client.get(source_url)
        response.raise_for_status()
        media_type = response.headers.get("content-type", "application/octet-stream")
        media_type = media_type.split(";", maxsplit=1)[0]
        return FetchedArtifact(
            content=response.content,
            media_type=media_type,
            sha256_hex=response.headers.get("x-artifact-sha256"),
        )
