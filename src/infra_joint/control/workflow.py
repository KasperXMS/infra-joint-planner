from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from infra_joint.control.contracts import LogicalAction, LogicalObservation
from infra_joint.core.base import ContractModel


class WorkflowDependency(ContractModel):
    """One semantic information-flow or control edge in a planned workflow."""

    dependency_type: Literal["artifact", "control"]
    producer_action_id: str = Field(min_length=1)
    consumer_action_id: str = Field(min_length=1)
    information_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def fields_match_dependency_type(self) -> Self:
        if self.producer_action_id == self.consumer_action_id:
            raise ValueError("a workflow dependency cannot be a self-loop")
        if self.dependency_type == "artifact" and self.information_id is None:
            raise ValueError("artifact dependency requires information_id")
        if self.dependency_type == "control" and self.information_id is not None:
            raise ValueError("control dependency cannot carry information_id")
        return self


class SemanticWorkflowPlan(ContractModel):
    """Infrastructure-free planned workflow; execution history lives elsewhere."""

    schema_version: Literal["semantic-workflow-v1"] = "semantic-workflow-v1"
    workflow_id: str = Field(min_length=1)
    version: int = Field(ge=0)
    actions: tuple[LogicalAction, ...]
    dependencies: tuple[WorkflowDependency, ...] = ()
    terminal_action_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def identifiers_are_unique(self) -> Self:
        action_ids = tuple(item.action_id for item in self.actions)
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("semantic workflow action IDs must be unique")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("semantic workflow dependencies must be unique")
        return self

    def canonical_sha256(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))

    def action_map(self) -> dict[str, LogicalAction]:
        return {item.action_id: item for item in self.actions}


class WorkflowRuntimeState(ContractModel):
    """Execution partition for one plan version.

    Completed includes both successful and failed dispatched actions. A failed action ends
    execution, so it can never be replayed through the pending set.
    """

    completed_action_ids: tuple[str, ...] = ()
    running_action_ids: tuple[str, ...] = ()
    pending_action_ids: tuple[str, ...] = ()
    observations: tuple[LogicalObservation, ...] = ()

    @field_validator(
        "completed_action_ids",
        "running_action_ids",
        "pending_action_ids",
    )
    @classmethod
    def action_ids_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("workflow runtime action IDs must be unique")
        return values

    @model_validator(mode="after")
    def partitions_are_disjoint(self) -> Self:
        completed = set(self.completed_action_ids)
        running = set(self.running_action_ids)
        pending = set(self.pending_action_ids)
        if completed & running or completed & pending or running & pending:
            raise ValueError("workflow runtime partitions must be disjoint")
        return self

    @classmethod
    def initialize(cls, plan: SemanticWorkflowPlan) -> WorkflowRuntimeState:
        return cls(pending_action_ids=tuple(item.action_id for item in plan.actions))

    def validate_against(self, plan: SemanticWorkflowPlan) -> None:
        expected = {item.action_id for item in plan.actions}
        actual = (
            set(self.completed_action_ids)
            | set(self.running_action_ids)
            | set(self.pending_action_ids)
        )
        if actual != expected:
            raise ValueError("workflow runtime state must partition every planned action")


class AddAction(ContractModel):
    edit_type: Literal["add_action"] = "add_action"
    action: LogicalAction


class RemovePendingAction(ContractModel):
    edit_type: Literal["remove_pending_action"] = "remove_pending_action"
    action_id: str = Field(min_length=1)


class ReplacePendingAction(ContractModel):
    edit_type: Literal["replace_pending_action"] = "replace_pending_action"
    action_id: str = Field(min_length=1)
    replacement: LogicalAction

    @model_validator(mode="after")
    def replacement_preserves_identity(self) -> Self:
        if self.replacement.action_id != self.action_id:
            raise ValueError("replacement must preserve the pending action ID")
        return self


class AddDependency(ContractModel):
    edit_type: Literal["add_dependency"] = "add_dependency"
    dependency: WorkflowDependency


class RemovePendingDependency(ContractModel):
    edit_type: Literal["remove_pending_dependency"] = "remove_pending_dependency"
    dependency: WorkflowDependency


WorkflowEdit = Annotated[
    AddAction
    | RemovePendingAction
    | ReplacePendingAction
    | AddDependency
    | RemovePendingDependency,
    Field(discriminator="edit_type"),
]


class WorkflowPatch(ContractModel):
    schema_version: Literal["workflow-patch-v1"] = "workflow-patch-v1"
    patch_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    edits: tuple[WorkflowEdit, ...] = Field(min_length=1)


class SemanticWorkflowVersion(ContractModel):
    version: int = Field(ge=0)
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan: SemanticWorkflowPlan

    @classmethod
    def create(cls, plan: SemanticWorkflowPlan) -> SemanticWorkflowVersion:
        return cls(
            version=plan.version,
            canonical_sha256=plan.canonical_sha256(),
            plan=plan,
        )


class WorkflowPatchRecord(ContractModel):
    from_version: int = Field(ge=0)
    to_version: int = Field(ge=0)
    decision: Literal["keep", "patch"]
    reason: str = Field(min_length=1)
    patch: WorkflowPatch | None = None

    @model_validator(mode="after")
    def version_change_matches_decision(self) -> Self:
        if self.decision == "keep":
            if self.patch is not None or self.to_version != self.from_version:
                raise ValueError("KEEP cannot include a patch or change workflow version")
        elif self.patch is None or self.to_version != self.from_version + 1:
            raise ValueError("PATCH must include one patch and increment workflow version")
        return self


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
