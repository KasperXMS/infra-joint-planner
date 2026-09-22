from datetime import UTC, datetime

import pytest

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
    LinkSpec,
)
from infra_joint.core.workflow import LogicalAgent, WorkflowNode
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.workflow.scheduler import (
    LocalityAwareMyopicScheduler,
    MyopicCostAwareScheduler,
    OperatorDeviceProfile,
    QueueSignal,
    SchedulerKind,
    SchedulingError,
    build_scheduler,
)


def logical_agent(model_instance_id: str = "edge-model") -> LogicalAgent:
    return LogicalAgent(
        agent_id="researcher",
        role="research",
        objective="process the current workflow node",
        model_instance_id=model_instance_id,
        allowed_operations=("filter_records", "invoke_model"),
    )


def node(operator: str = "filter_records") -> WorkflowNode:
    return WorkflowNode(
        node_id=f"node-{operator}",
        agent_id="researcher",
        operator=operator,
        inputs=("input",),
        arguments=(
            {"prompt": "answer from the artifact"}
            if operator == "invoke_model"
            else {
                "field": "kind",
                "op": "eq",
                "value": "evidence",
                "output_artifact_id": "filtered",
            }
        ),
        outputs=() if operator == "invoke_model" else ("filtered",),
    )


def operator_spec(operator: str = "filter_records") -> OperatorSpec:
    return OperatorSpec(
        operator_id=operator,
        description="test operator",
        capability_requirements=frozenset(
            {"model" if operator == "invoke_model" else "structured"}
        ),
    )


def registry() -> OperatorRegistry:
    result = OperatorRegistry()
    result.register(operator_spec(), lambda _: {})
    result.register(operator_spec("invoke_model"), lambda _: {})
    return result


def environment(*, reverse_link_only: bool = False) -> EnvironmentSpec:
    links = (
        (
            LinkSpec(
                source_agent_id="gpu",
                target_agent_id="edge",
                bandwidth_mbps=100,
                rtt_ms=10,
            )
            if reverse_link_only
            else LinkSpec(
                source_agent_id="edge",
                target_agent_id="gpu",
                bandwidth_mbps=100,
                rtt_ms=10,
            )
        ),
    )
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="edge",
                device="orin",
                capabilities=frozenset({"structured", "model"}),
            ),
            AgentSpec(
                agent_id="gpu",
                device="4090",
                capabilities=frozenset({"structured", "model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="edge-model",
                agent_id="edge",
                model_id="edge-reader",
                context_window=8192,
            ),
            DeploymentSpec(
                deployment_id="gpu-model",
                agent_id="gpu",
                model_id="gpu-reader",
                context_window=8192,
            ),
        ),
        links=links,
    )


def infrastructure(
    *,
    gpu_queue_depth: int | None = 0,
    gpu_in_flight: int = 0,
    reverse_link_only: bool = False,
) -> InfrastructureState:
    links = (
        (
            LinkRuntimeState(
                source_agent_id="gpu",
                target_agent_id="edge",
                available=True,
                bandwidth_mbps=100,
                rtt_ms=10,
            )
            if reverse_link_only
            else LinkRuntimeState(
                source_agent_id="edge",
                target_agent_id="gpu",
                available=True,
                bandwidth_mbps=100,
                rtt_ms=10,
            )
        ),
    )
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="edge", available=True),
            AgentRuntimeState(
                agent_id="gpu",
                available=True,
                queue_depth=gpu_queue_depth,
                in_flight=gpu_in_flight,
            ),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="edge-model", available=True),
            DeploymentRuntimeState(deployment_id="gpu-model", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="input",
                locations=("edge",),
                media_type="application/json",
                size_bytes=1_000_000,
                sha256_hex="a" * 64,
            ),
        ),
        links=links,
        observed_at=datetime.now(UTC),
    )


def profiles() -> tuple[OperatorDeviceProfile, ...]:
    return (
        OperatorDeviceProfile(
            operator_id="filter_records",
            device="orin",
            compute_latency_ms=500,
        ),
        OperatorDeviceProfile(
            operator_id="filter_records",
            device="4090",
            compute_latency_ms=100,
        ),
        OperatorDeviceProfile(
            operator_id="invoke_model",
            device="orin",
            compute_latency_ms=1000,
        ),
        OperatorDeviceProfile(
            operator_id="invoke_model",
            device="4090",
            compute_latency_ms=1,
        ),
    )


def test_b0_ordinary_node_defers_locality_to_runtime_auto() -> None:
    decision = LocalityAwareMyopicScheduler().schedule(
        node(),
        logical_agent(),
        environment(),
        infrastructure(),
        registry(),
    )

    assert decision.scheduler == SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
    assert decision.physical == PhysicalDecision(policy=PhysicalPolicy.AUTO)
    assert decision.selected_agent_id is None
    assert decision.candidate_costs == ()


def test_b0_model_node_is_pinned_to_logical_agent_model_instance() -> None:
    decision = LocalityAwareMyopicScheduler().schedule(
        node("invoke_model"),
        logical_agent(),
        environment(),
        infrastructure(),
        registry(),
    )

    assert decision.physical == PhysicalDecision(
        policy=PhysicalPolicy.TARGET_DEPLOYMENT,
        target_deployment_id="edge-model",
    )
    assert decision.selected_agent_id == "edge"
    assert decision.selected_deployment_id == "edge-model"


def test_b1_selects_minimum_transfer_compute_and_queue_cost() -> None:
    decision = MyopicCostAwareScheduler(profiles()).schedule(
        node(),
        logical_agent(),
        environment(),
        infrastructure(),
        registry(),
    )

    # edge: 0 + 500; gpu: (10 ms RTT + 80 ms serialization) + 100
    assert decision.selected_agent_id == "gpu"
    assert decision.physical == PhysicalDecision(
        policy=PhysicalPolicy.TARGET_AGENT,
        target_agent_id="gpu",
    )
    costs = {item.agent_id: item for item in decision.candidate_costs}
    assert costs["edge"].total_latency_ms == pytest.approx(500)
    assert costs["gpu"].transfer_latency_ms == pytest.approx(90)
    assert costs["gpu"].total_latency_ms == pytest.approx(190)


def test_b1_prefers_queue_depth_and_falls_back_to_in_flight() -> None:
    scheduler = MyopicCostAwareScheduler(profiles())
    queued = scheduler.schedule(
        node(),
        logical_agent(),
        environment(),
        infrastructure(gpu_queue_depth=5, gpu_in_flight=99),
        registry(),
    )
    queued_gpu = {item.agent_id: item for item in queued.candidate_costs}["gpu"]
    assert queued.selected_agent_id == "edge"
    assert queued_gpu.queue_signal == QueueSignal.QUEUE_DEPTH
    assert queued_gpu.queue_units == 5

    in_flight = scheduler.schedule(
        node(),
        logical_agent(),
        environment(),
        infrastructure(gpu_queue_depth=None, gpu_in_flight=2),
        registry(),
    )
    in_flight_gpu = {item.agent_id: item for item in in_flight.candidate_costs}["gpu"]
    assert in_flight_gpu.queue_signal == QueueSignal.IN_FLIGHT
    assert in_flight_gpu.queue_units == 2
    assert in_flight_gpu.queue_latency_ms == pytest.approx(200)


def test_b1_requires_the_measured_link_in_the_transfer_direction() -> None:
    decision = MyopicCostAwareScheduler(profiles()).schedule(
        node(),
        logical_agent(),
        environment(reverse_link_only=True),
        infrastructure(reverse_link_only=True),
        registry(),
    )

    costs = {item.agent_id: item for item in decision.candidate_costs}
    assert decision.selected_agent_id == "edge"
    assert not costs["gpu"].feasible
    assert costs["gpu"].reason == "no measured available directed link for artifact: input"


def test_b1_model_cost_does_not_allow_switching_deployments() -> None:
    decision = MyopicCostAwareScheduler(profiles()).schedule(
        node("invoke_model"),
        logical_agent("edge-model"),
        environment(),
        infrastructure(),
        registry(),
    )

    assert decision.selected_deployment_id == "edge-model"
    assert decision.selected_agent_id == "edge"
    assert len(decision.candidate_costs) == 1
    assert decision.candidate_costs[0].agent_id == "edge"


def test_b1_reports_all_candidates_when_none_is_feasible() -> None:
    scheduler = MyopicCostAwareScheduler(())

    with pytest.raises(SchedulingError) as raised:
        scheduler.schedule(
            node(),
            logical_agent(),
            environment(),
            infrastructure(),
            registry(),
        )

    assert {item.agent_id for item in raised.value.candidate_costs} == {"edge", "gpu"}
    assert all(not item.feasible for item in raised.value.candidate_costs)


def test_scheduler_factory_exposes_the_frozen_baseline_ids() -> None:
    assert isinstance(build_scheduler("b0"), LocalityAwareMyopicScheduler)
    assert isinstance(build_scheduler("b1", profiles=profiles()), MyopicCostAwareScheduler)
