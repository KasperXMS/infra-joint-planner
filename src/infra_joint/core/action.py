from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel


class PhysicalPolicy(StrEnum):
    AUTO = "auto"
    DATA_LOCAL = "data_local"
    TARGET_AGENT = "target_agent"
    TARGET_DEPLOYMENT = "target_deployment"


class SemanticAction(ContractModel):
    operator: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    arguments: dict[str, Any] = Field(default_factory=dict)


class PhysicalDecision(ContractModel):
    policy: PhysicalPolicy
    target_agent_id: str | None = None
    target_deployment_id: str | None = None

    @model_validator(mode="after")
    def target_matches_policy(self) -> "PhysicalDecision":
        if self.policy == PhysicalPolicy.TARGET_AGENT:
            if not self.target_agent_id or self.target_deployment_id:
                raise ValueError("target_agent requires only target_agent_id")
        elif self.policy == PhysicalPolicy.TARGET_DEPLOYMENT:
            if not self.target_deployment_id or self.target_agent_id:
                raise ValueError("target_deployment requires only target_deployment_id")
        elif self.target_agent_id or self.target_deployment_id:
            raise ValueError(f"{self.policy} does not accept an explicit target")
        return self


class JointAction(ContractModel):
    decision_type: Literal["action"] = "action"
    semantic: SemanticAction
    physical: PhysicalDecision


class FinishDecision(ContractModel):
    decision_type: Literal["finish"] = "finish"
    reason: str = Field(min_length=1)


JointDecision = Annotated[JointAction | FinishDecision, Field(discriminator="decision_type")]
