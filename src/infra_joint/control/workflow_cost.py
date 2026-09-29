from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

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


class ConcurrentServiceProfile(ContractModel):
    """Measured per-action service time at one worker-level concurrency."""

    operator: str = Field(min_length=1)
    concurrency: int = Field(ge=2)
    agent_id: str = Field(default="*", min_length=1)
    deployment_id: str | None = None
    input_units: int | None = Field(default=None, ge=0)
    unit_kind: Literal["bytes", "fixed"] = "bytes"
    service_latency_ms: float = Field(ge=0)
    source: str = Field(min_length=1)


class ConcurrentTransferProfile(ContractModel):
    """Measured per-flow latency for a shared directed link at one concurrency."""

    source_agent_id: str = Field(default="*", min_length=1)
    target_agent_id: str = Field(default="*", min_length=1)
    concurrency: int = Field(ge=2)
    input_units: int | None = Field(default=None, ge=0)
    unit_kind: Literal["bytes", "fixed"] = "bytes"
    transfer_latency_ms: float = Field(ge=0)
    source: str = Field(min_length=1)


class SelectedBindingPrediction(ContractModel):
    """Internal physical diagnostic, deliberately excluded from the logical view."""

    action_id: str = Field(min_length=1)
    frontier_index: int = Field(ge=0)
    selected_agent_id: str = Field(min_length=1)
    selected_deployment_id: str | None = None
    concurrency: int = Field(default=1, ge=1)
    transfer_bytes: int | None = Field(default=None, ge=0)
    base_transfer_latency_ms: float | None = Field(default=None, ge=0)
    transfer_latency_ms: float | None = Field(default=None, ge=0)
    base_service_latency_ms: float | None = Field(default=None, ge=0)
    service_latency_ms: float | None = Field(default=None, ge=0)
    queue_latency_ms: float | None = Field(default=None, ge=0)
    total_latency_ms: float | None = Field(default=None, ge=0)
    concurrency_profile_source: str | None = None
    transfer_concurrency_profile_sources: tuple[str, ...] = ()


class ConcurrentGroupPrediction(ContractModel):
    """Internal worker-level concurrency group for one projected ready frontier."""

    selected_agent_id: str = Field(min_length=1)
    action_ids: tuple[str, ...] = Field(min_length=2)
    deployment_ids: tuple[str, ...] = ()
    concurrency: int = Field(ge=2)
    profile_complete: bool


class ConcurrentTransferGroupPrediction(ContractModel):
    """Internal directed-link transfer group for one projected ready frontier."""

    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    action_ids: tuple[str, ...] = Field(min_length=2)
    artifact_ids: tuple[str, ...] = Field(min_length=2)
    concurrency: int = Field(ge=2)
    profile_complete: bool


class FrontierPrediction(ContractModel):
    frontier_index: int = Field(ge=0)
    action_ids: tuple[str, ...] = Field(min_length=1)
    concurrency_groups: tuple[ConcurrentGroupPrediction, ...] = ()
    transfer_concurrency_groups: tuple[ConcurrentTransferGroupPrediction, ...] = ()


class ProjectedArtifactPrediction(ContractModel):
    """Internal final projected artifact state for deterministic projection audits."""

    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=0)
    locations: tuple[str, ...]


class WorkflowCostEvaluation(ContractModel):
    view: WorkflowPhysicalView
    selected_bindings: tuple[SelectedBindingPrediction, ...]
    frontiers: tuple[FrontierPrediction, ...]
    projected_artifacts: tuple[ProjectedArtifactPrediction, ...]


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
    unknown_reasons: tuple[str, ...]
    transfer_demands: tuple[_TransferDemand, ...]


@dataclass(frozen=True, slots=True)
class _TransferDemand:
    artifact_id: str
    source_agent_id: str
    target_agent_id: str
    size_bytes: int
    base_latency_ms: float | None
    sequence_index: int


@dataclass(slots=True)
class _FrontierAction:
    action: LogicalAction
    candidates: tuple[_CandidateCost, ...]
    selection: PhysicalSelection | None
    selected: _CandidateCost | None
    profile: PendingActionPhysicalProfile
    adjusted_transfer_latency_ms: float | None
    adjusted_service_latency_ms: float | None
    concurrency: int = 1
    concurrency_profile_source: str | None = None
    transfer_concurrency_profile_sources: tuple[str, ...] = ()


class SemanticWorkflowCostEvaluator:
    """Simulate pending ready frontiers using the real AUTO selection policy."""

    def __init__(
        self,
        environment: EnvironmentSpec,
        registry: OperatorRegistry,
        profiles: tuple[ExecutionCostProfile, ...],
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        concurrent_profiles: tuple[ConcurrentServiceProfile, ...] = (),
        concurrent_transfer_profiles: tuple[ConcurrentTransferProfile, ...] = (),
        scheduler: AutoPhysicalScheduler | None = None,
    ) -> None:
        self._environment = environment
        self._registry = registry
        self._profiles = profiles
        self._concurrent_profiles = concurrent_profiles
        self._concurrent_transfer_profiles = concurrent_transfer_profiles
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
        static = analyze_static_workflow(plan, self._task, self._capabilities).artifact_map()
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
        actions = plan.action_map()
        declared_order = {item.action_id: index for index, item in enumerate(plan.actions)}
        predecessors = _predecessors(plan)
        pending = set(state.pending_action_ids)
        initial_pending_count = len(pending)
        completed = set(state.completed_action_ids)
        profiles: list[PendingActionPhysicalProfile] = []
        predictions: list[SelectedBindingPrediction] = []
        frontier_predictions: list[FrontierPrediction] = []
        node_costs: dict[str, float] = {}
        unknown: set[str] = set()
        frontier_index = 0

        while pending:
            ready_ids = sorted(
                (
                    action_id
                    for action_id in pending
                    if predecessors[action_id] <= completed
                ),
                key=declared_order.__getitem__,
            )
            if not ready_ids:
                unknown.add("workflow_projection_stalled")
                break

            # Every selection and candidate estimate in this frontier uses this exact snapshot.
            snapshot = _projected_state(infrastructure, projected)
            frontier: list[_FrontierAction] = []
            for action_id in ready_ids:
                action = actions[action_id]
                candidates = self._candidates(action, projected, snapshot)
                try:
                    selection = self._scheduler.select(
                        action,
                        semantic_action(action),
                        self._environment,
                        snapshot,
                        self._registry,
                    )
                except BindingResolutionError as exc:
                    selection = None
                    unknown.add(exc.code.value)
                selected = _selected_cost(candidates, selection)
                profile = self._profile(action, projected, candidates, selected, snapshot)
                frontier.append(
                    _FrontierAction(
                        action=action,
                        candidates=candidates,
                        selection=selection,
                        selected=selected,
                        profile=profile,
                        adjusted_transfer_latency_ms=(
                            selected.transfer_latency_ms if selected is not None else None
                        ),
                        adjusted_service_latency_ms=(
                            selected.service_latency_ms if selected is not None else None
                        ),
                    )
                )

            service_groups = self._apply_service_concurrency_profiles(frontier, projected)
            transfer_groups = self._apply_transfer_concurrency_profiles(frontier)
            frontier_predictions.append(
                FrontierPrediction(
                    frontier_index=frontier_index,
                    action_ids=tuple(ready_ids),
                    concurrency_groups=service_groups,
                    transfer_concurrency_groups=transfer_groups,
                )
            )
            input_replicas: dict[str, set[str]] = defaultdict(set)
            output_updates: dict[str, _ProjectedArtifact] = {}
            for item in frontier:
                profiles.append(item.profile)
                unknown.update(item.profile.unknown_reasons)
                if item.selection is None or item.selected is None:
                    continue
                selected = item.selected
                transfer = item.adjusted_transfer_latency_ms
                service = item.adjusted_service_latency_ms
                queue_latency = (
                    selected.queue_units * service if service is not None else None
                )
                total = _total_latency(
                    transfer,
                    service,
                    queue_latency,
                )
                prediction = SelectedBindingPrediction(
                    action_id=item.action.action_id,
                    frontier_index=frontier_index,
                    selected_agent_id=item.selection.selected_agent_id,
                    selected_deployment_id=item.selection.selected_deployment_id,
                    concurrency=item.concurrency,
                    transfer_bytes=selected.transfer_bytes,
                    base_transfer_latency_ms=selected.transfer_latency_ms,
                    transfer_latency_ms=transfer,
                    base_service_latency_ms=selected.service_latency_ms,
                    service_latency_ms=service,
                    queue_latency_ms=queue_latency,
                    total_latency_ms=total,
                    concurrency_profile_source=item.concurrency_profile_source,
                    transfer_concurrency_profile_sources=(
                        item.transfer_concurrency_profile_sources
                    ),
                )
                predictions.append(prediction)
                if total is not None:
                    node_costs[item.action.action_id] = total
                target = item.selection.selected_agent_id
                for artifact_id in item.action.inputs:
                    input_replicas[artifact_id].add(target)
                for output in item.action.outputs:
                    envelope = static[output.artifact_id]
                    output_updates[output.artifact_id] = _ProjectedArtifact(
                        artifact_id=output.artifact_id,
                        media_type=envelope.media_type,
                        size_bytes=envelope.size_upper_bound_bytes,
                        locations=(target,),
                    )

            # Runtime localization replicas and outputs become visible only after the whole
            # gather-style frontier completes. Siblings never observe each other's updates.
            for artifact_id, targets in input_replicas.items():
                artifact = projected[artifact_id]
                projected[artifact_id] = _ProjectedArtifact(
                    artifact_id=artifact.artifact_id,
                    media_type=artifact.media_type,
                    size_bytes=artifact.size_bytes,
                    locations=tuple(sorted(set(artifact.locations) | targets)),
                )
            projected.update(output_updates)
            pending.difference_update(ready_ids)
            completed.update(ready_ids)
            frontier_index += 1

        complete = (
            len(profiles) == initial_pending_count
            and len(predictions) == initial_pending_count
            and len(node_costs) == initial_pending_count
        )
        view = WorkflowPhysicalView(
            plan_version=plan.version,
            pending_action_profiles=tuple(profiles),
            predicted_transfer_bytes=(
                _sum_int(item.transfer_bytes for item in predictions)
                if len(predictions) == initial_pending_count
                else None
            ),
            predicted_transfer_latency_ms=(
                _sum_float(item.transfer_latency_ms for item in predictions)
                if len(predictions) == initial_pending_count
                else None
            ),
            predicted_service_latency_ms=(
                _sum_float(item.service_latency_ms for item in predictions)
                if len(predictions) == initial_pending_count
                else None
            ),
            predicted_queue_latency_ms=(
                _sum_float(item.queue_latency_ms for item in predictions)
                if len(predictions) == initial_pending_count
                else None
            ),
            predicted_critical_path_ms=(
                _critical_path(plan, set(state.pending_action_ids), node_costs)
                if complete
                else None
            ),
            predicted_total_work_ms=(sum(node_costs.values()) if complete else None),
            unknown_reasons=tuple(sorted(unknown)),
        )
        return WorkflowCostEvaluation(
            view=view,
            selected_bindings=tuple(predictions),
            frontiers=tuple(frontier_predictions),
            projected_artifacts=tuple(
                ProjectedArtifactPrediction(
                    artifact_id=item.artifact_id,
                    media_type=item.media_type,
                    size_bytes=item.size_bytes,
                    locations=item.locations,
                )
                for item in projected.values()
            ),
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
        remote_known = True
        transfer_bytes = 0
        transfer_bytes_known = True
        transfer_latency = 0.0
        transfer_latency_known = True
        reasons: set[str] = set()
        transfer_demands: list[_TransferDemand] = []
        transfer_sequence = 0
        for artifact_id in action.inputs:
            artifact = artifacts[artifact_id]
            if not artifact.locations:
                remote_known = False
                transfer_bytes_known = False
                transfer_latency_known = False
                reasons.add("future_artifact_location_unknown")
                continue
            if agent_id in artifact.locations:
                continue
            remote += 1
            if artifact.size_bytes is None:
                transfer_bytes_known = False
                transfer_latency_known = False
                reasons.add("future_artifact_size_unknown")
                continue
            transfer_bytes += artifact.size_bytes
            route = _runtime_transfer(
                artifact.locations,
                agent_id,
                artifact.size_bytes,
                infrastructure,
                self._environment,
            )
            if route is None:
                transfer_latency_known = False
                reasons.add("future_artifact_location_unknown")
                continue
            source_agent_id, latency = route
            transfer_demands.append(
                _TransferDemand(
                    artifact_id=artifact_id,
                    source_agent_id=source_agent_id,
                    target_agent_id=agent_id,
                    size_bytes=artifact.size_bytes,
                    base_latency_ms=latency,
                    sequence_index=transfer_sequence,
                )
            )
            transfer_sequence += 1
            if latency is None:
                transfer_latency_known = False
                reasons.add("transfer_route_unknown")
            else:
                transfer_latency += latency
        input_bytes = _sum_int(artifacts[item].size_bytes for item in action.inputs)
        operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
        service = self._matching_profile(operator, agent_id, deployment_id, input_bytes)
        if service is None:
            reasons.add("service_profile_unavailable")
        runtime = next(item for item in infrastructure.agents if item.agent_id == agent_id)
        queue = runtime.queue_depth if runtime.queue_depth is not None else runtime.in_flight
        return _CandidateCost(
            agent_id=agent_id,
            deployment_id=deployment_id,
            remote_inputs=remote if remote_known else None,
            transfer_bytes=transfer_bytes if transfer_bytes_known else None,
            transfer_latency_ms=(
                transfer_latency if transfer_latency_known and transfer_bytes_known else None
            ),
            service_latency_ms=service.service_latency_ms if service is not None else None,
            queue_units=queue,
            unknown_reasons=tuple(sorted(reasons)),
            transfer_demands=tuple(transfer_demands),
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
        reasons = {reason for item in candidates for reason in item.unknown_reasons}
        if input_bytes is None:
            reasons.add("future_artifact_size_unknown")
        if not candidates:
            reasons.add("no_feasible_candidates")
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
            unknown_reasons=tuple(sorted(reasons)),
        )

    def _apply_service_concurrency_profiles(
        self,
        frontier: list[_FrontierAction],
        artifacts: dict[str, _ProjectedArtifact],
    ) -> tuple[ConcurrentGroupPrediction, ...]:
        by_target: dict[str, list[_FrontierAction]] = defaultdict(list)
        for item in frontier:
            if item.selection is not None and item.selected is not None:
                by_target[item.selection.selected_agent_id].append(item)
        predictions: list[ConcurrentGroupPrediction] = []
        for agent_id, group in sorted(by_target.items()):
            concurrency = len(group)
            if concurrency < 2:
                continue
            complete = True
            sources: list[str] = []
            for item in group:
                item.concurrency = concurrency
                selected = item.selected
                if selected is None:
                    complete = False
                    continue
                operator = (
                    "invoke_model"
                    if isinstance(item.action, LogicalModelAction)
                    else item.action.operator
                )
                input_bytes = _sum_int(
                    artifacts[artifact_id].size_bytes for artifact_id in item.action.inputs
                )
                profile = self._matching_concurrent_profile(
                    operator,
                    agent_id,
                    selected.deployment_id,
                    input_bytes,
                    concurrency,
                )
                if profile is None:
                    complete = False
                    item.adjusted_service_latency_ms = None
                    item.profile = item.profile.model_copy(
                        update={
                            "unknown_reasons": tuple(
                                sorted(
                                    set(item.profile.unknown_reasons)
                                    | {"concurrent_service_profile_unavailable"}
                                )
                            )
                        }
                    )
                else:
                    item.adjusted_service_latency_ms = profile.service_latency_ms
                    item.concurrency_profile_source = profile.source
                    sources.append(profile.source)
            predictions.append(
                ConcurrentGroupPrediction(
                    selected_agent_id=agent_id,
                    action_ids=tuple(item.action.action_id for item in group),
                    deployment_ids=tuple(
                        sorted(
                            {
                                item.selection.selected_deployment_id
                                for item in group
                                if item.selection is not None
                                and item.selection.selected_deployment_id is not None
                            }
                        )
                    ),
                    concurrency=concurrency,
                    profile_complete=complete and len(sources) == concurrency,
                )
            )
        return tuple(predictions)

    def _apply_transfer_concurrency_profiles(
        self,
        frontier: list[_FrontierAction],
    ) -> tuple[ConcurrentTransferGroupPrediction, ...]:
        demands_by_link: dict[
            tuple[str, str, int],
            list[tuple[_FrontierAction, _TransferDemand]],
        ] = defaultdict(list)
        for item in frontier:
            if item.selected is None:
                continue
            for demand in item.selected.transfer_demands:
                demands_by_link[
                    (
                        demand.source_agent_id,
                        demand.target_agent_id,
                        demand.sequence_index,
                    )
                ].append((item, demand))

        adjusted_parts: dict[str, list[float]] = defaultdict(list)
        unknown_actions: set[str] = set()
        sources_by_action: dict[str, list[str]] = defaultdict(list)
        predictions: list[ConcurrentTransferGroupPrediction] = []
        for (
            source_agent_id,
            target_agent_id,
            _sequence_index,
        ), group in sorted(demands_by_link.items()):
            concurrency = len(group)
            if concurrency == 1:
                item, demand = group[0]
                if demand.base_latency_ms is None:
                    unknown_actions.add(item.action.action_id)
                else:
                    adjusted_parts[item.action.action_id].append(demand.base_latency_ms)
                continue

            complete = True
            for item, demand in group:
                profile = self._matching_transfer_profile(
                    source_agent_id,
                    target_agent_id,
                    demand.size_bytes,
                    concurrency,
                )
                if profile is None:
                    complete = False
                    unknown_actions.add(item.action.action_id)
                    item.profile = item.profile.model_copy(
                        update={
                            "unknown_reasons": tuple(
                                sorted(
                                    set(item.profile.unknown_reasons)
                                    | {"concurrent_transfer_profile_unavailable"}
                                )
                            )
                        }
                    )
                else:
                    adjusted_parts[item.action.action_id].append(
                        profile.transfer_latency_ms
                    )
                    sources_by_action[item.action.action_id].append(profile.source)
            predictions.append(
                ConcurrentTransferGroupPrediction(
                    source_agent_id=source_agent_id,
                    target_agent_id=target_agent_id,
                    action_ids=tuple(item.action.action_id for item, _ in group),
                    artifact_ids=tuple(demand.artifact_id for _, demand in group),
                    concurrency=concurrency,
                    profile_complete=complete,
                )
            )

        for item in frontier:
            selected = item.selected
            if selected is None:
                continue
            action_id = item.action.action_id
            if selected.transfer_bytes is None or action_id in unknown_actions:
                item.adjusted_transfer_latency_ms = None
            elif selected.transfer_demands:
                item.adjusted_transfer_latency_ms = sum(adjusted_parts[action_id])
            else:
                item.adjusted_transfer_latency_ms = 0.0
            item.transfer_concurrency_profile_sources = tuple(
                sources_by_action[action_id]
            )
        return tuple(predictions)

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
            and item.unit_kind in {"bytes", "fixed"}
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
                item.unit_kind != "bytes",
                (
                    abs((item.input_units or 0) - (input_bytes or 0))
                    if item.unit_kind == "bytes"
                    else 0
                ),
                item.service_latency_ms,
            ),
        )

    def _matching_concurrent_profile(
        self,
        operator: str,
        agent_id: str,
        deployment_id: str | None,
        input_bytes: int | None,
        concurrency: int,
    ) -> ConcurrentServiceProfile | None:
        matches = [
            item
            for item in self._concurrent_profiles
            if item.operator == operator
            and item.concurrency == concurrency
            and item.agent_id in {agent_id, "*"}
            and (
                item.deployment_id is None
                or item.deployment_id == deployment_id
            )
        ]
        if not matches:
            return None
        return min(
            matches,
            key=lambda item: (
                item.agent_id != agent_id,
                item.deployment_id != deployment_id,
                item.unit_kind != "bytes",
                (
                    abs((item.input_units or 0) - (input_bytes or 0))
                    if item.unit_kind == "bytes"
                    else 0
                ),
                item.service_latency_ms,
            ),
        )

    def _matching_transfer_profile(
        self,
        source_agent_id: str,
        target_agent_id: str,
        size_bytes: int,
        concurrency: int,
    ) -> ConcurrentTransferProfile | None:
        matches = [
            item
            for item in self._concurrent_transfer_profiles
            if item.concurrency == concurrency
            and item.source_agent_id in {source_agent_id, "*"}
            and item.target_agent_id in {target_agent_id, "*"}
        ]
        if not matches:
            return None
        return min(
            matches,
            key=lambda item: (
                item.source_agent_id != source_agent_id,
                item.target_agent_id != target_agent_id,
                item.unit_kind != "bytes",
                (
                    abs((item.input_units or 0) - size_bytes)
                    if item.unit_kind == "bytes"
                    else 0
                ),
                item.transfer_latency_ms,
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


def _projected_state(
    infrastructure: InfrastructureState,
    artifacts: dict[str, _ProjectedArtifact],
) -> InfrastructureState:
    return infrastructure.model_copy(
        update={
            "artifacts": tuple(
                ArtifactRuntimeState(
                    artifact_id=item.artifact_id,
                    locations=item.locations,
                    media_type=item.media_type,
                    size_bytes=item.size_bytes,
                )
                for item in artifacts.values()
            )
        }
    )


def _runtime_transfer(
    sources: tuple[str, ...],
    target: str,
    size_bytes: int,
    infrastructure: InfrastructureState,
    environment: EnvironmentSpec,
) -> tuple[str, float | None] | None:
    # RuntimeExecutor chooses the lexicographically first configured source, not the fastest link.
    configured_agents = {item.agent_id for item in environment.agents}
    source_candidates = sorted(set(sources) & configured_agents)
    if not source_candidates:
        return None
    source = source_candidates[0]
    link = next(
        (
            item
            for item in infrastructure.links
            if item.available
            and item.source_agent_id == source
            and item.target_agent_id == target
            and item.bandwidth_mbps is not None
            and item.rtt_ms is not None
        ),
        None,
    )
    if link is None or link.bandwidth_mbps is None or link.rtt_ms is None:
        return (source, None)
    return (
        source,
        link.rtt_ms + size_bytes * 8 / (link.bandwidth_mbps * 1_000_000) * 1000,
    )


def _predecessors(plan: SemanticWorkflowPlan) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {
        item.action_id: set() for item in plan.actions
    }
    for edge in plan.dependencies:
        result[edge.consumer_action_id].add(edge.producer_action_id)
    return result


def _critical_path(
    plan: SemanticWorkflowPlan,
    pending: set[str],
    node_cost: dict[str, float],
) -> float:
    predecessors = _predecessors(plan)
    distances: dict[str, float] = {}
    unresolved = set(pending)
    while unresolved:
        ready = sorted(
            action_id
            for action_id in unresolved
            if (predecessors[action_id] & pending) <= distances.keys()
        )
        if not ready:
            raise ValueError("cannot compute critical path for a cyclic pending workflow")
        for action_id in ready:
            distances[action_id] = node_cost[action_id] + max(
                (
                    distances[item]
                    for item in predecessors[action_id]
                    if item in pending
                ),
                default=0.0,
            )
            unresolved.remove(action_id)
    return max(distances.values(), default=0.0)


def _total_latency(
    transfer_latency_ms: float | None,
    service_latency_ms: float | None,
    queue_latency_ms: float | None,
) -> float | None:
    if (
        transfer_latency_ms is None
        or service_latency_ms is None
        or queue_latency_ms is None
    ):
        return None
    return transfer_latency_ms + service_latency_ms + queue_latency_ms


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
