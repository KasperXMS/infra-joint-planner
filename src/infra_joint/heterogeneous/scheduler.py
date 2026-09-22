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


class FixedPrefixScheduler:
    """Keep scripted upstream data preparation fixed and delegate the study node."""

    def __init__(
        self,
        delegate: "SynthesisStageScheduler",
        fixed_node_agents: dict[str, str],
        *,
        scheduler_kind: SchedulerKind,
    ) -> None:
        invalid = any(
            not key or not value for key, value in fixed_node_agents.items()
        )
        if not fixed_node_agents or invalid:
            raise ValueError("fixed prefix placements require non-empty node and agent IDs")
        self._delegate = delegate
        self._fixed_node_agents = dict(fixed_node_agents)
        self._scheduler_kind = scheduler_kind

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        target = self._fixed_node_agents.get(node.node_id)
        if target is None:
            return self._delegate.schedule(
                node, logical_agent, environment, infrastructure, registry
            )
        registry.validate_action(node.semantic_action())
        available = {item.agent_id for item in infrastructure.agents if item.available}
        if target not in available:
            raise SchedulingError(f"fixed upstream Worker is unavailable: {target}")
        return SchedulerDecision(
            scheduler=self._scheduler_kind,
            node_id=node.node_id,
            logical_agent_id=logical_agent.agent_id,
            physical=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_AGENT,
                target_agent_id=target,
            ),
            selected_agent_id=target,
            rationale="v1 scripted upstream DAG placement is frozen outside the study node",
        )


class ReplicaComputeEstimate(ContractModel):
    compute_profile_id: str = Field(min_length=1)
    replica_id: str = Field(min_length=1)
    median_service_latency_ms: float = Field(ge=0)


class SynthesisStageEstimate(ContractModel):
    """Measured cost of the fixed reduction + equivalent-model stage."""

    compute_profile_id: str = Field(min_length=1)
    replica_id: str = Field(min_length=1)
    median_reduction_latency_ms: float = Field(ge=0)
    median_model_service_latency_ms: float = Field(ge=0)

    @property
    def total_compute_latency_ms(self) -> float:
        return self.median_reduction_latency_ms + self.median_model_service_latency_ms


class SynthesisStageScheduler:
    """Select one site for a fixed reduction -> synthesis placement group.

    The large semantic package cannot be passed directly to the model context.  The
    fixed workflow therefore reduces it with BM25 before invoking an equivalent model
    replica.  This scheduler makes one physical choice at the reduction leader and
    reuses it for the model follower; it never changes the semantic DAG.
    """

    def __init__(
        self,
        kind: Literal["b0", "b1", "forced"],
        replica_set: EquivalentModelReplicaSet,
        *,
        leader_node_id: str,
        follower_node_id: str,
        intermediate_node_ids: tuple[str, ...] = (),
        stage_estimates: tuple[SynthesisStageEstimate, ...] = (),
        forced_agent_id: str | None = None,
        ordinary_profiles: tuple[OperatorDeviceProfile, ...] = (),
    ) -> None:
        self._kind = kind
        self._replica_set = replica_set
        self._leader_node_id = leader_node_id
        self._follower_node_id = follower_node_id
        if len(intermediate_node_ids) != len(set(intermediate_node_ids)):
            raise ValueError("synthesis stage intermediate node IDs must be unique")
        if {leader_node_id, follower_node_id}.intersection(intermediate_node_ids):
            raise ValueError("synthesis stage node roles must be disjoint")
        self._intermediate_node_ids = frozenset(intermediate_node_ids)
        estimates = {item.replica_id: item for item in stage_estimates}
        if len(estimates) != len(stage_estimates):
            raise ValueError("synthesis stage estimates must have unique replica IDs")
        if kind == "b1" and set(estimates) != {
            item.replica_id for item in replica_set.replicas
        }:
            raise ValueError("B1 requires one calibrated stage estimate per replica")
        self._stage_estimates = estimates
        if kind == "forced":
            if forced_agent_id is None:
                raise ValueError("forced stage placement requires an agent ID")
            if forced_agent_id not in {item.agent_id for item in replica_set.replicas}:
                raise ValueError("forced agent is not an equivalent model replica")
        elif forced_agent_id is not None:
            raise ValueError("only forced stage placement accepts forced_agent_id")
        self._forced_agent_id = forced_agent_id
        self._selected: ModelReplica | None = None
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
        stage_node_ids = {
            self._leader_node_id,
            self._follower_node_id,
            *self._intermediate_node_ids,
        }
        if node.node_id not in stage_node_ids:
            return self._ordinary.schedule(
                node, logical_agent, environment, infrastructure, registry
            )
        registry.validate_action(node.semantic_action())
        if node.node_id == self._leader_node_id:
            if self._selected is not None:
                raise SchedulingError("synthesis stage leader was scheduled more than once")
            candidates = self._available_replicas(environment, infrastructure)
            if not candidates:
                raise SchedulingError("no equivalent model replica is available")
            costs: tuple[CandidateCostEstimate, ...] = ()
            if self._kind == "forced":
                selected = next(
                    item for item in candidates if item.agent_id == self._forced_agent_id
                )
                rationale = "v1 empirical-oracle run forces the complete synthesis stage"
            elif self._kind == "b0":
                selected = min(
                    candidates,
                    key=lambda replica: (
                        ReplicaAwareScheduler.missing_input_count(
                            node, replica.agent_id, infrastructure
                        ),
                        replica.agent_id,
                    ),
                )
                rationale = (
                    "v1 B0 selected the synthesis stage site by input locality only; "
                    "no bandwidth or calibrated compute input was consumed"
                )
            else:
                costs = tuple(
                    self._estimate_stage(node, replica, infrastructure)
                    for replica in candidates
                )
                feasible = [item for item in costs if item.feasible]
                if not feasible:
                    raise SchedulingError(
                        "no equivalent synthesis stage has a complete calibrated cost",
                        candidate_costs=costs,
                    )
                selected_cost = min(
                    feasible,
                    key=lambda item: (
                        item.total_latency_ms
                        if item.total_latency_ms is not None
                        else float("inf"),
                        item.agent_id,
                    ),
                )
                selected = next(
                    item for item in candidates if item.agent_id == selected_cost.agent_id
                )
                rationale = (
                    "v1 B1 selected one fixed reduction+synthesis site using measured "
                    "transfer and compute with queue fixed to zero"
                )
            self._selected = selected
            return SchedulerDecision(
                scheduler=(
                    SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
                    if self._kind == "b0"
                    else SchedulerKind.B1_MYOPIC_COST_AWARE
                ),
                node_id=node.node_id,
                logical_agent_id=logical_agent.agent_id,
                physical=PhysicalDecision(
                    policy=PhysicalPolicy.TARGET_AGENT,
                    target_agent_id=selected.agent_id,
                ),
                selected_agent_id=selected.agent_id,
                candidate_costs=costs,
                rationale=rationale,
            )

        if self._selected is None:
            raise SchedulingError("synthesis stage follower scheduled before its leader")
        if node.node_id in self._intermediate_node_ids:
            return SchedulerDecision(
                scheduler=(
                    SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
                    if self._kind == "b0"
                    else SchedulerKind.B1_MYOPIC_COST_AWARE
                ),
                node_id=node.node_id,
                logical_agent_id=logical_agent.agent_id,
                physical=PhysicalDecision(
                    policy=PhysicalPolicy.TARGET_AGENT,
                    target_agent_id=self._selected.agent_id,
                ),
                selected_agent_id=self._selected.agent_id,
                rationale="v1 synthesis-stage intermediate reuses the leader's frozen site",
            )
        if node.operator != "invoke_model":
            raise SchedulingError("synthesis stage follower must invoke the model")
        if logical_agent.model_instance_id != self._replica_set.canonical_deployment_id:
            raise SchedulingError("synthesis stage follower changed logical model identity")
        return ReplicaAwareScheduler.decision(
            node,
            logical_agent,
            self._selected,
            (
                SchedulerKind.B0_LOCALITY_AWARE_MYOPIC
                if self._kind == "b0"
                else SchedulerKind.B1_MYOPIC_COST_AWARE
            ),
            (),
            "v1 synthesis follower reuses the leader's frozen equivalent-replica site",
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
        return tuple(
            replica
            for replica in self._replica_set.replicas
            if replica.agent_id in available_agents
            and replica.deployment_id in available_deployments
            and deployments.get(replica.deployment_id) is not None
            and deployments[replica.deployment_id].agent_id == replica.agent_id
        )

    def _estimate_stage(
        self,
        node: WorkflowNode,
        replica: ModelReplica,
        infrastructure: InfrastructureState,
    ) -> CandidateCostEstimate:
        artifacts = {item.artifact_id: item for item in infrastructure.artifacts}
        links = {
            (item.source_agent_id, item.target_agent_id): item
            for item in infrastructure.links
        }
        total_bytes = 0
        transfer_ms = 0.0
        for artifact_id in node.inputs:
            artifact = artifacts.get(artifact_id)
            if artifact is None or artifact.size_bytes is None:
                return _infeasible(
                    replica.agent_id, total_bytes, f"missing artifact metadata: {artifact_id}"
                )
            if replica.agent_id in artifact.locations:
                continue
            if not artifact.locations:
                return _infeasible(
                    replica.agent_id, total_bytes, f"artifact has no location: {artifact_id}"
                )
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
            transfer_ms += link.rtt_ms + artifact.size_bytes * 8 / (
                link.bandwidth_mbps * 1000
            )
        runtime = next(item for item in infrastructure.agents if item.agent_id == replica.agent_id)
        if runtime.queue_depth not in {None, 0} or runtime.in_flight != 0:
            return _infeasible(
                replica.agent_id,
                total_bytes,
                "v1 idle-state experiment rejects nonzero queue/load",
            )
        compute_ms = self._stage_estimates[replica.replica_id].total_compute_latency_ms
        return CandidateCostEstimate(
            agent_id=replica.agent_id,
            feasible=True,
            input_bytes=total_bytes,
            transfer_latency_ms=transfer_ms,
            compute_latency_ms=compute_ms,
            queue_latency_ms=0,
            total_latency_ms=transfer_ms + compute_ms,
            queue_signal=QueueSignal.IN_FLIGHT,
            queue_units=0,
        )


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
                    self.missing_input_count(node, replica.agent_id, infrastructure),
                    replica.agent_id,
                ),
            )
            return self.decision(
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
        return self.decision(
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
    def missing_input_count(
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
    def decision(
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
