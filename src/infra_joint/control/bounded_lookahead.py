"""Scriptable bounded pending-fragment interface; no live Manager integration."""

from __future__ import annotations

from infra_joint.control.adaptation import KeepWorkflow, PatchWorkflow
from infra_joint.control.contracts import LogicalAction, LogicalObservation
from infra_joint.control.workflow import (
    OpenSemanticWorkflowPlan,
    SemanticWorkflowPlan,
    WorkflowDependency,
)
from infra_joint.control.workflow_state import VersionedPendingWorkflow
from infra_joint.control.workflow_validation import WorkflowValidationError


class BoundedLookahead:
    """Let a Planner propose a small real fragment before any action dispatch.

    This is an offline interface prototype over the existing versioned state
    machine. It does not synthesize actions, choose a PATCH, or execute tools.
    """

    def __init__(
        self, workflow: VersionedPendingWorkflow, *, max_fragment_actions: int = 3
    ) -> None:
        if max_fragment_actions < 1 or max_fragment_actions > 3:
            raise ValueError("a lookahead fragment must allow one to three actions")
        self.workflow = workflow
        self.max_fragment_actions = max_fragment_actions

    def propose(
        self,
        actions: tuple[LogicalAction, ...],
        dependencies: tuple[WorkflowDependency, ...] = (),
        *,
        expected_version: int,
        terminal_action_id: str | None = None,
    ) -> OpenSemanticWorkflowPlan | SemanticWorkflowPlan:
        if not actions or len(actions) > self.max_fragment_actions:
            raise WorkflowValidationError("fragment must contain one to three proposed actions")
        return self.workflow.append_fragment(
            actions,
            dependencies,
            expected_version=expected_version,
            terminal_action_id=terminal_action_id,
        )

    def ready_action_ids(self) -> tuple[str, ...]:
        completed = {
            action_id
            for action_id, status in self.workflow.execution.statuses.items()
            if status == "completed"
        }
        return tuple(
            action.action_id
            for action in self.workflow.plan.actions
            if self.workflow.execution.statuses.get(action.action_id) == "pending"
            and all(
                edge.producer_action_id in completed
                for edge in self.workflow.plan.dependencies
                if edge.consumer_action_id == action.action_id
            )
        )

    def dispatch_ready(self, action_id: str) -> None:
        if action_id not in self.ready_action_ids():
            raise WorkflowValidationError("action is not ready for dispatch")
        self.workflow.reserve(action_id)
        self.workflow.start(action_id)

    def settle(self, observation: LogicalObservation) -> None:
        self.workflow.settle(observation)

    def keep_or_patch(
        self, decision: KeepWorkflow | PatchWorkflow, *, expected_version: int
    ) -> SemanticWorkflowPlan:
        return self.workflow.keep_or_patch(decision, expected_version=expected_version)
