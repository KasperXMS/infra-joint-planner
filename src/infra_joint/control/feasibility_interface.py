"""Future action feasibility boundary; no live routing or private resource state."""

from __future__ import annotations

from typing import Literal, Protocol, Self

from pydantic import Field, model_validator

from infra_joint.control.contracts import LogicalAction, StaticCapabilityContract
from infra_joint.core.base import ContractModel


class ActionFeasibilityQuery(ContractModel):
    schema_version: Literal["action-feasibility-query-v1"] = "action-feasibility-query-v1"
    action: LogicalAction
    static_capabilities: StaticCapabilityContract


class ActionFeasibilityAssessment(ContractModel):
    schema_version: Literal["action-feasibility-assessment-v1"] = "action-feasibility-assessment-v1"
    action_id: str = Field(min_length=1)
    feasible: bool | None
    modality_supported: bool | None
    context_budget: Literal["within_limit", "may_exceed", "exceeds_limit", "unknown"]
    input_reduction_needed: bool | None
    certainty: Literal["exact", "conservative", "unknown"]
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def uncertainty_is_explicit(self) -> Self:
        if self.certainty == "unknown" and self.feasible is not None:
            raise ValueError("unknown certainty cannot claim a definite feasible result")
        if self.context_budget == "unknown" and self.input_reduction_needed is not None:
            raise ValueError("unknown context budget cannot claim reduction is needed or not")
        return self


class ActionFeasibilityProvider(Protocol):
    def assess(self, query: ActionFeasibilityQuery) -> ActionFeasibilityAssessment: ...
