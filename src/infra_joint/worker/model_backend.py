# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import base64
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol, cast

from openai import AsyncOpenAI
from pydantic import Field

from infra_joint.core.base import ContractModel


class ModelArtifact(ContractModel):
    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    content: bytes


class ModelRequest(ContractModel):
    prompt: str = Field(min_length=1)
    artifacts: tuple[ModelArtifact, ...] = ()
    max_output_tokens: int | None = Field(default=None, gt=0)


class ModelCallTelemetry(ContractModel):
    service_latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None


class ModelCompletion(ContractModel):
    text: str
    telemetry: ModelCallTelemetry


class ModelBackend(Protocol):
    async def invoke(self, request: ModelRequest) -> ModelCompletion: ...

    async def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True, slots=True)
class ModelDeployment:
    deployment_id: str
    model_id: str
    backend: ModelBackend
    modalities: frozenset[str]
    context_window: int
    reserved_output_tokens: int
    image_token_cost: int

    def __post_init__(self) -> None:
        if not self.deployment_id or not self.model_id:
            raise ValueError("deployment_id and model_id must not be empty")
        if "text" not in self.modalities:
            raise ValueError("every model deployment must support text prompts")
        if self.context_window < 1 or self.reserved_output_tokens < 1:
            raise ValueError("context and output token limits must be positive")
        if self.reserved_output_tokens >= self.context_window:
            raise ValueError("reserved output tokens must be smaller than context window")
        if self.image_token_cost < 1:
            raise ValueError("image_token_cost must be positive")


class StaticModelBackend:
    """Deterministic backend for integration tests and substrate validation."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        started = perf_counter()
        input_tokens = conservative_text_tokens(request.prompt)
        input_tokens += sum(artifact_token_upper_bound(item) for item in request.artifacts)
        return ModelCompletion(
            text=self._response,
            telemetry=ModelCallTelemetry(
                service_latency_ms=(perf_counter() - started) * 1000,
                input_tokens=input_tokens,
                output_tokens=conservative_text_tokens(self._response),
                finish_reason="stop",
            ),
        )

    async def complete(self, prompt: str) -> str:
        return (await self.invoke(ModelRequest(prompt=prompt))).text


class ModelInputLimitError(ValueError):
    pass


class UnsupportedModelArtifactError(ValueError):
    pass


def is_text_media_type(media_type: str) -> bool:
    return media_type.startswith("text/") or media_type in {
        "application/json",
        "application/jsonl",
        "application/x-ndjson",
    }


def artifact_modality(media_type: str) -> str:
    if is_text_media_type(media_type):
        return "text"
    if media_type.startswith("image/"):
        return "image"
    raise UnsupportedModelArtifactError(
        f"model artifacts support only text and image media types: {media_type}"
    )


def conservative_text_tokens(text: str) -> int:
    """Byte upper bound for byte-tokenizing model families; intentionally fail-closed."""

    return len(text.encode("utf-8"))


def artifact_token_upper_bound(
    artifact: ModelArtifact,
    *,
    image_token_cost: int = 4096,
) -> int:
    modality = artifact_modality(artifact.media_type)
    if modality == "image":
        return image_token_cost
    try:
        text = artifact.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedModelArtifactError(
            f"text artifact is not valid UTF-8: {artifact.artifact_id}"
        ) from exc
    return conservative_text_tokens(text)


def preflight_model_request(
    request: ModelRequest,
    *,
    modalities: frozenset[str],
    context_window: int,
    reserved_output_tokens: int,
    image_token_cost: int,
) -> int:
    required = {artifact_modality(item.media_type) for item in request.artifacts}
    if "text" not in modalities:
        raise UnsupportedModelArtifactError("deployment does not support text prompts")
    unsupported = required - modalities
    if unsupported:
        raise UnsupportedModelArtifactError(
            f"deployment does not support required modalities: {sorted(unsupported)}"
        )
    estimated = conservative_text_tokens(request.prompt) + sum(
        artifact_token_upper_bound(item, image_token_cost=image_token_cost)
        for item in request.artifacts
    )
    if estimated + reserved_output_tokens > context_window:
        raise ModelInputLimitError(
            "context limit exceeded before request: "
            f"estimated_input={estimated}, reserved_output={reserved_output_tokens}, "
            f"context_window={context_window}"
        )
    return estimated


class OpenAICompatibleModelBackend:
    """OpenAI-compatible text/image backend with explicit, non-truncating requests."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        *,
        max_input_tokens: int | None = None,
        token_counter: Callable[[str], int] | None = None,
        reasoning_effort: Literal["none", "low", "medium", "high"] | None = None,
        temperature: float | None = None,
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
        self._reasoning_effort = reasoning_effort
        self._temperature = temperature

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        if self._token_counter is not None and self._max_input_tokens is not None:
            countable = self._countable_text(request)
            token_count = self._token_counter(countable)
            if token_count > self._max_input_tokens:
                raise ModelInputLimitError(
                    f"input has {token_count} tokens; limit is {self._max_input_tokens}"
                )
        content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
        for artifact in request.artifacts:
            modality = artifact_modality(artifact.media_type)
            if modality == "text":
                try:
                    text = artifact.content.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise UnsupportedModelArtifactError(
                        f"text artifact is not valid UTF-8: {artifact.artifact_id}"
                    ) from exc
                content.append(
                    {
                        "type": "text",
                        "text": f"\n[Artifact {artifact.artifact_id}]\n{text}",
                    }
                )
            else:
                encoded = base64.b64encode(artifact.content).decode("ascii")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{artifact.media_type};base64,{encoded}",
                        },
                    }
                )
        arguments: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
        }
        if request.max_output_tokens is not None:
            arguments["max_tokens"] = request.max_output_tokens
        if self._reasoning_effort is not None:
            arguments["reasoning_effort"] = self._reasoning_effort
        if self._temperature is not None:
            arguments["temperature"] = self._temperature
        started = perf_counter()
        completion = await self._client.chat.completions.create(**cast(Any, arguments))
        latency_ms = (perf_counter() - started) * 1000
        choice = completion.choices[0]
        response_text = choice.message.content
        if response_text is None:
            raise RuntimeError("model returned no text content")
        usage = completion.usage
        return ModelCompletion(
            text=response_text,
            telemetry=ModelCallTelemetry(
                service_latency_ms=latency_ms,
                input_tokens=usage.prompt_tokens if usage is not None else None,
                output_tokens=usage.completion_tokens if usage is not None else None,
                finish_reason=choice.finish_reason,
            ),
        )

    async def complete(self, prompt: str) -> str:
        return (await self.invoke(ModelRequest(prompt=prompt))).text

    @staticmethod
    def _countable_text(request: ModelRequest) -> str:
        parts = [request.prompt]
        for artifact in request.artifacts:
            if is_text_media_type(artifact.media_type):
                try:
                    parts.append(artifact.content.decode("utf-8"))
                except UnicodeDecodeError as exc:
                    raise UnsupportedModelArtifactError(
                        f"text artifact is not valid UTF-8: {artifact.artifact_id}"
                    ) from exc
        return "\n".join(parts)
