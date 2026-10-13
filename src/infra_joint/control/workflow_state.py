"""Versioned semantic plan, observed execution state, and information lineage.

This controller has one synchronous commit boundary. It does not infer a plan from
an execution trace and does not resume an interrupted SDK conversation.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from infra_joint.control.adaptation import KeepWorkflow, PatchWorkflow
from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    LogicalObservation,
    StaticCapabilityContract,
    SubagentResult,
)
from infra_joint.control.workflow import (
    OpenSemanticWorkflowPlan,
    RemovePendingAction,
    RemovePendingDependency,
    ReplacePendingAction,
    SemanticWorkflowPlan,
    WorkflowDependency,
    WorkflowPatch,
    WorkflowRuntimeState,
    canonical_sha256,
)
from infra_joint.control.workflow_validation import (
    WorkflowValidationError,
    apply_workflow_patch,
    validate_semantic_workflow,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry

ExecutionStatus = Literal[
    "pending", "reserved", "running", "completed", "failed", "indeterminate", "invalidated"
]


class WorkflowExecutionState(ContractModel):
    schema_version: Literal["workflow-execution-state-v2"] = "workflow-execution-state-v2"
    statuses: dict[str, ExecutionStatus] = Field(default_factory=dict)
    observations: tuple[LogicalObservation, ...] = ()

    @model_validator(mode="after")
    def observations_match_status(self) -> Self:
        ids = [item.action_id for item in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("an action cannot have multiple settled observations")
        for observation in self.observations:
            expected = "completed" if observation.succeeded else "failed"
            if self.statuses.get(observation.action_id) != expected:
                raise ValueError("observation disagrees with execution status")
        return self

    def to_runtime(
        self, plan: SemanticWorkflowPlan | OpenSemanticWorkflowPlan
    ) -> WorkflowRuntimeState:
        ids = tuple(item.action_id for item in plan.actions)
        if set(ids) != {key for key, value in self.statuses.items() if value != "invalidated"}:
            raise WorkflowValidationError("execution state does not partition the current plan")
        state = WorkflowRuntimeState(
            completed_action_ids=tuple(
                key for key in ids if self.statuses[key] in {"completed", "failed"}
            ),
            running_action_ids=tuple(
                key for key in ids if self.statuses[key] in {"reserved", "running", "indeterminate"}
            ),
            pending_action_ids=tuple(key for key in ids if self.statuses[key] == "pending"),
            observations=self.observations,
        )
        state.validate_against(plan)
        return state


class InformationProvenance(ContractModel):
    schema_version: Literal["information-provenance-v2"] = "information-provenance-v2"
    information_id: str = Field(min_length=1)
    source_kind: Literal[
        "task_artifact",
        "tool_artifact",
        "tool_observation",
        "manager_consumption",
        "specialist_result",
        "prompt_input",
    ]
    relation: Literal["explicit", "declared", "unknown"]
    producer_action_id: str | None = None
    consumer_action_id: str | None = None
    artifact_version: str | None = None
    sha256: str | None = None


class InformationProvenanceLedger(ContractModel):
    schema_version: Literal["information-provenance-ledger-v2"] = "information-provenance-ledger-v2"
    entries: tuple[InformationProvenance, ...] = ()

    def append(self, item: InformationProvenance) -> InformationProvenanceLedger:
        return self.model_copy(update={"entries": (*self.entries, item)})

    def assert_rewrite_safe(self, patch: WorkflowPatch) -> None:
        rewritten = {
            edit.action_id
            for edit in patch.edits
            if isinstance(edit, (RemovePendingAction, ReplacePendingAction))
        }
        rewritten.update(
            edit.dependency.consumer_action_id
            for edit in patch.edits
            if isinstance(edit, RemovePendingDependency)
        )
        if not rewritten:
            return
        for item in self.entries:
            if item.relation == "unknown" and (
                item.consumer_action_id is None or item.consumer_action_id in rewritten
            ):
                raise WorkflowValidationError(
                    "workflow rewrite requires provenance that is currently unknown"
                )


class WorkflowStateTransition(ContractModel):
    schema_version: Literal["workflow-state-transition-v2"] = "workflow-state-transition-v2"
    kind: Literal["fragment", "seal", "keep", "patch"]
    from_version: int = Field(ge=0)
    to_version: int = Field(ge=0)
    original_sha256: str
    new_sha256: str
    validation: Literal["accepted"] = "accepted"
    patch: WorkflowPatch | None = None


class VersionedPendingWorkflow:
    """One version-checked, quiescent formal plan transaction boundary."""

    def __init__(
        self,
        workflow_id: str,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        registry: OperatorRegistry,
    ) -> None:
        self.plan: OpenSemanticWorkflowPlan | SemanticWorkflowPlan = OpenSemanticWorkflowPlan(
            workflow_id=workflow_id, version=0
        )
        self.execution = WorkflowExecutionState()
        self.provenance = InformationProvenanceLedger()
        self.transitions: list[WorkflowStateTransition] = []
        self._task = task
        self._capabilities = capabilities
        self._registry = registry

    @property
    def task(self) -> TaskContract:
        return self._task

    @property
    def capabilities(self) -> StaticCapabilityContract:
        return self._capabilities

    def append_fragment(
        self,
        actions: tuple[LogicalAction, ...],
        dependencies: tuple[WorkflowDependency, ...] = (),
        *,
        expected_version: int,
        terminal_action_id: str | None = None,
    ) -> OpenSemanticWorkflowPlan | SemanticWorkflowPlan:
        self._check_version(expected_version)
        if isinstance(self.plan, SemanticWorkflowPlan):
            raise WorkflowValidationError("sealed plans change only through formal KEEP/PATCH")
        current = self.plan
        old_ids = set(current.action_map())
        if old_ids & {item.action_id for item in actions}:
            raise WorkflowValidationError("fragment reuses an existing action ID")
        locked = {
            key
            for key, value in self.execution.statuses.items()
            if value in {"reserved", "running", "completed", "failed", "indeterminate"}
        }
        if any(item.consumer_action_id in locked for item in dependencies):
            raise WorkflowValidationError("fragment changes dependencies of an executed action")
        all_actions = (*current.actions, *actions)
        all_dependencies = (*current.dependencies, *dependencies)
        if terminal_action_id is None:
            proposed: OpenSemanticWorkflowPlan | SemanticWorkflowPlan = OpenSemanticWorkflowPlan(
                workflow_id=current.workflow_id,
                version=current.version + 1,
                actions=all_actions,
                dependencies=all_dependencies,
            )
        else:
            proposed = SemanticWorkflowPlan(
                workflow_id=current.workflow_id,
                version=current.version + 1,
                actions=all_actions,
                dependencies=all_dependencies,
                terminal_action_id=terminal_action_id,
            )
        validate_semantic_workflow(
            proposed,
            self._task,
            self._capabilities,
            self._registry,
            require_terminal=terminal_action_id is not None,
        )
        new_statuses = dict(self.execution.statuses)
        new_statuses.update({item.action_id: "pending" for item in actions})
        updated = WorkflowExecutionState(
            statuses=new_statuses, observations=self.execution.observations
        )
        updated.to_runtime(proposed)
        self._commit(proposed, updated, "seal" if terminal_action_id is not None else "fragment")
        return proposed

    def reserve(self, action_id: str) -> None:
        self._change_status(action_id, "pending", "reserved")

    def start(self, action_id: str) -> None:
        self._change_status(action_id, "reserved", "running")
        action = self.plan.action_map()[action_id]
        task_artifacts = {item.artifact_id: item for item in self._task.artifacts}
        producers = {
            output.artifact_id: planned.action_id
            for planned in self.plan.actions
            for output in planned.outputs
        }
        for artifact_id in action.inputs:
            source = task_artifacts.get(artifact_id)
            producer = producers.get(artifact_id)
            self.record_provenance(
                InformationProvenance(
                    information_id=artifact_id,
                    source_kind="task_artifact" if source is not None else "tool_artifact",
                    relation="declared" if source is not None else "explicit",
                    producer_action_id=producer,
                    consumer_action_id=action_id,
                    artifact_version="task-v1" if source is not None else f"action:{producer}",
                    sha256=None,
                )
            )
        if isinstance(action, LogicalModelAction):
            self.record_provenance(
                InformationProvenance(
                    information_id=f"prompt:{action_id}",
                    source_kind="prompt_input",
                    relation="unknown",
                    consumer_action_id=action_id,
                    sha256=canonical_sha256(action.prompt),
                )
            )

    def settle(self, observation: LogicalObservation) -> None:
        action_id = observation.action_id
        old = self.execution.statuses.get(action_id)
        if old not in {"reserved", "running"}:
            raise WorkflowValidationError("only dispatched actions can settle")
        statuses = dict(self.execution.statuses)
        statuses[action_id] = "completed" if observation.succeeded else "failed"
        updated = WorkflowExecutionState(
            statuses=statuses, observations=(*self.execution.observations, observation)
        )
        updated.to_runtime(self.plan)
        ledger = self.provenance.append(
            InformationProvenance(
                information_id=f"observation:{action_id}",
                source_kind="tool_observation",
                relation="explicit",
                producer_action_id=action_id,
                sha256=canonical_sha256(observation.model_dump(mode="json")),
            )
        )
        for item in observation.produced_information:
            ledger = ledger.append(
                InformationProvenance(
                    information_id=item.artifact_id,
                    source_kind="tool_artifact",
                    relation="explicit",
                    producer_action_id=action_id,
                    artifact_version=f"action:{action_id}",
                    sha256=item.sha256_hex,
                )
            )
        self.execution = updated
        self.provenance = ledger

    def mark_indeterminate(self, action_id: str) -> None:
        if self.execution.statuses.get(action_id) not in {"reserved", "running"}:
            raise WorkflowValidationError("only dispatched actions can become indeterminate")
        statuses = dict(self.execution.statuses)
        statuses[action_id] = "indeterminate"
        self.execution = WorkflowExecutionState(
            statuses=statuses, observations=self.execution.observations
        )

    def keep_or_patch(
        self, decision: KeepWorkflow | PatchWorkflow, *, expected_version: int
    ) -> SemanticWorkflowPlan:
        self._check_version(expected_version)
        if not isinstance(self.plan, SemanticWorkflowPlan):
            raise WorkflowValidationError("an open workflow has no formal KEEP/PATCH opportunity")
        if any(
            status in {"reserved", "running", "indeterminate"}
            for status in self.execution.statuses.values()
        ):
            raise WorkflowValidationError("PATCH requires a quiescent execution frontier")
        current = self.plan
        if isinstance(decision, KeepWorkflow):
            self._commit(current, self.execution, "keep")
            return current
        self.provenance.assert_rewrite_safe(decision.patch)
        proposed = apply_workflow_patch(
            current,
            self.execution.to_runtime(current),
            decision.patch,
            self._task,
            self._capabilities,
            self._registry,
        )
        statuses = dict(self.execution.statuses)
        proposed_ids = set(proposed.action_map())
        for action_id in set(current.action_map()) - proposed_ids:
            statuses[action_id] = "invalidated"
        for action_id in proposed_ids - set(current.action_map()):
            statuses[action_id] = "pending"
        updated = WorkflowExecutionState(
            statuses=statuses, observations=self.execution.observations
        )
        updated.to_runtime(proposed)
        self._commit(proposed, updated, "patch", decision.patch)
        return proposed

    def record_provenance(self, item: InformationProvenance) -> None:
        self.provenance = self.provenance.append(item)

    def record_manager_consumption(
        self, information_id: str, *, source_action_ids: tuple[str, ...] = ()
    ) -> None:
        sources = source_action_ids or (None,)
        for source in sources:
            self.record_provenance(
                InformationProvenance(
                    information_id=information_id,
                    source_kind="manager_consumption",
                    relation="explicit" if source is not None else "unknown",
                    producer_action_id=source,
                )
            )

    def record_specialist_result(self, result: SubagentResult) -> None:
        sources = result.source_action_ids or (None,)
        for source in sources:
            self.record_provenance(
                InformationProvenance(
                    information_id=f"specialist:{result.call_id}",
                    source_kind="specialist_result",
                    relation="explicit" if source is not None else "unknown",
                    producer_action_id=source,
                    sha256=canonical_sha256(result.model_dump(mode="json")),
                )
            )

    def _change_status(
        self, action_id: str, expected: ExecutionStatus, new: ExecutionStatus
    ) -> None:
        if self.execution.statuses.get(action_id) != expected:
            raise WorkflowValidationError(f"action {action_id} is not {expected}")
        statuses = dict(self.execution.statuses)
        statuses[action_id] = new
        self.execution = WorkflowExecutionState(
            statuses=statuses, observations=self.execution.observations
        )

    def _check_version(self, expected_version: int) -> None:
        if self.plan.version != expected_version:
            raise WorkflowValidationError("stale workflow plan version")

    def _commit(
        self,
        proposed: OpenSemanticWorkflowPlan | SemanticWorkflowPlan,
        execution: WorkflowExecutionState,
        kind: Literal["fragment", "seal", "keep", "patch"],
        patch: WorkflowPatch | None = None,
    ) -> None:
        transition = WorkflowStateTransition(
            kind=kind,
            from_version=self.plan.version,
            to_version=proposed.version,
            original_sha256=self.plan.canonical_sha256(),
            new_sha256=proposed.canonical_sha256(),
            patch=patch,
        )
        self.plan = proposed
        self.execution = execution
        self.transitions.append(transition)
