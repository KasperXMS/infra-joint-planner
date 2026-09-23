import json

import pytest

from infra_joint.benchmarks.multimodalqa import (
    MultiModalQAAdapter,
    MultiModalQAImage,
    MultiModalQAOfficialEvaluator,
    MultiModalQASample,
    MultiModalQATable,
    MultiModalQAText,
    PrivateMultiModalQAEvaluation,
)


def _sample() -> MultiModalQASample:
    return MultiModalQASample(
        qid="qid-1",
        question="What is shown?",
        question_type="Compose(ImageQ,TextQ)",
        modalities=("image", "text"),
        texts=(MultiModalQAText(id="t1", title="T", url="u", text="public"),),
        table=MultiModalQATable(id="table-1", payload={"rows": [["public"]]}),
        images=(
            MultiModalQAImage(
                id="i1", filename="i1.jpg", media_type="image/jpeg", content=b"jpeg"
            ),
        ),
        answers=("secret-gold",),
        supporting_context=({"doc_id": "secret-support"},),
        intermediate_answers=("secret-intermediate",),
    )


def test_adapter_keeps_private_annotations_out_of_execution() -> None:
    bundle = MultiModalQAAdapter("revision").adapt(_sample())
    public = json.dumps(bundle.execution.model_dump(mode="json")) + "".join(
        item.content.decode("utf-8", errors="ignore") for item in bundle.prepared_artifacts
    )
    assert "secret-gold" not in public
    assert "secret-support" not in public
    assert "secret-intermediate" not in public
    private = bundle.private_evaluation
    assert isinstance(private, PrivateMultiModalQAEvaluation)
    assert private.gold_answers == ("secret-gold",)


@pytest.mark.asyncio
async def test_official_evaluator_reports_list_metrics() -> None:
    bundle = MultiModalQAAdapter("revision").adapt(_sample())
    result = await MultiModalQAOfficialEvaluator(("The Boat",)).evaluate(
        bundle.execution.task, "boat"
    )
    assert result.format_valid
    assert result.benchmark_score == 1.0
    assert json.loads(result.details) == {"list_em": 1.0, "list_f1": 1.0}


@pytest.mark.asyncio
async def test_official_evaluator_matches_number_words_and_alternative_references() -> None:
    task = MultiModalQAAdapter("revision").adapt(_sample()).execution.task
    numeric = await MultiModalQAOfficialEvaluator(("8",)).evaluate(task, "eight")
    alternative = await MultiModalQAOfficialEvaluator(("wrong", "The Boat")).evaluate(
        task, "boat"
    )

    assert numeric.benchmark_score == 1.0
    assert json.loads(numeric.details) == {"list_em": 1.0, "list_f1": 1.0}
    assert alternative.benchmark_score == 1.0
    assert json.loads(alternative.details) == {"list_em": 1.0, "list_f1": 1.0}
