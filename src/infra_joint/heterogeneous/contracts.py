from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel


class NetworkControlMethod(StrEnum):
    APPLICATION_EMULATOR = "application_emulator"
    TC = "tc"


class PayloadClass(StrEnum):
    S = "S"
    M = "M"
    L = "L"


class DistributionSummary(ContractModel):
    count: int = Field(gt=0)
    mean: float = Field(ge=0)
    median: float = Field(ge=0)
    std: float = Field(ge=0)
    p90: float = Field(ge=0)
    p95: float = Field(ge=0)


class ModelReplica(ContractModel):
    replica_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    checkpoint_id: str = Field(min_length=1)
    checkpoint_fingerprint: str = Field(min_length=1)
    quantization: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    runtime_version: str = Field(min_length=1)
    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    prompt_template_id: str = Field(min_length=1)
    generation_config_id: str = Field(min_length=1)


class EquivalentModelReplicaSet(ContractModel):
    """A semantic model identity backed by equivalent physical deployments.

    This is deliberately a v1 sidecar. ``LogicalAgent.model_instance_id`` keeps
    its frozen v0 meaning and names the canonical deployment. The v1 schedulers
    may choose another member only after this contract has proved equivalence.
    """

    logical_model_id: str = Field(min_length=1)
    canonical_deployment_id: str = Field(min_length=1)
    replicas: tuple[ModelReplica, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def replicas_are_equivalent(self) -> Self:
        replica_ids = [item.replica_id for item in self.replicas]
        deployment_ids = [item.deployment_id for item in self.replicas]
        agent_ids = [item.agent_id for item in self.replicas]
        if len(replica_ids) != len(set(replica_ids)):
            raise ValueError("model replica IDs must be unique")
        if len(deployment_ids) != len(set(deployment_ids)):
            raise ValueError("model replica deployment IDs must be unique")
        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("model replicas must be on distinct physical agents")
        if self.canonical_deployment_id not in set(deployment_ids):
            raise ValueError("canonical deployment must be a member of the replica set")
        fields = (
            "checkpoint_id",
            "checkpoint_fingerprint",
            "quantization",
            "runtime",
            "runtime_version",
            "context_window",
            "max_output_tokens",
            "prompt_template_id",
            "generation_config_id",
        )
        reference = self.replicas[0]
        mismatched = [
            field
            for field in fields
            if any(getattr(item, field) != getattr(reference, field) for item in self.replicas[1:])
        ]
        if mismatched:
            raise ValueError(f"model replicas are not equivalent: {mismatched}")
        return self


class NetworkRegime(ContractModel):
    regime_id: str = Field(min_length=1)
    bandwidth_mbps: float = Field(gt=0)
    added_rtt_ms: float = Field(ge=0)
    control_method: NetworkControlMethod
    tc_configuration_id: str | None = None

    @model_validator(mode="after")
    def tc_requires_configuration(self) -> Self:
        if self.control_method == NetworkControlMethod.TC and not self.tc_configuration_id:
            raise ValueError("tc network control requires tc_configuration_id")
        if self.control_method != NetworkControlMethod.TC and self.tc_configuration_id is not None:
            raise ValueError("non-tc network control must not name a tc configuration")
        return self


class ArtifactTransferCalibration(ContractModel):
    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    artifact_bytes: int = Field(gt=0)
    duration_ms: DistributionSummary
    effective_throughput_mbps: DistributionSummary


class NetworkCalibration(ContractModel):
    calibration_id: str = Field(min_length=1)
    regime: NetworkRegime
    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    median_rtt_ms: float = Field(ge=0)
    p95_rtt_ms: float = Field(ge=0)
    achieved_throughput_mbps: DistributionSummary
    artifact_transfers: tuple[ArtifactTransferCalibration, ...] = Field(min_length=1)


class ComputeProfilePoint(ContractModel):
    input_tokens: int = Field(gt=0)
    requested_output_tokens: int = Field(gt=0)
    warmup_runs: int = Field(ge=10)
    measured_runs: int = Field(ge=30)
    ttft_ms: DistributionSummary | None = None
    prefill_ms: DistributionSummary | None = None
    decode_ms: DistributionSummary | None = None
    total_service_ms: DistributionSummary
    output_tokens_per_second: DistributionSummary | None = None
    actual_input_tokens: DistributionSummary
    actual_output_tokens: DistributionSummary
    peak_memory_bytes: int | None = Field(default=None, gt=0)


class ComputeProfile(ContractModel):
    profile_id: str = Field(min_length=1)
    replica_id: str = Field(min_length=1)
    points: tuple[ComputeProfilePoint, ...] = Field(min_length=1)


class ExperimentMetadata(ContractModel):
    experiment_version: str = Field(pattern=r"^heterogeneous-infrastructure-v1$")
    hardware_topology_id: str = Field(min_length=1)
    network_control_method: NetworkControlMethod
    network_calibration_id: str = Field(min_length=1)
    compute_profile_id: str = Field(min_length=1)
    model_checkpoint_id: str = Field(min_length=1)
    model_replica_id: str = Field(min_length=1)
    model_quantization: str = Field(min_length=1)
    tc_configuration_id: str = Field(min_length=1)
    payload_class: PayloadClass
    placement_policy: str = Field(min_length=1)
    workflow_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
