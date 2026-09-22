from datetime import UTC, datetime

import pytest
from test_heterogeneous_contracts import replica

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.core.workflow import LogicalAgent, WorkflowNode
from infra_joint.heterogeneous.contracts import EquivalentModelReplicaSet
from infra_joint.heterogeneous.metrics import (
    ForcedPlacementMeasurements,
    calculate_routing_regret,
    summarize_routing_regret,
)
from infra_joint.heterogeneous.scheduler import (
    ReplicaAwareScheduler,
    ReplicaComputeEstimate,
)
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.workflow.scheduler import SchedulerKind


def replica_set() -> EquivalentModelReplicaSet:
    return EquivalentModelReplicaSet(
        logical_model_id="synthesis-qwen",
        canonical_deployment_id="agx-qwen",
        replicas=(
            replica("agx", "A28", "agx-qwen"),
            replica("gpu", "G4090", "gpu-qwen"),
        ),
    )


def registry() -> OperatorRegistry:
    result = OperatorRegistry()
    result.register(
        OperatorSpec(
            operator_id="invoke_model",
            description="model",
            capability_requirements=frozenset({"model"}),
        ),
        lambda _: {},
    )
    return result


def logical_agent() -> LogicalAgent:
    return LogicalAgent(
        agent_id="synthesizer",
        role="synthesis",
        objective="synthesize evidence",
        model_instance_id="agx-qwen",
        allowed_operations=("invoke_model",),
    )


def node() -> WorkflowNode:
    return WorkflowNode(
        node_id="synthesize",
        agent_id="synthesizer",
        operator="invoke_model",
        inputs=("evidence",),
        arguments={"prompt": "Synthesize the evidence. /no_think"},
    )


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="A28",
                device="AGX Orin",
                capabilities=frozenset({"model"}),
            ),
            AgentSpec(
                agent_id="G4090",
                device="2x RTX 4090",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="agx-qwen",
                agent_id="A28",
                model_id="qwen",
                context_window=32768,
                reserved_output_tokens=256,
            ),
            DeploymentSpec(
                deployment_id="gpu-qwen",
                agent_id="G4090",
                model_id="qwen",
                context_window=32768,
                reserved_output_tokens=256,
            ),
        ),
    )


def infrastructure(bandwidth_mbps: float, *, local_gpu: bool = False) -> InfrastructureState:
    locations = ("A28", "G4090") if local_gpu else ("A28",)
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="A28", available=True),
            AgentRuntimeState(agent_id="G4090", available=True),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="agx-qwen", available=True),
            DeploymentRuntimeState(deployment_id="gpu-qwen", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="evidence",
                locations=locations,
                media_type="application/json",
                size_bytes=8_000_000,
                sha256_hex="a" * 64,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="A28",
                target_agent_id="G4090",
                available=True,
                bandwidth_mbps=bandwidth_mbps,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )


def estimates() -> tuple[ReplicaComputeEstimate, ...]:
    return (
        ReplicaComputeEstimate(
            compute_profile_id="agx-profile",
            replica_id="agx",
            median_service_latency_ms=5000,
        ),
        ReplicaComputeEstimate(
            compute_profile_id="gpu-profile",
            replica_id="gpu",
            median_service_latency_ms=500,
        ),
    )


def test_b0_uses_locality_and_does_not_consume_cost_profiles() -> None:
    decision = ReplicaAwareScheduler("b0", replica_set()).schedule(
        node(), logical_agent(), environment(), infrastructure(1000), registry()
    )

    assert decision.scheduler == SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
    assert decision.selected_agent_id == "A28"
    assert decision.candidate_costs == ()


def test_b1_uses_calibrated_transfer_and_compute_decomposition() -> None:
    scheduler = ReplicaAwareScheduler("b1", replica_set(), compute_estimates=estimates())
    slow = scheduler.schedule(
        node(), logical_agent(), environment(), infrastructure(10), registry()
    )
    fast = scheduler.schedule(
        node(), logical_agent(), environment(), infrastructure(1000), registry()
    )

    assert slow.selected_agent_id == "A28"
    assert fast.selected_agent_id == "G4090"
    costs = {item.agent_id: item for item in fast.candidate_costs}
    assert costs["G4090"].transfer_latency_ms == pytest.approx(84)
    assert costs["G4090"].total_latency_ms == pytest.approx(584)
    assert fast.physical == PhysicalDecision(
        policy=PhysicalPolicy.TARGET_DEPLOYMENT,
        target_deployment_id="gpu-qwen",
    )


def test_b1_rejects_uncontrolled_queue_load() -> None:
    state = infrastructure(1000)
    object.__setattr__(
        state,
        "agents",
        (
            AgentRuntimeState(agent_id="A28", available=True),
            AgentRuntimeState(agent_id="G4090", available=True, in_flight=1),
        ),
    )
    decision = ReplicaAwareScheduler("b1", replica_set(), compute_estimates=estimates()).schedule(
        node(), logical_agent(), environment(), state, registry()
    )

    costs = {item.agent_id: item for item in decision.candidate_costs}
    assert not costs["G4090"].feasible
    assert "rejects nonzero queue" in str(costs["G4090"].reason)


def test_empirical_oracle_and_routing_regret_use_forced_measurements() -> None:
    forced = (
        ForcedPlacementMeasurements(agent_id="A28", costs_ms=(5000, 5100, 4900)),
        ForcedPlacementMeasurements(agent_id="G4090", costs_ms=(900, 1000, 1100)),
    )
    bad = calculate_routing_regret("A28", forced)
    good = calculate_routing_regret("G4090", forced)
    summary = summarize_routing_regret((bad, good))

    assert bad.oracle_agent_id == "G4090"
    assert bad.regret_ms == 4000
    assert good.regret_ms == 0
    assert summary.oracle_selection_accuracy == 0.5
    assert summary.p95_regret_ms == 4000
