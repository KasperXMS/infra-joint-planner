import os
from pathlib import Path
from typing import Annotated, Literal

import yaml
from openai import AsyncOpenAI
from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.worker.model_backend import (
    ModelBackend,
    OpenAICompatibleModelBackend,
    StaticModelBackend,
)


class StaticBackendConfig(ContractModel):
    backend: Literal["static"] = "static"
    response: str


class OpenAIBackendConfig(ContractModel):
    backend: Literal["openai_compatible"] = "openai_compatible"
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key_env: str = Field(default="OPENAI_API_KEY", min_length=1)


BackendConfig = Annotated[
    StaticBackendConfig | OpenAIBackendConfig,
    Field(discriminator="backend"),
]


class WorkerConfig(ContractModel):
    agent_id: str = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    artifact_root: Path
    deployment_ids: tuple[str, ...] = ()
    allowed_artifact_hosts: frozenset[str] = frozenset()
    model: BackendConfig


def load_worker_config(path: Path) -> WorkerConfig:
    with path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return WorkerConfig.model_validate(raw)


def build_model_backend(config: BackendConfig) -> tuple[ModelBackend, AsyncOpenAI | None]:
    if isinstance(config, StaticBackendConfig):
        return StaticModelBackend(config.response), None
    try:
        api_key = os.environ[config.api_key_env]
    except KeyError as exc:
        raise RuntimeError(
            f"required API key environment variable is not set: {config.api_key_env}"
        ) from exc
    client = AsyncOpenAI(api_key=api_key, base_url=config.base_url)
    return OpenAICompatibleModelBackend(client, config.model), client
