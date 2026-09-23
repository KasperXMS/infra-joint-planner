from pydantic import Field

from infra_joint.agents.information import InformationObjectRef
from infra_joint.agents.state import AgentState
from infra_joint.core.base import ContractModel
from infra_joint.core.task import ArtifactContentSchema, OutputContract, TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowNode


class AgentArtifactView(ContractModel):
    artifact_id: str = Field(min_length=1)
    logical_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    content_schema: ArtifactContentSchema | None = None


class AgentTaskView(ContractModel):
    """Runtime-safe task fields; evaluator and source metadata are excluded."""

    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    artifacts: tuple[AgentArtifactView, ...]
    output_contract: OutputContract

    @classmethod
    def from_contract(cls, task: TaskContract) -> "AgentTaskView":
        return cls(
            task_id=task.task_id,
            benchmark_id=task.benchmark_id,
            objective=task.objective,
            artifacts=tuple(
                AgentArtifactView(
                    artifact_id=item.artifact_id,
                    logical_type=item.logical_type,
                    media_type=item.media_type,
                    size_bytes=item.size_bytes,
                    content_schema=item.content_schema,
                )
                for item in task.artifacts
            ),
            output_contract=task.output_contract,
        )


class AgentExecutionContext(ContractModel):
    task: AgentTaskView
    agent: LogicalAgent
    state: AgentState
    node: WorkflowNode
    inputs: tuple[InformationObjectRef, ...]
