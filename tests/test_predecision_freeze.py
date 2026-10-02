# pyright: reportPrivateUsage=false
import sys
from pathlib import Path

from infra_joint.config import EnvironmentSpec
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.operators.catalog import build_operator_catalog

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from blind_3family_validation_v1 import (  # noqa: E402
    REPO,
    _operations,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
)
from sdk_native_infra_preliminary_v1_3 import _validate_config  # noqa: E402


def test_predecision_harness_preserves_shared_models_prompts_tools_and_budgets() -> None:
    old = load_harness(REPO / "configs/experiments/qwen-infra-preliminary-v1.yaml")
    new = load_harness(REPO / "configs/experiments/infra-aware-predecision-v1.yaml")
    for name in ("manager", "verifier", "budget", "available_operations",
                 "anonymous_model_contract", "static_capability_contract_sha256",
                 "model_service_timeout_seconds"):
        assert getattr(new, name) == getattr(old, name)
    environment = EnvironmentSpec.model_validate(_yaml(
        REPO / "configs/experiments/blind-3family-video-environment-v1.3.yaml"
    )["environment"])
    operations = _operations(_yaml(
        REPO / "configs/experiments/blind-baseline-6task-semantic-cleanup-v1.yaml"
    ))
    capabilities = build_static_capability_contract(
        environment, build_operator_catalog(), operations
    )
    validate_harness(new, environment, capabilities, operations)
    assert new.runtime["profile_timing"] == "fresh_before_every_manager_turn"
    assert new.runtime["terminal_canonical_labels"] == ["Yes", "No"]


def test_preregistered_twelve_cells_have_distinct_fresh_stores_and_new_run_ids() -> None:
    stores: set[str] = set()
    run_ids: set[str] = set()
    for replicate in (1, 2, 3):
        for condition in ("fast-blind", "fast-aware", "slow-blind", "slow-aware"):
            config = _yaml(REPO / (
                f"configs/experiments/infra-aware-predecision-v1-{condition}-r{replicate}.yaml"
            ))
            _validate_config(config)
            _validate_harness_manifest_hash(config, REPO / str(config["harness_manifest"]))
            assert config["run_id"] not in run_ids
            run_ids.add(config["run_id"])
            for store in config["fresh_worker_stores"].values():
                assert store not in stores
                stores.add(store)
    assert len(run_ids) == 12
    assert len(stores) == 48
