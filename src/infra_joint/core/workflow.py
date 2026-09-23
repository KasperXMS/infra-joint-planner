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
        active_agents = {node.agent_id for node in self.nodes}
        unused_agents = sorted(set(agents) - active_agents)
        if unused_agents:
            raise ValueError(f"every logical agent must own a workflow node: {unused_agents}")

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
        available_operations: Iterable[str],
    ) -> Self:
        """Validate external model/operator refs and all artifact dependencies."""

        system_operations = frozenset(available_operations)
        unknown_system_operations = sorted(
            operation for operation in system_operations if operation not in registry
        )
        if unknown_system_operations:
            raise ValueError(
                f"system action space references unknown operators: {unknown_system_operations}"
            )
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

        feasible_operations = derive_agent_feasible_operations(
            self,
            environment,
            registry,
            system_operations,
        )
        artifact_media_types = self._artifact_media_types(task)

        available_artifacts = task_artifacts | produced_artifacts
        for node in self.nodes:
            agent = agents[node.agent_id]
            if node.operator not in registry:
                raise ValueError(f"workflow node references unknown operator: {node.operator}")
            if node.operator not in system_operations:
                raise ValueError(
                    f"operator {node.operator} is outside the system action space"
                )
            if node.operator not in feasible_operations[agent.agent_id]:
                raise ValueError(
                    f"operator {node.operator} is not feasible for logical agent "
                    f"{agent.agent_id}"
                )
            missing_artifacts = sorted(set(node.inputs) - available_artifacts)
            if missing_artifacts:
                raise ValueError(
                    f"workflow node references unknown input artifacts: {missing_artifacts}"
                )
            if node.operator == "invoke_model":
                self._validate_model_modalities(
                    node,
                    deployments[agent.model_instance_id].modalities,
                    artifact_media_types,
                )
                if len(node.outputs) > 1:
                    raise ValueError("invoke_model supports at most one materialized output")
                configured_output = node.arguments.get("output_artifact_id")
                if configured_output is not None and tuple(node.outputs) != (configured_output,):
                    raise ValueError(
                        "invoke_model output_artifact_id must exactly match node outputs"
                    )
                output_media_type = node.arguments.get("output_media_type", "text/plain")
                if output_media_type not in {"text/plain", "application/json"}:
                    raise ValueError(
                        "invoke_model output_media_type must be text/plain or application/json"
                    )
                if not node.outputs and any(
                    key in node.arguments
                    for key in (
                        "output_artifact_id",
                        "output_media_type",
                        "output_semantic_type",
                    )
                ):
                    raise ValueError(
                        "terminal inline invoke_model must not declare output materialization"
                    )
            registry.validate_action(node.semantic_action())
        return self

    def _artifact_media_types(self, task: TaskContract) -> dict[str, str | None]:
        media_types: dict[str, str | None] = {
            item.artifact_id: item.media_type for item in task.artifacts
        }
        json_operators = {
            "aggregate_artifacts",
            "aggregate_records",
            "bm25_retrieve",
            "derive_fields",
            "filter_records",
            "select_fields",
            "top_k_records",
        }
        for node in self.nodes:
            if node.operator == "invoke_model":
                media_type = str(node.arguments.get("output_media_type", "text/plain"))
            elif node.operator in {"make_contact_sheet", "sample_frames"}:
                media_type = "image/jpeg"
            elif node.operator == "extract_clip":
                media_type = "video/mp4"
            elif node.operator in json_operators:
                media_type = "application/json"
            elif node.outputs:
                media_type = None
            else:
                continue
            media_types.update(dict.fromkeys(node.outputs, media_type))
        return media_types

    @staticmethod
    def _validate_model_modalities(
        node: WorkflowNode,
        deployment_modalities: frozenset[str],
        artifact_media_types: dict[str, str | None],
    ) -> None:
        required = {"text"}
        for artifact_id in node.inputs:
            media_type = artifact_media_types[artifact_id]
            if media_type is None:
                raise ValueError(
                    "invoke_model input media type cannot be derived: "
                    f"{artifact_id}"
                )
            if media_type.startswith("image/"):
                required.add("image")
            elif media_type.startswith("text/") or media_type in {
                "application/json",
                "application/jsonl",
                "application/x-ndjson",
            }:
                required.add("text")
            else:
                raise ValueError(
                    "invoke_model input has unsupported media type: "
                    f"{artifact_id}/{media_type}"
                )
        unsupported = required - deployment_modalities
        if unsupported:
            raise ValueError(
                f"model instance for node {node.node_id} does not support modalities: "
                f"{sorted(unsupported)}"
            )

    def terminal_model_node(self) -> WorkflowNode:
        """Return the unique terminal model node that owns the benchmark answer."""

        producers_with_consumers = {edge.producer_node for edge in self.edges}
        terminal_nodes = tuple(
            node for node in self.nodes if node.node_id not in producers_with_consumers
        )
        if len(terminal_nodes) != 1:
            raise ValueError("workflow must have exactly one terminal node")
        terminal = terminal_nodes[0]
        if terminal.operator != "invoke_model":
            raise ValueError("workflow terminal node must use invoke_model")
        return terminal

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


def feasible_operations_for_model_instance(
    model_instance_id: str,
    environment: EnvironmentSpec,
    registry: "OperatorRegistry",
    available_operations: Iterable[str],
) -> frozenset[str]:
    """Derive the finite system-owned action space for one model-bound agent."""

    deployments = {
        deployment.deployment_id: deployment for deployment in environment.deployments
    }
    agents = {agent.agent_id: agent for agent in environment.agents}
    try:
        deployment = deployments[model_instance_id]
    except KeyError as exc:
        raise ValueError(f"unknown model instance: {model_instance_id}") from exc
    host = agents[deployment.agent_id]
    feasible: set[str] = set()
    for operator_id in available_operations:
        if operator_id not in registry:
            continue
        requirements = registry.binding(operator_id).spec.capability_requirements
        if "model" in requirements:
            if requirements <= host.capabilities and "text" in deployment.modalities:
                feasible.add(operator_id)
        elif any(
            requirements <= physical_agent.capabilities
            for physical_agent in environment.agents
        ):
            feasible.add(operator_id)
    return frozenset(feasible)


def derive_agent_feasible_operations(
    plan: WorkflowPlan,
    environment: EnvironmentSpec,
    registry: "OperatorRegistry",
    available_operations: Iterable[str],
) -> dict[str, frozenset[str]]:
    """Derive each logical agent's action space from system-owned contracts."""

    system_operations = tuple(available_operations)
    return {
        agent.agent_id: feasible_operations_for_model_instance(
            agent.model_instance_id,
            environment,
            registry,
            system_operations,
        )
        for agent in plan.agents
    }


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
