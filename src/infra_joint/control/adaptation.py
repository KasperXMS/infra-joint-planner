from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from time import perf_counter
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, TypeAdapter, ValidationError, model_validator

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import LogicalObservation, StaticCapabilityContract
from infra_joint.control.prior import (
    PriorLogicalAction,
    formalize_prior_action,
    without_quality_tiers,
)
from infra_joint.control.workflow import (
    AddAction,
    AddDependency,
    RemovePendingAction,
    RemovePendingDependency,
    ReplacePendingAction,
    SemanticWorkflowPlan,
    WorkflowDependency,
    WorkflowPatch,
    WorkflowRuntimeState,
)
from infra_joint.control.workflow_profile import WorkflowPhysicalView
from infra_joint.core.base import ContractModel
from infra_joint.planning.planner import CompletionBackend
from infra_joint.worker.model_backend import ModelRequest


class WorkflowAdaptationContext(ContractModel):
    task: AgentTaskView
    plan: SemanticWorkflowPlan
    runtime: WorkflowRuntimeState
    observations: tuple[LogicalObservation, ...]
    static_capabilities: StaticCapabilityContract
    physical: WorkflowPhysicalView


class KeepWorkflow(ContractModel):
    decision_type: Literal["keep"] = "keep"
    reason: str = Field(min_length=1)


class PatchWorkflow(ContractModel):
    decision_type: Literal["patch"] = "patch"
    reason: str = Field(min_length=1)
    patch: WorkflowPatch


class PriorAddAction(ContractModel):
    edit_type: Literal["add_action"] = "add_action"
    action: PriorLogicalAction


class PriorReplacePendingAction(ContractModel):
    edit_type: Literal["replace_pending_action"] = "replace_pending_action"
    action_id: str = Field(min_length=1)
    replacement: PriorLogicalAction

    @model_validator(mode="after")
    def replacement_preserves_identity(self) -> Self:
        if self.replacement.action_id != self.action_id:
            raise ValueError("replacement must preserve the pending action ID")
        return self


class PriorRemovePendingAction(ContractModel):
    edit_type: Literal["remove_pending_action"] = "remove_pending_action"
    action_id: str = Field(min_length=1)


class PriorAddDependency(ContractModel):
    edit_type: Literal["add_dependency"] = "add_dependency"
    dependency: WorkflowDependency


class PriorRemovePendingDependency(ContractModel):
    edit_type: Literal["remove_pending_dependency"] = "remove_pending_dependency"
    dependency: WorkflowDependency


PriorWorkflowEdit = Annotated[
    PriorAddAction
    | PriorRemovePendingAction
    | PriorReplacePendingAction
    | PriorAddDependency
    | PriorRemovePendingDependency,
    Field(discriminator="edit_type"),
]


class PriorWorkflowPatch(ContractModel):
    schema_version: Literal["workflow-patch-v1"] = "workflow-patch-v1"
    patch_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    edits: tuple[PriorWorkflowEdit, ...] = Field(min_length=1)


class PriorPatchWorkflow(ContractModel):
    decision_type: Literal["patch"] = "patch"
    reason: str = Field(min_length=1)
    patch: PriorWorkflowPatch


WorkflowAdaptationDecision = Annotated[
    KeepWorkflow | PatchWorkflow,
    Field(discriminator="decision_type"),
]
PriorWorkflowAdaptationDecision = Annotated[
    KeepWorkflow | PriorPatchWorkflow,
    Field(discriminator="decision_type"),
]
ADAPTATION_ADAPTER: TypeAdapter[PriorWorkflowAdaptationDecision] = TypeAdapter(
    PriorWorkflowAdaptationDecision
)


class WorkflowAdaptationPolicy(Protocol):
    async def adapt(
        self,
        context: WorkflowAdaptationContext,
    ) -> WorkflowAdaptationOutcome: ...


class WorkflowAdaptationTelemetry(ContractModel):
    adaptation_latency_ms: float = Field(ge=0)
    model_service_latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    decision_type: Literal["keep", "patch"]
    patch_edit_count: int = Field(ge=0)


class WorkflowAdaptationOutcome(ContractModel):
    decision: WorkflowAdaptationDecision
    telemetry: WorkflowAdaptationTelemetry


class KeepWorkflowPolicy:
    def __init__(self, reason: str = "current workflow remains appropriate") -> None:
        self._reason = reason

    async def adapt(self, context: WorkflowAdaptationContext) -> WorkflowAdaptationOutcome:
        started = perf_counter()
        del context
        decision = KeepWorkflow(reason=self._reason)
        return WorkflowAdaptationOutcome(
            decision=decision,
            telemetry=WorkflowAdaptationTelemetry(
                adaptation_latency_ms=(perf_counter() - started) * 1000,
                decision_type="keep",
                patch_edit_count=0,
            ),
        )


class ScriptedWorkflowAdaptationPolicy:
    def __init__(self, decisions: Iterable[WorkflowAdaptationDecision]) -> None:
        self._decisions = deque(decisions)

    async def adapt(
        self,
        context: WorkflowAdaptationContext,
    ) -> WorkflowAdaptationOutcome:
        started = perf_counter()
        del context
        if not self._decisions:
            decision: WorkflowAdaptationDecision = KeepWorkflow(
                reason="script exhausted; preserve current pending suffix"
            )
        else:
            decision = self._decisions.popleft()
        edit_count = len(decision.patch.edits) if isinstance(decision, PatchWorkflow) else 0
        return WorkflowAdaptationOutcome(
            decision=decision,
            telemetry=WorkflowAdaptationTelemetry(
                adaptation_latency_ms=(perf_counter() - started) * 1000,
                decision_type=decision.decision_type,
                patch_edit_count=edit_count,
            ),
        )


class LLMInfraAwareWorkflowAdapter:
    """Adapt only the pending suffix from an anonymous workflow-level physical view."""

    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend

    async def adapt(
        self,
        context: WorkflowAdaptationContext,
    ) -> WorkflowAdaptationOutcome:
        started = perf_counter()
        completion = await self._backend.invoke(ModelRequest(prompt=self.render_prompt(context)))
        try:
            draft = ADAPTATION_ADAPTER.validate_json(completion.text)
        except ValidationError as exc:
            raise ValueError("workflow adapter returned an invalid KEEP/PATCH decision") from exc
        decision = _formal_decision(draft)
        return WorkflowAdaptationOutcome(
            decision=decision,
            telemetry=WorkflowAdaptationTelemetry(
                adaptation_latency_ms=(perf_counter() - started) * 1000,
                model_service_latency_ms=completion.telemetry.service_latency_ms,
                input_tokens=completion.telemetry.input_tokens,
                output_tokens=completion.telemetry.output_tokens,
                decision_type=decision.decision_type,
                patch_edit_count=(
                    len(decision.patch.edits) if isinstance(decision, PatchWorkflow) else 0
                ),
            ),
        )

    def render_prompt(self, context: WorkflowAdaptationContext) -> str:
        return "\n".join(
            (
                "You adapt the pending suffix of a semantically reasonable prior workflow.",
                "Return KEEP unless abstract infrastructure indicates a significant cost or "
                "feasibility problem. Preserve task evidence and semantic correctness.",
                "PATCH may only use the finite edit vocabulary and may not modify completed or "
                "running actions. Do not name or infer physical identities or placement.",
                "Model requirements describe only semantic feasibility: modalities, context "
                "and output budgets, and required capabilities. Model quality and latency "
                "tiers are system-owned and unavailable.",
                "Never expose workers, devices, deployments, IPs, routes, evaluator metadata, "
                "gold, supporting evidence, or source references.",
                "Return exactly one keep/patch JSON object with no Markdown.",
                json.dumps(
                    {
                        "context": without_quality_tiers(
                            context.model_dump(mode="json", by_alias=True)
                        ),
                        "decision_output_schema": ADAPTATION_ADAPTER.json_schema(),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        )


def _formal_decision(
    decision: PriorWorkflowAdaptationDecision,
) -> WorkflowAdaptationDecision:
    if isinstance(decision, KeepWorkflow):
        return decision
    edits: list[
        AddAction
        | RemovePendingAction
        | ReplacePendingAction
        | AddDependency
        | RemovePendingDependency
    ] = []
    for edit in decision.patch.edits:
        if isinstance(edit, PriorAddAction):
            edits.append(AddAction(action=formalize_prior_action(edit.action)))
        elif isinstance(edit, PriorReplacePendingAction):
            edits.append(
                ReplacePendingAction(
                    action_id=edit.action_id,
                    replacement=formalize_prior_action(edit.replacement),
                )
            )
        elif isinstance(edit, PriorRemovePendingAction):
            edits.append(RemovePendingAction(action_id=edit.action_id))
        elif isinstance(edit, PriorAddDependency):
            edits.append(AddDependency(dependency=edit.dependency))
        else:
            edits.append(RemovePendingDependency(dependency=edit.dependency))
    return PatchWorkflow(
        reason=decision.reason,
        patch=WorkflowPatch(
            patch_id=decision.patch.patch_id,
            reason=decision.patch.reason,
            edits=tuple(edits),
        ),
    )
