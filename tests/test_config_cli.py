from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, InternalServerError
from pydantic import ValidationError
from typer.testing import CliRunner

from infra_joint.cli import app
from infra_joint.config import (
    OpenAIBackendConfig,
    PlannerConfig,
    build_model_backend,
    load_planner_config,
    load_worker_config,
)
from infra_joint.worker.model_backend import ModelRequest, StaticModelBackend


def test_load_static_worker_config(tmp_path: Path) -> None:
    config_path = tmp_path / "worker.yaml"
    config_path.write_text(
        """
agent_id: edge-a4
artifact_root: ./artifacts/a4
deployments:
  edge-model:
    model_id: static-model
    context_window: 4096
    model:
      backend: static
      response: A
""".strip(),
        encoding="utf-8",
    )

    config = load_worker_config(config_path)
    backend, client = build_model_backend(config.deployments["edge-model"].model)

    assert config.agent_id == "edge-a4"
    assert isinstance(backend, StaticModelBackend)
    assert client is None


def test_openai_config_requires_named_environment_variable(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_TEST_API_KEY", raising=False)
    config = OpenAIBackendConfig(
        base_url="http://localhost:11434/v1",
        model="local-model",
        api_key_env="MISSING_TEST_API_KEY",
    )

    with pytest.raises(RuntimeError, match="MISSING_TEST_API_KEY"):
        build_model_backend(config)


def test_load_planner_config_keeps_only_environment_variable_name(tmp_path: Path) -> None:
    config_path = tmp_path / "planner.yaml"
    config_path.write_text(
        "\n".join(
            (
                "model:",
                "  backend: openai_compatible",
                "  base_url: https://api.example.test/v1",
                "  model: cloud-model",
                "  api_key_env: TEST_PLANNER_API_KEY",
            )
        ),
        encoding="utf-8",
    )

    config = load_planner_config(config_path)

    assert isinstance(config, PlannerConfig)
    assert isinstance(config.model, OpenAIBackendConfig)
    assert config.model.api_key_env == "TEST_PLANNER_API_KEY"
    assert "secret" not in config.model.model_dump_json()


def test_openai_backend_config_preserves_explicit_non_thinking_mode() -> None:
    config = OpenAIBackendConfig(
        base_url="http://localhost:11434/v1",
        model="local-model",
        reasoning_effort="none",
        temperature=0,
    )

    assert config.reasoning_effort == "none"
    assert config.temperature == 0


@pytest.mark.asyncio
async def test_backend_factory_has_no_hidden_sdk_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_BACKEND_KEY", "test-only")
    _, client = build_model_backend(OpenAIBackendConfig(
        base_url="http://backend.test/v1", model="unchanged-model",
        api_key_env="TEST_BACKEND_KEY",
    ))
    assert client is not None
    try:
        assert client.max_retries == 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_backend_factory_uses_explicit_read_timeout_without_other_policy_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_BACKEND_KEY", "test-only")
    _, client = build_model_backend(OpenAIBackendConfig(
        base_url="http://backend.test/v1", model="unchanged-model",
        api_key_env="TEST_BACKEND_KEY", request_timeout_seconds=1200,
        reasoning_effort="none", temperature=0,
    ))
    assert client is not None
    try:
        assert client.max_retries == 0
        assert client.timeout == httpx.Timeout(600, connect=5, read=1200)
    finally:
        await client.close()


@pytest.mark.parametrize("timeout", [0, -1])
def test_backend_timeout_rejects_nonpositive_values(timeout: float) -> None:
    with pytest.raises(ValidationError):
        OpenAIBackendConfig(
            base_url="http://backend.test/v1", model="unchanged-model",
            request_timeout_seconds=timeout,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ["http_500", "read_timeout", "disconnect"])
async def test_backend_failure_reaches_caller_after_exactly_one_request(
    monkeypatch: pytest.MonkeyPatch, failure_kind: str,
) -> None:
    monkeypatch.setenv("TEST_BACKEND_KEY", "test-only")
    calls = 0

    async def fail(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if failure_kind == "read_timeout":
            raise httpx.ReadTimeout("diagnostic timeout", request=request)
        if failure_kind == "disconnect":
            raise httpx.RemoteProtocolError("diagnostic disconnect", request=request)
        return httpx.Response(500, json={"error": {"message": "diagnostic failure"}})

    def factory(**kwargs: Any) -> AsyncOpenAI:
        return AsyncOpenAI(
            **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(fail)),
        )

    monkeypatch.setattr("infra_joint.config.AsyncOpenAI", factory)
    backend, client = build_model_backend(OpenAIBackendConfig(
        base_url="http://backend.test/v1", model="unchanged-model",
        api_key_env="TEST_BACKEND_KEY",
    ))
    assert client is not None
    expected = {
        "http_500": InternalServerError,
        "read_timeout": APITimeoutError,
        "disconnect": APIConnectionError,
    }[failure_kind]
    try:
        with pytest.raises(expected):
            await backend.invoke(ModelRequest(prompt="diagnostic", max_output_tokens=2048))
        assert calls == 1
    finally:
        await client.close()


def test_cli_help_exposes_worker_command() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Commands" in result.stdout
    assert "worker" in result.stdout
    assert "blind-plan-once" in result.stdout


def test_blind_plan_once_cli_uses_configured_backend(tmp_path: Path) -> None:
    config_path = tmp_path / "planner.yaml"
    config_path.write_text(
        "\n".join(
            (
                "model:",
                "  backend: static",
                '  response: \'{"decision_type":"finish","reason":"done"}\'',
            )
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "blind-plan-once",
            "--config",
            str(config_path),
            "--objective",
            "Return a short answer",
        ],
    )

    assert result.exit_code == 0
    assert '"decision_type":"finish"' in result.stdout
