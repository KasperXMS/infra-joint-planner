import json

import pytest
from pydantic import ValidationError

from infra_joint.benchmarks.base import BenchmarkSettingKind
from infra_joint.benchmarks.video_mme import (
    FixedIntervalSegmentation,
    SourceArtifact,
    VideoChunk,
    VideoMMEAdapter,
    VideoMMEOption,
    VideoMMESample,
)
from infra_joint.core.task import OutputFormat


def sample() -> VideoMMESample:
    return VideoMMESample(
        sample_id="795-3",
        video=SourceArtifact(
            artifact_id="video-795",
            logical_type="video",
            media_type="video/mp4",
            size_bytes=123456,
            source_ref="dataset/videos/795.mp4",
        ),
        question="What happens at the end?",
        options=(
            VideoMMEOption(label="A", text="The person sits down"),
            VideoMMEOption(label="B", text="The person leaves"),
            VideoMMEOption(label="C", text="The camera stops"),
            VideoMMEOption(label="D", text="Nothing changes"),
        ),
        answer_label="B",
        additional_artifacts=(
            SourceArtifact(
                artifact_id="subtitle-795",
                logical_type="subtitle",
                media_type="text/vtt",
                size_bytes=500,
                source_ref="dataset/subtitles/795.vtt",
            ),
        ),
    )


def test_video_mme_adapter_preserves_inputs_and_hides_gold() -> None:
    bundle = VideoMMEAdapter(source_revision="video-mme@sha256:test").adapt(sample())
    task = bundle.execution.task

    assert [artifact.artifact_id for artifact in task.artifacts] == [
        "video-795",
        "subtitle-795",
    ]
    assert task.artifacts[0].size_bytes == 123456
    assert task.output_contract.format == OutputFormat.CHOICE
    assert task.output_contract.choices == ("A", "B", "C", "D")
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.OFFICIAL_EQUIVALENT
    serialized_task = task.model_dump_json()
    assert "answer_label" not in serialized_task
    assert "gold_answer" not in serialized_task
    assert json.loads(serialized_task)["benchmark_id"] == "video_mme"

    assert bundle.private_evaluation.task_id == task.task_id


@pytest.mark.asyncio
async def test_private_video_mme_evaluator_uses_canonical_choice() -> None:
    bundle = VideoMMEAdapter(source_revision="revision").adapt(sample())
    evaluator = bundle.private_evaluation.build_evaluator()

    correct = await evaluator.evaluate(bundle.execution.task, "B")
    verbose = await evaluator.evaluate(bundle.execution.task, "B because the person leaves")

    assert correct.benchmark_score == 1.0
    assert verbose.benchmark_score == 0.0
    assert not verbose.format_valid


def test_video_mme_objective_has_no_workflow_hint() -> None:
    objective = VideoMMEAdapter(source_revision="revision").adapt(sample()).execution.task.objective

    assert objective.startswith("What happens at the end?")
    assert "B. The person leaves" in objective
    assert "sample frames" not in objective.casefold()
    assert "preprocessing" not in objective.casefold()


def test_video_mme_rejects_invalid_gold_label() -> None:
    data = sample().model_dump()
    data["answer_label"] = "Z"
    with pytest.raises(ValidationError, match="official option"):
        VideoMMESample.model_validate(data)


def segmentation(*, information_preserved: bool = True) -> FixedIntervalSegmentation:
    return FixedIntervalSegmentation(
        source_artifact_id="video-795",
        video_duration_seconds=25,
        interval_seconds=10,
        information_preserved=information_preserved,
        chunks=(
            VideoChunk(
                artifact=SourceArtifact(
                    artifact_id="video-795/chunk-0",
                    logical_type="video_chunk",
                    media_type="video/mp4",
                    size_bytes=40,
                    source_ref="prepared/795-0.mp4",
                ),
                start_seconds=0,
                end_seconds=10,
            ),
            VideoChunk(
                artifact=SourceArtifact(
                    artifact_id="video-795/chunk-1",
                    logical_type="video_chunk",
                    media_type="video/mp4",
                    size_bytes=40,
                    source_ref="prepared/795-1.mp4",
                ),
                start_seconds=10,
                end_seconds=20,
            ),
            VideoChunk(
                artifact=SourceArtifact(
                    artifact_id="video-795/chunk-2",
                    logical_type="video_chunk",
                    media_type="video/mp4",
                    size_bytes=20,
                    source_ref="prepared/795-2.mp4",
                ),
                start_seconds=20,
                end_seconds=25,
            ),
        ),
    )


def test_fixed_interval_segmentation_exposes_every_chunk_in_order() -> None:
    bundle = VideoMMEAdapter(source_revision="revision").adapt(sample(), segmentation())

    assert [artifact.artifact_id for artifact in bundle.execution.task.artifacts] == [
        "video-795/chunk-0",
        "video-795/chunk-1",
        "video-795/chunk-2",
        "subtitle-795",
    ]
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.OFFICIAL_EQUIVALENT
    assert bundle.execution.transformations[0].gold_independent


def test_lossy_segmentation_is_explicitly_derived() -> None:
    bundle = VideoMMEAdapter(source_revision="revision").adapt(
        sample(), segmentation(information_preserved=False)
    )

    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.DERIVED


def test_segmentation_manifest_rejects_coverage_gap() -> None:
    data = segmentation().model_dump()
    data["chunks"][1]["start_seconds"] = 11

    with pytest.raises(ValidationError, match="contiguous fixed intervals"):
        FixedIntervalSegmentation.model_validate(data)
