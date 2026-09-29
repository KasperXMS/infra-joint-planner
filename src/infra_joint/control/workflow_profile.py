from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field, model_validator

from infra_joint.control.contracts import PhysicalProfileView
from infra_joint.control.workflow import SemanticWorkflowPlan, WorkflowRuntimeState
from infra_joint.core.base import ContractModel


class PendingActionPhysicalProfile(ContractModel):
    action_id: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    input_bytes: int = Field(ge=0)
    remote_input_count_range: tuple[int, int]
    transfer_latency_ms_range: tuple[float, float] | None = None
    service_latency_ms_range: tuple[float, float] | None = None
    queue_pressure_range: tuple[int, int] | None = None
    network_class: Literal["local", "constrained", "moderate", "fast", "unknown"]
    unknown_reasons: tuple[str, ...] = ()

    @classmethod
    def from_view(
        cls,
        action_id: str,
        view: PhysicalProfileView,
    ) -> PendingActionPhysicalProfile:
        abstract_unknown = tuple(
            sorted({reason.partition(":")[0] for reason in view.unknown_reasons})
        )
        return cls(
            action_id=action_id,
            **view.model_dump(
                mode="python",
                exclude={"schema_version", "unknown_reasons"},
            ),
            unknown_reasons=abstract_unknown,
        )


class WorkflowPhysicalView(ContractModel):
    schema_version: Literal["workflow-physical-view-v1"] = "workflow-physical-view-v1"
    plan_version: int = Field(ge=0)
    pending_action_profiles: tuple[PendingActionPhysicalProfile, ...]
    predicted_transfer_bytes: int | None = Field(default=None, ge=0)
    predicted_transfer_latency_ms: float | None = Field(default=None, ge=0)
    predicted_service_latency_ms: float | None = Field(default=None, ge=0)
    predicted_queue_latency_ms: float | None = Field(default=None, ge=0)
    predicted_critical_path_ms: float | None = Field(default=None, ge=0)
    predicted_total_work_ms: float | None = Field(default=None, ge=0)
    unknown_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def action_profiles_are_unique(self) -> WorkflowPhysicalView:
        action_ids = tuple(item.action_id for item in self.pending_action_profiles)
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("pending physical action profiles must be unique")
        return self


class WorkflowProfileProvider(Protocol):
    async def build(
        self,
        plan: SemanticWorkflowPlan,
        state: WorkflowRuntimeState,
    ) -> WorkflowPhysicalView: ...
