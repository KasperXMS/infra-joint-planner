import json
from typing import Protocol

from infra_joint.core.action import JointDecision
from infra_joint.core.task import OutputFormat, TaskContract
from infra_joint.planning.planner import (
    CompletionBackend,
    PlannerObservation,
    logical_decision_payload,
    logical_task_payload,
)
from infra_joint.runtime.executor import ExecutionResult


class Finalizer(Protocol):
    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str: ...


class LastModelOutputFinalizer:
    """M1 finalizer that uses existing evidence and cannot call an operator."""

    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str:
        del task, decisions
        if not observations:
            return ""
        text = observations[-1].output.get("text")
        return text if isinstance(text, str) else ""


class ContractAwareFinalizer:
    """Dedicated tool-free model call that preserves the model's exact final text."""

    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend

    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str:
        prompt = self.render_prompt(task, decisions, observations)
        return await self._backend.complete(prompt)

    @staticmethod
    def render_prompt(
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str:
        logical_observations = [
            PlannerObservation.from_execution(observation).model_dump(mode="json")
            for observation in observations
        ]
        payload = {
            "task": logical_task_payload(task),
            "decision_history": [logical_decision_payload(decision) for decision in decisions],
            "observations": logical_observations,
        }
        contract_instruction = ContractAwareFinalizer._contract_instruction(task)
        return "\n".join(
            (
                "Produce the final benchmark answer using only the supplied logical evidence.",
                "You cannot call tools or request more evidence.",
                contract_instruction,
                "Return only the final answer with no Markdown, explanation, or wrapper.",
                "State:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )

    @staticmethod
    def _contract_instruction(task: TaskContract) -> str:
        contract = task.output_contract
        if contract.format == OutputFormat.CHOICE:
            choices = json.dumps(contract.choices, ensure_ascii=False, separators=(",", ":"))
            return f"Output exactly one of these canonical choice labels: {choices}."
        if contract.format == OutputFormat.SHORT_TEXT:
            return "Output one concise plain-text answer."
        schema = json.dumps(
            contract.schema_definition,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return f"Output exactly one JSON value satisfying this JSON Schema: {schema}."
