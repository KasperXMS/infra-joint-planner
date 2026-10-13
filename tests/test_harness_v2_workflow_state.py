from __future__ import annotations

import pytest

from infra_joint.control.adaptation import KeepWorkflow, PatchWorkflow
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import (
    LogicalModelAction,
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
)
from infra_joint.control.workflow import (
    OpenSemanticWorkflowPlan,
    RemovePendingAction,
    ReplacePendingAction,
    WorkflowDependency,
    WorkflowPatch,
)
from infra_joint.control.workflow_state import (
    InformationProvenance,
    VersionedPendingWorkflow,
)
from infra_joint.control.workflow_validation import WorkflowValidationError
from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)
from infra_joint.operators.catalog import build_operator_catalog


def _task() -> TaskContract:
    return TaskContract(
        task_id="workflow-v2",
        benchmark_id="synthetic",
        objective="Find answer.",
        artifacts=(
            ArtifactSpec(
                artifact_id="raw",
                logical_type="records",
                media_type="application/json",
                size_bytes=1000,
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={"text": "string"},
                    text_field="text",
                    record_count=2,
                    max_record_bytes=100,
                ),
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private",
    )


def _controller() -> VersionedPendingWorkflow:
    registry = build_operator_catalog()
    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="worker", device="gpu", capabilities=frozenset({"model"})),),
        deployments=(
            DeploymentSpec(
                deployment_id="model",
                agent_id="worker",
                model_id="test",
                context_window=32768,
                reserved_output_tokens=64,
            ),
        ),
    )
    capabilities = build_static_capability_contract(
        environment, registry, ("bm25_retrieve", "invoke_model")
    )
    return VersionedPendingWorkflow("workflow-v2", _task(), capabilities, registry)


def _retrieve() -> LogicalToolAction:
    return LogicalToolAction(
        action_id="retrieve",
        owner_agent_id="manager",
        operator="bm25_retrieve",
        inputs=("raw",),
        outputs=(
            LogicalOutput(
                artifact_id="hits", semantic_type="retrieval_hits", media_type="application/json"
            ),
        ),
        arguments={
            "query": "answer",
            "top_k": 2,
            "text_field": "text",
            "output_artifact_id": "hits",
        },
    )


def _answer(prompt: str = "Answer from hits.") -> LogicalModelAction:
    return LogicalModelAction(
        action_id="answer", owner_agent_id="manager", inputs=("hits",), prompt=prompt
    )


def _seal(controller: VersionedPendingWorkflow) -> None:
    controller.append_fragment((_retrieve(),), expected_version=0)
    controller.append_fragment(
        (_answer(),),
        (
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="retrieve",
                consumer_action_id="answer",
                information_id="hits",
            ),
        ),
        expected_version=1,
        terminal_action_id="answer",
    )


def test_incremental_fragments_hold_real_pending_plan_and_lock_completed_prefix() -> None:
    controller = _controller()
    first = controller.append_fragment((_retrieve(),), expected_version=0)
    assert isinstance(first, OpenSemanticWorkflowPlan)
    assert controller.execution.statuses == {"retrieve": "pending"}
    controller.reserve("retrieve")
    controller.start("retrieve")
    controller.settle(
        LogicalObservation(action_id="retrieve", owner_agent_id="manager", succeeded=True)
    )
    assert any(
        item.source_kind == "tool_observation" and item.producer_action_id == "retrieve"
        for item in controller.provenance.entries
    )
    sealed = controller.append_fragment(
        (_answer(),),
        (
            WorkflowDependency(
                dependency_type="artifact",
                producer_action_id="retrieve",
                consumer_action_id="answer",
                information_id="hits",
            ),
        ),
        expected_version=1,
        terminal_action_id="answer",
    )
    assert sealed.version == 2
    assert controller.execution.statuses == {"retrieve": "completed", "answer": "pending"}
    patch = WorkflowPatch(
        patch_id="refine-answer",
        reason="clarify output",
        edits=(
            ReplacePendingAction(
                action_id="answer", replacement=_answer("Give a short supported answer.")
            ),
        ),
    )
    changed = controller.keep_or_patch(
        PatchWorkflow(reason="refine", patch=patch), expected_version=2
    )
    assert changed.version == 3
    assert changed.action_map()["retrieve"] == _retrieve()
    assert controller.execution.statuses["retrieve"] == "completed"
    assert controller.transitions[-1].patch == patch
    with pytest.raises(WorkflowValidationError, match="stale"):
        controller.keep_or_patch(KeepWorkflow(reason="old version"), expected_version=2)
    with pytest.raises(WorkflowValidationError):
        controller.keep_or_patch(
            PatchWorkflow(
                reason="illegal removal",
                patch=WorkflowPatch(
                    patch_id="remove-prefix",
                    reason="illegal",
                    edits=(RemovePendingAction(action_id="retrieve"),),
                ),
            ),
            expected_version=3,
        )


def test_patch_requires_quiescent_frontier_and_known_rewrite_provenance() -> None:
    controller = _controller()
    _seal(controller)
    patch = WorkflowPatch(
        patch_id="refine",
        reason="new wording",
        edits=(
            ReplacePendingAction(
                action_id="answer",
                replacement=_answer("New wording."),
            ),
        ),
    )
    controller.reserve("retrieve")
    with pytest.raises(WorkflowValidationError, match="quiescent"):
        controller.keep_or_patch(PatchWorkflow(reason="refine", patch=patch), expected_version=2)
    controller.start("retrieve")
    controller.settle(
        LogicalObservation(action_id="retrieve", owner_agent_id="manager", succeeded=True)
    )
    controller.record_provenance(
        InformationProvenance(
            information_id="unparsed-manager-text",
            source_kind="manager_consumption",
            relation="unknown",
            consumer_action_id="answer",
        )
    )
    with pytest.raises(WorkflowValidationError, match="provenance"):
        controller.keep_or_patch(PatchWorkflow(reason="refine", patch=patch), expected_version=2)
    assert controller.plan.version == 2  # rejected transaction changed nothing


def test_fragment_with_generated_input_requires_formal_artifact_edge() -> None:
    controller = _controller()
    controller.append_fragment((_retrieve(),), expected_version=0)
    with pytest.raises(WorkflowValidationError, match="artifact dependency"):
        controller.append_fragment((_answer(),), expected_version=1, terminal_action_id="answer")
    assert controller.plan.version == 1
    assert controller.execution.statuses == {"retrieve": "pending"}
