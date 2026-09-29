from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from time import perf_counter
from typing import Annotated, Literal, Protocol

from pydantic import Field, TypeAdapter, ValidationError

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import LogicalObservation, StaticCapabilityContract
from infra_joint.control.workflow import (
    SemanticWorkflowPlan,
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


WorkflowAdaptationDecision = Annotated[
    KeepWorkflow | PatchWorkflow,
    Field(discriminator="decision_type"),
]
ADAPTATION_ADAPTER: TypeAdapter[WorkflowAdaptationDecision] = TypeAdapter(
    WorkflowAdaptationDecision
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
            decision = ADAPTATION_ADAPTER.validate_json(completion.text)
        except ValidationError as exc:
            raise ValueError("workflow adapter returned an invalid KEEP/PATCH decision") from exc
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
                "Never expose workers, devices, deployments, IPs, routes, evaluator metadata, "
                "gold, supporting evidence, or source references.",
                "Return exactly one keep/patch JSON object with no Markdown.",
                json.dumps(
                    {
                        "context": context.model_dump(mode="json", by_alias=True),
                        "decision_output_schema": ADAPTATION_ADAPTER.json_schema(),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        )
