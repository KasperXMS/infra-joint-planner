from collections.abc import Callable
from typing import Protocol

from openai import AsyncOpenAI


class ModelBackend(Protocol):
    async def complete(self, prompt: str) -> str: ...


class StaticModelBackend:
    """Deterministic backend for integration tests and substrate validation."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(self, prompt: str) -> str:
        del prompt
        return self._response


class ModelInputLimitError(ValueError):
    pass


class OpenAICompatibleModelBackend:
    """Explicitly configured OpenAI-compatible backend with optional exact token guard."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        *,
        max_input_tokens: int | None = None,
        token_counter: Callable[[str], int] | None = None,
    ) -> None:
        if not model:
            raise ValueError("model must not be empty")
        if (max_input_tokens is None) != (token_counter is None):
            raise ValueError("max_input_tokens and token_counter must be configured together")
        if max_input_tokens is not None and max_input_tokens < 1:
            raise ValueError("max_input_tokens must be positive")
        self._client = client
        self._model = model
        self._max_input_tokens = max_input_tokens
        self._token_counter = token_counter

    async def complete(self, prompt: str) -> str:
        if self._token_counter is not None and self._max_input_tokens is not None:
            token_count = self._token_counter(prompt)
            if token_count > self._max_input_tokens:
                raise ModelInputLimitError(
                    f"input has {token_count} tokens; limit is {self._max_input_tokens}"
                )
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = completion.choices[0].message.content
        if content is None:
            raise RuntimeError("model returned no text content")
        return content
