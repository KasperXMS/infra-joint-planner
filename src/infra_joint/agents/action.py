from enum import StrEnum
from typing import Any

from pydantic import Field

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel


class AgentActionType(StrEnum):
    REASON = "reason"
    TOOL = "tool"
    CONTROL = "control"


class AgentAction(ContractModel):
    """Logical action prepared independently of physical placement."""

    agent_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    action_type: AgentActionType
    operator: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    arguments: dict[str, Any] = Field(default_factory=dict)
    outputs: tuple[str, ...] = ()

    def semantic_action(self) -> SemanticAction:
        return SemanticAction(
            operator=self.operator,
            inputs=self.inputs,
            arguments=self.arguments,
        )
