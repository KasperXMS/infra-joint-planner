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
from infra_joint.control.workflow_cost import (
    ConcurrentServiceProfile,
    ConcurrentTransferProfile,
    SemanticWorkflowCostEvaluator,
)
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
            unit_kind="fixed",
            service_latency_ms=100,
            source="test",
        ),
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="B",
            deployment_id="dep-b",
            unit_kind="fixed",
            service_latency_ms=1,
            source="test",
        ),
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="C",
            deployment_id="dep-c",
            unit_kind="fixed",
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


def _frontier_task(*artifact_ids: str) -> TaskContract:
    return TaskContract(
        task_id="frontier-projection",
        benchmark_id="synthetic",
        objective="Use the evidence and return A or B.",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=artifact_id,
                logical_type="evidence",
                media_type="application/json",
                size_bytes=1_000,
                content_schema=ArtifactContentSchema(kind="record_array"),
            )
            for artifact_id in artifact_ids
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private",
    )


def _model_action(
    action_id: str,
    inputs: tuple[str, ...],
    output_id: str | None = None,
) -> LogicalModelAction:
    outputs = (
        (
            LogicalOutput(
                artifact_id=output_id,
                semantic_type="analysis",
                media_type="text/plain",
            ),
        )
        if output_id is not None
        else ()
    )
    return LogicalModelAction(
        action_id=action_id,
        owner_agent_id="analysis-role",
        inputs=inputs,
        outputs=outputs,
        prompt="Analyze the supplied evidence.",
        requirements=ExecutionRequirements(
            min_context_tokens=256,
            reserved_output_tokens=32,
        ),
    )


def _single_compute_environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="A", device="source"),
            AgentSpec(
                agent_id="B",
                device="gpu",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="dep-b",
                agent_id="B",
                model_id="test-model",
                context_window=8_192,
                reserved_output_tokens=64,
                image_token_cost=256,
                max_output_bytes=256,
            ),
        ),
        links=(
            LinkSpec(
                source_agent_id="A",
                target_agent_id="B",
                bandwidth_mbps=10,
                rtt_ms=20,
            ),
        ),
    )


def _single_compute_state(*artifact_ids: str) -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="A", available=True),
            AgentRuntimeState(agent_id="B", available=True),
        ),
        deployments=(DeploymentRuntimeState(deployment_id="dep-b", available=True),),
        artifacts=tuple(
            ArtifactRuntimeState(
                artifact_id=artifact_id,
                locations=("A",),
                media_type="application/json",
                size_bytes=1_000,
            )
            for artifact_id in artifact_ids
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="A",
                target_agent_id="B",
                available=True,
                bandwidth_mbps=10,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )


def _model_profiles() -> tuple[ExecutionCostProfile, ...]:
    return (
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="B",
            deployment_id="dep-b",
            input_units=1_000,
            unit_kind="bytes",
            service_latency_ms=100,
            source="single-service-calibration",
        ),
    )


def _frontier_evaluator(
    plan: SemanticWorkflowPlan,
    *,
    concurrent_profiles: tuple[ConcurrentServiceProfile, ...] = (),
    concurrent_transfer_profiles: tuple[ConcurrentTransferProfile, ...] = (),
) -> SemanticWorkflowCostEvaluator:
    environment = _single_compute_environment()
    registry = build_operator_catalog()
    return SemanticWorkflowCostEvaluator(
        environment,
        registry,
        _model_profiles(),
        _frontier_task("raw"),
        build_static_capability_contract(environment, registry, ("invoke_model",)),
        concurrent_profiles=concurrent_profiles,
        concurrent_transfer_profiles=concurrent_transfer_profiles,
    )


def _replica_plan() -> SemanticWorkflowPlan:
    inspect = _model_action("inspect", ("raw",), "note")
    answer = _model_action("answer", ("raw", "note"))
    return SemanticWorkflowPlan(
        workflow_id="replica-projection",
        version=0,
        actions=(inspect, answer),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="inspect",
                consumer_action_id="answer",
                information_id="note",
            ),
        ),
        terminal_action_id="answer",
    )


def _parallel_model_plan(*, serial: bool = False) -> SemanticWorkflowPlan:
    first = _model_action("branch-a", ("raw",), "note-a")
    second = _model_action("branch-b", ("raw",), "note-b")
    answer = _model_action("answer", ("note-a", "note-b"))
    dependencies = [
        WorkflowDependency(
            dependency_type="artifact",
            producer_action_id="branch-a",
            consumer_action_id="answer",
            information_id="note-a",
        ),
        WorkflowDependency(
            dependency_type="artifact",
            producer_action_id="branch-b",
            consumer_action_id="answer",
            information_id="note-b",
        ),
    ]
    if serial:
        dependencies.append(
            WorkflowDependency(
                dependency_type="control",
                producer_action_id="branch-a",
                consumer_action_id="branch-b",
            )
        )
    return SemanticWorkflowPlan(
        workflow_id="serial-projection" if serial else "parallel-projection",
        version=0,
        actions=(first, second, answer),
        dependencies=tuple(dependencies),
        terminal_action_id="answer",
    )


def _concurrent_profile() -> tuple[ConcurrentServiceProfile, ...]:
    return (
        ConcurrentServiceProfile(
            operator="invoke_model",
            concurrency=2,
            agent_id="B",
            deployment_id="dep-b",
            service_latency_ms=150,
            source="measured-dual-model",
        ),
    )


def _concurrent_transfer_profile() -> tuple[ConcurrentTransferProfile, ...]:
    return (
        ConcurrentTransferProfile(
            source_agent_id="A",
            target_agent_id="B",
            concurrency=2,
            input_units=1_000,
            unit_kind="bytes",
            transfer_latency_ms=30,
            source="measured-dual-transfer",
        ),
    )


def test_frontier_projection_propagates_input_replica_and_future_output_location() -> None:
    plan = _replica_plan()
    state = _single_compute_state("raw")
    detail = _frontier_evaluator(plan).evaluate_detailed(
        plan,
        WorkflowRuntimeState.initialize(plan),
        state,
    )
    selected = {item.action_id: item for item in detail.selected_bindings}
    assert selected["inspect"].transfer_bytes == 1_000
    assert selected["answer"].transfer_bytes == 0
    assert [item.action_ids for item in detail.frontiers] == [
        ("inspect",),
        ("answer",),
    ]
    artifacts = {item.artifact_id: item for item in detail.projected_artifacts}
    assert artifacts["raw"].locations == ("A", "B")
    assert artifacts["note"].locations == ("B",)

    scheduler = AutoPhysicalScheduler()
    environment = _single_compute_environment()
    registry = build_operator_catalog()
    first = scheduler.select(
        plan.actions[0],
        semantic_action(plan.actions[0]),
        environment,
        state,
        registry,
    )
    after_first = state.model_copy(
        update={
            "artifacts": (
                ArtifactRuntimeState(
                    artifact_id="raw",
                    locations=("A", "B"),
                    media_type="application/json",
                    size_bytes=1_000,
                ),
                ArtifactRuntimeState(
                    artifact_id="note",
                    locations=("B",),
                    media_type="text/plain",
                    size_bytes=256,
                ),
            )
        }
    )
    second = scheduler.select(
        plan.actions[1],
        semantic_action(plan.actions[1]),
        environment,
        after_first,
        registry,
    )
    assert selected["inspect"].selected_agent_id == first.selected_agent_id
    assert selected["answer"].selected_agent_id == second.selected_agent_id


def test_same_frontier_uses_one_snapshot_and_known_concurrency_profile() -> None:
    plan = _parallel_model_plan()
    detail = _frontier_evaluator(
        plan,
        concurrent_profiles=_concurrent_profile(),
        concurrent_transfer_profiles=_concurrent_transfer_profile(),
    ).evaluate_detailed(
        plan,
        WorkflowRuntimeState.initialize(plan),
        _single_compute_state("raw"),
    )
    selected = {item.action_id: item for item in detail.selected_bindings}
    assert selected["branch-a"].transfer_bytes == 1_000
    assert selected["branch-b"].transfer_bytes == 1_000
    assert selected["branch-a"].concurrency == 2
    assert selected["branch-b"].concurrency == 2
    assert selected["branch-a"].service_latency_ms == 150
    assert selected["branch-b"].service_latency_ms == 150
    assert selected["branch-a"].concurrency_profile_source == "measured-dual-model"
    group = detail.frontiers[0].concurrency_groups[0]
    assert group.action_ids == ("branch-a", "branch-b")
    assert group.concurrency == 2
    assert group.profile_complete
    transfer_group = detail.frontiers[0].transfer_concurrency_groups[0]
    assert transfer_group.action_ids == ("branch-a", "branch-b")
    assert transfer_group.artifact_ids == ("raw", "raw")
    assert transfer_group.concurrency == 2
    assert transfer_group.profile_complete
    assert selected["branch-a"].base_transfer_latency_ms == pytest.approx(20.8)
    assert selected["branch-a"].transfer_latency_ms == 30
    assert selected["branch-a"].transfer_concurrency_profile_sources == (
        "measured-dual-transfer",
    )
    assert detail.view.predicted_service_latency_ms == 400
    assert detail.view.predicted_transfer_latency_ms == 60
    assert detail.view.predicted_critical_path_ms == pytest.approx(280)


def test_missing_concurrency_profile_fails_unknown() -> None:
    plan = _parallel_model_plan()
    detail = _frontier_evaluator(plan).evaluate_detailed(
        plan,
        WorkflowRuntimeState.initialize(plan),
        _single_compute_state("raw"),
    )
    assert detail.frontiers[0].concurrency_groups[0].profile_complete is False
    assert detail.view.predicted_critical_path_ms is None
    assert detail.view.predicted_total_work_ms is None
    assert "concurrent_service_profile_unavailable" in detail.view.unknown_reasons
    assert "concurrent_transfer_profile_unavailable" in detail.view.unknown_reasons


def test_different_device_parallel_actions_have_known_critical_path() -> None:
    environment = EnvironmentSpec(
        agents=tuple(
            AgentSpec(
                agent_id=agent_id,
                device="gpu",
                capabilities=frozenset({"model"}),
            )
            for agent_id in ("A", "B")
        ),
        deployments=tuple(
            DeploymentSpec(
                deployment_id=f"dep-{agent_id.lower()}",
                agent_id=agent_id,
                model_id="test-model",
                context_window=8_192,
                reserved_output_tokens=64,
                image_token_cost=256,
                max_output_bytes=256,
            )
            for agent_id in ("A", "B")
        ),
        links=(
            LinkSpec(
                source_agent_id="B",
                target_agent_id="A",
                bandwidth_mbps=10,
                rtt_ms=20,
            ),
            LinkSpec(
                source_agent_id="A",
                target_agent_id="B",
                bandwidth_mbps=10,
                rtt_ms=20,
            ),
        ),
    )
    state = InfrastructureState(
        agents=tuple(
            AgentRuntimeState(agent_id=agent_id, available=True)
            for agent_id in ("A", "B")
        ),
        deployments=tuple(
            DeploymentRuntimeState(
                deployment_id=f"dep-{agent_id.lower()}",
                available=True,
            )
            for agent_id in ("A", "B")
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw-a",
                locations=("A",),
                media_type="application/json",
                size_bytes=1_000,
            ),
            ArtifactRuntimeState(
                artifact_id="raw-b",
                locations=("B",),
                media_type="application/json",
                size_bytes=1_000,
            ),
        ),
        links=tuple(
            LinkRuntimeState(
                source_agent_id=source,
                target_agent_id=target,
                available=True,
                bandwidth_mbps=10,
                rtt_ms=20,
            )
            for source, target in (("B", "A"), ("A", "B"))
        ),
        observed_at=datetime.now(UTC),
    )
    first = _model_action("branch-a", ("raw-a",), "note-a")
    second = _model_action("branch-b", ("raw-b",), "note-b")
    answer = _model_action("answer", ("note-a", "note-b"))
    plan = SemanticWorkflowPlan(
        workflow_id="different-device-parallel",
        version=0,
        actions=(first, second, answer),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="branch-a",
                consumer_action_id="answer",
                information_id="note-a",
            ),
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="branch-b",
                consumer_action_id="answer",
                information_id="note-b",
            ),
        ),
        terminal_action_id="answer",
    )
    registry = build_operator_catalog()
    profiles = tuple(
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id=agent_id,
            deployment_id=f"dep-{agent_id.lower()}",
            unit_kind="fixed",
            service_latency_ms=latency,
            source="per-device-calibration",
        )
        for agent_id, latency in (("A", 100), ("B", 200))
    )
    detail = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        profiles,
        _frontier_task("raw-a", "raw-b"),
        build_static_capability_contract(environment, registry, ("invoke_model",)),
    ).evaluate_detailed(plan, WorkflowRuntimeState.initialize(plan), state)
    first_frontier = {
        item.action_id: item.selected_agent_id
        for item in detail.selected_bindings
        if item.frontier_index == 0
    }
    assert first_frontier == {"branch-a": "A", "branch-b": "B"}
    assert detail.frontiers[0].concurrency_groups == ()
    assert detail.view.predicted_critical_path_ms is not None
    assert "concurrent_service_profile_unavailable" not in detail.view.unknown_reasons


def test_dependency_changes_parallel_critical_path_to_serial() -> None:
    state = _single_compute_state("raw")
    parallel_plan = _parallel_model_plan()
    serial_plan = _parallel_model_plan(serial=True)
    parallel = _frontier_evaluator(
        parallel_plan,
        concurrent_profiles=_concurrent_profile(),
        concurrent_transfer_profiles=_concurrent_transfer_profile(),
    ).evaluate(
        parallel_plan,
        WorkflowRuntimeState.initialize(parallel_plan),
        state,
    )
    serial = _frontier_evaluator(serial_plan).evaluate(
        serial_plan,
        WorkflowRuntimeState.initialize(serial_plan),
        state,
    )
    assert parallel.predicted_critical_path_ms == pytest.approx(280)
    assert serial.predicted_critical_path_ms == pytest.approx(320.8)
    assert serial.predicted_critical_path_ms > parallel.predicted_critical_path_ms


def test_service_and_transfer_contention_each_fail_unknown_when_unmeasured() -> None:
    plan = _parallel_model_plan()
    state = _single_compute_state("raw")
    service_only = _frontier_evaluator(
        plan,
        concurrent_profiles=_concurrent_profile(),
    ).evaluate(plan, WorkflowRuntimeState.initialize(plan), state)
    transfer_only = _frontier_evaluator(
        plan,
        concurrent_transfer_profiles=_concurrent_transfer_profile(),
    ).evaluate(plan, WorkflowRuntimeState.initialize(plan), state)

    assert service_only.predicted_critical_path_ms is None
    assert "concurrent_transfer_profile_unavailable" in service_only.unknown_reasons
    assert "concurrent_service_profile_unavailable" not in service_only.unknown_reasons
    assert transfer_only.predicted_critical_path_ms is None
    assert "concurrent_service_profile_unavailable" in transfer_only.unknown_reasons
    assert "concurrent_transfer_profile_unavailable" not in transfer_only.unknown_reasons


def test_simultaneous_different_links_are_not_grouped_as_contended() -> None:
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="S1", device="source"),
            AgentSpec(agent_id="S2", device="source"),
            AgentSpec(
                agent_id="B",
                device="gpu",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="dep-b",
                agent_id="B",
                model_id="test-model",
                context_window=8_192,
                reserved_output_tokens=64,
                image_token_cost=256,
                max_output_bytes=256,
            ),
        ),
        links=tuple(
            LinkSpec(
                source_agent_id=source,
                target_agent_id="B",
                bandwidth_mbps=10,
                rtt_ms=20,
            )
            for source in ("S1", "S2")
        ),
    )
    task = _frontier_task("raw-a", "raw-b")
    state = InfrastructureState(
        agents=tuple(
            AgentRuntimeState(agent_id=agent_id, available=True)
            for agent_id in ("S1", "S2", "B")
        ),
        deployments=(DeploymentRuntimeState(deployment_id="dep-b", available=True),),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="raw-a",
                locations=("S1",),
                media_type="application/json",
                size_bytes=1_000,
            ),
            ArtifactRuntimeState(
                artifact_id="raw-b",
                locations=("S2",),
                media_type="application/json",
                size_bytes=1_000,
            ),
        ),
        links=tuple(
            LinkRuntimeState(
                source_agent_id=source,
                target_agent_id="B",
                available=True,
                bandwidth_mbps=10,
                rtt_ms=20,
            )
            for source in ("S1", "S2")
        ),
        observed_at=datetime.now(UTC),
    )
    first = _model_action("branch-a", ("raw-a",), "note-a")
    second = _model_action("branch-b", ("raw-b",), "note-b")
    answer = _model_action("answer", ("note-a", "note-b"))
    plan = SemanticWorkflowPlan(
        workflow_id="different-link-parallel",
        version=0,
        actions=(first, second, answer),
        dependencies=(
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="branch-a",
                consumer_action_id="answer",
                information_id="note-a",
            ),
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="branch-b",
                consumer_action_id="answer",
                information_id="note-b",
            ),
        ),
        terminal_action_id="answer",
    )
    registry = build_operator_catalog()
    detail = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        (
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id="B",
                deployment_id="dep-b",
                unit_kind="fixed",
                service_latency_ms=100,
                source="single-service",
            ),
        ),
        task,
        build_static_capability_contract(environment, registry, ("invoke_model",)),
        concurrent_profiles=_concurrent_profile(),
    ).evaluate_detailed(plan, WorkflowRuntimeState.initialize(plan), state)

    assert detail.frontiers[0].transfer_concurrency_groups == ()
    assert "concurrent_transfer_profile_unavailable" not in detail.view.unknown_reasons
    assert detail.view.predicted_critical_path_ms == pytest.approx(270.8)


def test_token_service_profile_does_not_match_byte_input() -> None:
    with pytest.raises(ValueError, match="unit_kind"):
        ConcurrentServiceProfile.model_validate(
            {
                "operator": "invoke_model",
                "concurrency": 2,
                "unit_kind": "tokens",
                "service_latency_ms": 1,
                "source": "invalid",
            }
        )
    environment = _single_compute_environment()
    registry = build_operator_catalog()
    plan = direct_plan()
    detail = SemanticWorkflowCostEvaluator(
        environment,
        registry,
        (
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id="B",
                deployment_id="dep-b",
                input_units=1_000,
                unit_kind="tokens",
                service_latency_ms=1,
                source="incompatible-token-profile",
            ),
        ),
        large_task(size_bytes=1_000),
        build_static_capability_contract(environment, registry, ("invoke_model",)),
    ).evaluate_detailed(
        plan,
        WorkflowRuntimeState.initialize(plan),
        _single_compute_state("raw"),
    )
    assert detail.selected_bindings[0].service_latency_ms is None
    assert detail.view.predicted_critical_path_ms is None
    assert "service_profile_unavailable" in detail.view.unknown_reasons


def test_model_output_byte_bound_is_explicit_or_unknown() -> None:
    plan = SemanticWorkflowPlan(
        workflow_id="model-output-bound",
        version=0,
        actions=(_model_action("produce", ("raw",), "note"),),
        terminal_action_id="produce",
    )
    registry = build_operator_catalog()
    explicit_environment = _single_compute_environment()
    explicit = analyze_static_workflow(
        plan,
        _frontier_task("raw"),
        build_static_capability_contract(
            explicit_environment,
            registry,
            ("invoke_model",),
        ),
    ).artifact_map()["note"]
    assert explicit.size_upper_bound_bytes == 256
    assert explicit.unknown_reasons == ()

    unknown_environment = explicit_environment.model_copy(
        update={
            "deployments": tuple(
                item.model_copy(update={"max_output_bytes": None})
                for item in explicit_environment.deployments
            )
        }
    )
    unknown = analyze_static_workflow(
        plan,
        _frontier_task("raw"),
        build_static_capability_contract(
            unknown_environment,
            registry,
            ("invoke_model",),
        ),
    ).artifact_map()["note"]
    assert unknown.size_upper_bound_bytes is None
    assert unknown.unknown_reasons == ("model_output_byte_bound_unavailable",)
