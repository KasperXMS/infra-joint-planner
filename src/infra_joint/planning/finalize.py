import json
from typing import Protocol

from infra_joint.core.action import JointDecision
from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputFormat, TaskContract
from infra_joint.planning.planner import (
    CompletionBackend,
    PlannerObservation,
    logical_decision_payload,
    logical_task_payload,
)
from infra_joint.runtime.executor import ExecutionResult
from infra_joint.worker.model_backend import ModelCallTelemetry, ModelRequest


class FinalizationOutcome(ContractModel):
    answer: str
    model_telemetry: ModelCallTelemetry | None = None


class Finalizer(Protocol):
    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> FinalizationOutcome: ...


class LastModelOutputFinalizer:
    """M1 finalizer that uses existing evidence and cannot call an operator."""

    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> FinalizationOutcome:
        del task, decisions
        if not observations:
            return FinalizationOutcome(answer="")
        text = observations[-1].output.get("text")
        return FinalizationOutcome(answer=text if isinstance(text, str) else "")


class ContractAwareFinalizer:
    """Dedicated tool-free model call that preserves the model's exact final text."""

    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend

    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> FinalizationOutcome:
        prompt = self.render_prompt(task, decisions, observations)
        completion = await self._backend.invoke(ModelRequest(prompt=prompt))
        return FinalizationOutcome(
            answer=completion.text,
            model_telemetry=completion.telemetry,
        )

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
            return (
                "Output only the shortest answer span that directly answers the question; "
                "omit explanation and trailing punctuation."
            )
        schema = json.dumps(
            contract.schema_definition,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return f"Output exactly one JSON value satisfying this JSON Schema: {schema}."
