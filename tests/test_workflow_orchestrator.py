import asyncio
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
from infra_joint.core.workflow import (
    LogicalAgent,
    NodeStatus,
    WorkflowEdge,
    WorkflowNode,
    WorkflowPlan,
)
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.executor import ExecutionResult
from infra_joint.workflow.orchestrator import WorkflowOrchestrator
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler

SHA = "a" * 64


class MutableObserver:
    def __init__(self) -> None:
        self.artifacts: dict[str, ArtifactRuntimeState] = {
            "shard-a": ArtifactRuntimeState(
                artifact_id="shard-a",
                locations=("A",),
                media_type="application/json",
                size_bytes=100,
                sha256_hex=SHA,
            ),
            "shard-b": ArtifactRuntimeState(
                artifact_id="shard-b",
                locations=("B",),
                media_type="application/json",
                size_bytes=100,
                sha256_hex=SHA,
            ),
        }

    async def observe(self) -> InfrastructureState:
        return InfrastructureState(
            agents=tuple(
                AgentRuntimeState(agent_id=value, available=True)
                for value in ("A", "B", "C")
            ),
            deployments=(DeploymentRuntimeState(deployment_id="text", available=True),),
            artifacts=tuple(self.artifacts.values()),
            links=(),
            observed_at=datetime.now(UTC),
        )


class ConcurrentExecutor:
    def __init__(self, observer: MutableObserver) -> None:
        self._observer = observer
        self.active = 0
        self.max_active = 0

    async def execute(
        self,
        action: JointAction,
        infrastructure: InfrastructureState,
    ) -> ExecutionResult:
        del infrastructure
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.02)
        try:
            if action.semantic.operator == "bm25_retrieve":
                output_id = str(action.semantic.arguments["output_artifact_id"])
                agent_id = "A" if action.semantic.inputs == ("shard-a",) else "B"
                artifact = ArtifactRuntimeState(
                    artifact_id=output_id,
                    locations=(agent_id,),
                    media_type="application/json",
                    size_bytes=50,
                    sha256_hex=SHA,
                )
                self._observer.artifacts[output_id] = artifact
                return ExecutionResult(
                    operator="bm25_retrieve",
                    agent_ids=(agent_id,),
                    output={
                        "artifact_id": output_id,
                        "media_type": "application/json",
                        "size_bytes": 50,
                        "sha256_hex": SHA,
                    },
                    operator_latency_ms=20,
                )
            return ExecutionResult(
                operator="invoke_model",
                agent_ids=("C",),
                deployment_id="text",
                output={"text": "answer"},
                operator_latency_ms=20,
            )
        finally:
            self.active -= 1


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=tuple(
            AgentSpec(
                agent_id=value,
                device="test-device",
                capabilities=frozenset({"retrieval", "model"}),
            )
            for value in ("A", "B", "C")
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
        task_id="fanout",
        benchmark_id="synthetic",
        objective="answer",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=value,
                logical_type="corpus_shard",
                media_type="application/json",
                size_bytes=100,
            )
            for value in ("shard-a", "shard-b")
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="exact",
    )


def plan() -> WorkflowPlan:
    agents = tuple(
        LogicalAgent(
            agent_id=value,
            role="retriever" if value != "synth" else "synthesis",
            objective="independent context",
            model_instance_id="text",
        )
        for value in ("retriever-a", "retriever-b", "synth")
    )
    retrievals = tuple(
        WorkflowNode(
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
        for suffix in ("a", "b")
    )
    synthesis = WorkflowNode(
        node_id="synthesize",
        agent_id="synth",
        operator="invoke_model",
        inputs=("evidence-a", "evidence-b"),
        arguments={"prompt": "answer from both artifacts"},
    )
    return WorkflowPlan(
        agents=agents,
        nodes=(*retrievals, synthesis),
        edges=tuple(
            WorkflowEdge(
                producer_node=f"retrieve-{suffix}",
                consumer_node="synthesize",
                artifact_id=f"evidence-{suffix}",
            )
            for suffix in ("a", "b")
        ),
    )


@pytest.mark.asyncio
async def test_orchestrator_really_overlaps_ready_nodes_and_fans_in() -> None:
    observer = MutableObserver()
    executor = ConcurrentExecutor(observer)
    result = await WorkflowOrchestrator(
        build_operator_catalog(),
        environment(),
        observer,
        executor,
        LocalityAwareMyopicScheduler(),
        available_operations=("bm25_retrieve", "invoke_model"),
    ).execute(task(), plan())

    assert result.completed
    assert set(result.state.node_status.values()) == {NodeStatus.DONE}
    assert executor.max_active == 2
    assert result.telemetry.max_parallelism == 2
    assert result.telemetry.parallel_overlap_ms > 0
    assert [item.scheduling_batch for item in result.records] == [0, 0, 1]
    assert result.records[-1].execution is not None
    assert result.records[-1].execution.deployment_id == "text"
