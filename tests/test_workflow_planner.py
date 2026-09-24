import json
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
    ArtifactCollectionRelation,
    ArtifactContentSchema,
    ArtifactSpec,
    CollectionCompleteness,
    OutputContract,
    OutputFormat,
    PartitionSemantics,
    TaskContract,
)
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelRequest,
)
from infra_joint.workflow.planner import LLMWorkflowPlanner, WorkflowPlanningError
from infra_joint.workflow.replanning import (
    ExecutionCostProfile,
    InfrastructureReplanView,
    LLMInfrastructureAwareWorkflowReplanner,
    LLMWorkflowReplanner,
    SemanticNodeObservation,
    TransferCostEstimate,
    WorkflowReplanContext,
)
from infra_joint.workflow.workload import WorkloadSpec


class CapturingBackend:
    def __init__(self, response: str) -> None:
        self._response = response
        self.requests: list[ModelRequest] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        return ModelCompletion(
            text=self._response,
            telemetry=ModelCallTelemetry(service_latency_ms=1),
        )


class StaticInfrastructureViewProvider:
    def __init__(self, view: InfrastructureReplanView) -> None:
        self._view = view

    async def observe(
        self, context: WorkflowReplanContext
    ) -> InfrastructureReplanView:
        del context
        return self._view


def task() -> TaskContract:
    return TaskContract(
        task_id="fanout",
        benchmark_id="synthetic",
        objective="Answer from two independent corpus shards.",
        artifacts=(
            ArtifactSpec(
                artifact_id="shard-a",
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=10,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"text": "string", "title": "string"},
                    text_field="text",
                    record_count=2,
                    max_record_bytes=10,
                ),
                source_ref="private://must-not-leak",
            ),
            ArtifactSpec(
                artifact_id="shard-b",
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=10,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"text": "string", "title": "string"},
                    text_field="text",
                    record_count=2,
                    max_record_bytes=10,
                ),
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private-evaluator-must-not-leak",
    )


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="physical-secret",
                device="device-secret",
                capabilities=frozenset({"retrieval", "model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="text-instance",
                agent_id="physical-secret",
                model_id="text-model",
                modalities=frozenset({"text", "image"}),
                context_window=8192,
            ),
        ),
    )


def workflow_json() -> str:
    agents = [
        {
            "agent_id": value,
            "role": "retrieve" if value != "synth" else "synthesize",
            "objective": "work on an independent logical context",
            "model_instance_id": "text-instance",
        }
        for value in ("retriever-a", "retriever-b", "synth")
    ]
    nodes = [
        {
            "node_id": "retrieve-a",
            "agent_id": "retriever-a",
            "operator": "bm25_retrieve",
            "inputs": ["shard-a"],
            "arguments": {
                "query": "question",
                "top_k": 2,
                "text_field": "text",
                "output_artifact_id": "evidence-a",
            },
            "outputs": ["evidence-a"],
        },
        {
            "node_id": "retrieve-b",
            "agent_id": "retriever-b",
            "operator": "bm25_retrieve",
            "inputs": ["shard-b"],
            "arguments": {
                "query": "question",
                "top_k": 2,
                "text_field": "text",
                "output_artifact_id": "evidence-b",
            },
            "outputs": ["evidence-b"],
        },
        {
            "node_id": "synthesize",
            "agent_id": "synth",
            "operator": "invoke_model",
            "inputs": ["evidence-a", "evidence-b"],
            "arguments": {"prompt": "Answer the task from both retrieved artifacts."},
            "outputs": [],
        },
    ]
    edges = [
        {
            "producer_node": "retrieve-a",
            "consumer_node": "synthesize",
            "artifact_id": "evidence-a",
        },
        {
            "producer_node": "retrieve-b",
            "consumer_node": "synthesize",
            "artifact_id": "evidence-b",
        },
    ]
    return json.dumps({"agents": agents, "nodes": nodes, "edges": edges})


@pytest.mark.asyncio
async def test_llm_workflow_planner_generates_explicit_fanout_fanin_without_leakage() -> None:
    registry = build_operator_catalog()
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
        min_agents=3,
        max_agents=3,
    )
    backend = CapturingBackend(workflow_json())
    planner = LLMWorkflowPlanner(backend, registry, current_environment)

    result = await planner.plan(current_task, workload)

    roots = {node.node_id for node in result.plan.nodes if node.node_id != "synthesize"}
    assert roots == {"retrieve-a", "retrieve-b"}
    assert {edge.consumer_node for edge in result.plan.edges} == {"synthesize"}
    assert len(result.plan.agents) == 3
    prompt = backend.requests[0].prompt
    assert "private://must-not-leak" not in prompt
    assert "private-evaluator-must-not-leak" not in prompt
    assert "physical-secret" not in prompt
    assert "device-secret" not in prompt
    assert "Use multiple logical agents only" in prompt
    assert "a single logical agent is valid" in prompt
    assert '"context_window":8192' in prompt
    assert "will not lower top_k or repair the workflow" in prompt
    assert "top_k=3 is safe while top_k=12 or 20 is not" in prompt
    assert "The task objective and output contract are prompt context, not artifact IDs" in prompt
    assert "materialize concise evidence notes" in prompt
    assert "system_context_preflight_guidance" in prompt
    assert "max_equal_bm25_top_k_per_artifact" in prompt
    assert "never clipframe/clipframe-000001.jpg" in prompt
    assert '"text_field":"text"' in prompt


def test_context_preflight_guidance_accounts_for_parallel_record_fan_in() -> None:
    current_task = task().model_copy(
        update={
            "artifacts": tuple(
                item.model_copy(
                    update={
                        "artifact_id": f"shard-{index}",
                        "content_schema": item.content_schema.model_copy(
                            update={"max_record_bytes": 3_000}
                        ),
                    }
                )
                for index, item in enumerate(task().artifacts * 2, start=1)
            )[:3]
        }
    )
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
    )

    guidance = LLMWorkflowPlanner.context_preflight_guidance(
        current_task, workload
    )

    assert guidance == [
        {
            "model_instance_id": "text-instance",
            "record_artifact_ids": ["shard-1", "shard-2", "shard-3"],
            "max_equal_bm25_top_k_per_artifact": 0,
            "max_invoke_prompt_bytes": 1_024,
            "assumption": (
                "one BM25 result from every listed artifact enters the same "
                "invoke_model call"
            ),
        }
    ]


@pytest.mark.asyncio
async def test_llm_workflow_planner_rejects_invalid_model_output_before_execution() -> None:
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
        min_agents=3,
        max_agents=3,
    )
    raw = json.loads(workflow_json())
    raw["nodes"][-1]["arguments"]["output_media_type"] = "image/png"
    planner = LLMWorkflowPlanner(
        CapturingBackend(json.dumps(raw)),
        build_operator_catalog(),
        current_environment,
    )

    with pytest.raises(WorkflowPlanningError, match="output_media_type"):
        await planner.plan(current_task, workload)


@pytest.mark.asyncio
async def test_llm_workflow_planner_rejects_schema_inconsistent_field_before_execution() -> None:
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
    )
    raw = json.loads(workflow_json())
    raw["nodes"][0]["arguments"]["text_field"] = "invented"
    planner = LLMWorkflowPlanner(
        CapturingBackend(json.dumps(raw)),
        build_operator_catalog(),
        current_environment,
    )

    with pytest.raises(WorkflowPlanningError, match="schema field"):
        await planner.plan(current_task, workload)


@pytest.mark.asyncio
async def test_llm_workflow_planner_allows_natural_single_agent_plan() -> None:
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("invoke_model",),
        max_agents=6,
    )
    raw = {
        "agents": [
            {
                "agent_id": "answerer",
                "role": "answerer",
                "objective": "Answer directly when decomposition is unnecessary.",
                "model_instance_id": "text-instance",
            }
        ],
        "nodes": [
            {
                "node_id": "answer",
                "agent_id": "answerer",
                "operator": "invoke_model",
                "inputs": ["shard-a", "shard-b"],
                "arguments": {"prompt": "Answer from the supplied evidence."},
                "outputs": [],
            }
        ],
        "edges": [],
    }

    result = await LLMWorkflowPlanner(
        CapturingBackend(json.dumps(raw)),
        build_operator_catalog(),
        current_environment,
    ).plan(current_task, workload)

    assert len(result.plan.agents) == 1


def test_workload_has_capabilities_but_no_solution_or_placement_fields() -> None:
    schema = WorkloadSpec.model_json_schema()
    properties = set(schema["properties"])
    assert properties == {
        "available_operations",
        "available_model_instances",
        "artifacts",
        "min_agents",
        "max_agents",
    }
    forbidden = {"nodes", "edges", "placements", "links", "gold", "evidence"}
    assert not properties.intersection(forbidden)


def test_workflow_prompt_sorts_model_modalities_deterministically() -> None:
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("invoke_model",),
    )
    prompt = LLMWorkflowPlanner(
        CapturingBackend(workflow_json()),
        build_operator_catalog(),
        current_environment,
    ).render_prompt(current_task, workload)
    planning_input = json.loads(prompt.splitlines()[-1])

    assert planning_input["workload"]["available_model_instances"][0]["modalities"] == [
        "image",
        "text",
    ]
    assert planning_input["system_feasible_operations_by_model_instance"] == {
        "text-instance": ["invoke_model"]
    }
    assert "allowed_operations" not in prompt


def test_planner_and_replanner_see_collection_semantics_without_private_or_physical_data() -> None:
    current_task = task().model_copy(
        update={
            "artifacts": tuple(
                artifact.model_copy(
                    update={
                        "collection": ArtifactCollectionRelation(
                            collection_id="complete-corpus",
                            partition_index=index,
                            partition_count=2,
                            partition_method="sha256(document) modulo partition_count",
                            partition_semantics=PartitionSemantics.NON_SEMANTIC,
                            completeness=CollectionCompleteness.UNION_IS_COMPLETE,
                        )
                    }
                )
                for index, artifact in enumerate(task().artifacts)
            )
        }
    )
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
    )
    current_plan = WorkflowPlan.model_validate_json(workflow_json())
    context = WorkflowReplanContext(
        revision_index=0,
        current_plan=current_plan,
        completed_node_ids=("retrieve-a", "retrieve-b"),
        pending_node_ids=("synthesize",),
        semantic_observations=(
            SemanticNodeObservation(
                node_id="retrieve-a",
                operator="bm25_retrieve",
                output={"artifact_id": "evidence-a"},
            ),
        ),
    )

    initial_prompt = LLMWorkflowPlanner(
        CapturingBackend(workflow_json()),
        build_operator_catalog(),
        current_environment,
    ).render_prompt(current_task, workload)
    replan_prompt = LLMWorkflowReplanner(
        CapturingBackend('{"decision":"keep","reason":"sufficient"}'),
        build_operator_catalog(),
        current_environment,
    ).render_prompt(current_task, workload, context)

    for prompt in (initial_prompt, replan_prompt):
        assert '"collection_id":"complete-corpus"' in prompt
        assert '"partition_semantics":"non_semantic"' in prompt
        assert '"completeness":"union_is_complete"' in prompt
        assert "private://must-not-leak" not in prompt
        assert "private-evaluator-must-not-leak" not in prompt
        assert "physical-secret" not in prompt
        assert "device-secret" not in prompt
    assert "completed_node_ids list is an immutable prefix contract" in replan_prompt
    assert "add a new retrieval node and a new reasoning node with fresh IDs" in replan_prompt
    assert "system_context_preflight_guidance" in replan_prompt
    assert "will not lower top_k or repair the graph" in replan_prompt


@pytest.mark.asyncio
async def test_infra_aware_replanner_alone_receives_explicit_physical_cost_view() -> None:
    current_task = task()
    current_environment = environment()
    workload = WorkloadSpec.from_task_environment(
        current_task,
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
    )
    current_plan = WorkflowPlan.model_validate_json(workflow_json())
    context = WorkflowReplanContext(
        revision_index=0,
        current_plan=current_plan,
        completed_node_ids=("retrieve-a", "retrieve-b"),
        pending_node_ids=("synthesize",),
        semantic_observations=(),
    )
    state = InfrastructureState(
        agents=(AgentRuntimeState(agent_id="physical-secret", available=True),),
        deployments=(
            DeploymentRuntimeState(deployment_id="text-instance", available=True),
        ),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="evidence-a",
                locations=("physical-secret",),
                media_type="application/json",
                size_bytes=1024,
                sha256_hex="a" * 64,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="physical-secret",
                target_agent_id="cloud",
                available=True,
                bandwidth_mbps=3,
                rtt_ms=20,
            ),
        ),
        observed_at=datetime.now(UTC),
    )
    view = InfrastructureReplanView(
        environment=current_environment,
        state=state,
        relevant_artifact_ids=("evidence-a",),
        pending_transfer_estimates=(
            TransferCostEstimate(
                node_id="synthesize",
                target_agent_id="cloud",
                artifact_ids=("evidence-a",),
                transfer_bytes=1024,
                estimated_latency_ms=22.7,
                basis="current artifact locations and measured link",
            ),
        ),
        execution_cost_profiles=(
            ExecutionCostProfile(
                operator="invoke_model",
                agent_id="cloud",
                deployment_id="text-instance",
                input_units=1024,
                output_units=128,
                service_latency_ms=1600,
                source="frozen measured profile",
            ),
        ),
    )
    blind_backend = CapturingBackend('{"decision":"keep","reason":"sufficient"}')
    aware_backend = CapturingBackend('{"decision":"keep","reason":"sufficient"}')
    blind = LLMWorkflowReplanner(
        blind_backend,
        build_operator_catalog(),
        current_environment,
    )
    aware = LLMInfrastructureAwareWorkflowReplanner(
        aware_backend,
        build_operator_catalog(),
        current_environment,
        StaticInfrastructureViewProvider(view),
    )

    await blind.replan(current_task, workload, context)
    await aware.replan(current_task, workload, context)

    blind_prompt = blind_backend.requests[0].prompt
    aware_prompt = aware_backend.requests[0].prompt
    assert "physical-secret" not in blind_prompt
    assert '"bandwidth_mbps":3.0' not in blind_prompt
    assert "physical-secret" in aware_prompt
    assert '"bandwidth_mbps":3.0' in aware_prompt
    assert '"service_latency_ms":1600.0' in aware_prompt
    assert "private://must-not-leak" not in aware_prompt
    assert "private-evaluator-must-not-leak" not in aware_prompt
