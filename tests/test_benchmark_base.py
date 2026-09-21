import pytest
from pydantic import ValidationError

from infra_joint.benchmarks.base import (
    BenchmarkSettingKind,
    TransformationRecord,
    ValidityAssessment,
    assess_validity,
)


def test_validity_gate_marks_lossy_adaptation_as_derived() -> None:
    record = TransformationRecord(
        benchmark_id="benchmark",
        source_revision="revision",
        source_task_id="task",
        transformation="top_30_candidates",
        information_preserved=False,
        order_preserved=None,
        gold_independent=True,
    )

    assessment = assess_validity(
        (record,), query_equivalent=True, evaluator_equivalent=True
    )

    assert assessment.setting_kind == BenchmarkSettingKind.DERIVED
    assert not assessment.information_equivalent
    assert assessment.reasons


def test_validity_kind_cannot_contradict_evidence() -> None:
    with pytest.raises(ValidationError, match="does not match equivalence evidence"):
        ValidityAssessment(
            information_equivalent=False,
            query_equivalent=True,
            evaluator_equivalent=True,
            setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
        )
