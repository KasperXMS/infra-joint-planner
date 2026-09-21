from pathlib import Path

import pytest
from typer.testing import CliRunner

from infra_joint.cli import app
from infra_joint.config import (
    OpenAIBackendConfig,
    PlannerConfig,
    build_model_backend,
    load_planner_config,
    load_worker_config,
)
from infra_joint.worker.model_backend import StaticModelBackend


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
