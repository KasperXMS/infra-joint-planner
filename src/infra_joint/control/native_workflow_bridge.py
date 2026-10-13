"""Opt-in bridge from SDK-native actions to the formal versioned workflow."""

from __future__ import annotations

from infra_joint.control.adaptation import KeepWorkflow, PatchWorkflow
from infra_joint.control.contracts import LogicalAction
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.workflow import SemanticWorkflowPlan, WorkflowDependency
from infra_joint.control.workflow_state import VersionedPendingWorkflow
from infra_joint.control.workflow_validation import WorkflowValidationError
from infra_joint.workflow.trace import WorkflowTraceRecorder


class NativeFormalWorkflowBridge:
    """Preserve open-ended SDK proposals while enforcing a formal dispatch boundary.

    The bridge does not select KEEP/PATCH and does not infer semantic dependencies from
    free text. Only declared artifact inputs and depends_on fields create edges.
    """

    def __init__(
        self,
        workflow: VersionedPendingWorkflow,
        gateway: ActionGateway,
        *,
        trace: WorkflowTraceRecorder | None = None,
    ) -> None:
        self.workflow = workflow
        self.gateway = gateway
        self.trace = trace

    def prepare(self, action: LogicalAction) -> None:
        """Translate one SDK tool proposal into a pending formal action, then reserve it."""
        self.gateway.validate_batch((action,))
        planned = self.workflow.plan.action_map().get(action.action_id)
        if planned is None:
            dependencies = self._declared_dependencies(action)
            self.workflow.append_fragment(
                (action,), dependencies, expected_version=self.workflow.plan.version
            )
            self._emit("workflow.v2.plan", self.workflow.transitions[-1].model_dump(mode="json"))
        elif planned != action:
            raise WorkflowValidationError("SDK action differs from the current pending plan")
        predecessors = {
            edge.producer_action_id
            for edge in self.workflow.plan.dependencies
            if edge.consumer_action_id == action.action_id
        }
        incomplete = sorted(
            key for key in predecessors if self.workflow.execution.statuses.get(key) != "completed"
        )
        if incomplete:
            raise WorkflowValidationError(
                f"workflow action prerequisites have not completed successfully: {incomplete}"
            )
        self.workflow.reserve(action.action_id)
        self.workflow.start(action.action_id)
        self._emit("workflow.v2.execution", self.workflow.execution.model_dump(mode="json"))

    async def execute(
        self, action: LogicalAction, *, expose_profile: bool
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        try:
            outcomes = await self.gateway.execute_batch((action,), expose_profile=expose_profile)
        except BaseException as exc:
            settled = getattr(exc, "_infra_joint_settled_outcomes", ())
            matched = next(
                (
                    item
                    for item in settled
                    if isinstance(item, PhysicalExecutionOutcome)
                    and item.observation.action_id == action.action_id
                ),
                None,
            )
            if matched is None:
                self.workflow.mark_indeterminate(action.action_id)
                self._emit("workflow.v2.execution", self.workflow.execution.model_dump(mode="json"))
                raise
            outcomes = (matched,)
        for outcome in outcomes:
            self.workflow.settle(outcome.observation)
        self._emit("workflow.v2.execution", self.workflow.execution.model_dump(mode="json"))
        self._emit("workflow.v2.provenance", self.workflow.provenance.model_dump(mode="json"))
        return outcomes

    def keep_or_patch(
        self, decision: KeepWorkflow | PatchWorkflow, *, expected_version: int
    ) -> SemanticWorkflowPlan:
        plan = self.workflow.keep_or_patch(decision, expected_version=expected_version)
        self._emit("workflow.v2.plan", self.workflow.transitions[-1].model_dump(mode="json"))
        return plan

    def _declared_dependencies(self, action: LogicalAction) -> tuple[WorkflowDependency, ...]:
        producer_by_artifact = {
            output.artifact_id: prior.action_id
            for prior in self.workflow.plan.actions
            for output in prior.outputs
        }
        dependencies: list[WorkflowDependency] = []
        for artifact_id in action.inputs:
            producer = producer_by_artifact.get(artifact_id)
            if producer is not None:
                dependencies.append(
                    WorkflowDependency(
                        dependency_type="artifact",
                        producer_action_id=producer,
                        consumer_action_id=action.action_id,
                        information_id=artifact_id,
                    )
                )
        for producer in action.depends_on:
            if producer not in {item.producer_action_id for item in dependencies}:
                dependencies.append(
                    WorkflowDependency(
                        dependency_type="control",
                        producer_action_id=producer,
                        consumer_action_id=action.action_id,
                    )
                )
        return tuple(dependencies)

    def _emit(self, event_type: str, payload: dict[str, object]) -> None:
        if self.trace is not None:
            self.trace.emit(event_type, payload)
