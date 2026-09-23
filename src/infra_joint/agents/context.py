from infra_joint.agents.information import InformationObjectRef
from infra_joint.agents.state import AgentState
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowNode


class AgentExecutionContext(ContractModel):
    task: TaskContract
    agent: LogicalAgent
    state: AgentState
    node: WorkflowNode
    inputs: tuple[InformationObjectRef, ...]
