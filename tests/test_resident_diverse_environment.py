import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.core.state import EnvironmentSpec
from infra_joint.operators.catalog import build_operator_catalog
from scripts.prepare_resident_worker_v1 import worker_config


def test_calibrated_environment_has_three_weights_five_instances_and_blind_view() -> None:
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/experiments/resident-diverse-environment-v1.yaml")
                            .read_text(encoding="utf-8"))
    environment = EnvironmentSpec.model_validate(config["environment"])
    assert len(environment.agents) == 4
    assert len(environment.deployments) == 5
    assert len({item.model_id for item in environment.deployments}) == 3
    backends = config["resident_backends"]
    assert set(backends) == {item.deployment_id for item in environment.deployments}
    strong = [item for item in environment.deployments if item.agent_id == "strong-4090"]
    assert len({backends[item.deployment_id]["base_url"] for item in strong}) == 2
    for deployment in environment.deployments:
        assert deployment.context_window == 32768
        assert deployment.reserved_output_tokens == 2048
        assert deployment.image_token_cost == 4096
    registry = build_operator_catalog()
    capability = build_static_capability_contract(environment, registry, tuple(registry))
    assert len(capability.model_classes) == 1  # Different weights do not imply quality tiers.
    assert not capability.model_classes[0].quality_classes
    logical = json.dumps(capability.model_dump(mode="json"))
    for private in ("192.168", "127.0.0.1", "4090", "Jetson", "resident-a4",
                    "qwen35", "deployment_id", "bandwidth", "queue_depth"):
        assert private not in logical
    assert config["benchmark_execution_allowed"] is False
    assert config["model_request"]["temperature"] is None


def test_worker_derivation_preserves_substrate_and_rejects_anonymous_binding(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    pool = yaml.safe_load((root / "configs/experiments/resident-diverse-environment-v1.yaml")
                          .read_text(encoding="utf-8"))
    folder = root / "configs/experiments/workers/blind-3family-video-v1.3"
    for agent in ("A4", "A5", "A28", "strong-4090"):
        original = yaml.safe_load((folder / f"worker-{agent.lower()}.yaml")
                                  .read_text(encoding="utf-8"))
        before = deepcopy(original)
        worker = worker_config(pool, original, agent, tmp_path / agent)
        assert original == before
        assert worker.max_read_artifact_bytes == original["max_read_artifact_bytes"]
        assert worker.allowed_artifact_hosts == frozenset(original["allowed_artifact_hosts"])
        assert worker.ffmpeg_probe_input == Path(original["ffmpeg_probe_input"])
        assert len(worker.deployments) == (2 if agent == "strong-4090" else 1)
    bad = deepcopy(pool)
    bad["resident_backends"]["resident-4090-gpu1-vl8b-v1"]["base_url"] = (
        bad["resident_backends"]["resident-4090-gpu0-qwen35-27b-v1"]["base_url"]
    )
    original = yaml.safe_load((folder / "worker-strong-4090.yaml").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="distinct resident servers"):
        worker_config(bad, original, "strong-4090", tmp_path / "invalid")
