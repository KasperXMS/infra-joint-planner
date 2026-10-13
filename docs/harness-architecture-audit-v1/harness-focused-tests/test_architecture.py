"""Offline characterization tests for the architecture audit; no production edits."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
import test_native_agents as fixture  # noqa: E402

from infra_joint.control.contracts import (  # noqa: E402
    LogicalModelAction,
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
)
from infra_joint.control.gateway import RuntimeActionGateway  # noqa: E402
from infra_joint.control.physical import (  # noqa: E402
    PhysicalExecutionOutcome,
    PhysicalExecutionService,
)
from infra_joint.control.validation import SemanticActionValidator  # noqa: E402
from infra_joint.control.verification import VerificationResult  # noqa: E402
from infra_joint.core.state import InfrastructureState  # noqa: E402
from infra_joint.operators.catalog import build_operator_catalog  # noqa: E402


def _bm25(action_id: str, output_id: str) -> LogicalToolAction:
    return LogicalToolAction(
        action_id=action_id,
        owner_agent_id="manager",
        operator="bm25_retrieve",
        inputs=("source-0",),
        outputs=(
            LogicalOutput(
                artifact_id=output_id, semantic_type="retrieval_hits", media_type="application/json"
            ),
        ),
        arguments={
            "query": "evidence",
            "top_k": 2,
            "text_field": "text",
            "output_artifact_id": output_id,
        },
    )


class PartialPhysical(PhysicalExecutionService):
    """Exercise RuntimeActionGateway's real-service branch without hardware."""

    def __init__(self) -> None:
        self.success_done = asyncio.Event()
        self.external_effects: list[str] = []
        self.snapshot = InfrastructureState(
            agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now(UTC)
        )

    async def observe_infrastructure(self) -> InfrastructureState:
        return self.snapshot

    def prepare_batch(self, actions, infrastructure_snapshot, *, batch_id, expose_profile):
        return actions

    async def execute_prepared(self, action, shared_pre_frontier_state):
        if action.action_id == "fail":
            await self.success_done.wait()
            raise RuntimeError("synthetic transport interruption")
        self.external_effects.append(action.outputs[0].artifact_id)
        self.success_done.set()
        return PhysicalExecutionOutcome(
            observation=LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
            ),
            infrastructure_before=self.snapshot,
            infrastructure_after=self.snapshot,
        )


@pytest.mark.asyncio
async def test_parallel_gateway_exception_loses_successful_sibling_commit():
    task = fixture.benchmark_task()
    physical = PartialPhysical()
    validator = SemanticActionValidator(task, build_operator_catalog(), ("bm25_retrieve",))
    gateway = RuntimeActionGateway(validator, physical)
    actions = (_bm25("success", "hits-ok"), _bm25("fail", "hits-fail"))
    with pytest.raises(RuntimeError, match="synthetic transport interruption"):
        await gateway.execute_batch(actions, expose_profile=False)
    assert physical.external_effects == ["hits-ok"]
    assert "hits-ok" not in validator.known_artifacts
    with pytest.raises(ValueError, match="already exist"):
        gateway.validate_batch((actions[0],))


@pytest.mark.asyncio
async def test_verifier_complete_has_no_candidate_binding_and_selects_latest():
    class TwoAnswers(fixture.FakePhysicalService):
        async def execute(self, action, *, expose_profile):
            outcome = await super().execute(action, expose_profile=expose_profile)
            text = "A" if action.action_id.endswith("first") else "B"
            return outcome.model_copy(
                update={
                    "observation": outcome.observation.model_copy(update={"output": {"text": text}})
                }
            )

    verdict = VerificationResult(
        status="complete", failure_stage="none", reason="Candidate first (A) is sufficient"
    )
    verifier = fixture.FakeVerifier((verdict,))
    task = fixture.benchmark_task()
    runtime, gateway = fixture.runtime_and_gateway(
        task, TwoAnswers(), ("invoke_model",), verifier=verifier
    )

    async def behavior(agent, _input, context, hooks):
        await fixture.reasoning_start(hooks, context, agent)
        model_tool = fixture.tool(agent, "invoke_model")
        results = []
        for call_id in ("first", "second"):
            result = await model_tool.on_invoke_tool(
                fixture.tool_context(agent, context, call_id),
                json.dumps({"inputs": ["source-0"], "arguments": {"prompt": "Return A or B"}}),
            )
            results.append((model_tool, result))
        await fixture.reasoning_end(hooks, context, agent)
        decision, _ = await fixture.resolve_tool_batch(agent, tuple(results))
        return str(decision.final_output)

    fixture.FakeRunner.behavior = behavior
    result = await runtime.run(task, gateway)
    assert result.final_answer == "B"
    assert result.terminal_action_id.endswith("second")
    assert [item.output["text"] for item in verifier.contexts[0].observations] == ["A", "B"]


def test_execution_graph_omits_inline_observation_dependency():
    from infra_joint.control.graph import ExecutionGrownGraph

    graph = ExecutionGrownGraph()
    first = _bm25("retrieve", "hits")
    second = LogicalModelAction(
        action_id="followup",
        owner_agent_id="manager",
        inputs=("source-0",),
        prompt="Use the inline excerpt A copied from retrieve's observation.",
    )
    graph.add((first,))
    graph.mark_running((first.action_id,))
    graph.mark_finished((first.action_id,), ())
    graph.add((second,))
    assert not any(
        edge.producer_action_id == "retrieve" and edge.consumer_action_id == "followup"
        for edge in graph.snapshot().edges
    )


@pytest.mark.asyncio
async def test_installed_sdk_agent_tool_failure_is_plain_text(monkeypatch):
    import agents
    from agents.tool_context import ToolContext

    async def fail_run(*args, **kwargs):
        raise RuntimeError("nested failure sentinel")

    monkeypatch.setattr(agents.Runner, "run", fail_run)
    tool = agents.Agent(name="child", instructions="Return a result").as_tool(
        tool_name="child", tool_description="test"
    )
    output = await tool.on_invoke_tool(
        ToolContext(
            context=None, tool_name="child", tool_call_id="c1", tool_arguments='{"input":"hello"}'
        ),
        '{"input":"hello"}',
    )
    assert isinstance(output, str)
    assert "nested failure sentinel" in output
