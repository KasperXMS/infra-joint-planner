from __future__ import annotations

from collections import defaultdict

from infra_joint.control.physical import PhysicalProfiler
from infra_joint.control.workflow import SemanticWorkflowPlan, WorkflowRuntimeState
from infra_joint.control.workflow_profile import (
    PendingActionPhysicalProfile,
    WorkflowPhysicalView,
)
from infra_joint.core.state import InfrastructureState
from infra_joint.infrastructure.observer import InfrastructureObserver


class SemanticWorkflowCostEvaluator:
    """Estimate a semantic workflow through anonymous feasible binding ranges."""

    def __init__(self, profiler: PhysicalProfiler) -> None:
        self._profiler = profiler

    def evaluate(
        self,
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
        infrastructure: InfrastructureState,
    ) -> WorkflowPhysicalView:
        state.validate_against(plan)
        pending = set(state.pending_action_ids)
        profiles = tuple(
            PendingActionPhysicalProfile.from_view(
                action.action_id,
                self._profiler.for_action(action, infrastructure),
            )
            for action in plan.actions
            if action.action_id in pending
        )
        unknown = tuple(sorted({reason for item in profiles for reason in item.unknown_reasons}))
        transfer_values = [
            item.transfer_latency_ms_range[0]
            for item in profiles
            if item.transfer_latency_ms_range is not None
        ]
        service_values = [
            item.service_latency_ms_range[0]
            for item in profiles
            if item.service_latency_ms_range is not None
        ]
        queue_values = [
            float(item.queue_pressure_range[0]) * item.service_latency_ms_range[0]
            for item in profiles
            if item.queue_pressure_range is not None and item.service_latency_ms_range is not None
        ]
        complete_transfer = len(transfer_values) == len(profiles)
        complete_service = len(service_values) == len(profiles)
        complete_queue = len(queue_values) == len(profiles)
        node_cost = {
            item.action_id: (
                (item.transfer_latency_ms_range or (0.0, 0.0))[0]
                + (item.service_latency_ms_range or (0.0, 0.0))[0]
                + (
                    float((item.queue_pressure_range or (0, 0))[0])
                    * (item.service_latency_ms_range or (0.0, 0.0))[0]
                )
            )
            for item in profiles
        }
        critical = self._critical_path(plan, pending, node_cost)
        return WorkflowPhysicalView(
            plan_version=plan.version,
            pending_action_profiles=profiles,
            predicted_transfer_bytes=sum(
                item.input_bytes for item in profiles if item.remote_input_count_range[0] > 0
            ),
            predicted_transfer_latency_ms=(sum(transfer_values) if complete_transfer else None),
            predicted_service_latency_ms=(sum(service_values) if complete_service else None),
            predicted_queue_latency_ms=sum(queue_values) if complete_queue else None,
            predicted_critical_path_ms=(
                critical if complete_transfer and complete_service and complete_queue else None
            ),
            predicted_total_work_ms=(
                sum(node_cost.values())
                if complete_transfer and complete_service and complete_queue
                else None
            ),
            unknown_reasons=unknown,
        )

    @staticmethod
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
                action_id for action_id in unresolved if predecessors[action_id] <= distances.keys()
            )
            if not ready:
                return 0.0
            for action_id in ready:
                distances[action_id] = node_cost.get(action_id, 0.0) + max(
                    (distances[item] for item in predecessors[action_id]),
                    default=0.0,
                )
                unresolved.remove(action_id)
        return max(distances.values(), default=0.0)


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
