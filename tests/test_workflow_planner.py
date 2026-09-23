import json

import pytest

from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelRequest,
)
from infra_joint.workflow.planner import LLMWorkflowPlanner, WorkflowPlanningError
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
                source_ref="private://must-not-leak",
            ),
            ArtifactSpec(
                artifact_id="shard-b",
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=10,
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
            "allowed_operations": ["bm25_retrieve", "invoke_model"],
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
                "allowed_operations": ["invoke_model"],
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
