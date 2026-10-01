import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from blind_3family_validation_v1 import REPO, _yaml  # noqa: E402
from prepare_sdk_native_infra_worker_v1_3 import prepare  # noqa: E402
from sdk_native_infra_preliminary_v1_3 import _validate_config  # noqa: E402

CELLS = (
    "sdk-native-infra-v1.3-fast-blind.yaml",
    "sdk-native-infra-v1.3-fast-aware.yaml",
    "sdk-native-infra-v1.3-slow-blind.yaml",
    "sdk-native-infra-v1.3-slow-aware.yaml",
)


def test_sdk_native_preliminary_is_exactly_frozen_two_by_two() -> None:
    configs = [
        _yaml(REPO / "configs/experiments" / name)
        for name in CELLS
    ]
    for config in configs:
        _validate_config(config)
        assert config["harness_manifest"] == (
            "configs/experiments/blind-harness-v1.3.yaml"
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
    cell = REPO / "configs/experiments/sdk-native-infra-v1.3-slow-aware.yaml"
    output = tmp_path / "worker-a28.yaml"
    prepare(cell, "A28", output)
    value = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert value["agent_id"] == "A28"
    assert value["port"] == 42128
    assert value["artifact_root"].endswith("/slow-aware/a28")
    deployment = value["deployments"]["a28-qwen3.8-27b-q4km-v1"]
    assert deployment["context_window"] == 32768
    assert deployment["reserved_output_tokens"] == 2048
    assert deployment["model"]["model"] == "qwen3.8-27b-v1"
