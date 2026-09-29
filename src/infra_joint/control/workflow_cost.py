from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import Field

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    StaticCapabilityContract,
)
from infra_joint.control.physical import AutoPhysicalScheduler, NetworkClass, PhysicalSelection
from infra_joint.control.static_feasibility import analyze_static_workflow
from infra_joint.control.validation import semantic_action
from infra_joint.control.workflow import SemanticWorkflowPlan, WorkflowRuntimeState
from infra_joint.control.workflow_profile import (
    PendingActionPhysicalProfile,
    WorkflowPhysicalView,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.state import ArtifactRuntimeState, EnvironmentSpec, InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.infrastructure.observer import InfrastructureObserver
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.resolver import BindingResolutionError
from infra_joint.workflow.costing import ExecutionCostProfile


class SelectedBindingPrediction(ContractModel):
    """Internal physical diagnostic, deliberately excluded from the logical view."""

    action_id: str = Field(min_length=1)
    selected_agent_id: str = Field(min_length=1)
    selected_deployment_id: str | None = None
    transfer_bytes: int | None = Field(default=None, ge=0)
    transfer_latency_ms: float | None = Field(default=None, ge=0)
    service_latency_ms: float | None = Field(default=None, ge=0)
    queue_latency_ms: float | None = Field(default=None, ge=0)
    total_latency_ms: float | None = Field(default=None, ge=0)


class WorkflowCostEvaluation(ContractModel):
    view: WorkflowPhysicalView
    selected_bindings: tuple[SelectedBindingPrediction, ...]


@dataclass(frozen=True, slots=True)
class _ProjectedArtifact:
    artifact_id: str
    media_type: str
    size_bytes: int | None
    locations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _CandidateCost:
    agent_id: str
    deployment_id: str | None
    remote_inputs: int | None
    transfer_bytes: int | None
    transfer_latency_ms: float | None
    service_latency_ms: float | None
    queue_units: int

    @property
    def queue_latency_ms(self) -> float | None:
        if self.service_latency_ms is None:
            return None
        return self.queue_units * self.service_latency_ms

    @property
    def total_latency_ms(self) -> float | None:
        if self.transfer_latency_ms is None or self.service_latency_ms is None:
            return None
        queue = self.queue_latency_ms
        if queue is None:
            return None
        return self.transfer_latency_ms + self.service_latency_ms + queue


class SemanticWorkflowCostEvaluator:
    """Predict AUTO execution from correlated costs for real feasible bindings."""

    def __init__(
        self,
        environment: EnvironmentSpec,
        registry: OperatorRegistry,
        profiles: tuple[ExecutionCostProfile, ...],
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        scheduler: AutoPhysicalScheduler | None = None,
    ) -> None:
        self._environment = environment
        self._registry = registry
        self._profiles = profiles
        self._task = task
        self._capabilities = capabilities
        self._scheduler = scheduler or AutoPhysicalScheduler()

    def evaluate(
        self,
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
        infrastructure: InfrastructureState,
    ) -> WorkflowPhysicalView:
        return self.evaluate_detailed(plan, state, infrastructure).view

    def evaluate_detailed(
        self,
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
        infrastructure: InfrastructureState,
    ) -> WorkflowCostEvaluation:
        state.validate_against(plan)
        static = analyze_static_workflow(
            plan,
            self._task,
            self._capabilities,
        ).artifact_map()
        runtime_artifacts = {item.artifact_id: item for item in infrastructure.artifacts}
        projected = {
            artifact_id: _ProjectedArtifact(
                artifact_id=artifact_id,
                media_type=(
                    runtime_artifacts[artifact_id].media_type or envelope.media_type
                    if artifact_id in runtime_artifacts
                    else envelope.media_type
                ),
                size_bytes=(
                    runtime_artifacts[artifact_id].size_bytes
                    if artifact_id in runtime_artifacts
                    else envelope.size_upper_bound_bytes
                ),
                locations=(
                    runtime_artifacts[artifact_id].locations
                    if artifact_id in runtime_artifacts
                    else ()
                ),
            )
            for artifact_id, envelope in static.items()
        }
        pending = set(state.pending_action_ids)
        profiles: list[PendingActionPhysicalProfile] = []
        selected_predictions: list[SelectedBindingPrediction] = []
        node_costs: dict[str, float] = {}
        unknown: set[str] = set()

        for action in _topological_actions(plan):
            if action.action_id not in pending:
                continue
            projected_state = infrastructure.model_copy(
                update={
                    "artifacts": tuple(
                        ArtifactRuntimeState(
                            artifact_id=item.artifact_id,
                            locations=item.locations,
                            media_type=item.media_type,
                            size_bytes=item.size_bytes,
                        )
                        for item in projected.values()
                    )
                }
            )
            candidates = self._candidates(action, projected, projected_state)
            try:
                selection = self._scheduler.select(
                    action,
                    semantic_action(action),
                    self._environment,
                    projected_state,
                    self._registry,
                )
            except BindingResolutionError as exc:
                selection = None
                unknown.add(exc.code.value)
            selected = _selected_cost(candidates, selection)
            profile = self._profile(
                action,
                projected,
                candidates,
                selected,
                infrastructure,
            )
            profiles.append(profile)
            unknown.update(profile.unknown_reasons)
            output_locations: tuple[str, ...] = ()
            if selected is not None and selection is not None:
                prediction = SelectedBindingPrediction(
                    action_id=action.action_id,
                    selected_agent_id=selection.selected_agent_id,
                    selected_deployment_id=selection.selected_deployment_id,
                    transfer_bytes=selected.transfer_bytes,
                    transfer_latency_ms=selected.transfer_latency_ms,
                    service_latency_ms=selected.service_latency_ms,
                    queue_latency_ms=selected.queue_latency_ms,
                    total_latency_ms=selected.total_latency_ms,
                )
                selected_predictions.append(prediction)
                if prediction.total_latency_ms is not None:
                    node_costs[action.action_id] = prediction.total_latency_ms
                output_locations = (selection.selected_agent_id,)
            for output in action.outputs:
                envelope = static[output.artifact_id]
                projected[output.artifact_id] = _ProjectedArtifact(
                    artifact_id=output.artifact_id,
                    media_type=envelope.media_type,
                    size_bytes=envelope.size_upper_bound_bytes,
                    locations=output_locations,
                )

        complete = len(node_costs) == len(profiles)
        view = WorkflowPhysicalView(
            plan_version=plan.version,
            pending_action_profiles=tuple(profiles),
            predicted_transfer_bytes=_sum_int(
                item.transfer_bytes for item in selected_predictions
            ),
            predicted_transfer_latency_ms=_sum_float(
                item.transfer_latency_ms for item in selected_predictions
            ),
            predicted_service_latency_ms=_sum_float(
                item.service_latency_ms for item in selected_predictions
            ),
            predicted_queue_latency_ms=_sum_float(
                item.queue_latency_ms for item in selected_predictions
            ),
            predicted_critical_path_ms=(
                _critical_path(plan, pending, node_costs) if complete else None
            ),
            predicted_total_work_ms=sum(node_costs.values()) if complete else None,
            unknown_reasons=tuple(sorted(unknown)),
        )
        return WorkflowCostEvaluation(
            view=view,
            selected_bindings=tuple(selected_predictions),
        )

    def _candidates(
        self,
        action: LogicalAction,
        artifacts: dict[str, _ProjectedArtifact],
        infrastructure: InfrastructureState,
    ) -> tuple[_CandidateCost, ...]:
        if isinstance(action, LogicalModelAction):
            try:
                deployments = self._scheduler.feasible_model_deployments(
                    action,
                    semantic_action(action),
                    self._environment,
                    infrastructure,
                    self._registry,
                )
            except BindingResolutionError:
                deployments = ()
            bindings = tuple((item.agent_id, item.deployment_id) for item in deployments)
        else:
            operator = self._registry.binding(action.operator).spec
            live = {item.agent_id for item in infrastructure.agents if item.available}
            bindings = tuple(
                (item.agent_id, None)
                for item in self._environment.agents
                if item.agent_id in live
                and operator.capability_requirements <= item.capabilities
            )
        return tuple(
            self._candidate_cost(action, artifacts, infrastructure, agent_id, deployment_id)
            for agent_id, deployment_id in bindings
        )

    def _candidate_cost(
        self,
        action: LogicalAction,
        artifacts: dict[str, _ProjectedArtifact],
        infrastructure: InfrastructureState,
        agent_id: str,
        deployment_id: str | None,
    ) -> _CandidateCost:
        remote = 0
        transfer_bytes = 0
        transfer_latency = 0.0
        complete_transfer = True
        for artifact_id in action.inputs:
            artifact = artifacts[artifact_id]
            if agent_id in artifact.locations:
                continue
            remote += 1
            if artifact.size_bytes is None or not artifact.locations:
                complete_transfer = False
                continue
            route = _best_transfer(
                artifact.locations,
                agent_id,
                artifact.size_bytes,
                infrastructure,
            )
            if route is None:
                complete_transfer = False
                continue
            transfer_bytes += artifact.size_bytes
            transfer_latency += route
        input_bytes = _sum_int(artifacts[item].size_bytes for item in action.inputs)
        operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
        service = self._matching_profile(operator, agent_id, deployment_id, input_bytes)
        runtime = next(item for item in infrastructure.agents if item.agent_id == agent_id)
        queue = runtime.queue_depth if runtime.queue_depth is not None else runtime.in_flight
        return _CandidateCost(
            agent_id=agent_id,
            deployment_id=deployment_id,
            remote_inputs=remote if complete_transfer else None,
            transfer_bytes=transfer_bytes if complete_transfer else None,
            transfer_latency_ms=transfer_latency if complete_transfer else None,
            service_latency_ms=service.service_latency_ms if service is not None else None,
            queue_units=queue,
        )

    def _profile(
        self,
        action: LogicalAction,
        artifacts: dict[str, _ProjectedArtifact],
        candidates: tuple[_CandidateCost, ...],
        selected: _CandidateCost | None,
        infrastructure: InfrastructureState,
    ) -> PendingActionPhysicalProfile:
        input_bytes = _sum_int(artifacts[item].size_bytes for item in action.inputs)
        remote = [item.remote_inputs for item in candidates if item.remote_inputs is not None]
        transfer = [
            item.transfer_latency_ms
            for item in candidates
            if item.transfer_latency_ms is not None
        ]
        service = [
            item.service_latency_ms for item in candidates if item.service_latency_ms is not None
        ]
        reasons: list[str] = []
        if input_bytes is None:
            reasons.append("predicted input size unavailable")
        if not candidates:
            reasons.append("no feasible candidates")
        if len(remote) != len(candidates):
            reasons.append("future input locality or route unavailable")
        if len(service) != len(candidates):
            reasons.append("one or more service profiles unavailable")
        if selected is None or selected.remote_inputs is None:
            network_class: NetworkClass = "unknown"
        elif selected.remote_inputs == 0:
            network_class = "local"
        else:
            network_class = _network_class(
                [
                    item.bandwidth_mbps
                    for item in infrastructure.links
                    if item.available and item.bandwidth_mbps is not None
                ]
            )
        return PendingActionPhysicalProfile(
            action_id=action.action_id,
            candidate_count=len(candidates),
            input_bytes=input_bytes,
            remote_input_count_range=_range(remote),
            transfer_latency_ms_range=_range(transfer),
            service_latency_ms_range=_range(service),
            queue_pressure_range=_range([item.queue_units for item in candidates]),
            network_class=network_class,
            unknown_reasons=tuple(reasons),
        )

    def _matching_profile(
        self,
        operator: str,
        agent_id: str,
        deployment_id: str | None,
        input_bytes: int | None,
    ) -> ExecutionCostProfile | None:
        matches = [
            item
            for item in self._profiles
            if item.operator == operator
            and item.agent_id in {agent_id, "*"}
            and (
                (deployment_id is None and item.deployment_id is None)
                or item.deployment_id == deployment_id
            )
        ]
        if not matches:
            return None
        return min(
            matches,
            key=lambda item: (
                item.agent_id != agent_id,
                abs((item.input_units or 0) - (input_bytes or 0)),
                item.service_latency_ms,
            ),
        )


class ObservedWorkflowProfileProvider:
    def __init__(
        self,
        observer: InfrastructureObserver,
        evaluator: SemanticWorkflowCostEvaluator,
    ) -> None:
        self._observer = observer
        self._evaluator = evaluator

    async def build(
        self,
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
    ) -> WorkflowPhysicalView:
        return self._evaluator.evaluate(plan, state, await self._observer.observe())


def _selected_cost(
    candidates: tuple[_CandidateCost, ...],
    selection: PhysicalSelection | None,
) -> _CandidateCost | None:
    if selection is None:
        return None
    return next(
        (
            item
            for item in candidates
            if item.agent_id == selection.selected_agent_id
            and item.deployment_id == selection.selected_deployment_id
        ),
        None,
    )


def _best_transfer(
    sources: tuple[str, ...],
    target: str,
    size_bytes: int,
    infrastructure: InfrastructureState,
) -> float | None:
    estimates = [
        item.rtt_ms + size_bytes * 8 / (item.bandwidth_mbps * 1_000_000) * 1000
        for item in infrastructure.links
        if item.available
        and item.source_agent_id in sources
        and item.target_agent_id == target
        and item.rtt_ms is not None
        and item.bandwidth_mbps is not None
    ]
    return min(estimates) if estimates else None


def _topological_actions(plan: SemanticWorkflowPlan) -> tuple[LogicalAction, ...]:
    actions = plan.action_map()
    declared = {item.action_id: index for index, item in enumerate(plan.actions)}
    indegree = dict.fromkeys(actions, 0)
    successors: dict[str, list[str]] = defaultdict(list)
    for edge in plan.dependencies:
        indegree[edge.consumer_action_id] += 1
        successors[edge.producer_action_id].append(edge.consumer_action_id)
    ready = sorted(
        (action_id for action_id, count in indegree.items() if count == 0),
        key=declared.__getitem__,
    )
    result: list[LogicalAction] = []
    while ready:
        action_id = ready.pop(0)
        result.append(actions[action_id])
        for successor in successors[action_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort(key=declared.__getitem__)
    return tuple(result)


def _critical_path(
    plan: SemanticWorkflowPlan,
    pending: set[str],
    node_cost: dict[str, float],
) -> float:
    predecessors: dict[str, set[str]] = defaultdict(set)
    for edge in plan.dependencies:
        if edge.consumer_action_id in pending and edge.producer_action_id in pending:
            predecessors[edge.consumer_action_id].add(edge.producer_action_id)
    distances: dict[str, float] = {}
    unresolved = set(pending)
    while unresolved:
        ready = sorted(
            action_id
            for action_id in unresolved
            if predecessors[action_id] <= distances.keys()
        )
        if not ready:
            return 0.0
        for action_id in ready:
            distances[action_id] = node_cost[action_id] + max(
                (distances[item] for item in predecessors[action_id]),
                default=0.0,
            )
            unresolved.remove(action_id)
    return max(distances.values(), default=0.0)


def _range[T: int | float](values: list[T]) -> tuple[T, T] | None:
    return (min(values), max(values)) if values else None


def _sum_int(values: Iterable[int | None]) -> int | None:
    materialized = tuple(values)
    if any(item is None for item in materialized):
        return None
    return sum(item for item in materialized if item is not None)


def _sum_float(values: Iterable[float | None]) -> float | None:
    materialized = tuple(values)
    if any(item is None for item in materialized):
        return None
    return sum(item for item in materialized if item is not None)


def _network_class(values: list[float]) -> NetworkClass:
    if not values:
        return "unknown"
    representative = min(values)
    if representative <= 5:
        return "constrained"
    if representative < 30:
        return "moderate"
    return "fast"
