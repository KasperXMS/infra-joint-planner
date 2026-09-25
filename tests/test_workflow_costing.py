from datetime import UTC, datetime

import pytest

from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.core.workflow import LogicalAgent, WorkflowEdge, WorkflowNode, WorkflowPlan
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import ModelCallTelemetry, ModelCompletion, ModelRequest
from infra_joint.workflow.costing import (
    ExecutionCostProfile,
    InfrastructurePlanningView,
    WorkflowCostEvaluator,
)
from infra_joint.workflow.planner import LLMInfrastructureAwareWorkflowPlanner
from infra_joint.workflow.workload import WorkloadSpec


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="edge",
                device="edge",
                capabilities=frozenset({"retrieval", "model"}),
            ),
            AgentSpec(
                agent_id="gpu",
                device="gpu",
                capabilities=frozenset({"retrieval", "model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="edge-model",
                agent_id="edge",
                model_id="same-model",
                context_window=16_384,
            ),
            DeploymentSpec(
                deployment_id="gpu-model",
                agent_id="gpu",
                model_id="same-model",
                context_window=16_384,
            ),
        ),
    )


def task() -> TaskContract:
    return TaskContract(
        task_id="cost-task",
        benchmark_id="benchmark",
        evaluator_id="private-evaluator",
        objective="Answer from the artifact.",
        artifacts=(
            ArtifactSpec(
                artifact_id="source",
                logical_type="records",
                media_type="application/json",
                size_bytes=3_000,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"body": "string"},
                    text_field="body",
                    record_count=1,
                    max_record_bytes=2_000,
                ),
                source_ref="private://source",
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
    )


def state(bandwidth_mbps: float) -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="edge", available=True),
            AgentRuntimeState(agent_id="gpu", available=True, in_flight=1),
        ),
        deployments=(
            DeploymentRuntimeState(deployment_id="edge-model", available=True),
            DeploymentRuntimeState(deployment_id="gpu-model", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="source",
                locations=("edge",),
                media_type="text/plain",
                size_bytes=3_000,
                sha256_hex="a" * 64,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="edge",
                target_agent_id="gpu",
                available=True,
                bandwidth_mbps=bandwidth_mbps,
                rtt_ms=20,
            ),
            LinkRuntimeState(
                source_agent_id="gpu",
                target_agent_id="edge",
                available=True,
                bandwidth_mbps=bandwidth_mbps,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )


def plan() -> WorkflowPlan:
    return WorkflowPlan(
        agents=(
            LogicalAgent(
                agent_id="retriever",
                role="retriever",
                objective="reduce locally",
                model_instance_id="edge-model",
            ),
            LogicalAgent(
                agent_id="answerer",
                role="answerer",
                objective="answer",
                model_instance_id="gpu-model",
            ),
        ),
        nodes=(
            WorkflowNode(
                node_id="read",
                agent_id="retriever",
                operator="bm25_retrieve",
                inputs=("source",),
                arguments={
                    "output_artifact_id": "reduced",
                    "query": "question",
                    "text_field": "body",
                    "top_k": 1,
                },
                outputs=("reduced",),
            ),
            WorkflowNode(
                node_id="answer",
                agent_id="answerer",
                operator="invoke_model",
                inputs=("reduced",),
                arguments={"prompt": "answer"},
            ),
        ),
        edges=(
            WorkflowEdge(
                producer_node="read",
                consumer_node="answer",
                artifact_id="reduced",
            ),
        ),
    )


def profiles() -> tuple[ExecutionCostProfile, ...]:
    return (
        ExecutionCostProfile(
            operator="bm25_retrieve",
            agent_id="edge",
            unit_kind="fixed",
            estimated_output_bytes=3_000,
            service_latency_ms=10,
            source="measured",
        ),
        ExecutionCostProfile(
            operator="invoke_model",
            agent_id="gpu",
            deployment_id="gpu-model",
            input_units=3_000,
            service_latency_ms=100,
            source="measured",
        ),
    )


def test_cost_evaluator_applies_b0_placement_transfer_queue_and_bandwidth() -> None:
    slow = WorkflowCostEvaluator(
        environment(), state(3), build_operator_catalog(), profiles()
    ).estimate(plan(), task())
    fast = WorkflowCostEvaluator(
        environment(), state(30), build_operator_catalog(), profiles()
    ).estimate(plan(), task())

    assert slow.complete
    assert slow.node_estimates[0].target_agent_id == "edge"
    assert slow.node_estimates[1].target_agent_id == "gpu"
    assert slow.predicted_transfer_bytes == 3_000
    assert slow.predicted_queue_latency_ms == 100
    assert slow.predicted_transfer_latency_ms == pytest.approx(28)
    assert fast.predicted_transfer_latency_ms == pytest.approx(20.8)
    assert slow.predicted_critical_path_ms > fast.predicted_critical_path_ms


class StaticViewProvider:
    def __init__(self, view: InfrastructurePlanningView) -> None:
        self.view = view

    async def observe_for_planning(self) -> InfrastructurePlanningView:
        return self.view


class RecordingBackend:
    request: ModelRequest | None = None

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.request = request
        return ModelCompletion(
            text=plan().model_dump_json(),
            telemetry=ModelCallTelemetry(service_latency_ms=1),
        )


@pytest.mark.asyncio
async def test_infra_aware_planner_receives_evaluated_cost_contract_without_private_data() -> None:
    current_task = task()
    current_environment = environment()
    current_state = state(3)
    evaluator = WorkflowCostEvaluator(
        current_environment,
        current_state,
        build_operator_catalog(),
        profiles(),
    )
    view = InfrastructurePlanningView(
        environment=current_environment,
        state=current_state,
        relevant_artifact_ids=("source",),
        cost_guidance=evaluator.guidance(("source",)),
    )
    backend = RecordingBackend()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
        max_agents=6,
    )

    outcome = await LLMInfrastructureAwareWorkflowPlanner(
        backend,
        build_operator_catalog(),
        current_environment,
        StaticViewProvider(view),
    ).plan(current_task, workload)

    assert outcome.plan == plan()
    assert backend.request is not None
    assert "open-ended-dag-cost-v1" in backend.request.prompt
    assert "critical_path_ms" in backend.request.prompt
    assert '"bandwidth_mbps":3.0' in backend.request.prompt
    assert "private-evaluator" not in backend.request.prompt
    assert "private://source" not in backend.request.prompt
    assert "candidate workflows" in backend.request.prompt
