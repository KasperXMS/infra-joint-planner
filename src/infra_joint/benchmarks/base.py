from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.evaluation.evaluator import Evaluator, ExactChoiceEvaluator


class BenchmarkSettingKind(StrEnum):
    OFFICIAL_EQUIVALENT = "official_equivalent"
    DERIVED = "derived"


class TransformationRecord(ContractModel):
    benchmark_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    source_task_id: str = Field(min_length=1)
    transformation: str = Field(min_length=1)
    information_preserved: bool
    order_preserved: bool | None
    gold_independent: bool
    notes: str = ""


class ValidityAssessment(ContractModel):
    information_equivalent: bool
    query_equivalent: bool
    evaluator_equivalent: bool
    setting_kind: BenchmarkSettingKind
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def kind_matches_evidence(self) -> "ValidityAssessment":
        equivalent = (
            self.information_equivalent
            and self.query_equivalent
            and self.evaluator_equivalent
        )
        expected = (
            BenchmarkSettingKind.OFFICIAL_EQUIVALENT
            if equivalent
            else BenchmarkSettingKind.DERIVED
        )
        if self.setting_kind != expected:
            raise ValueError("setting_kind does not match equivalence evidence")
        return self


def assess_validity(
    transformations: tuple[TransformationRecord, ...],
    *,
    query_equivalent: bool,
    evaluator_equivalent: bool,
) -> ValidityAssessment:
    reasons: list[str] = []
    information_equivalent = all(
        record.information_preserved and record.gold_independent
        for record in transformations
    )
    if not information_equivalent:
        reasons.append("one or more transformations are lossy or gold-dependent")
    if not query_equivalent:
        reasons.append("adapted query differs from the official query semantics")
    if not evaluator_equivalent:
        reasons.append("adapted evaluator differs from the official evaluator")
    equivalent = information_equivalent and query_equivalent and evaluator_equivalent
    return ValidityAssessment(
        information_equivalent=information_equivalent,
        query_equivalent=query_equivalent,
        evaluator_equivalent=evaluator_equivalent,
        setting_kind=(
            BenchmarkSettingKind.OFFICIAL_EQUIVALENT
            if equivalent
            else BenchmarkSettingKind.DERIVED
        ),
        reasons=tuple(reasons),
    )


class AdaptedExecutionCase(ContractModel):
    task: TaskContract
    transformations: tuple[TransformationRecord, ...]
    validity: ValidityAssessment


class PrivateEvaluationSpec(Protocol):
    task_id: str
    evaluator_id: str

    def build_evaluator(self) -> Evaluator: ...


class PrivateChoiceEvaluation(ContractModel):
    task_id: str = Field(min_length=1)
    evaluator_id: str = Field(min_length=1)
    gold_answer: str = Field(min_length=1)

    def build_evaluator(self) -> Evaluator:
        return ExactChoiceEvaluator(self.gold_answer)


@dataclass(frozen=True, slots=True)
class AdaptationBundle:
    """Explicit split: only execution is allowed to enter Planner/Runtime state."""

    execution: AdaptedExecutionCase
    private_evaluation: PrivateEvaluationSpec


class BenchmarkAdapter[SampleT](Protocol):
    def adapt(self, sample: SampleT) -> AdaptationBundle: ...
