import pytest

from infra_joint.benchmarks.multihop_rag import MultiHopOfficialTokenOverlapEvaluator
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract
from infra_joint.evaluation.yesno_audit import audit_yesno, canonical_yesno


@pytest.mark.parametrize("answer", ["Yes", "Yes.", "Yes,", "**Yes.**", "YES:", "Yes because"])
def test_explicit_affirmative_prefix(answer: str) -> None:
    assert canonical_yesno(answer) == "yes"
    assert audit_yesno(answer, reference="yes").canonical_score == 1


@pytest.mark.parametrize("answer", ["No", "No.", "**No.**", "NO: explanation"])
def test_explicit_negative_prefix(answer: str) -> None:
    assert canonical_yesno(answer) == "no"
    assert audit_yesno(answer, reference="yes").canonical_score == 0


@pytest.mark.parametrize(
    "answer",
    [
        None,
        "",
        "The evidence suggests yes",
        "Answer: Yes",
        "Yes or no",
        "Yes/no",
        "Yes and no",
        "Yes, no",
        "No; yes",
        "Yesterday",
        "Nobody",
        "Yes?",
        "**Yes",
        "**Yes or no**",
        "Maybe yes",
    ],
)
def test_ambiguous_or_nonleading_labels_fail_closed(answer: str | None) -> None:
    assert canonical_yesno(answer) == "unresolved"
    assert audit_yesno(answer, reference="yes").canonical_score is None


def test_extraction_is_reference_independent_and_never_searches_body() -> None:
    answer = "No. The explanation includes the word Yes."
    assert audit_yesno(answer, reference="yes").canonical_yesno == "no"
    assert audit_yesno(answer, reference="no").canonical_yesno == "no"
    with pytest.raises(ValueError, match="canonical yes/no reference"):
        audit_yesno("Yes", reference="gold explanation saying yes")


@pytest.mark.asyncio
@pytest.mark.parametrize("answer,expected", [("Yes", 1), ("Yes.", 0), ("Yes,", 0), ("**Yes.**", 0)])
async def test_original_evaluator_is_unchanged(answer: str, expected: int) -> None:
    task = TaskContract(
        task_id="synthetic",
        benchmark_id="synthetic",
        objective="Synthetic yes/no question",
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private",
    )
    original = await MultiHopOfficialTokenOverlapEvaluator("Yes").evaluate(task, answer)
    assert original.benchmark_score == expected
    assert audit_yesno(answer, reference="yes").canonical_score == 1
