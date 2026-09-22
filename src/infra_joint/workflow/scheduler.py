from enum import StrEnum
from typing import Literal, Protocol, Self

from pydantic import Field, model_validator

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy
from infra_joint.core.base import ContractModel
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.core.workflow import LogicalAgent, WorkflowNode
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec


class SchedulerKind(StrEnum):
    B0_LOCALITY_AWARE_MYOPIC = "b0_locality_aware_myopic"
    B1_MYOPIC_COST_AWARE = "b1_myopic_cost_aware"


class QueueSignal(StrEnum):
    QUEUE_DEPTH = "queue_depth"
    IN_FLIGHT = "in_flight"


class OperatorDeviceProfile(ContractModel):
    """Measured single-operation service time for an operator/device pair."""

    operator_id: str = Field(min_length=1)
    device: str = Field(min_length=1)
    compute_latency_ms: float = Field(ge=0)


class CandidateCostEstimate(ContractModel):
    """Auditable, current-node-only estimate for one physical agent."""

    agent_id: str = Field(min_length=1)
    feasible: bool
    input_bytes: int = Field(ge=0)
    transfer_latency_ms: float | None = Field(default=None, ge=0)
    compute_latency_ms: float | None = Field(default=None, ge=0)
    queue_latency_ms: float | None = Field(default=None, ge=0)
    total_latency_ms: float | None = Field(default=None, ge=0)
    queue_signal: QueueSignal | None = None
    queue_units: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @model_validator(mode="after")
    def complete_cost_if_feasible(self) -> Self:
        components = (
            self.transfer_latency_ms,
            self.compute_latency_ms,
            self.queue_latency_ms,
            self.total_latency_ms,
            self.queue_signal,
            self.queue_units,
        )
        if self.feasible and any(component is None for component in components):
            raise ValueError("a feasible candidate must contain a complete cost estimate")
        if self.feasible and self.reason is not None:
            raise ValueError("a feasible candidate must not contain an infeasibility reason")
        if not self.feasible and not self.reason:
            raise ValueError("an infeasible candidate must explain why it is infeasible")
        return self


class SchedulerDecision(ContractModel):
    """Physical decision plus the evidence used by a workflow scheduler."""

    scheduler: SchedulerKind
    node_id: str = Field(min_length=1)
    logical_agent_id: str = Field(min_length=1)
    physical: PhysicalDecision
    selected_agent_id: str | None = None
    selected_deployment_id: str | None = None
    candidate_costs: tuple[CandidateCostEstimate, ...] = ()
    rationale: str = Field(min_length=1)


class SchedulingError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        candidate_costs: tuple[CandidateCostEstimate, ...] = (),
    ) -> None:
        super().__init__(message)
        self.candidate_costs = candidate_costs


class WorkflowScheduler(Protocol):
    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision: ...


def _assert_node_agent(node: WorkflowNode, logical_agent: LogicalAgent) -> None:
    if node.agent_id != logical_agent.agent_id:
        raise SchedulingError(
            f"workflow node {node.node_id} belongs to logical agent {node.agent_id}, "
            f"not {logical_agent.agent_id}"
        )


def _operator_spec(node: WorkflowNode, registry: OperatorRegistry) -> OperatorSpec:
    try:
        operator = registry.binding(node.operator).spec
    except KeyError as exc:
        raise SchedulingError(f"unknown workflow operator: {node.operator}") from exc
    registry.validate_action(node.semantic_action())
    return operator


def _fixed_deployment(
    logical_agent: LogicalAgent,
    environment: EnvironmentSpec,
    infrastructure: InfrastructureState,
) -> DeploymentSpec:
    deployments = {item.deployment_id: item for item in environment.deployments}
    deployment = deployments.get(logical_agent.model_instance_id)
    if deployment is None:
        raise SchedulingError(
            "logical agent references an unknown model deployment: "
            f"{logical_agent.model_instance_id}"
        )
    available = {
        item.deployment_id for item in infrastructure.deployments if item.available
    }
    if deployment.deployment_id not in available:
        raise SchedulingError(
            f"fixed model deployment is unavailable: {deployment.deployment_id}"
        )
    return deployment


class LocalityAwareMyopicScheduler:
    """B0: defer ordinary placement to Runtime AUTO; pin model nodes by identity."""

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        _assert_node_agent(node, logical_agent)
        _operator_spec(node, registry)
        if node.operator != "invoke_model":
            return SchedulerDecision(
                scheduler=SchedulerKind.B0_LOCALITY_AWARE_MYOPIC,
                node_id=node.node_id,
                logical_agent_id=logical_agent.agent_id,
                physical=PhysicalDecision(policy=PhysicalPolicy.AUTO),
                rationale=(
                    "ordinary node uses Runtime AUTO locality resolution; no future workflow "
                    "state is considered"
                ),
            )

        deployment = _fixed_deployment(logical_agent, environment, infrastructure)
        return SchedulerDecision(
            scheduler=SchedulerKind.B0_LOCALITY_AWARE_MYOPIC,
            node_id=node.node_id,
            logical_agent_id=logical_agent.agent_id,
            physical=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                target_deployment_id=deployment.deployment_id,
            ),
            selected_agent_id=deployment.agent_id,
            selected_deployment_id=deployment.deployment_id,
            rationale="model node is pinned to the logical agent model instance",
        )


class MyopicCostAwareScheduler:
    """B1: minimize measured transfer + compute + current queue cost per ready node."""

    def __init__(self, profiles: tuple[OperatorDeviceProfile, ...]) -> None:
        keys = [(item.operator_id, item.device) for item in profiles]
        if len(keys) != len(set(keys)):
            raise ValueError("operator/device profiles must be unique")
        self._profiles = {
            (item.operator_id, item.device): item for item in profiles
        }

    def schedule(
        self,
        node: WorkflowNode,
        logical_agent: LogicalAgent,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> SchedulerDecision:
        _assert_node_agent(node, logical_agent)
        operator = _operator_spec(node, registry)

        agents = {item.agent_id: item for item in environment.agents}
        runtime_agents = {item.agent_id: item for item in infrastructure.agents}
        if node.operator == "invoke_model":
            deployment = _fixed_deployment(logical_agent, environment, infrastructure)
            agent = agents.get(deployment.agent_id)
            runtime = runtime_agents.get(deployment.agent_id)
            if agent is None or runtime is None:
                raise SchedulingError(
                    f"fixed deployment agent is absent: {deployment.agent_id}"
                )
            estimate = self._estimate(
                node,
                operator,
                agent,
                runtime,
                environment,
                infrastructure,
            )
            if not estimate.feasible:
                raise SchedulingError(
                    f"fixed model deployment is not schedulable: {estimate.reason}",
                    candidate_costs=(estimate,),
                )
            return SchedulerDecision(
                scheduler=SchedulerKind.B1_MYOPIC_COST_AWARE,
                node_id=node.node_id,
                logical_agent_id=logical_agent.agent_id,
                physical=PhysicalDecision(
                    policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                    target_deployment_id=deployment.deployment_id,
                ),
                selected_agent_id=deployment.agent_id,
                selected_deployment_id=deployment.deployment_id,
                candidate_costs=(estimate,),
                rationale=(
                    "model node remains pinned to the logical agent model instance; cost is "
                    "telemetry only and no alternative deployment is considered"
                ),
            )

        costs = tuple(
            self._estimate(
                node,
                operator,
                agent,
                runtime_agents.get(agent.agent_id),
                environment,
                infrastructure,
            )
            for agent in sorted(agents.values(), key=lambda item: item.agent_id)
        )
        feasible = [item for item in costs if item.feasible]
        if not feasible:
            raise SchedulingError(
                f"no feasible physical agent for workflow node: {node.node_id}",
                candidate_costs=costs,
            )
        selected = min(
            feasible,
            key=lambda item: (
                item.total_latency_ms if item.total_latency_ms is not None else float("inf"),
                item.agent_id,
            ),
        )
        return SchedulerDecision(
            scheduler=SchedulerKind.B1_MYOPIC_COST_AWARE,
            node_id=node.node_id,
            logical_agent_id=logical_agent.agent_id,
            physical=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_AGENT,
                target_agent_id=selected.agent_id,
            ),
            selected_agent_id=selected.agent_id,
            candidate_costs=costs,
            rationale=(
                "selected the minimum current-node transfer + compute + queue estimate; "
                "future DAG state and global search are excluded"
            ),
        )

    def _estimate(
        self,
        node: WorkflowNode,
        operator: OperatorSpec,
        agent: AgentSpec,
        runtime_agent: AgentRuntimeState | None,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
    ) -> CandidateCostEstimate:
        artifacts = {item.artifact_id: item for item in infrastructure.artifacts}
        input_bytes = sum(
            item.size_bytes or 0
            for artifact_id in node.inputs
            if (item := artifacts.get(artifact_id)) is not None
        )
        if runtime_agent is None or not runtime_agent.available:
            return self._infeasible(agent.agent_id, input_bytes, "agent is unavailable")
        if not operator.capability_requirements <= agent.capabilities:
            return self._infeasible(
                agent.agent_id,
                input_bytes,
                "agent does not satisfy operator capability requirements",
            )
        profile = self._profiles.get((operator.operator_id, agent.device))
        if profile is None:
            return self._infeasible(
                agent.agent_id,
                input_bytes,
                "operator/device compute profile is missing",
            )

        transfer_latency_ms = 0.0
        available_agents = {
            item.agent_id for item in infrastructure.agents if item.available
        }
        links = self._directed_links(environment, infrastructure)
        for artifact_id in node.inputs:
            artifact = artifacts.get(artifact_id)
            if artifact is None:
                return self._infeasible(
                    agent.agent_id,
                    input_bytes,
                    f"input artifact is absent: {artifact_id}",
                )
            if artifact.size_bytes is None:
                return self._infeasible(
                    agent.agent_id,
                    input_bytes,
                    f"input artifact size is unavailable: {artifact_id}",
                )
            if agent.agent_id in artifact.locations:
                continue
            source_costs = [
                self._transfer_latency_ms(artifact.size_bytes, links[(source, agent.agent_id)])
                for source in artifact.locations
                if source in available_agents and (source, agent.agent_id) in links
            ]
            if not source_costs:
                return self._infeasible(
                    agent.agent_id,
                    input_bytes,
                    f"no measured available directed link for artifact: {artifact_id}",
                )
            transfer_latency_ms += min(source_costs)

        if runtime_agent.queue_depth is not None:
            queue_signal = QueueSignal.QUEUE_DEPTH
            queue_units = runtime_agent.queue_depth
        else:
            queue_signal = QueueSignal.IN_FLIGHT
            queue_units = runtime_agent.in_flight
        compute_latency_ms = profile.compute_latency_ms
        queue_latency_ms = compute_latency_ms * queue_units
        return CandidateCostEstimate(
            agent_id=agent.agent_id,
            feasible=True,
            input_bytes=input_bytes,
            transfer_latency_ms=transfer_latency_ms,
            compute_latency_ms=compute_latency_ms,
            queue_latency_ms=queue_latency_ms,
            total_latency_ms=(
                transfer_latency_ms + compute_latency_ms + queue_latency_ms
            ),
            queue_signal=queue_signal,
            queue_units=queue_units,
        )

    @staticmethod
    def _directed_links(
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
    ) -> dict[tuple[str, str], LinkRuntimeState]:
        declared = {
            (item.source_agent_id, item.target_agent_id) for item in environment.links
        }
        measured: dict[tuple[str, str], LinkRuntimeState] = {}
        for link in infrastructure.links:
            key = (link.source_agent_id, link.target_agent_id)
            if (
                key in declared
                and link.available
                and link.bandwidth_mbps is not None
                and link.rtt_ms is not None
            ):
                measured[key] = link
        return measured

    @staticmethod
    def _transfer_latency_ms(size_bytes: int, link: LinkRuntimeState) -> float:
        if link.bandwidth_mbps is None or link.rtt_ms is None:
            raise ValueError("transfer estimate requires measured bandwidth and RTT")
        serialization_ms = size_bytes * 8 / (link.bandwidth_mbps * 1_000_000) * 1000
        return link.rtt_ms + serialization_ms

    @staticmethod
    def _infeasible(
        agent_id: str,
        input_bytes: int,
        reason: str,
    ) -> CandidateCostEstimate:
        return CandidateCostEstimate(
            agent_id=agent_id,
            feasible=False,
            input_bytes=input_bytes,
            reason=reason,
        )


SchedulingMode = Literal["b0", "b1"]


def build_scheduler(
    mode: SchedulingMode,
    *,
    profiles: tuple[OperatorDeviceProfile, ...] = (),
) -> WorkflowScheduler:
    if mode == "b0":
        return LocalityAwareMyopicScheduler()
    return MyopicCostAwareScheduler(profiles)
