from enum import StrEnum

from pydantic import Field

from infra_joint.agents.action import AgentAction
from infra_joint.core.base import ContractModel


class AgentStatus(StrEnum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"


class AgentStepRecord(ContractModel):
    node_id: str = Field(min_length=1)
    action: AgentAction
    succeeded: bool
    received_objects: tuple[str, ...] = ()
    produced_objects: tuple[str, ...] = ()
    failure_code: str | None = None


class AgentState(ContractModel):
    agent_id: str = Field(min_length=1)
    status: AgentStatus
    history: tuple[AgentStepRecord, ...] = ()
    inbox: tuple[str, ...] = ()
    produced_objects: tuple[str, ...] = ()
