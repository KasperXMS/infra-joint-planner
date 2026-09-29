from __future__ import annotations

import importlib
import json
from collections.abc import Iterable
from typing import Any, Protocol, cast

from infra_joint.control.contracts import (
    ManagerContext,
    ManagerDecision,
    SubagentCall,
)
from infra_joint.control.loop import ManagerPolicy, SubagentPolicyFactory
from infra_joint.core.base import ContractModel
from infra_joint.operators.registry import OperatorRegistry


class _AgentConstructor(Protocol):
    def __call__(self, **kwargs: Any) -> object: ...


class _RunnerType(Protocol):
    @staticmethod
    async def run(agent: object, input: str) -> object: ...


class _DecisionEnvelope(ContractModel):
    decision: ManagerDecision


class OpenAIAgentsManagerPolicy:
    """Optional OpenAI Agents SDK policy over the substrate-neutral contracts.

    The SDK owns semantic turn-taking only. It returns logical decisions; every
    executable primitive is still validated and dispatched by ``ActionGateway``.
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str,
        registry: OperatorRegistry,
        available_operations: Iterable[str],
    ) -> None:
        self._name = name
        self._instructions = instructions
        self._model = model
        allowed = frozenset(available_operations)
        self._tools = tuple(
            spec.model_dump(mode="json")
            for operator_id, spec in sorted(registry.specs().items())
            if operator_id in allowed
        )

    async def decide(self, context: ManagerContext) -> ManagerDecision:
        agent_constructor, runner = _load_agents_sdk()
        agent = agent_constructor(
            name=self._name,
            instructions=self._system_instructions(),
            model=self._model,
            output_type=_DecisionEnvelope,
        )
        result = await runner.run(agent, input=self._input(context))
        output = getattr(result, "final_output", None)
        envelope = (
            output
            if isinstance(output, _DecisionEnvelope)
            else _DecisionEnvelope.model_validate(output)
        )
        return envelope.decision

    def _system_instructions(self) -> str:
        return (
            self._instructions
            + "\nYou are a persistent manager or bounded specialist. Decide only the next "
            "logical step after inspecting observations; never predict a complete future DAG. "
            "Use only the finite operator contracts supplied in the input. Model work must use "
            "LogicalModelAction requirements, never a deployment/model instance/worker/device/IP/"
            "route/placement. Finish only by citing your own successful model action. A manager "
            "may create bounded specialists as subagent_calls and retains final-answer ownership."
        )

    def _input(self, context: ManagerContext) -> str:
        payload = {
            "context": context.model_dump(mode="json"),
            "finite_operator_contracts": self._tools,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class OpenAIAgentsSubagentFactory(SubagentPolicyFactory):
    """Create bounded SDK specialists that return results to the manager as tools."""

    def __init__(
        self,
        model: str,
        registry: OperatorRegistry,
        available_operations: Iterable[str],
    ) -> None:
        self._model = model
        self._registry = registry
        self._available_operations = tuple(available_operations)

    def create(self, call: SubagentCall) -> ManagerPolicy:
        return OpenAIAgentsManagerPolicy(
            name=call.agent.logical_agent_id,
            instructions=(
                f"Role: {call.agent.role}\nObjective: {call.agent.objective}\n"
                f"Manager instruction: {call.instruction}"
            ),
            model=self._model,
            registry=self._registry,
            available_operations=self._available_operations,
        )


def agents_sdk_available() -> bool:
    try:
        importlib.import_module("agents")
    except ImportError:
        return False
    return True


def _load_agents_sdk() -> tuple[_AgentConstructor, _RunnerType]:
    try:
        module = importlib.import_module("agents")
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed; install the project's 'agents' extra"
        ) from exc
    constructor = cast(_AgentConstructor, module.__dict__["Agent"])
    runner = cast(_RunnerType, module.__dict__["Runner"])
    return constructor, runner
