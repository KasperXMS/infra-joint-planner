"""Scripted interface checks; no provider, scheduler, or physical executor calls."""

from __future__ import annotations

import pytest
from test_harness_v2_workflow_state import _answer, _controller, _retrieve

from infra_joint.control.adaptation import KeepWorkflow, PatchWorkflow
from infra_joint.control.bounded_lookahead import BoundedLookahead
from infra_joint.control.contracts import LogicalObservation
from infra_joint.control.workflow import ReplacePendingAction, WorkflowDependency, WorkflowPatch
from infra_joint.control.workflow_state import InformationProvenance
from infra_joint.control.workflow_validation import WorkflowValidationError


def _edge() -> WorkflowDependency:
    return WorkflowDependency(
        dependency_type="artifact",
        producer_action_id="retrieve",
        consumer_action_id="answer",
        information_id="hits",
    )


def _patch(prompt: str = "Refine the answer.") -> PatchWorkflow:
    return PatchWorkflow(
        reason="new evidence",
        patch=WorkflowPatch(
            patch_id="refine-answer",
            reason="new evidence",
            edits=(
                ReplacePendingAction(action_id="answer", replacement=_answer(prompt)),
            ),
        ),
    )


def test_two_action_fragment_waits_for_dependency_and_preserves_prefix() -> None:
    controller = _controller()
    interface = BoundedLookahead(controller)
    plan = interface.propose(
        (_retrieve(), _answer()), (_edge(),), expected_version=0, terminal_action_id="answer"
    )
    assert plan.version == 1
    assert interface.ready_action_ids() == ("retrieve",)
    with pytest.raises(WorkflowValidationError, match="not ready"):
        interface.dispatch_ready("answer")
    interface.dispatch_ready("retrieve")
    assert interface.ready_action_ids() == ()
    with pytest.raises(WorkflowValidationError, match="quiescent"):
        interface.keep_or_patch(_patch(), expected_version=1)
    interface.settle(
        LogicalObservation(action_id="retrieve", owner_agent_id="manager", succeeded=True)
    )
    assert interface.ready_action_ids() == ("answer",)
    patched = interface.keep_or_patch(_patch(), expected_version=1)
    assert patched.version == 2
    assert patched.action_map()["retrieve"] == _retrieve()
    assert controller.execution.statuses["retrieve"] == "completed"
    assert interface.ready_action_ids() == ("answer",)
    interface.dispatch_ready("answer")
    interface.settle(
        LogicalObservation(action_id="answer", owner_agent_id="manager", succeeded=True)
    )
    assert controller.execution.statuses["answer"] == "completed"


def test_open_fragment_can_extend_and_seal_without_forced_patch() -> None:
    controller = _controller()
    interface = BoundedLookahead(controller)
    interface.propose((_retrieve(),), expected_version=0)
    with pytest.raises(WorkflowValidationError, match="open workflow"):
        interface.keep_or_patch(KeepWorkflow(reason="not sealed"), expected_version=1)
    interface.dispatch_ready("retrieve")
    interface.settle(
        LogicalObservation(action_id="retrieve", owner_agent_id="manager", succeeded=True)
    )
    interface.propose((_answer(),), (_edge(),), expected_version=1, terminal_action_id="answer")
    assert interface.ready_action_ids() == ("answer",)
    kept = interface.keep_or_patch(KeepWorkflow(reason="no adaptation needed"), expected_version=2)
    assert kept.version == 2
    assert controller.execution.statuses["retrieve"] == "completed"


def test_unknown_provenance_rejects_patch_and_fragment_cap_is_enforced() -> None:
    controller = _controller()
    interface = BoundedLookahead(controller, max_fragment_actions=2)
    with pytest.raises(WorkflowValidationError, match="one to three"):
        interface.propose((_retrieve(), _answer(), _answer("Other")), expected_version=0)
    interface.propose(
        (_retrieve(), _answer()), (_edge(),), expected_version=0, terminal_action_id="answer"
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
        interface.keep_or_patch(_patch(), expected_version=1)
    assert controller.plan.version == 1
