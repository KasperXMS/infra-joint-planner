from collections import Counter, deque
from collections.abc import Iterable
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self

from pydantic import Field, field_validator, model_validator

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import TaskContract

if TYPE_CHECKING:
    from infra_joint.operators.registry import OperatorRegistry


class LogicalAgent(ContractModel):
    """A semantic workflow role bound to a concrete model deployment.

    Logical agents are intentionally distinct from physical ``AgentSpec`` and
    ``DeploymentSpec`` records. Multiple logical agents may share one
    ``model_instance_id`` when they use the same deployment for different roles.
    """

    agent_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    model_instance_id: str = Field(min_length=1)
    allowed_operations: tuple[str, ...] = Field(min_length=1)

    @field_validator("allowed_operations")
    @classmethod
    def operations_are_unique(cls, operations: tuple[str, ...]) -> tuple[str, ...]:
        if any(not operation for operation in operations):
            raise ValueError("allowed operation IDs must be non-empty")
        if len(operations) != len(set(operations)):
            raise ValueError("allowed_operations values must be unique")
        return operations


class WorkflowNode(ContractModel):
    node_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    inputs: tuple[str, ...] = ()
    arguments: dict[str, Any] = Field(default_factory=dict)
    outputs: tuple[str, ...] = ()

    @field_validator("inputs", "outputs")
    @classmethod
    def artifact_ids_are_unique(cls, artifact_ids: tuple[str, ...]) -> tuple[str, ...]:
        if any(not artifact_id for artifact_id in artifact_ids):
            raise ValueError("workflow artifact IDs must be non-empty")
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("workflow artifact IDs must be unique within a node")
        return artifact_ids

    def semantic_action(self) -> SemanticAction:
        return SemanticAction(
            operator=self.operator,
            inputs=self.inputs,
            arguments=self.arguments,
        )


class WorkflowEdge(ContractModel):
    producer_node: str = Field(min_length=1)
    consumer_node: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def endpoints_differ(self) -> Self:
        if self.producer_node == self.consumer_node:
            raise ValueError("a workflow edge cannot connect a node to itself")
        return self


class WorkflowPlan(ContractModel):
    agents: tuple[LogicalAgent, ...] = Field(min_length=1)
    nodes: tuple[WorkflowNode, ...] = Field(min_length=1)
    edges: tuple[WorkflowEdge, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        agents = self._unique_by_id(
            self.agents,
            (agent.agent_id for agent in self.agents),
            "agent_id",
        )
        nodes = self._unique_by_id(
            self.nodes,
            (node.node_id for node in self.nodes),
            "node_id",
        )

        for node in self.nodes:
            if node.agent_id not in agents:
                raise ValueError(f"workflow node references unknown agent: {node.agent_id}")

        output_counts = Counter(output for node in self.nodes for output in node.outputs)
        duplicate_outputs = sorted(
            artifact_id for artifact_id, count in output_counts.items() if count > 1
        )
        if duplicate_outputs:
            raise ValueError(
                f"workflow outputs must have one producer: {duplicate_outputs}"
            )
        producer_by_artifact = {
            output: node.node_id for node in self.nodes for output in node.outputs
        }

        edge_keys = [
            (edge.producer_node, edge.consumer_node, edge.artifact_id)
            for edge in self.edges
        ]
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("workflow edges must be unique")

        edge_by_dependency: dict[tuple[str, str], WorkflowEdge] = {}
        for edge in self.edges:
            if edge.producer_node not in nodes:
                raise ValueError(
                    f"workflow edge references unknown producer node: {edge.producer_node}"
                )
            if edge.consumer_node not in nodes:
                raise ValueError(
                    f"workflow edge references unknown consumer node: {edge.consumer_node}"
                )
            producer = nodes[edge.producer_node]
            consumer = nodes[edge.consumer_node]
            if edge.artifact_id not in producer.outputs:
                raise ValueError(
                    f"edge artifact is not produced by {edge.producer_node}: "
                    f"{edge.artifact_id}"
                )
            if edge.artifact_id not in consumer.inputs:
                raise ValueError(
                    f"edge artifact is not consumed by {edge.consumer_node}: "
                    f"{edge.artifact_id}"
                )
            dependency = (edge.consumer_node, edge.artifact_id)
            if dependency in edge_by_dependency:
                raise ValueError(
                    f"artifact dependency has multiple edges: {edge.consumer_node}/"
                    f"{edge.artifact_id}"
                )
            edge_by_dependency[dependency] = edge

        for node in self.nodes:
            for artifact_id in node.inputs:
                producer_node = producer_by_artifact.get(artifact_id)
                if producer_node is None:
                    continue
                edge = edge_by_dependency.get((node.node_id, artifact_id))
                if edge is None or edge.producer_node != producer_node:
                    raise ValueError(
                        f"node-produced input requires an exact edge: "
                        f"{node.node_id}/{artifact_id}"
                    )

        self._assert_acyclic(nodes)
        return self

    def validate_against(
        self,
        task: TaskContract,
        environment: EnvironmentSpec,
        registry: "OperatorRegistry",
    ) -> Self:
        """Validate external model/operator refs and all artifact dependencies."""

        deployments = {
            deployment.deployment_id: deployment for deployment in environment.deployments
        }
        task_artifacts = {artifact.artifact_id for artifact in task.artifacts}
        produced_artifacts = {
            artifact_id for node in self.nodes for artifact_id in node.outputs
        }
        collisions = sorted(task_artifacts.intersection(produced_artifacts))
        if collisions:
            raise ValueError(f"workflow outputs collide with task artifacts: {collisions}")

        agents = {agent.agent_id: agent for agent in self.agents}
        for agent in self.agents:
            if agent.model_instance_id not in deployments:
                raise ValueError(
                    "logical agent references unknown model_instance_id deployment: "
                    f"{agent.model_instance_id}"
                )
            unknown_operations = sorted(
                operation for operation in agent.allowed_operations if operation not in registry
            )
            if unknown_operations:
                raise ValueError(
                    f"logical agent references unknown operators: {unknown_operations}"
                )

        available_artifacts = task_artifacts | produced_artifacts
        for node in self.nodes:
            agent = agents[node.agent_id]
            if node.operator not in registry:
                raise ValueError(f"workflow node references unknown operator: {node.operator}")
            if node.operator not in agent.allowed_operations:
                raise ValueError(
                    f"operator {node.operator} is not allowed for logical agent "
                    f"{agent.agent_id}"
                )
            missing_artifacts = sorted(set(node.inputs) - available_artifacts)
            if missing_artifacts:
                raise ValueError(
                    f"workflow node references unknown input artifacts: {missing_artifacts}"
                )
            registry.validate_action(node.semantic_action())
        return self

    @staticmethod
    def _unique_by_id[T](
        values: tuple[T, ...], identifiers: Iterable[str], label: str
    ) -> dict[str, T]:
        identifiers = tuple(identifiers)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"{label} values must be unique")
        return dict(zip(identifiers, values, strict=True))

    def _assert_acyclic(self, nodes: dict[str, WorkflowNode]) -> None:
        successors: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        indegree = {node_id: 0 for node_id in nodes}
        for edge in self.edges:
            if edge.consumer_node not in successors[edge.producer_node]:
                successors[edge.producer_node].add(edge.consumer_node)
                indegree[edge.consumer_node] += 1
        ready = deque(node_id for node_id, count in indegree.items() if count == 0)
        visited = 0
        while ready:
            node_id = ready.popleft()
            visited += 1
            for successor in successors[node_id]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if visited != len(nodes):
            raise ValueError("workflow graph must be acyclic")


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class WorkflowState(ContractModel):
    node_status: dict[str, NodeStatus]

    @classmethod
    def initialize(cls, plan: WorkflowPlan) -> "WorkflowState":
        return cls(
            node_status={node.node_id: NodeStatus.PENDING for node in plan.nodes}
        )

    def validate_against(self, plan: WorkflowPlan) -> Self:
        expected = {node.node_id for node in plan.nodes}
        actual = set(self.node_status)
        if actual != expected:
            missing = sorted(expected - actual)
            unknown = sorted(actual - expected)
            raise ValueError(
                f"workflow state node IDs do not match plan; "
                f"missing={missing}, unknown={unknown}"
            )
        return self
