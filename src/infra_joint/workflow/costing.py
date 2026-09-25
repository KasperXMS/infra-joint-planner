from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec, InfrastructureState, LinkRuntimeState
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import WorkflowNode, WorkflowPlan
from infra_joint.operators.registry import OperatorRegistry


class ExecutionCostProfile(ContractModel):
    """Measured service-time point used by the open-ended cost evaluator."""

    operator: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    deployment_id: str | None = None
    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    unit_kind: Literal["tokens", "bytes", "fixed"] = "tokens"
    estimated_output_bytes: int | None = Field(default=None, ge=0)
    service_latency_ms: float = Field(ge=0)
    source: str = Field(min_length=1)


class ArtifactRouteCost(ContractModel):
    artifact_id: str = Field(min_length=1)
    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    transfer_latency_ms: float = Field(ge=0)
    formula: str = "rtt_ms + size_bytes * 8 / (bandwidth_mbps * 1e6) * 1000"


class WorkflowNodeCostEstimate(ContractModel):
    node_id: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    target_agent_id: str | None = None
    deployment_id: str | None = None
    input_bytes: int | None = Field(default=None, ge=0)
    transfer_bytes: int = Field(ge=0)
    transfer_latency_ms: float = Field(ge=0)
    service_latency_ms: float | None = Field(default=None, ge=0)
    queue_units: int | None = Field(default=None, ge=0)
    queue_latency_ms: float | None = Field(default=None, ge=0)
    predicted_latency_ms: float | None = Field(default=None, ge=0)
    profile_source: str | None = None
    unknown_reasons: tuple[str, ...] = ()


class WorkflowCostEstimate(ContractModel):
    formula_version: str = "open-ended-dag-cost-v1"
    complete: bool
    predicted_critical_path_ms: float
    predicted_total_work_ms: float
    predicted_transfer_bytes: int = Field(ge=0)
    predicted_transfer_latency_ms: float = Field(ge=0)
    predicted_service_latency_ms: float = Field(ge=0)
    predicted_queue_latency_ms: float = Field(ge=0)
    evaluated_node_ids: tuple[str, ...]
    node_estimates: tuple[WorkflowNodeCostEstimate, ...]
    unknown_reasons: tuple[str, ...] = ()


class InfrastructureCostGuidance(ContractModel):
    """System-generated optimization contract, never an enumerated workflow pool."""

    formula_version: str = "open-ended-dag-cost-v1"
    objective: tuple[str, ...] = (
        "preserve benchmark semantics, evidence coverage, and output contract",
        "minimize predicted DAG critical-path latency",
        "then minimize transfer latency and bytes without reducing required evidence",
    )
    transfer_formula: str = (
        "transfer_ms = rtt_ms + size_bytes * 8 / (bandwidth_mbps * 1e6) * 1000"
    )
    node_formula: str = (
        "node_ms = input_transfer_ms + profiled_service_ms + "
        "profiled_service_ms * current_queue_units"
    )
    dag_formula: str = (
        "critical_path_ms = max over source-to-sink paths of sum(node_ms); "
        "ready branches may overlap"
    )
    placement_rule: str = (
        "non-model nodes follow B0 AUTO: capability-feasible, then fewest input "
        "artifact transfers, then stable agent ID; model nodes run at their bound deployment"
    )
    missing_data_rule: str = "unknown profile or route is unknown, never zero"
    artifact_routes: tuple[ArtifactRouteCost, ...] = ()
    execution_cost_profiles: tuple[ExecutionCostProfile, ...] = ()
    current_plan_cost: WorkflowCostEstimate | None = None


class InfrastructurePlanningView(ContractModel):
    """Live physical input admitted only to an infrastructure-aware Planner."""

    environment: EnvironmentSpec
    state: InfrastructureState
    relevant_artifact_ids: tuple[str, ...]
    cost_guidance: InfrastructureCostGuidance


class WorkflowCostEvaluator:
    """Evaluate an arbitrary valid workflow without generating candidate workflows."""

    def __init__(
        self,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
        profiles: tuple[ExecutionCostProfile, ...],
    ) -> None:
        self._environment = environment
        self._infrastructure = infrastructure
        self._registry = registry
        self._profiles = profiles
        self._agents = {item.agent_id: item for item in environment.agents}
        self._runtime_agents = {
            item.agent_id: item for item in infrastructure.agents if item.available
        }
        self._deployments = {
            item.deployment_id: item for item in environment.deployments
        }
        self._available_deployments = {
            item.deployment_id
            for item in infrastructure.deployments
            if item.available
        }
        self._links = {
            (item.source_agent_id, item.target_agent_id): item
            for item in infrastructure.links
            if item.available
            and item.bandwidth_mbps is not None
            and item.rtt_ms is not None
        }

    def guidance(
        self,
        relevant_artifact_ids: tuple[str, ...],
        *,
        current_plan: WorkflowPlan | None = None,
        task: TaskContract | None = None,
        node_ids: tuple[str, ...] | None = None,
    ) -> InfrastructureCostGuidance:
        relevant = set(relevant_artifact_ids)
        routes: list[ArtifactRouteCost] = []
        for artifact in self._infrastructure.artifacts:
            if artifact.artifact_id not in relevant or artifact.size_bytes is None:
                continue
            for target in sorted(self._runtime_agents):
                if target in artifact.locations:
                    continue
                route = self._best_route(
                    artifact.artifact_id,
                    artifact.locations,
                    target,
                    artifact.size_bytes,
                )
                if route is not None:
                    routes.append(route)
        current = None
        if current_plan is not None and task is not None:
            current = self.estimate(current_plan, task, node_ids=node_ids)
        return InfrastructureCostGuidance(
            artifact_routes=tuple(routes),
            execution_cost_profiles=self._profiles,
            current_plan_cost=current,
        )

    def estimate(
        self,
        plan: WorkflowPlan,
        task: TaskContract,
        *,
        node_ids: tuple[str, ...] | None = None,
    ) -> WorkflowCostEstimate:
        nodes = {item.node_id: item for item in plan.nodes}
        included = set(nodes if node_ids is None else node_ids)
        unknown_node_ids = sorted(included - set(nodes))
        if unknown_node_ids:
            raise ValueError(f"cost evaluation references unknown nodes: {unknown_node_ids}")
        logical_agents = {item.agent_id: item for item in plan.agents}
        artifact_locations = {
            item.artifact_id: set(item.locations)
            for item in self._infrastructure.artifacts
        }
        artifact_sizes = {
            item.artifact_id: item.size_bytes
            for item in self._infrastructure.artifacts
        }
        for artifact in task.artifacts:
            artifact_sizes.setdefault(artifact.artifact_id, artifact.size_bytes)
        predecessors: dict[str, set[str]] = defaultdict(set)
        successors: dict[str, set[str]] = defaultdict(set)
        for edge in plan.edges:
            predecessors[edge.consumer_node].add(edge.producer_node)
            successors[edge.producer_node].add(edge.consumer_node)

        estimates: dict[str, WorkflowNodeCostEstimate] = {}
        completion_ms: dict[str, float] = {}
        unknowns: list[str] = []
        for node in self._topological_nodes(plan):
            if node.node_id not in included:
                completion_ms[node.node_id] = 0.0
                continue
            deployment_id: str | None = None
            if node.operator == "invoke_model":
                deployment_id = logical_agents[node.agent_id].model_instance_id
                deployment = self._deployments.get(deployment_id)
                target = (
                    deployment.agent_id
                    if deployment is not None
                    and deployment_id in self._available_deployments
                    else None
                )
            else:
                target = self._auto_target(node, artifact_locations)

            node_unknown: list[str] = []
            input_sizes = [artifact_sizes.get(item) for item in node.inputs]
            input_bytes = (
                sum(value for value in input_sizes if value is not None)
                if all(value is not None for value in input_sizes)
                else None
            )
            transfer_bytes = 0
            transfer_latency_ms = 0.0
            if target is None:
                node_unknown.append("no feasible predicted target")
            else:
                for artifact_id in node.inputs:
                    locations = artifact_locations.get(artifact_id)
                    size_bytes = artifact_sizes.get(artifact_id)
                    if not locations:
                        node_unknown.append(f"artifact location unknown: {artifact_id}")
                        continue
                    if target in locations:
                        continue
                    if size_bytes is None:
                        node_unknown.append(f"artifact size unknown: {artifact_id}")
                        continue
                    route = self._best_route(
                        artifact_id,
                        tuple(locations),
                        target,
                        size_bytes,
                    )
                    if route is None:
                        node_unknown.append(f"transfer route unknown: {artifact_id}->{target}")
                        continue
                    transfer_bytes += size_bytes
                    transfer_latency_ms += route.transfer_latency_ms
                    locations.add(target)

            profile = self._profile(node, target, deployment_id, input_bytes)
            service_latency_ms = profile.service_latency_ms if profile is not None else None
            if profile is None:
                node_unknown.append(
                    f"service profile unknown: {node.operator}/{target or 'unplaced'}"
                )
            runtime = self._runtime_agents.get(target) if target is not None else None
            queue_units = None
            queue_latency_ms = None
            if runtime is not None and service_latency_ms is not None:
                queue_units = (
                    runtime.queue_depth
                    if runtime.queue_depth is not None
                    else runtime.in_flight
                )
                queue_latency_ms = service_latency_ms * queue_units
            elif target is not None:
                node_unknown.append(f"queue/service estimate unknown: {target}")
            predicted = None
            if service_latency_ms is not None and queue_latency_ms is not None:
                predicted = transfer_latency_ms + service_latency_ms + queue_latency_ms

            estimate = WorkflowNodeCostEstimate(
                node_id=node.node_id,
                operator=node.operator,
                target_agent_id=target,
                deployment_id=deployment_id,
                input_bytes=input_bytes,
                transfer_bytes=transfer_bytes,
                transfer_latency_ms=transfer_latency_ms,
                service_latency_ms=service_latency_ms,
                queue_units=queue_units,
                queue_latency_ms=queue_latency_ms,
                predicted_latency_ms=predicted,
                profile_source=profile.source if profile is not None else None,
                unknown_reasons=tuple(node_unknown),
            )
            estimates[node.node_id] = estimate
            if node_unknown:
                unknowns.extend(f"{node.node_id}: {item}" for item in node_unknown)
            predecessor_finish = max(
                (completion_ms[item] for item in predecessors[node.node_id]),
                default=0.0,
            )
            completion_ms[node.node_id] = predecessor_finish + (predicted or 0.0)
            self._propagate_outputs(
                node,
                target,
                deployment_id,
                profile,
                input_sizes,
                artifact_locations,
                artifact_sizes,
            )

        ordered = tuple(
            estimates[item.node_id] for item in plan.nodes if item.node_id in included
        )
        known = [item for item in ordered if item.predicted_latency_ms is not None]
        sinks = [
            node_id
            for node_id in included
            if not (successors[node_id] & included)
        ]
        return WorkflowCostEstimate(
            complete=not unknowns,
            predicted_critical_path_ms=max(
                (completion_ms[node_id] for node_id in sinks), default=0.0
            ),
            predicted_total_work_ms=sum(
                item.predicted_latency_ms or 0.0 for item in ordered
            ),
            predicted_transfer_bytes=sum(item.transfer_bytes for item in ordered),
            predicted_transfer_latency_ms=sum(
                item.transfer_latency_ms for item in ordered
            ),
            predicted_service_latency_ms=sum(
                item.service_latency_ms or 0.0 for item in known
            ),
            predicted_queue_latency_ms=sum(
                item.queue_latency_ms or 0.0 for item in known
            ),
            evaluated_node_ids=tuple(
                item.node_id for item in plan.nodes if item.node_id in included
            ),
            node_estimates=ordered,
            unknown_reasons=tuple(unknowns),
        )

    def _auto_target(
        self,
        node: WorkflowNode,
        artifact_locations: dict[str, set[str]],
    ) -> str | None:
        operator = self._registry.binding(node.operator).spec
        feasible = [
            agent_id
            for agent_id, agent in self._agents.items()
            if agent_id in self._runtime_agents
            and operator.capability_requirements <= agent.capabilities
        ]
        if not feasible:
            return None
        return min(
            feasible,
            key=lambda agent_id: (
                sum(
                    agent_id not in artifact_locations.get(artifact_id, set())
                    for artifact_id in node.inputs
                ),
                agent_id,
            ),
        )

    def _best_route(
        self,
        artifact_id: str,
        sources: tuple[str, ...] | set[str],
        target: str,
        size_bytes: int,
    ) -> ArtifactRouteCost | None:
        candidates: list[tuple[float, str, LinkRuntimeState]] = []
        for source in sources:
            link = self._links.get((source, target))
            if link is None or link.bandwidth_mbps is None or link.rtt_ms is None:
                continue
            latency = (
                link.rtt_ms
                + size_bytes * 8 / (link.bandwidth_mbps * 1_000_000) * 1000
            )
            candidates.append((latency, source, link))
        if not candidates:
            return None
        latency, source, _ = min(candidates, key=lambda item: (item[0], item[1]))
        return ArtifactRouteCost(
            artifact_id=artifact_id,
            source_agent_id=source,
            target_agent_id=target,
            size_bytes=size_bytes,
            transfer_latency_ms=latency,
        )

    def _profile(
        self,
        node: WorkflowNode,
        agent_id: str | None,
        deployment_id: str | None,
        input_units: int | None,
    ) -> ExecutionCostProfile | None:
        if agent_id is None:
            return None
        candidates = [
            item
            for item in self._profiles
            if item.operator == node.operator
            and item.agent_id in {agent_id, "*"}
            and (
                (deployment_id is None and item.deployment_id is None)
                or item.deployment_id == deployment_id
            )
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda item: (
                item.agent_id != agent_id,
                abs((item.input_units or 0) - (input_units or 0)),
                item.service_latency_ms,
            ),
        )

    def _propagate_outputs(
        self,
        node: WorkflowNode,
        target: str | None,
        deployment_id: str | None,
        profile: ExecutionCostProfile | None,
        input_sizes: list[int | None],
        locations: dict[str, set[str]],
        sizes: dict[str, int | None],
    ) -> None:
        output_size = profile.estimated_output_bytes if profile is not None else None
        if (
            output_size is None
            and node.operator == "invoke_model"
            and deployment_id is not None
        ):
            logical_output = node.arguments.get("output_artifact_id")
            if logical_output is not None:
                output_size = 4 * self._deployments[deployment_id].reserved_output_tokens
        if output_size is None and node.operator in {
            "filter_records",
            "select_fields",
            "top_k_records",
            "aggregate_records",
            "read_artifact",
        }:
            output_size = input_sizes[0] if input_sizes else None
        if (
            output_size is None
            and node.operator in {"aggregate_artifacts", "derive_fields"}
            and input_sizes
            and all(item is not None for item in input_sizes)
        ):
            output_size = sum(item or 0 for item in input_sizes)
        if (
            output_size is None
            and node.operator == "bm25_retrieve"
            and input_sizes
            and input_sizes[0] is not None
        ):
            output_size = min(
                input_sizes[0],
                int(node.arguments.get("top_k", 1)) * 4_096,
            )
        per_output = (
            output_size // len(node.outputs)
            if output_size is not None and node.outputs
            else output_size
        )
        for artifact_id in node.outputs:
            sizes[artifact_id] = per_output
            locations[artifact_id] = {target} if target is not None else set()

    @staticmethod
    def _topological_nodes(plan: WorkflowPlan) -> tuple[WorkflowNode, ...]:
        nodes = {item.node_id: item for item in plan.nodes}
        declared = {item.node_id: index for index, item in enumerate(plan.nodes)}
        indegree = dict.fromkeys(nodes, 0)
        successors: dict[str, list[str]] = defaultdict(list)
        for edge in plan.edges:
            indegree[edge.consumer_node] += 1
            successors[edge.producer_node].append(edge.consumer_node)
        ready = sorted(
            (node_id for node_id, count in indegree.items() if count == 0),
            key=declared.__getitem__,
        )
        ordered: list[WorkflowNode] = []
        while ready:
            node_id = ready.pop(0)
            ordered.append(nodes[node_id])
            for successor in successors[node_id]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
                    ready.sort(key=declared.__getitem__)
        return tuple(ordered)
