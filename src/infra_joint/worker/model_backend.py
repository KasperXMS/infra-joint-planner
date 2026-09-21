from typing import Protocol


class ModelBackend(Protocol):
    async def complete(self, prompt: str) -> str: ...


class StaticModelBackend:
    """Deterministic backend for integration tests and substrate validation."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(self, prompt: str) -> str:
        del prompt
        return self._response
