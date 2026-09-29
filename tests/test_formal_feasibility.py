from datetime import UTC, datetime

import pytest

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalModelAction,
    LogicalOutput,
    LogicalToolAction,
)
from infra_joint.control.physical import AutoPhysicalScheduler
from infra_joint.control.static_feasibility import analyze_static_workflow
from infra_joint.control.validation import semantic_action
from infra_joint.control.workflow import (
    SemanticWorkflowPlan,
    WorkflowDependency,
    WorkflowRuntimeState,
)
from infra_joint.control.workflow_cost import SemanticWorkflowCostEvaluator
from infra_joint.control.workflow_validation import (
    WorkflowValidationError,
    validate_semantic_workflow,
)
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
    LinkSpec,
)
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.costing import ExecutionCostProfile


def large_task(size_bytes: int = 50_000) -> TaskContract:
    return TaskContract(
        task_id="large-static-case",
        benchmark_id="synthetic",
        objective="Answer from the corpus.",
        artifacts=(
            ArtifactSpec(
                artifact_id="raw",
                logical_type="corpus",
                media_type="application/json",
                size_bytes=size_bytes,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"text": "string", "id": "string"},
                    text_field="text",
                    record_count=100,
                    max_record_bytes=500,
                ),
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private",
    )


def reduction_environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="source",
                device="edge",
                capabilities=frozenset({"retrieval"}),
            ),
            AgentSpec(
                agent_id="compute",
                device="gpu",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="text-model",
                agent_id="compute",
                model_id="test",
                context_window=4096,
                reserved_output_tokens=64,
                image_token_cost=256,
            ),
        ),
        links=(
            LinkSpec(
                source_agent_id="source",
                target_agent_id="compute",
                bandwidth_mbps=3,
                rtt_ms=20,
            ),
        ),
    )


def direct_plan() -> SemanticWorkflowPlan:
    return SemanticWorkflowPlan(
        workflow_id="direct",
        version=0,
        actions=(
            LogicalModelAction(
                action_id="answer",
                owner_agent_id="answer-role",
                inputs=("raw",),
                prompt="Return A or B.",
                requirements=ExecutionRequirements(
                    min_context_tokens=256,
                    reserved_output_tokens=32,
                ),
            ),
        ),
        terminal_action_id="answer",
    )


def reduced_plan() -> SemanticWorkflowPlan:
    reduction = LogicalToolAction(
        action_id="reduce",
        owner_agent_id="retrieval-role",
        operator="bm25_retrieve",
        inputs=("raw",),
        outputs=(
            LogicalOutput(
                artifact_id="reduced",
                semantic_type="retrieval_hits",
                media_type="application/json",
            ),
        ),
        arguments={
            "query": "answer evidence",
            "top_k": 2,
            "text_field": "text",
            "output_artifact_id": "reduced",
        },
    )
    answer = direct_plan().actions[0].model_copy(update={"inputs": ("reduced",)})
    return SemanticWorkflowPlan(
        workflow_id="reduced",
        version=0,
        actions=(reduction, answer),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="reduce",
                consumer_action_id="answer",
                information_id="reduced",
            ),
        ),
        terminal_action_id="answer",
    )


def reduction_capabilities():
    return build_static_capability_contract(
        reduction_environment(),
        build_operator_catalog(),
        ("bm25_retrieve", "invoke_model"),
    )


def test_oversized_direct_model_input_rejected_but_bm25_reduction_is_feasible() -> None:
    registry = build_operator_catalog()
    with pytest.raises(WorkflowValidationError, match="context envelope"):
        validate_semantic_workflow(
            direct_plan(),
            large_task(),
            reduction_capabilities(),
            registry,
        )
    validate_semantic_workflow(
        reduced_plan(),
        large_task(),
        reduction_capabilities(),
        registry,
    )


def test_derived_artifact_size_propagates_along_dag() -> None:
    analysis = analyze_static_workflow(
        reduced_plan(),
        large_task(),
        reduction_capabilities(),
    )
    reduced = analysis.artifact_map()["reduced"]
    assert reduced.size_upper_bound_bytes == 1_260
    assert analysis.model_contexts[0].artifact_token_upper_bound == 1_260


def test_future_derived_artifact_profile_is_not_silent_zero_or_local() -> None:
    environment = reduction_environment()
    task = large_task()
    registry = build_operator_catalog()
    state = InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="source", available=True),
            AgentRuntimeState(agent_id="compute", available=True),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="text-model", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw",
                locations=("source",),
                media_type="application/json",
                size_bytes=task.artifacts[0].size_bytes,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="source",
                target_agent_id="compute",
                available=True,
                bandwidth_mbps=3,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )
    evaluator = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        (
            ExecutionCostProfile(
                operator="bm25_retrieve",
                agent_id="source",
                input_units=50_000,
                unit_kind="bytes",
                service_latency_ms=10,
                source="test",
            ),
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id="compute",
                deployment_id="text-model",
                input_units=1_260,
                unit_kind="bytes",
                service_latency_ms=100,
                source="test",
            ),
        ),
        task,
        reduction_capabilities(),
    )
    detail = evaluator.evaluate_detailed(
        reduced_plan(),
        WorkflowRuntimeState.initialize(reduced_plan()),
        state,
    )
    by_action = {item.action_id: item for item in detail.view.pending_action_profiles}
    model_profile = by_action["answer"]
    assert model_profile.input_bytes == 1_260
    assert model_profile.remote_input_count_range == (1, 1)
    assert model_profile.network_class == "constrained"
    assert detail.view.predicted_transfer_bytes == 1_260


def test_candidate_correlated_cost_matches_actual_auto_scheduler_selection() -> None:
    agents = tuple(
        AgentSpec(
            agent_id=name,
            device="gpu",
            capabilities=frozenset({"model"}),
        )
        for name in ("A", "B", "C")
    )
    deployments = tuple(
        DeploymentSpec(
            deployment_id=f"dep-{name.lower()}",
            agent_id=name,
            model_id="same",
            context_window=8192,
            reserved_output_tokens=64,
            image_token_cost=256,
        )
        for name in ("A", "B", "C")
    )
    environment = EnvironmentSpec(
        agents=agents,
        deployments=deployments,
        links=(
            LinkSpec(source_agent_id="A", target_agent_id="B", bandwidth_mbps=10, rtt_ms=10),
            LinkSpec(source_agent_id="A", target_agent_id="C", bandwidth_mbps=30, rtt_ms=10),
        ),
    )
    task = large_task(size_bytes=1_000)
    state = InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="A", available=True, queue_depth=1),
            AgentRuntimeState(agent_id="B", available=True, queue_depth=5),
            AgentRuntimeState(agent_id="C", available=True, queue_depth=0),
        ),
        deployments=tuple(
            DeploymentRuntimeState(deployment_id=item.deployment_id, available=True)
            for item in deployments
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw",
                locations=("A",),
                media_type="application/json",
                size_bytes=1_000,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="A",
                target_agent_id="B",
                available=True,
                bandwidth_mbps=10,
                rtt_ms=10,
            ),
            LinkRuntimeState(
                source_agent_id="A",
                target_agent_id="C",
                available=True,
                bandwidth_mbps=30,
                rtt_ms=10,
            ),
        ),
        observed_at=datetime.now(UTC),
    )
    registry = build_operator_catalog()
    capabilities = build_static_capability_contract(
        environment,
        registry,
        ("invoke_model",),
    )
    profiles = (
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="A",
            deployment_id="dep-a",
            service_latency_ms=100,
            source="test",
        ),
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="B",
            deployment_id="dep-b",
            service_latency_ms=1,
            source="test",
        ),
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="C",
            deployment_id="dep-c",
            service_latency_ms=10,
            source="test",
        ),
    )
    plan = direct_plan()
    evaluator = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        profiles,
        task,
        capabilities,
    )
    detail = evaluator.evaluate_detailed(
        plan,
        WorkflowRuntimeState.initialize(plan),
        state,
    )
    actual = AutoPhysicalScheduler().select(
        plan.actions[0],
        semantic_action(plan.actions[0]),
        environment,
        state,
        registry,
    )
    selected = detail.selected_bindings[0]
    assert selected.selected_agent_id == actual.selected_agent_id == "A"
    assert selected.selected_deployment_id == actual.selected_deployment_id == "dep-a"
    assert selected.service_latency_ms == 100
    assert selected.queue_latency_ms == 100
    assert selected.total_latency_ms == 200
    action_profile = detail.view.pending_action_profiles[0]
    assert action_profile.service_latency_ms_range == (1, 100)
    assert detail.view.predicted_service_latency_ms == 100
    assert detail.view.predicted_total_work_ms == 200
