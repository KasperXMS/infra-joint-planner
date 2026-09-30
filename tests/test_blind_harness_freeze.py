import sys
from pathlib import Path

import pytest

from infra_joint.config import EnvironmentSpec
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.operators.catalog import build_operator_catalog

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from blind_3family_validation_v1 import (  # noqa: E402
    REPO,
    _operations,
    _revision,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
)


def frozen_components() -> tuple[object, EnvironmentSpec, object, tuple[str, ...]]:
    harness = load_harness(REPO / "configs/experiments/blind-harness-v1.yaml")
    base = _yaml(REPO / "configs/experiments/blind-baseline-6task-semantic-cleanup-v1.yaml")
    fresh = _yaml(REPO / "configs/experiments/blind-3family-longbench-environment-v1.yaml")
    environment = EnvironmentSpec.model_validate(fresh["environment"])
    operations = _operations(base)
    capabilities = build_static_capability_contract(
        environment,
        build_operator_catalog(),
        operations,
    )
    return harness, environment, capabilities, operations


def test_committed_blind_harness_v1_is_internally_consistent() -> None:
    harness, environment, capabilities, operations = frozen_components()
    validate_harness(harness, environment, capabilities, operations)  # type: ignore[arg-type]


def test_blind_harness_rejects_manager_instruction_drift() -> None:
    harness, environment, capabilities, operations = frozen_components()
    changed_manager = {**harness.manager, "instructions_sha256": "0" * 64}  # type: ignore[union-attr]
    drifted = harness.model_copy(update={"manager": changed_manager})  # type: ignore[union-attr]
    with pytest.raises(RuntimeError, match="Manager instructions drift"):
        validate_harness(drifted, environment, capabilities, operations)  # type: ignore[arg-type]


def test_stage2_config_pins_harness_manifest_bytes(tmp_path: Path) -> None:
    config = _yaml(REPO / "configs/experiments/blind-3family-longbench-v1.yaml")
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    changed = tmp_path / "blind-harness-v1.yaml"
    changed.write_bytes(harness_path.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="manifest drift"):
        _validate_harness_manifest_hash(config, changed)


def test_archive_deployment_revision_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "blind_3family_validation_v1.subprocess.check_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", "a" * 40)
    assert _revision() == "a" * 40
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", "not-a-commit")
    with pytest.raises(RuntimeError, match="code revision is unavailable"):
        _revision()
