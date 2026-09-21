import os
from pathlib import Path
from typing import Annotated, Literal

import yaml
from openai import AsyncOpenAI
from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
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


class WorkerDeploymentConfig(ContractModel):
    model_id: str = Field(min_length=1)
    model: BackendConfig
    modalities: frozenset[str] = frozenset({"text"})
    context_window: int = Field(gt=0)
    reserved_output_tokens: int = Field(default=1024, gt=0)
    image_token_cost: int = Field(default=4096, gt=0)


class WorkerConfig(ContractModel):
    agent_id: str = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    artifact_root: Path
    deployments: dict[str, WorkerDeploymentConfig] = Field(default_factory=dict)
    allowed_artifact_hosts: frozenset[str] = frozenset()
    ffmpeg_executable: str | None = None
    max_read_artifact_bytes: int = Field(default=65_536, gt=0)


class PlannerConfig(ContractModel):
    model: BackendConfig


class RunnerConfig(ContractModel):
    environment: EnvironmentSpec
    worker_urls: dict[str, str]
    planner: PlannerConfig
    artifact_sources: dict[str, Path] = Field(default_factory=dict)
    output_root: Path
    max_planning_steps: int = Field(default=8, gt=0)
    http_timeout_seconds: float = Field(default=120, gt=0)

    @model_validator(mode="after")
    def workers_match_environment(self) -> "RunnerConfig":
        agent_ids = {agent.agent_id for agent in self.environment.agents}
        if set(self.worker_urls) != agent_ids:
            raise ValueError("worker_urls must exactly match EnvironmentSpec agents")
        return self


def load_worker_config(path: Path) -> WorkerConfig:
    with path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return WorkerConfig.model_validate(raw)


def load_planner_config(path: Path) -> PlannerConfig:
    with path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return PlannerConfig.model_validate(raw)


def load_runner_config(path: Path) -> RunnerConfig:
    with path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return RunnerConfig.model_validate(raw)


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
