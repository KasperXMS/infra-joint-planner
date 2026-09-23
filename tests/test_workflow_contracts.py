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
from infra_joint.operators.catalog import build_operator_catalog
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
        agents=(
            AgentSpec(
                agent_id="physical-a",
                device="gpu",
                capabilities=frozenset({"model"}),
            ),
        ),
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


def logical_agent(agent_id: str) -> LogicalAgent:
    return LogicalAgent(
        agent_id=agent_id,
        role=f"role-{agent_id}",
        objective="Process assigned evidence",
        model_instance_id="shared-model",
    )


def valid_plan() -> WorkflowPlan:
    return WorkflowPlan(
        agents=(
            logical_agent("researcher"),
            logical_agent("writer"),
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
    assert plan.validate_against(
        task(), environment(), registry(), ("transform", "summarize")
    ) is plan


def test_logical_agent_contract_has_no_planner_declared_action_space() -> None:
    assert "allowed_operations" not in LogicalAgent.model_json_schema()["properties"]
    with pytest.raises(ValidationError, match="allowed_operations"):
        LogicalAgent.model_validate(
            {
                **logical_agent("researcher").model_dump(),
                "allowed_operations": ["transform"],
            }
        )


def test_plan_rejects_unknown_logical_agent_reference() -> None:
    with pytest.raises(ValidationError, match="unknown agent"):
        WorkflowPlan(
            agents=(logical_agent("researcher"),),
            nodes=(
                WorkflowNode(
                    node_id="node",
                    agent_id="missing",
                    operator="transform",
                ),
            ),
        )


def test_plan_rejects_declared_agent_without_owned_node() -> None:
    with pytest.raises(ValidationError, match="every logical agent must own"):
        WorkflowPlan(
            agents=(
                logical_agent("active"),
                logical_agent("unused"),
            ),
            nodes=(
                WorkflowNode(
                    node_id="node",
                    agent_id="active",
                    operator="transform",
                ),
            ),
        )


def test_plan_rejects_cycles() -> None:
    with pytest.raises(ValidationError, match="must be acyclic"):
        WorkflowPlan(
            agents=(logical_agent("researcher"),),
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
            agents=(logical_agent("researcher"),),
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
            agents=(logical_agent("researcher"),),
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
                logical_agent("researcher").model_copy(
                    update={"model_instance_id": "missing-model"}
                ),
                logical_agent("writer"),
            )
        }
    )
    with pytest.raises(ValueError, match="unknown model_instance_id"):
        unknown_model.validate_against(
            task(), environment(), registry(), ("transform", "summarize")
        )

    unknown_operator = valid_plan().model_copy(
        update={
            "nodes": (
                valid_plan().nodes[0].model_copy(update={"operator": "missing-operator"}),
                valid_plan().nodes[1],
            )
        }
    )
    with pytest.raises(ValueError, match="unknown operator"):
        unknown_operator.validate_against(
            task(), environment(), registry(), ("transform", "summarize")
        )

    with pytest.raises(ValueError, match="outside the system action space"):
        valid_plan().validate_against(task(), environment(), registry(), ("summarize",))


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
        plan.validate_against(
            task(), environment(), registry(), ("transform", "summarize")
        )


def test_system_rejects_operator_without_any_capable_execution_surface() -> None:
    plan = WorkflowPlan(
        agents=(logical_agent("researcher"),),
        nodes=(
            WorkflowNode(
                node_id="retrieve",
                agent_id="researcher",
                operator="bm25_retrieve",
                inputs=("source",),
                arguments={
                    "query": "question",
                    "top_k": 1,
                    "text_field": "text",
                    "output_artifact_id": "evidence",
                },
                outputs=("evidence",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="not feasible"):
        plan.validate_against(
            task(), environment(), build_operator_catalog(), ("bm25_retrieve",)
        )


def test_system_rejects_model_input_modality_unsupported_by_binding() -> None:
    image_task = task().model_copy(
        update={
            "artifacts": (
                task().artifacts[0].model_copy(update={"media_type": "image/jpeg"}),
            )
        }
    )
    plan = WorkflowPlan(
        agents=(logical_agent("writer"),),
        nodes=(
            WorkflowNode(
                node_id="answer",
                agent_id="writer",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Answer."},
            ),
        ),
    )

    with pytest.raises(ValueError, match="does not support modalities.*image"):
        plan.validate_against(
            image_task,
            environment(),
            build_operator_catalog(),
            ("invoke_model",),
        )


@pytest.mark.parametrize(
    ("outputs", "arguments", "error"),
    (
        (
            ("first", "second"),
            {"prompt": "Answer."},
            "at most one materialized output",
        ),
        (
            ("answer",),
            {"prompt": "Answer.", "output_artifact_id": "different"},
            "must exactly match node outputs",
        ),
        (
            ("answer",),
            {"prompt": "Answer.", "output_media_type": "image/png"},
            "output_media_type",
        ),
        (
            (),
            {"prompt": "Answer.", "output_media_type": "text/plain"},
            "must not declare output materialization",
        ),
    ),
)
def test_invoke_model_output_contract_is_validated_before_execution(
    outputs: tuple[str, ...],
    arguments: dict[str, str],
    error: str,
) -> None:
    plan = WorkflowPlan(
        agents=(logical_agent("writer"),),
        nodes=(
            WorkflowNode(
                node_id="answer",
                agent_id="writer",
                operator="invoke_model",
                inputs=("source",),
                arguments=arguments,
                outputs=outputs,
            ),
        ),
    )

    with pytest.raises(ValueError, match=error):
        plan.validate_against(
            task(), environment(), build_operator_catalog(), ("invoke_model",)
        )


def test_invoke_model_accepts_one_declared_text_output_without_redundant_id() -> None:
    plan = WorkflowPlan(
        agents=(logical_agent("writer"),),
        nodes=(
            WorkflowNode(
                node_id="reason",
                agent_id="writer",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Reason.", "output_media_type": "application/json"},
                outputs=("reasoning",),
            ),
        ),
    )

    assert plan.validate_against(
        task(), environment(), build_operator_catalog(), ("invoke_model",)
    ) is plan
    assert plan.terminal_model_node() == plan.nodes[0]


def test_sample_frames_requires_concrete_deterministic_frame_outputs() -> None:
    video_task = TaskContract(
        task_id="video",
        benchmark_id="video",
        objective="Answer from sampled frames",
        artifacts=(
            ArtifactSpec(
                artifact_id="video",
                logical_type="complete_video",
                media_type="video/mp4",
                size_bytes=100,
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private",
    )
    media_environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="worker",
                device="opaque",
                capabilities=frozenset({"model", "media.ffmpeg", "media.image"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="shared-model",
                agent_id="worker",
                model_id="reader-model",
                modalities=frozenset({"text", "image"}),
                context_window=8192,
            ),
        ),
    )
    invalid = WorkflowPlan(
        agents=(logical_agent("viewer"),),
        nodes=(
            WorkflowNode(
                node_id="sample",
                agent_id="viewer",
                operator="sample_frames",
                inputs=("video",),
                arguments={
                    "every_seconds": 10,
                    "max_frames": 2,
                    "output_prefix": "frames",
                },
                outputs=("frames",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="enumerate every deterministic frame"):
        invalid.validate_against(
            video_task,
            media_environment,
            build_operator_catalog(),
            ("sample_frames",),
        )

    valid = invalid.model_copy(
        update={
            "nodes": (
                invalid.nodes[0].model_copy(
                    update={
                        "outputs": (
                            "frames/frame-000001.jpg",
                            "frames/frame-000002.jpg",
                        )
                    }
                ),
            )
        }
    )
    assert valid.validate_against(
        video_task,
        media_environment,
        build_operator_catalog(),
        ("sample_frames",),
    ) is valid


def test_invoke_model_rejects_known_oversized_context_before_execution() -> None:
    oversized_task = task().model_copy(
        update={
            "artifacts": (
                task().artifacts[0].model_copy(update={"size_bytes": 9_000}),
            )
        }
    )
    plan = WorkflowPlan(
        agents=(logical_agent("reader"),),
        nodes=(
            WorkflowNode(
                node_id="answer",
                agent_id="reader",
                operator="invoke_model",
                inputs=("source",),
                arguments={"prompt": "Answer from the complete source."},
            ),
        ),
    )

    with pytest.raises(ValueError, match="context upper bound exceeds model contract"):
        plan.validate_against(
            oversized_task,
            environment(),
            build_operator_catalog(),
            ("invoke_model",),
        )


def test_external_validation_rejects_unknown_or_overwritten_artifacts() -> None:
    unknown = WorkflowPlan(
        agents=(logical_agent("researcher"),),
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
        unknown.validate_against(
            task(), environment(), registry(), ("transform", "summarize")
        )

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
        overwrite.validate_against(
            task(), environment(), registry(), ("transform", "summarize")
        )


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
