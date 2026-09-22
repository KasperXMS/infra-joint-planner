import pytest
from pydantic import ValidationError

from infra_joint.core import (
    LogicalAgent,
    NodeStatus,
    WorkflowEdge,
    WorkflowNode,
    WorkflowPlan,
    WorkflowState,
)
from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec


def registry() -> OperatorRegistry:
    result = OperatorRegistry()
    schema = {
        "type": "object",
        "properties": {"mode": {"type": "string", "minLength": 1}},
        "required": ["mode"],
        "additionalProperties": False,
    }
    input_schema = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 1,
    }
    for operator_id in ("transform", "summarize"):
        result.register(
            OperatorSpec(
                operator_id=operator_id,
                description=f"{operator_id} an artifact",
                input_schema=input_schema,
                argument_schema=schema,
            ),
            lambda: None,
        )
    return result


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(AgentSpec(agent_id="physical-a", device="gpu"),),
        deployments=(
            DeploymentSpec(
                deployment_id="shared-model",
                agent_id="physical-a",
                model_id="reader-model",
                context_window=8192,
            ),
        ),
    )


def task() -> TaskContract:
    return TaskContract(
        task_id="task-1",
        benchmark_id="demo",
        objective="Produce an answer",
        artifacts=(
            ArtifactSpec(
                artifact_id="source",
                logical_type="document",
                media_type="text/plain",
                size_bytes=10,
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="exact-v1",
    )


def logical_agent(agent_id: str, *operations: str) -> LogicalAgent:
    return LogicalAgent(
        agent_id=agent_id,
        role=f"role-{agent_id}",
        objective="Process assigned evidence",
        model_instance_id="shared-model",
        allowed_operations=operations,
    )


def valid_plan() -> WorkflowPlan:
    return WorkflowPlan(
        agents=(
            logical_agent("researcher", "transform"),
            logical_agent("writer", "summarize"),
        ),
        nodes=(
            WorkflowNode(
                node_id="retrieve",
                agent_id="researcher",
                operator="transform",
                inputs=("source",),
                arguments={"mode": "evidence"},
                outputs=("evidence",),
            ),
            WorkflowNode(
                node_id="answer",
                agent_id="writer",
                operator="summarize",
                inputs=("evidence",),
                arguments={"mode": "concise"},
                outputs=("answer",),
            ),
        ),
        edges=(
            WorkflowEdge(
                producer_node="retrieve",
                consumer_node="answer",
                artifact_id="evidence",
            ),
        ),
    )


def test_plan_allows_multiple_logical_agents_to_share_a_deployment() -> None:
    plan = valid_plan()

    assert {agent.model_instance_id for agent in plan.agents} == {"shared-model"}
    assert plan.validate_against(task(), environment(), registry()) is plan


def test_plan_rejects_unknown_logical_agent_reference() -> None:
    with pytest.raises(ValidationError, match="unknown agent"):
        WorkflowPlan(
            agents=(logical_agent("researcher", "transform"),),
            nodes=(
                WorkflowNode(
                    node_id="node",
                    agent_id="missing",
                    operator="transform",
                ),
            ),
        )


def test_plan_rejects_cycles() -> None:
    with pytest.raises(ValidationError, match="must be acyclic"):
        WorkflowPlan(
            agents=(logical_agent("researcher", "transform"),),
            nodes=(
                WorkflowNode(
                    node_id="one",
                    agent_id="researcher",
                    operator="transform",
                    inputs=("from-two",),
                    outputs=("from-one",),
                ),
                WorkflowNode(
                    node_id="two",
                    agent_id="researcher",
                    operator="transform",
                    inputs=("from-one",),
                    outputs=("from-two",),
                ),
            ),
            edges=(
                WorkflowEdge(
                    producer_node="one",
                    consumer_node="two",
                    artifact_id="from-one",
                ),
                WorkflowEdge(
                    producer_node="two",
                    consumer_node="one",
                    artifact_id="from-two",
                ),
            ),
        )


def test_plan_rejects_invalid_edge_and_missing_dependency_edge() -> None:
    with pytest.raises(ValidationError, match="not produced"):
        WorkflowPlan(
            agents=(logical_agent("researcher", "transform"),),
            nodes=(
                WorkflowNode(
                    node_id="one",
                    agent_id="researcher",
                    operator="transform",
                    outputs=("produced",),
                ),
                WorkflowNode(
                    node_id="two",
                    agent_id="researcher",
                    operator="transform",
                    inputs=("wrong",),
                ),
            ),
            edges=(
                WorkflowEdge(
                    producer_node="one",
                    consumer_node="two",
                    artifact_id="wrong",
                ),
            ),
        )

    with pytest.raises(ValidationError, match="requires an exact edge"):
        WorkflowPlan(
            agents=(logical_agent("researcher", "transform"),),
            nodes=(
                WorkflowNode(
                    node_id="one",
                    agent_id="researcher",
                    operator="transform",
                    outputs=("produced",),
                ),
                WorkflowNode(
                    node_id="two",
                    agent_id="researcher",
                    operator="transform",
                    inputs=("produced",),
                ),
            ),
        )


def test_external_validation_rejects_model_and_operator_reference_errors() -> None:
    unknown_model = valid_plan().model_copy(
        update={
            "agents": (
                logical_agent("researcher", "transform").model_copy(
                    update={"model_instance_id": "missing-model"}
                ),
                logical_agent("writer", "summarize"),
            )
        }
    )
    with pytest.raises(ValueError, match="unknown model_instance_id"):
        unknown_model.validate_against(task(), environment(), registry())

    unknown_operator = valid_plan().model_copy(
        update={
            "agents": (
                logical_agent("researcher", "missing-operator"),
                logical_agent("writer", "summarize"),
            )
        }
    )
    with pytest.raises(ValueError, match="unknown operators"):
        unknown_operator.validate_against(task(), environment(), registry())

    forbidden_operator = valid_plan().model_copy(
        update={
            "agents": (
                logical_agent("researcher", "summarize"),
                logical_agent("writer", "summarize"),
            )
        }
    )
    with pytest.raises(ValueError, match="not allowed"):
        forbidden_operator.validate_against(task(), environment(), registry())


def test_external_validation_applies_operator_schema() -> None:
    plan = valid_plan().model_copy(
        update={
            "nodes": (
                valid_plan().nodes[0].model_copy(update={"arguments": {}}),
                valid_plan().nodes[1],
            )
        }
    )

    with pytest.raises(ValueError, match="required property"):
        plan.validate_against(task(), environment(), registry())


def test_external_validation_rejects_unknown_or_overwritten_artifacts() -> None:
    unknown = WorkflowPlan(
        agents=(logical_agent("researcher", "transform"),),
        nodes=(
            WorkflowNode(
                node_id="node",
                agent_id="researcher",
                operator="transform",
                inputs=("missing",),
                arguments={"mode": "evidence"},
                outputs=("result",),
            ),
        ),
    )
    with pytest.raises(ValueError, match="unknown input artifacts"):
        unknown.validate_against(task(), environment(), registry())

    overwrite = valid_plan().model_copy(
        update={
            "nodes": (
                valid_plan().nodes[0].model_copy(update={"outputs": ("source",)}),
                valid_plan().nodes[1].model_copy(update={"inputs": ("source",)}),
            ),
            "edges": (
                WorkflowEdge(
                    producer_node="retrieve",
                    consumer_node="answer",
                    artifact_id="source",
                ),
            ),
        }
    )
    with pytest.raises(ValueError, match="collide with task artifacts"):
        overwrite.validate_against(task(), environment(), registry())


def test_workflow_state_is_initialized_and_checked_against_the_plan() -> None:
    plan = valid_plan()
    state = WorkflowState.initialize(plan)

    assert state.node_status == {
        "retrieve": NodeStatus.PENDING,
        "answer": NodeStatus.PENDING,
    }
    assert state.validate_against(plan) is state

    incomplete = WorkflowState(node_status={"retrieve": NodeStatus.DONE})
    with pytest.raises(ValueError, match="do not match plan"):
        incomplete.validate_against(plan)
