import json
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from blind_3family_validation_v1 import REPO, _yaml  # noqa: E402
from prepare_sdk_native_infra_worker_v1_3 import prepare  # noqa: E402
from sdk_native_infra_preliminary_v1_3 import (  # noqa: E402
    _compact_trace,
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
