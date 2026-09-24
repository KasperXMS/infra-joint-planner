import json
from types import SimpleNamespace

import pytest

from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.core.task import (
    ArtifactCollectionRelation,
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.core.workflow import LogicalAgent, WorkflowNode, WorkflowPlan
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import (
    ModelCallTelemetry,
    ModelCompletion,
    ModelRequest,
)
from infra_joint.workflow.replanning import (
    OpaqueModelAliasWorkflowReplanner,
    ReviseWorkflowProposal,
    WorkflowReplanContext,
)
from infra_joint.workflow.workload import WorkloadSpec
from scripts.open_ended_mas_preliminary_v1 import (
    _alias_environment,
    _alias_workload,
    _code_revision,
)


class RecordingKeepBackend:
    def __init__(self, response: str | None = None) -> None:
        self.request: ModelRequest | None = None
        self.response = response or '{"decision":"keep","reason":"evidence is sufficient"}'

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.request = request
        return ModelCompletion(
            text=self.response,
            telemetry=ModelCallTelemetry(service_latency_ms=1),
        )


def test_alias_contract_preserves_configured_budget_and_collection_semantics() -> None:
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="physical",
                device="opaque",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="real-model",
                agent_id="physical",
                model_id="model",
                context_window=16_384,
                reserved_output_tokens=1_024,
            ),
        ),
    )
    relation = ArtifactCollectionRelation(
        collection_id="complete-corpus",
        partition_index=0,
        partition_count=1,
        partition_method="sha256(document) modulo partition_count",
        partition_semantics="non_semantic",
        completeness="union_is_complete",
    )
    task = TaskContract(
        task_id="task",
        benchmark_id="benchmark",
        evaluator_id="private-evaluator",
        objective="answer from the complete corpus",
        artifacts=(
            ArtifactSpec(
                artifact_id="shard",
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=100,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"body": "string"},
                    text_field="body",
                    record_count=1,
                    max_record_bytes=100,
                ),
                collection=relation,
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
    )
    bundle = SimpleNamespace(execution=SimpleNamespace(task=task))

    aliased_environment = _alias_environment(
        {"reasoner": "real-model"},
        environment,
    )
    workload = _alias_workload(
        bundle,
        {"reasoner": "real-model"},
        ("invoke_model",),
        6,
        environment,
    )

    assert aliased_environment.deployments[0].reserved_output_tokens == 1_024
    assert workload.available_model_instances[0].reserved_output_tokens == 1_024
    assert workload.artifacts[0].collection == relation


def test_deployed_experiment_accepts_explicit_full_git_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "a" * 40
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", revision.upper())

    assert _code_revision() == revision


def test_deployed_experiment_rejects_malformed_git_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INFRA_JOINT_CODE_REVISION", "not-a-full-git-sha")

    with pytest.raises(ValueError, match="full 40-character Git SHA"):
        _code_revision()


@pytest.mark.asyncio
async def test_blind_replanner_uses_opaque_model_aliases() -> None:
    environment = EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="physical-a28-secret",
                device="device-secret",
                capabilities=frozenset({"model"}),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="a28-model-secret",
                agent_id="physical-a28-secret",
                model_id="model",
                context_window=16_384,
                reserved_output_tokens=1_024,
            ),
        ),
    )
    task = TaskContract(
        task_id="task",
        benchmark_id="benchmark",
        evaluator_id="private-evaluator",
        objective="return a short answer",
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
    )
    workload = WorkloadSpec.from_task_environment(
        task,
        environment,
        available_operations=("invoke_model",),
    )
    plan = WorkflowPlan(
        agents=(
            LogicalAgent(
                agent_id="answerer",
                role="answerer",
                objective="answer",
                model_instance_id="a28-model-secret",
            ),
        ),
        nodes=(
            WorkflowNode(
                node_id="answer",
                agent_id="answerer",
                operator="invoke_model",
                arguments={"prompt": "answer now"},
            ),
        ),
    )
    context = WorkflowReplanContext(
        revision_index=0,
        current_plan=plan,
        completed_node_ids=(),
        pending_node_ids=("answer",),
        semantic_observations=(),
    )
    backend = RecordingKeepBackend()

    outcome = await OpaqueModelAliasWorkflowReplanner(
        backend,
        build_operator_catalog(),
        environment,
        {"reasoner-alpha": "a28-model-secret"},
    ).replan(task, workload, context)

    assert outcome.proposal.decision == "keep"
    assert backend.request is not None
    assert "reasoner-alpha" in backend.request.prompt
    assert "a28-model-secret" not in backend.request.prompt
    assert "physical-a28-secret" not in backend.request.prompt
    assert "device-secret" not in backend.request.prompt
    assert "private-evaluator" not in backend.request.prompt

    revised_plan = plan.model_copy(
        update={
            "agents": tuple(
                agent.model_copy(update={"model_instance_id": "reasoner-alpha"})
                for agent in plan.agents
            ),
            "nodes": (
                plan.nodes[0].model_copy(
                    update={"arguments": {"prompt": "answer from sufficient evidence"}}
                ),
            ),
        }
    )
    revise_backend = RecordingKeepBackend(
        json.dumps(
            {
                "decision": "revise",
                "trigger": "evidence_insufficient",
                "reason": "the pending answer needs a clearer instruction",
                "plan": revised_plan.model_dump(mode="json"),
            }
        )
    )
    revised = await OpaqueModelAliasWorkflowReplanner(
        revise_backend,
        build_operator_catalog(),
        environment,
        {"reasoner-alpha": "a28-model-secret"},
    ).replan(task, workload, context)

    assert isinstance(revised.proposal, ReviseWorkflowProposal)
    assert revised.proposal.plan.agents[0].model_instance_id == "a28-model-secret"
