from typing import Literal

from pydantic import Field, field_validator, model_validator

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PrivateChoiceEvaluation,
    TransformationRecord,
    assess_validity,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import (
    ArtifactContentSchema,
    ArtifactSpec,
    OutputContract,
    OutputFormat,
    TaskContract,
)

VIDEO_MME_BENCHMARK_ID = "video_mme"
VIDEO_MME_EVALUATOR_ID = "video_mme_exact_choice_v1"


class SourceArtifact(ContractModel):
    artifact_id: str = Field(min_length=1)
    logical_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    source_ref: str = Field(min_length=1)
    content_schema: ArtifactContentSchema | None = None


class VideoMMEOption(ContractModel):
    label: str = Field(min_length=1)
    text: str = Field(min_length=1)


class VideoMMESample(ContractModel):
    sample_id: str = Field(min_length=1)
    video: SourceArtifact
    question: str = Field(min_length=1)
    options: tuple[VideoMMEOption, ...] = Field(min_length=2)
    answer_label: str = Field(min_length=1)
    additional_artifacts: tuple[SourceArtifact, ...] = ()

    @field_validator("video")
    @classmethod
    def primary_artifact_is_video(cls, video: SourceArtifact) -> SourceArtifact:
        if not video.media_type.startswith("video/"):
            raise ValueError("primary Video-MME artifact must have a video media type")
        return video

    @model_validator(mode="after")
    def options_and_artifacts_are_consistent(self) -> "VideoMMESample":
        labels = [option.label for option in self.options]
        if len(labels) != len(set(labels)):
            raise ValueError("option labels must be unique")
        if self.answer_label not in labels:
            raise ValueError("answer_label must identify an official option")
        artifact_ids = [
            self.video.artifact_id,
            *(artifact.artifact_id for artifact in self.additional_artifacts),
        ]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("source artifact IDs must be unique")
        return self


class VideoChunk(ContractModel):
    artifact: SourceArtifact
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def interval_is_positive(self) -> "VideoChunk":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("video chunk end must be after start")
        if not self.artifact.media_type.startswith("video/"):
            raise ValueError("video chunk artifact must have a video media type")
        return self


class FixedIntervalSegmentation(ContractModel):
    strategy: Literal["fixed_interval"] = "fixed_interval"
    source_artifact_id: str = Field(min_length=1)
    video_duration_seconds: float = Field(gt=0)
    interval_seconds: float = Field(gt=0)
    chunks: tuple[VideoChunk, ...] = Field(min_length=1)
    information_preserved: bool

    @model_validator(mode="after")
    def chunks_match_fixed_intervals(self) -> "FixedIntervalSegmentation":
        tolerance = 1e-6
        artifact_ids = [chunk.artifact.artifact_id for chunk in self.chunks]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("video chunk artifact IDs must be unique")
        for index, chunk in enumerate(self.chunks):
            expected_start = index * self.interval_seconds
            expected_end = min(
                self.video_duration_seconds,
                (index + 1) * self.interval_seconds,
            )
            if abs(chunk.start_seconds - expected_start) > tolerance:
                raise ValueError("video chunks must be contiguous fixed intervals")
            if abs(chunk.end_seconds - expected_end) > tolerance:
                raise ValueError("video chunks must be contiguous fixed intervals")
        if abs(self.chunks[-1].end_seconds - self.video_duration_seconds) > tolerance:
            raise ValueError("video chunks must cover the complete source duration")
        return self


class VideoMMEAdapter:
    """Identity adapter that exposes the complete official video without workflow hints."""

    def __init__(self, source_revision: str) -> None:
        if not source_revision:
            raise ValueError("source_revision must be pinned")
        self._source_revision = source_revision

    def adapt(
        self,
        sample: VideoMMESample,
        segmentation: FixedIntervalSegmentation | None = None,
    ) -> AdaptationBundle:
        primary_artifacts, transformation = self._adapt_video(sample, segmentation)
        artifacts = (*primary_artifacts, *sample.additional_artifacts)
        task = TaskContract(
            task_id=sample.sample_id,
            benchmark_id=VIDEO_MME_BENCHMARK_ID,
            objective=self._objective(sample),
            artifacts=tuple(
                ArtifactSpec(
                    artifact_id=artifact.artifact_id,
                    logical_type=artifact.logical_type,
                    media_type=artifact.media_type,
                    size_bytes=artifact.size_bytes,
                    content_schema=artifact.content_schema,
                    source_ref=artifact.source_ref,
                )
                for artifact in artifacts
            ),
            output_contract=OutputContract(
                format=OutputFormat.CHOICE,
                choices=tuple(option.label for option in sample.options),
            ),
            evaluator_id=VIDEO_MME_EVALUATOR_ID,
        )
        execution = AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=assess_validity(
                (transformation,),
                query_equivalent=True,
                evaluator_equivalent=True,
            ),
        )
        private_evaluation = PrivateChoiceEvaluation(
            task_id=sample.sample_id,
            evaluator_id=VIDEO_MME_EVALUATOR_ID,
            gold_answer=sample.answer_label,
        )
        return AdaptationBundle(execution, private_evaluation)

    def _adapt_video(
        self,
        sample: VideoMMESample,
        segmentation: FixedIntervalSegmentation | None,
    ) -> tuple[tuple[SourceArtifact, ...], TransformationRecord]:
        if segmentation is None:
            return (sample.video,), TransformationRecord(
                benchmark_id=VIDEO_MME_BENCHMARK_ID,
                source_revision=self._source_revision,
                source_task_id=sample.sample_id,
                transformation="identity_reference_complete_video",
                information_preserved=True,
                order_preserved=True,
                gold_independent=True,
                notes=(
                    "Complete video and all declared official auxiliary artifacts remain reachable."
                ),
            )
        if segmentation.source_artifact_id != sample.video.artifact_id:
            raise ValueError("segmentation manifest references a different source video")
        return tuple(chunk.artifact for chunk in segmentation.chunks), TransformationRecord(
            benchmark_id=VIDEO_MME_BENCHMARK_ID,
            source_revision=self._source_revision,
            source_task_id=sample.sample_id,
            transformation="fixed_interval_complete_video_segmentation",
            information_preserved=segmentation.information_preserved,
            order_preserved=True,
            gold_independent=True,
            notes=(
                f"{len(segmentation.chunks)} chunks cover the complete "
                f"{segmentation.video_duration_seconds:g}s source at "
                f"{segmentation.interval_seconds:g}s fixed intervals."
            ),
        )

    @staticmethod
    def _objective(sample: VideoMMESample) -> str:
        options = "\n".join(f"{option.label}. {option.text}" for option in sample.options)
        return f"{sample.question}\n\n{options}"
