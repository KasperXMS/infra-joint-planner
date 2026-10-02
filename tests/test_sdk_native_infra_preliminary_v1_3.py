import json
import os
import sys
from pathlib import Path

import pytest
import yaml
from agents import ModelSettings

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from blind_3family_validation_v1 import (  # noqa: E402
    REPO,
    _validate_harness_manifest_hash,
    _yaml,
)
from prepare_sdk_native_infra_worker_v1_3 import prepare  # noqa: E402
from sdk_native_infra_preliminary_v1_3 import (  # noqa: E402
    ModelRequestBodyAdapter,
    _compact_trace,
    _load_control_plane_key,
    _validate_config,
)

CELLS = (
    "sdk-native-infra-v1.3-fast-blind-r1.yaml",
    "sdk-native-infra-v1.3-fast-aware-r1.yaml",
    "sdk-native-infra-v1.3-slow-blind-r1.yaml",
    "sdk-native-infra-v1.3-slow-aware-r1.yaml",
)


def test_sdk_native_preliminary_is_exactly_frozen_two_by_two() -> None:
    configs = [
        _yaml(REPO / "configs/experiments" / name)
        for name in CELLS
    ]
    for config in configs:
        _validate_config(config)
        assert config["harness_manifest"] == (
            "configs/experiments/blind-harness-v1.3.1.yaml"
        )
        assert config["task"] == "multihop-multisource"
        assert config["model_service_timeout_seconds"] == 1200
        assert config["execution"] == {
            "scheduler": "auto_physical_locality_aware",
            "repetitions": 1,
            "retry": False,
            "replacement": False,
        }
    factors = {
        (config["network"]["regime"], config["profile_visibility"])
        for config in configs
    }
    assert factors == {
        ("fast", "blind"),
        ("fast", "aware"),
        ("slow", "blind"),
        ("slow", "aware"),
    }
    all_stores = [
        value
        for config in configs
        for value in config["fresh_worker_stores"].values()
    ]
    assert len(all_stores) == len(set(all_stores)) == 16


def test_worker_config_is_deterministically_derived_from_frozen_contract(
    tmp_path: Path,
) -> None:
    cell = REPO / "configs/experiments/sdk-native-infra-v1.3-slow-aware-r1.yaml"
    output = tmp_path / "worker-a28.yaml"
    prepare(cell, "A28", output)
    value = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert value["agent_id"] == "A28"
    assert value["port"] == 46128
    assert value["artifact_root"].endswith("/slow-aware/a28")
    deployment = value["deployments"]["a28-qwen3.8-27b-q4km-v1"]
    assert deployment["context_window"] == 32768
    assert deployment["reserved_output_tokens"] == 2048
    assert deployment["model"]["model"] == "qwen3.8-27b-v1"


def test_trace_projection_recovers_failed_run_costs(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    events = [
        {
            "event_type": "workflow.graph.snapshot",
            "payload": {"nodes": [], "edges": []},
        },
        {
            "event_type": "physical.execution",
            "payload": {
                "execution": {
                    "transfers": [
                        {"bytes_transferred": 1234, "duration_ms": 45.5}
                    ]
                }
            },
        },
        {
            "event_type": "run.failed",
            "payload": {"e2e_latency_ms": 987.25},
        },
    ]
    trace.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )

    summary = _compact_trace(trace)

    assert summary["trace_e2e_latency_ms"] == 987.25
    assert summary["trace_action_transfer_bytes"] == 1234
    assert summary["trace_action_transfer_latency_ms"] == 45.5


def test_trace_projection_reads_profiles_from_persisted_observations(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "event_type": "workflow.graph.snapshot",
                "payload": {"nodes": [], "edges": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "loop": {
            "observations": [
                {
                    "physical_profile": {
                        "network_class": "constrained",
                    }
                },
                {"physical_profile": None},
            ]
        }
    }

    summary = _compact_trace(trace, result)

    assert summary["physical_profile_observations"] == 1
    assert summary["observed_network_classes"] == ["constrained"]


def test_qwen_sanity_config_is_pinned_to_existing_provider_contract() -> None:
    config = _yaml(
        REPO / "configs/experiments/sdk-native-infra-qwen-v1-sanity.yaml"
    )
    _validate_config(config)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    assert harness_path.name == "qwen-infra-sanity-v1.yaml"
    assert config["profile_visibility"] == "blind"
    assert config["network"] == {
        "regime": "fast",
        "bandwidth_mbps": 100,
        "added_rtt_ms": 5,
    }
    assert len(set(config["fresh_worker_stores"].values())) == 4


def test_control_plane_key_loader_uses_configured_provider_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    key_file = tmp_path / "keys.env"
    key_file.write_text(
        "DASHSCOPE_API_KEY=qwen-secret\nDeepSeek API Key: deepseek-secret\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    _load_control_plane_key(key_file, "DASHSCOPE_API_KEY")
    assert os.environ["DASHSCOPE_API_KEY"] == "qwen-secret"


def test_qwen38max_sanity_config_pins_requested_model() -> None:
    config = _yaml(
        REPO / "configs/experiments/sdk-native-infra-qwen38max-v1-sanity.yaml"
    )
    _validate_config(config)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    assert config["run_id"] == "qwen38max-sanity-multihop-fast-blind-v1"
    assert config["profile_visibility"] == "blind"
    assert len(set(config["fresh_worker_stores"].values())) == 4


@pytest.mark.parametrize(
    ("condition", "visibility", "bandwidth_mbps", "added_rtt_ms"),
    [
        ("fast-blind", "blind", 100, 5),
        ("fast-aware", "aware", 100, 5),
        ("slow-blind", "blind", 3, 50),
        ("slow-aware", "aware", 3, 50),
    ],
)
def test_qwen38max_r1_matrix_is_preregistered(
    condition: str,
    visibility: str,
    bandwidth_mbps: int,
    added_rtt_ms: int,
) -> None:
    config = _yaml(
        REPO
        / f"configs/experiments/sdk-native-infra-qwen38max-v1-{condition}-r1.yaml"
    )
    _validate_config(config)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    assert config["profile_visibility"] == visibility
    assert config["network"]["bandwidth_mbps"] == bandwidth_mbps
    assert config["network"]["added_rtt_ms"] == added_rtt_ms
    assert config["execution"] == {
        "scheduler": "auto_physical_locality_aware",
        "repetitions": 1,
        "retry": False,
        "replacement": False,
    }


@pytest.mark.asyncio
async def test_model_request_body_adapter_injects_provider_option() -> None:
    captured: dict[str, object] = {}

    class FakeModel:
        async def get_response(self, *args: object, **kwargs: object) -> str:
            captured["settings"] = kwargs["model_settings"]
            return "ok"

    adapter = ModelRequestBodyAdapter(
        FakeModel(),
        {"enable_thinking": False},
    )
    response = await adapter.get_response(
        model_settings=ModelSettings(parallel_tool_calls=False)
    )

    assert response == "ok"
    settings = captured["settings"]
    assert isinstance(settings, ModelSettings)
    assert settings.parallel_tool_calls is False
    assert settings.extra_body == {"enable_thinking": False}


@pytest.mark.asyncio
async def test_model_request_body_adapter_rejects_option_conflict() -> None:
    class FakeModel:
        async def get_response(self, *args: object, **kwargs: object) -> str:
            return "unreachable"

    adapter = ModelRequestBodyAdapter(
        FakeModel(),
        {"enable_thinking": False},
    )
    with pytest.raises(RuntimeError, match="enable_thinking"):
        await adapter.get_response(
            model_settings=ModelSettings(extra_body={"enable_thinking": True})
        )
