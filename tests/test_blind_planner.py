import json

import pytest

from infra_joint.core.action import (
    JointAction,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.finalize import ContractAwareFinalizer
from infra_joint.planning.planner import (
    BlindPlannerContext,
    LLMBlindPlanner,
    PlannerDecisionError,
    PlannerObservation,
)
from infra_joint.runtime.executor import ExecutionResult


class CapturingBackend:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def task() -> TaskContract:
    return TaskContract(
        task_id="blind-1",
        benchmark_id="synthetic",
        objective="Find the answer.",
        artifacts=(
            ArtifactSpec(
                artifact_id="document",
                logical_type="text",
                media_type="text/plain",
                size_bytes=12,
                source_ref="http://SECRET-SOURCE-HOST/document",
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-evaluator",
    )


def context() -> BlindPlannerContext:
    prior = JointAction(
        semantic=SemanticAction(operator="read_artifact", inputs=("document",)),
        physical=PhysicalDecision(
            policy=PhysicalPolicy.TARGET_AGENT,
            target_agent_id="SECRET-PRIOR-WORKER",
        ),
    )
    execution = ExecutionResult(
        operator="read_artifact",
        agent_ids=("SECRET-RESULT-WORKER",),
        deployment_id="SECRET-DEPLOYMENT",
        output={"text": "logical evidence"},
    )
    return BlindPlannerContext(
        task=task(),
        decisions=(prior,),
        observations=(PlannerObservation.from_execution(execution),),
        remaining_steps=2,
    )


@pytest.mark.asyncio
async def test_llm_blind_planner_emits_validated_auto_action_without_physical_leakage() -> None:
    backend = CapturingBackend(
        json.dumps(
            {
                "decision_type": "action",
                "operator": "invoke_model",
                "inputs": [],
                "arguments": {"prompt": "Answer from the evidence."},
            }
        )
    )
    planner = LLMBlindPlanner(backend, build_operator_catalog())

    decision = await planner.decide(context())

    assert isinstance(decision, JointAction)
    assert decision.semantic.operator == "invoke_model"
    assert decision.physical == PhysicalDecision(policy=PhysicalPolicy.AUTO)
    prompt = backend.prompts[0]
    assert "filter_records" in prompt
    assert "bm25_retrieve" in prompt
    assert "logical evidence" in prompt
    assert "SECRET-SOURCE-HOST" not in prompt
    assert "SECRET-PRIOR-WORKER" not in prompt
    assert "SECRET-RESULT-WORKER" not in prompt
    assert "SECRET-DEPLOYMENT" not in prompt
    assert "private-evaluator" not in prompt


@pytest.mark.asyncio
async def test_llm_blind_planner_accepts_finish_decision() -> None:
    backend = CapturingBackend('{"decision_type":"finish","reason":"evidence is sufficient"}')
    planner = LLMBlindPlanner(backend, build_operator_catalog())

    decision = await planner.decide(context())

    assert decision.decision_type == "finish"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response, message",
    (
        ("```json\n{}\n```", "valid JSON decision"),
        (
            '{"decision_type":"action","operator":"missing","inputs":[],"arguments":{}}',
            "unknown operator",
        ),
        (
            '{"decision_type":"action","operator":"invoke_model","inputs":[],"arguments":{}}',
            "required property",
        ),
        (
            '{"decision_type":"action","operator":"invoke_model",'
            '"inputs":[],"arguments":{"prompt":"x"},"physical":{"policy":"auto"}}',
            "valid JSON decision",
        ),
    ),
)
async def test_llm_blind_planner_rejects_invalid_decisions(response: str, message: str) -> None:
    planner = LLMBlindPlanner(CapturingBackend(response), build_operator_catalog())

    with pytest.raises(PlannerDecisionError, match=message):
        await planner.decide(context())


@pytest.mark.asyncio
async def test_contract_finalizer_is_tool_free_and_preserves_exact_model_text() -> None:
    backend = CapturingBackend("A")
    finalizer = ContractAwareFinalizer(backend)
    decision = context().decisions[0]
    observation = ExecutionResult(
        operator="invoke_model",
        agent_ids=("SECRET-FINAL-WORKER",),
        deployment_id="SECRET-FINAL-DEPLOYMENT",
        output={"text": "Evidence supports A."},
    )

    answer = await finalizer.finalize(task(), (decision,), (observation,))

    assert answer == "A"
    prompt = backend.prompts[0]
    assert 'exactly one of these canonical choice labels: ["A","B"]' in prompt
    assert "Evidence supports A." in prompt
    assert "available_operators" not in prompt
    assert "SECRET-SOURCE-HOST" not in prompt
    assert "SECRET-FINAL-WORKER" not in prompt
    assert "SECRET-FINAL-DEPLOYMENT" not in prompt


@pytest.mark.asyncio
async def test_contract_finalizer_does_not_repair_noncanonical_output() -> None:
    backend = CapturingBackend("The answer is A")
    finalizer = ContractAwareFinalizer(backend)

    answer = await finalizer.finalize(task(), (), ())

    assert answer == "The answer is A"
