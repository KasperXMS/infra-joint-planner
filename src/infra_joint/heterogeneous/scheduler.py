from typing import Literal

from pydantic import Field

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy
from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.core.workflow import LogicalAgent, WorkflowNode
from infra_joint.heterogeneous.contracts import EquivalentModelReplicaSet, ModelReplica
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.workflow.scheduler import (
    CandidateCostEstimate,
    LocalityAwareMyopicScheduler,
    MyopicCostAwareScheduler,
    OperatorDeviceProfile,
    QueueSignal,
    SchedulerDecision,
    SchedulerKind,
    SchedulingError,
)


class ReplicaComputeEstimate(ContractModel):
    compute_profile_id: str = Field(min_length=1)
    replica_id: str = Field(min_length=1)
    median_service_latency_ms: float = Field(ge=0)


class ReplicaAwareScheduler:
    """v1 model-replica placement without changing the semantic workflow DAG."""

    def __init__(
        self,
        kind: Literal["b0", "b1"],
        replica_set: EquivalentModelReplicaSet,
        *,
        compute_estimates: tuple[ReplicaComputeEstimate, ...] = (),
        ordinary_profiles: tuple[OperatorDeviceProfile, ...] = (),
    ) -> None:
        self._kind = kind
        self._replica_set = replica_set
        estimates = {item.replica_id: item for item in compute_estimates}
        if len(estimates) != len(compute_estimates):
            raise ValueError("replica compute estimates must be unique")
        if kind == "b1" and set(estimates) != {item.replica_id for item in replica_set.replicas}:
            raise ValueError("B1 requires one calibrated compute estimate per replica")
        self._compute_estimates = estimates
        self._ordinary = (
            LocalityAwareMyopicScheduler()
            if kind == "b0"
            else MyopicCostAwareScheduler(ordinary_profiles)
        )

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        if (
            node.operator != "invoke_model"
            or logical_agent.model_instance_id != self._replica_set.canonical_deployment_id
        ):
            return self._ordinary.schedule(
                node, logical_agent, environment, infrastructure, registry
            )
        registry.validate_action(node.semantic_action())
        candidates = self._available_replicas(environment, infrastructure)
        if not candidates:
            raise SchedulingError("no equivalent model replica is available")
        if self._kind == "b0":
            selected = min(
                candidates,
                key=lambda replica: (
                    self._missing_input_count(node, replica.agent_id, infrastructure),
                    replica.agent_id,
                ),
            )
            return self._decision(
                node,
                logical_agent,
                selected,
                SchedulerKind.B0_LOCALITY_AWARE_MYOPIC,
                (),
                "v1 B0 selected the equivalent replica with the fewest non-local inputs; "
                "bandwidth and calibrated compute were not consumed",
            )

        costs = tuple(
            self._estimate(node, replica, environment, infrastructure) for replica in candidates
        )
        feasible = [item for item in costs if item.feasible]
        if not feasible:
            raise SchedulingError(
                "no equivalent model replica has a complete calibrated cost",
                candidate_costs=costs,
            )
        selected_cost = min(
            feasible,
            key=lambda item: (
                item.total_latency_ms if item.total_latency_ms is not None else float("inf"),
                item.agent_id,
            ),
        )
        selected = next(item for item in candidates if item.agent_id == selected_cost.agent_id)
        return self._decision(
            node,
            logical_agent,
            selected,
            SchedulerKind.B1_MYOPIC_COST_AWARE,
            costs,
            "v1 B1 minimized calibrated transfer + replica compute with queue fixed to zero",
        )

    def _available_replicas(
        self,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
    ) -> tuple[ModelReplica, ...]:
        deployments = {item.deployment_id: item for item in environment.deployments}
        available_agents = {item.agent_id for item in infrastructure.agents if item.available}
        available_deployments = {
            item.deployment_id for item in infrastructure.deployments if item.available
        }
        result: list[ModelReplica] = []
        for replica in self._replica_set.replicas:
            deployment = deployments.get(replica.deployment_id)
            if (
                deployment is not None
                and deployment.agent_id == replica.agent_id
                and replica.agent_id in available_agents
                and replica.deployment_id in available_deployments
            ):
                result.append(replica)
        return tuple(result)

    @staticmethod
    def _missing_input_count(
        node: WorkflowNode,
        target_agent_id: str,
        infrastructure: InfrastructureState,
    ) -> int:
        artifacts = {item.artifact_id: item for item in infrastructure.artifacts}
        return sum(
            1
            for artifact_id in node.inputs
            if artifact_id not in artifacts
            or target_agent_id not in artifacts[artifact_id].locations
        )

    def _estimate(
        self,
        node: WorkflowNode,
        replica: ModelReplica,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
    ) -> CandidateCostEstimate:
        del environment  # the sidecar has already frozen deployment equivalence
        artifacts = {item.artifact_id: item for item in infrastructure.artifacts}
        runtime_agents = {item.agent_id: item for item in infrastructure.agents}
        links = {
            (item.source_agent_id, item.target_agent_id): item for item in infrastructure.links
        }
        total_bytes = 0
        transfer_ms = 0.0
        for artifact_id in node.inputs:
            artifact = artifacts.get(artifact_id)
            if artifact is None or artifact.size_bytes is None:
                return _infeasible(
                    replica.agent_id,
                    total_bytes,
                    f"missing artifact metadata: {artifact_id}",
                )
            if replica.agent_id in artifact.locations:
                continue
            if not artifact.locations:
                return _infeasible(
                    replica.agent_id,
                    total_bytes,
                    f"artifact has no location: {artifact_id}",
                )
            # RuntimeExecutor's frozen source policy is lexicographically first.
            source = sorted(artifact.locations)[0]
            link = links.get((source, replica.agent_id))
            if (
                link is None
                or not link.available
                or link.bandwidth_mbps is None
                or link.rtt_ms is None
            ):
                return _infeasible(
                    replica.agent_id,
                    total_bytes,
                    f"no measured directed link for artifact: {artifact_id}",
                )
            total_bytes += artifact.size_bytes
            transfer_ms += link.rtt_ms + (artifact.size_bytes * 8 / (link.bandwidth_mbps * 1000))
        compute = self._compute_estimates[replica.replica_id].median_service_latency_ms
        runtime = runtime_agents[replica.agent_id]
        if runtime.queue_depth not in {None, 0} or runtime.in_flight != 0:
            return _infeasible(
                replica.agent_id,
                total_bytes,
                "v1 idle-state experiment rejects nonzero queue/load",
            )
        return CandidateCostEstimate(
            agent_id=replica.agent_id,
            feasible=True,
            input_bytes=total_bytes,
            transfer_latency_ms=transfer_ms,
            compute_latency_ms=compute,
            queue_latency_ms=0,
            total_latency_ms=transfer_ms + compute,
            queue_signal=QueueSignal.IN_FLIGHT,
            queue_units=0,
        )

    @staticmethod
    def _decision(
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        replica: ModelReplica,
        scheduler: SchedulerKind,
        costs: tuple[CandidateCostEstimate, ...],
        rationale: str,
    ) -> SchedulerDecision:
        return SchedulerDecision(
            scheduler=scheduler,
            node_id=node.node_id,
            logical_agent_id=logical_agent.agent_id,
            physical=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                target_deployment_id=replica.deployment_id,
            ),
            selected_agent_id=replica.agent_id,
            selected_deployment_id=replica.deployment_id,
            candidate_costs=costs,
            rationale=rationale,
        )


class ForcedReplicaScheduler:
    def __init__(
        self,
        replica_set: EquivalentModelReplicaSet,
        forced_agent_id: str,
        *,
        ordinary_profiles: tuple[OperatorDeviceProfile, ...] = (),
    ) -> None:
        self._replica_set = replica_set
        try:
            self._forced = next(
                item for item in replica_set.replicas if item.agent_id == forced_agent_id
            )
        except StopIteration as exc:
            raise ValueError("forced agent is not an equivalent model replica") from exc
        self._ordinary = MyopicCostAwareScheduler(ordinary_profiles)

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        if (
            node.operator != "invoke_model"
            or logical_agent.model_instance_id != self._replica_set.canonical_deployment_id
        ):
            return self._ordinary.schedule(
                node, logical_agent, environment, infrastructure, registry
            )
        available = {item.deployment_id for item in infrastructure.deployments if item.available}
        if self._forced.deployment_id not in available:
            raise SchedulingError(f"forced replica is unavailable: {self._forced.deployment_id}")
        return SchedulerDecision(
            scheduler=SchedulerKind.B1_MYOPIC_COST_AWARE,
            node_id=node.node_id,
            logical_agent_id=logical_agent.agent_id,
            physical=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                target_deployment_id=self._forced.deployment_id,
            ),
            selected_agent_id=self._forced.agent_id,
            selected_deployment_id=self._forced.deployment_id,
            rationale="v1 empirical-oracle run uses an explicitly forced equivalent replica",
        )


def _infeasible(agent_id: str, input_bytes: int, reason: str) -> CandidateCostEstimate:
    return CandidateCostEstimate(
        agent_id=agent_id,
        feasible=False,
        input_bytes=input_bytes,
        reason=reason,
    )
