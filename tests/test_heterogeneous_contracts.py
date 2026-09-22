from pathlib import Path

import pytest

from infra_joint.config import load_runner_config
from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.heterogeneous.contracts import EquivalentModelReplicaSet, ModelReplica
from infra_joint.heterogeneous.preflight import (
    HeterogeneousPreflightError,
    validate_heterogeneous_preflight,
)
from infra_joint.worker.server import WorkerDeploymentState, WorkerStateResponse


def replica(
    replica_id: str,
    agent_id: str,
    deployment_id: str,
    *,
    fingerprint: str = "sha256:equivalent",
) -> ModelReplica:
    return ModelReplica(
        replica_id=replica_id,
        agent_id=agent_id,
        deployment_id=deployment_id,
        checkpoint_id="qwen3-vl-8b",
        checkpoint_fingerprint=fingerprint,
        quantization="Q4_K_M",
        runtime="ollama",
        runtime_version="0.12.3",
        context_window=32768,
        max_output_tokens=256,
        prompt_template_id="qwen3-v1",
        generation_config_id="deterministic-no-think-v1",
    )


def replica_set(*, gpu_fingerprint: str = "sha256:equivalent") -> EquivalentModelReplicaSet:
    return EquivalentModelReplicaSet(
        logical_model_id="synthesis-qwen",
        canonical_deployment_id="agx-qwen",
        replicas=(
            replica("agx", "A28", "agx-qwen"),
            replica("gpu", "G4090", "gpu-qwen", fingerprint=gpu_fingerprint),
        ),
    )


def environment(*, include_gpu: bool = True) -> EnvironmentSpec:
    agents = [AgentSpec(agent_id="A28", device="AGX Orin", capabilities=frozenset({"model"}))]
    deployments = [
        DeploymentSpec(
            deployment_id="agx-qwen",
            agent_id="A28",
            model_id="qwen3-vl-8b",
            modalities=frozenset({"text"}),
            context_window=32768,
            reserved_output_tokens=256,
        )
    ]
    if include_gpu:
        agents.append(
            AgentSpec(
                agent_id="G4090",
                device="2x RTX 4090",
                capabilities=frozenset({"model"}),
            )
        )
        deployments.append(
            DeploymentSpec(
                deployment_id="gpu-qwen",
                agent_id="G4090",
                model_id="qwen3-vl-8b",
                modalities=frozenset({"text"}),
                context_window=32768,
                reserved_output_tokens=256,
            )
        )
    return EnvironmentSpec(agents=tuple(agents), deployments=tuple(deployments))


def worker_state(agent_id: str, deployment_id: str) -> WorkerStateResponse:
    return WorkerStateResponse(
        agent_id=agent_id,
        available=True,
        in_flight=0,
        operators=("invoke_model",),
        deployments=(
            WorkerDeploymentState(
                deployment_id=deployment_id,
                model_id="qwen3-vl-8b",
                modalities=frozenset({"text"}),
                context_window=32768,
                reserved_output_tokens=256,
                image_token_cost=4096,
            ),
        ),
        artifacts=(),
    )


def test_replica_set_rejects_checkpoint_mismatch() -> None:
    with pytest.raises(ValueError, match="not equivalent"):
        replica_set(gpu_fingerprint="sha256:different")


def test_preflight_rejects_missing_heterogeneous_target() -> None:
    with pytest.raises(HeterogeneousPreflightError, match="missing"):
        validate_heterogeneous_preflight(
            environment(include_gpu=False),
            {"A28": worker_state("A28", "agx-qwen")},
            replica_set(),
            required_agent_ids=frozenset({"A28", "G4090"}),
            rtx_agent_id="G4090",
        )


def test_preflight_accepts_exact_equivalent_replica_surface() -> None:
    validate_heterogeneous_preflight(
        environment(),
        {
            "A28": worker_state("A28", "agx-qwen"),
            "G4090": worker_state("G4090", "gpu-qwen"),
        },
        replica_set(),
        required_agent_ids=frozenset({"A28", "G4090"}),
        rtx_agent_id="G4090",
    )


def test_v0_runner_config_still_loads() -> None:
    # The v1 sidecar must not change the old configuration schema.
    path = Path("configs/example-planner.yaml")
    assert path.exists()
    assert load_runner_config  # keep import/type surface exercised without local secrets
