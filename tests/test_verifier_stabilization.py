"""Deterministic v2.1 checks against the frozen terminal mismatch pattern."""

from __future__ import annotations

from typing import Any

import pytest
from agents import Model
from agents.exceptions import MaxTurnsExceeded
from agents.items import ModelResponse
from test_cost_quotes import tool_response
from test_native_agents import benchmark_task

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import ExecutionRequirements, WorkflowGraphSnapshot
from infra_joint.control.verification import (
    VerificationContext,
    VerificationResponse,
    VerificationResult,
    VerifierActionView,
    VerifierBudgetView,
    VerifierObservation,
)
from infra_joint.control.verifier_stabilization import (
    BoundedProtocolVerifier,
    TerminalContractVerifier,
)
from infra_joint.core.task import OutputContract, OutputFormat


class CompleteVerifier:
    async def verify(self, context: VerificationContext) -> VerificationResponse:
        del context
        return VerificationResponse(
            result=VerificationResult(
                status="complete",
                failure_stage="none",
                reason="Candidate appears sufficient.",
                candidate_action_id="candidate-1",
            ),
            input_tokens=23,
            output_tokens=9,
        )


def context(candidate: str) -> VerificationContext:
    task = benchmark_task().model_copy(
        update={
            "output_contract": OutputContract(
                format=OutputFormat.CHOICE,
                choices=("A", "B", "C", "D"),
            )
        }
    )
    return VerificationContext(
        task=AgentTaskView.from_contract(task),
        workflow=WorkflowGraphSnapshot(version=1, nodes=(), edges=()),
        actions=(
            VerifierActionView(
                action_id="candidate-1",
                owner_agent_id="manager",
                action_type="model",
                operator="invoke_model",
                description="Synthesize a choice answer.",
                prompt="Choose a declared label.",
                requirements=ExecutionRequirements(),
            ),
        ),
        observations=(
            VerifierObservation(
                action_id="candidate-1",
                owner_agent_id="manager",
                succeeded=True,
                output={"text": candidate},
            ),
        ),
        produced_artifacts=(),
        phase="synthesis",
        remaining_budget=VerifierBudgetView(
            remaining_manager_turns=4,
            remaining_tool_model_calls=10,
            remaining_created_subagents=4,
            remaining_verifier_calls=4,
        ),
    )


@pytest.mark.asyncio
async def test_whitespace_choice_candidate_gets_synthesis_feedback() -> None:
    response = await TerminalContractVerifier(CompleteVerifier()).verify(
        context("A explanation without a formatting delimiter")
    )
    assert response.result.status == "ready_for_synthesis"
    assert response.input_tokens == 23
    assert response.output_tokens == 9


@pytest.mark.asyncio
async def test_valid_choice_candidate_keeps_independent_verdict() -> None:
    response = await TerminalContractVerifier(CompleteVerifier()).verify(context("A. Supported."))
    assert response.result.status == "complete"
    assert response.result.candidate_action_id == "candidate-1"


class SequenceVerifierModel(Model):
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.inputs: list[list[dict[str, Any]]] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        del args
        items = kwargs["input"]
        self.inputs.append(items)
        index = len(self.inputs)
        if index > 1:
            tool_outputs = [
                item["output"] for item in items if item.get("type") == "function_call_output"
            ]
            assert tool_outputs
            assert '"succeeded": false' in tool_outputs[-1]
        return tool_response(index, [("submit_verification", self.payloads[index - 1])])

    async def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("deterministic test does not stream")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "expected_code"),
    [
        (
            {
                "status": "complete",
                "failure_stage": "none",
                "reason": "Candidate appears sufficient.",
                "candidate_action_id": "candidate-1",
                "evidence_state_version": "1",
            },
            "schema_validation_failed",
        ),
        (
            {
                "status": "continue",
                "failure_stage": "none",
                "reason": "More evidence is needed.",
            },
            "semantic_validation_failed",
        ),
    ],
)
async def test_bounded_protocol_recovers_with_real_sdk(
    first: dict[str, Any], expected_code: str
) -> None:
    valid = {
        "status": "ready_for_synthesis",
        "failure_stage": "none",
        "reason": "Evidence is sufficient for synthesis.",
    }
    model = SequenceVerifierModel([first, valid])
    verifier = BoundedProtocolVerifier(model=model, max_attempts=2)
    response = await verifier.verify(context("A."))
    assert response.result.status == "ready_for_synthesis"
    assert len(model.inputs) == 2
    assert expected_code in model.inputs[1][-1]["output"]
    assert response.input_tokens == 40
    assert response.output_tokens == 20


@pytest.mark.asyncio
async def test_bounded_protocol_stops_after_two_invalid_calls() -> None:
    invalid = {
        "status": "complete",
        "failure_stage": "none",
        "reason": "Candidate appears sufficient.",
        "candidate_action_id": "candidate-1",
        "evidence_state_version": "1",
    }
    model = SequenceVerifierModel([invalid, invalid])
    with pytest.raises(MaxTurnsExceeded):
        await BoundedProtocolVerifier(model=model, max_attempts=2).verify(context("A."))
    assert len(model.inputs) == 2
