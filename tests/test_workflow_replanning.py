from datetime import UTC, datetime

import pytest

from infra_joint.core.action import JointAction
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.core.workflow import LogicalAgent, WorkflowEdge, WorkflowNode, WorkflowPlan
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.executor import ExecutionResult
from infra_joint.workflow.orchestrator import WorkflowOrchestrator
from infra_joint.workflow.replanning import (
    KeepWorkflowProposal,
    ReplanningWorkflowExecutor,
    ReplanTrigger,
    ReviseWorkflowProposal,
    ScriptedWorkflowReplanner,
    WorkflowReplanningError,
    validate_workflow_revision,
)
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler
from infra_joint.workflow.workload import WorkloadSpec

SHA = "a" * 64


class ReplanningObserver:
    def __init__(self) -> None:
        self.artifacts = {
            name: ArtifactRuntimeState(
                artifact_id=name,
                locations=(agent,),
                media_type="application/json",
                size_bytes=100,
                sha256_hex=SHA,
            )
            for name, agent in (("shard-a", "A"), ("shard-b", "B"))
        }

    async def observe(self) -> InfrastructureState:
        return InfrastructureState(
            agents=tuple(
                AgentRuntimeState(agent_id=agent_id, available=True)
                for agent_id in ("A", "B", "C")
            ),
            deployments=(DeploymentRuntimeState(deployment_id="text", available=True),),
            artifacts=tuple(self.artifacts.values()),
            links=(),
            observed_at=datetime.now(UTC),
        )


class RecordingExecutor:
    def __init__(self, observer: ReplanningObserver) -> None:
        self._observer = observer
        self.nodes: list[tuple[str, ...]] = []

    async def execute(
        self,
        action: JointAction,
        infrastructure: InfrastructureState,
    ) -> ExecutionResult:
        del infrastructure
        self.nodes.append(action.semantic.inputs)
        if action.semantic.operator == "bm25_retrieve":
            output_id = str(action.semantic.arguments["output_artifact_id"])
            location = "A" if action.semantic.inputs == ("shard-a",) else "B"
            self._observer.artifacts[output_id] = ArtifactRuntimeState(
                artifact_id=output_id,
                locations=(location,),
                media_type="application/json",
                size_bytes=50,
                sha256_hex=SHA,
            )
            return ExecutionResult(
                operator="bm25_retrieve",
                agent_ids=(location,),
                output={
                    "artifact_id": output_id,
                    "media_type": "application/json",
                    "size_bytes": 50,
                    "sha256_hex": SHA,
                },
                operator_latency_ms=1,
            )
        return ExecutionResult(
            operator="invoke_model",
            agent_ids=("C",),
            deployment_id="text",
            output={"text": "answer"},
            operator_latency_ms=1,
        )


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=tuple(
            AgentSpec(
                agent_id=agent_id,
                device="test",
                capabilities=frozenset({"retrieval", "model"}),
            )
            for agent_id in ("A", "B", "C")
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="text",
                agent_id="C",
                model_id="text-model",
                context_window=4096,
                reserved_output_tokens=512,
            ),
        ),
    )


def task() -> TaskContract:
    return TaskContract(
        task_id="replanning",
        benchmark_id="synthetic",
        objective="answer from sufficient corpus evidence",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=artifact_id,
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=100,
            )
            for artifact_id in ("shard-a", "shard-b")
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private",
    )


def agent(agent_id: str) -> LogicalAgent:
    return LogicalAgent(
        agent_id=agent_id,
        role="retriever" if agent_id != "synth" else "synthesizer",
        objective="produce evidence" if agent_id != "synth" else "answer",
        model_instance_id="text",
    )


def retrieval(suffix: str) -> WorkflowNode:
    return WorkflowNode(
        node_id=f"retrieve-{suffix}",
        agent_id=f"retriever-{suffix}",
        operator="bm25_retrieve",
        inputs=(f"shard-{suffix}",),
        arguments={
            "query": "answer",
            "top_k": 1,
            "text_field": "text",
            "output_artifact_id": f"evidence-{suffix}",
        },
        outputs=(f"evidence-{suffix}",),
    )


def initial_plan() -> WorkflowPlan:
    terminal = WorkflowNode(
        node_id="terminal",
        agent_id="synth",
        operator="invoke_model",
        inputs=("evidence-a",),
        arguments={"prompt": "answer from the available evidence"},
    )
    return WorkflowPlan(
        agents=(agent("retriever-a"), agent("synth")),
        nodes=(retrieval("a"), terminal),
        edges=(
            WorkflowEdge(
                producer_node="retrieve-a",
                consumer_node="terminal",
                artifact_id="evidence-a",
            ),
        ),
    )


def revised_plan() -> WorkflowPlan:
    terminal = WorkflowNode(
        node_id="terminal",
        agent_id="synth",
        operator="invoke_model",
        inputs=("evidence-a", "evidence-b"),
        arguments={"prompt": "answer only after checking both evidence branches"},
    )
    return WorkflowPlan(
        agents=(agent("retriever-a"), agent("retriever-b"), agent("synth")),
        nodes=(retrieval("a"), retrieval("b"), terminal),
        edges=tuple(
            WorkflowEdge(
                producer_node=f"retrieve-{suffix}",
                consumer_node="terminal",
                artifact_id=f"evidence-{suffix}",
            )
            for suffix in ("a", "b")
        ),
    )


def build_executor(
    scripted: ScriptedWorkflowReplanner,
) -> tuple[ReplanningWorkflowExecutor, RecordingExecutor, WorkloadSpec]:
    current_environment = environment()
    registry = build_operator_catalog()
    observer = ReplanningObserver()
    action_executor = RecordingExecutor(observer)
    workload = WorkloadSpec.from_task_environment(
        task(),
        current_environment,
        available_operations=("bm25_retrieve", "invoke_model"),
        max_agents=4,
    )
    orchestrator = WorkflowOrchestrator(
        registry,
        current_environment,
        observer,
        action_executor,
        LocalityAwareMyopicScheduler(),
        available_operations=workload.available_operations,
    )
    return ReplanningWorkflowExecutor(orchestrator, scripted), action_executor, workload


@pytest.mark.asyncio
async def test_replanning_adds_missing_branch_without_replaying_completed_node() -> None:
    revised = revised_plan()
    loop, actions, workload = build_executor(
        ScriptedWorkflowReplanner(
            (
                ReviseWorkflowProposal(
                    trigger=ReplanTrigger.EVIDENCE_INSUFFICIENT,
                    reason="the second non-semantic shard has not been searched",
                    plan=revised,
                ),
            )
        )
    )

    result = await loop.execute(task(), workload, initial_plan())

    assert result.workflow.completed
    assert [version.plan for version in result.versions] == [initial_plan(), revised]
    assert result.revisions[0].changes is not None
    assert result.revisions[0].changes.added_nodes == ("retrieve-b",)
    assert actions.nodes.count(("shard-a",)) == 1
    assert actions.nodes.count(("shard-b",)) == 1
    assert actions.nodes[-1] == ("evidence-a", "evidence-b")
    assert len(result.workflow.records) == 3


@pytest.mark.asyncio
async def test_keep_decision_executes_original_future_without_changes() -> None:
    loop, actions, workload = build_executor(
        ScriptedWorkflowReplanner(
            (KeepWorkflowProposal(reason="evidence is sufficient and consistent"),)
        )
    )

    result = await loop.execute(task(), workload, initial_plan())

    assert result.workflow.completed
    assert len(result.versions) == 1
    assert result.revisions[0].decision == "keep"
    assert actions.nodes == [("shard-a",), ("evidence-a",)]


def test_revision_rejects_modifying_a_completed_node() -> None:
    current = initial_plan()
    changed = current.model_copy(
        update={
            "nodes": (
                retrieval("a").model_copy(
                    update={"arguments": {**retrieval("a").arguments, "top_k": 2}}
                ),
                current.nodes[1],
            )
        }
    )

    with pytest.raises(ValueError, match="modified completed nodes"):
        validate_workflow_revision(current, changed, ("retrieve-a",))


@pytest.mark.asyncio
async def test_invalid_revision_carries_the_paused_execution_for_persistence() -> None:
    current = initial_plan()
    invalid = current.model_copy(
        update={
            "nodes": (
                retrieval("a").model_copy(
                    update={"arguments": {**retrieval("a").arguments, "top_k": 2}}
                ),
                current.nodes[1],
            )
        }
    )
    loop, _, workload = build_executor(
        ScriptedWorkflowReplanner(
            (
                ReviseWorkflowProposal(
                    trigger=ReplanTrigger.EVIDENCE_INSUFFICIENT,
                    reason="try to change completed work",
                    plan=invalid,
                ),
            )
        )
    )

    with pytest.raises(WorkflowReplanningError) as captured:
        await loop.execute(task(), workload, current)

    assert captured.value.execution is not None
    assert captured.value.execution.paused
    assert [record.node_id for record in captured.value.execution.records] == ["retrieve-a"]
    assert len(captured.value.versions) == 1
    assert captured.value.current_plan == current
