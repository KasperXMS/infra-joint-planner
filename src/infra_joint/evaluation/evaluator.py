from typing import Protocol

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputFormat, TaskContract


class EvaluationResult(ContractModel):
    format_valid: bool
    benchmark_score: float = Field(ge=0.0, le=1.0)
    details: str = ""


class Evaluator(Protocol):
    async def evaluate(self, task: TaskContract, answer: str) -> EvaluationResult: ...


class ExactChoiceEvaluator:
    """Strict evaluator whose gold answer remains encapsulated outside graph state."""

    def __init__(self, gold_answer: str) -> None:
        self._gold_answer = gold_answer

    async def evaluate(self, task: TaskContract, answer: str) -> EvaluationResult:
        contract = task.output_contract
        if contract.format != OutputFormat.CHOICE or contract.choices is None:
            return EvaluationResult(
                format_valid=False,
                benchmark_score=0.0,
                details="task does not declare a choice output contract",
            )
        format_valid = answer in contract.choices
        return EvaluationResult(
            format_valid=format_valid,
            benchmark_score=float(format_valid and answer == self._gold_answer),
        )
