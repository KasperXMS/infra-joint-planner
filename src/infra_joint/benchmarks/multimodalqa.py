"""MultiModalQA adapter with a hard public-execution/private-evaluation split."""

from __future__ import annotations

import json
import re
import string
from functools import cache
from hashlib import sha256
from typing import Any

from pydantic import Field

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.evaluation.evaluator import EvaluationResult, Evaluator

MULTIMODALQA_BENCHMARK_ID = "multimodalqa_dev"
MULTIMODALQA_EVALUATOR_ID = "multimodalqa_official_list_f1_v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


class MultiModalQAText(ContractModel):
    id: str = Field(min_length=1)
    title: str
    url: str
    text: str


class MultiModalQATable(ContractModel):
    id: str = Field(min_length=1)
    payload: dict[str, Any]


class MultiModalQAImage(ContractModel):
    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    media_type: str = Field(pattern=r"^image/")
    content: bytes


class MultiModalQASample(ContractModel):
    qid: str = Field(min_length=1)
    question: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    modalities: tuple[str, ...] = Field(min_length=1)
    texts: tuple[MultiModalQAText, ...]
    table: MultiModalQATable
    images: tuple[MultiModalQAImage, ...] = Field(min_length=1)
    answers: tuple[str, ...] = Field(min_length=1)
    supporting_context: tuple[dict[str, Any], ...]
    intermediate_answers: tuple[Any, ...]


class PrivateMultiModalQAEvaluation(ContractModel):
    """Gold and annotations that must never enter TaskContract or planner state."""

    task_id: str = Field(min_length=1)
    evaluator_id: str = Field(default=MULTIMODALQA_EVALUATOR_ID, min_length=1)
    gold_answers: tuple[str, ...] = Field(min_length=1)
    supporting_context: tuple[dict[str, Any], ...]
    intermediate_answers: tuple[Any, ...]

    def build_evaluator(self) -> Evaluator:
        return MultiModalQAOfficialEvaluator(self.gold_answers)


def _normalize_answer(value: str) -> str:
    def normalize_token(token: str) -> str:
        lowered = token.lower()
        if not _is_number(lowered):
            lowered = "".join(ch for ch in lowered if ch not in string.punctuation)
        lowered = re.sub(r"\b(a|an|the)\b", " ", lowered)
        if _is_number(lowered.strip()):
            lowered = str(float(lowered.strip()))
        return " ".join(lowered.split())

    return " ".join(
        part for token in re.split(r" |--?", value) if (part := normalize_token(token))
    ).strip()


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _bag(value: str) -> tuple[str, set[str]]:
    normalized = _normalize_answer(value)
    return normalized, set(normalized.split())


def _pair_score(predicted: set[str], gold: set[str]) -> float:
    gold_numbers = {item for item in gold if _is_number(item)}
    predicted_numbers = {item for item in predicted if _is_number(item)}
    if gold_numbers and not gold_numbers.intersection(predicted_numbers):
        return 0.0
    overlap = len(predicted.intersection(gold))
    precision = overlap / len(predicted) if predicted else 1.0
    recall = overlap / len(gold) if gold else 1.0
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _list_f1(predicted: tuple[str, ...], gold: tuple[str, ...]) -> float:
    predicted_bags = tuple(_bag(item)[1] for item in predicted)
    gold_bags = tuple(_bag(item)[1] for item in gold)

    @cache
    def best(gold_index: int, used_mask: int) -> float:
        if gold_index == len(gold_bags):
            return 0.0
        unmatched = best(gold_index + 1, used_mask)
        matched = max(
            (
                _pair_score(predicted_bags[index], gold_bags[gold_index])
                + best(gold_index + 1, used_mask | (1 << index))
                for index in range(len(predicted_bags))
                if not used_mask & (1 << index)
            ),
            default=0.0,
        )
        return max(unmatched, matched)

    denominator = max(len(predicted_bags), len(gold_bags), 1)
    return round(best(0, 0) / denominator, 2)


class MultiModalQAOfficialEvaluator:
    """Dependency-free port of official list EM/F1 for one prediction."""

    def __init__(self, gold_answers: tuple[str, ...]) -> None:
        self._gold_answers = gold_answers

    async def evaluate(self, task: TaskContract, answer: str) -> EvaluationResult:
        if task.output_contract.format != OutputFormat.SHORT_TEXT:
            return EvaluationResult(
                format_valid=False,
                benchmark_score=0.0,
                details="task does not declare a short-text output contract",
            )
        predicted = (answer,)
        pred_norm = tuple(_bag(item)[0] for item in predicted)
        gold_norm = tuple(_bag(item)[0] for item in self._gold_answers)
        list_em = float(set(pred_norm) == set(gold_norm) and len(pred_norm) == len(gold_norm))
        list_f1 = _list_f1(predicted, self._gold_answers)
        return EvaluationResult(
            format_valid=bool(answer.strip()),
            benchmark_score=list_f1,
            details=json.dumps({"list_em": list_em, "list_f1": list_f1}, sort_keys=True),
        )


class MultiModalQAAdapter:
    def __init__(self, source_revision: str) -> None:
        if not source_revision:
            raise ValueError("source_revision must be pinned")
        self._source_revision = source_revision

    def adapt(self, sample: MultiModalQASample) -> AdaptationBundle:
        prefix = f"mmqa-{sample.qid[:12]}"
        text_records = [item.model_dump(mode="json") for item in sample.texts]
        text_bytes = _canonical_json(text_records)
        table_bytes = _canonical_json(sample.table.payload)
        prepared = [
            self._artifact(
                f"{prefix}-texts",
                "candidate_text_corpus;text_field=text",
                "application/json",
                text_bytes,
            ),
            self._artifact(f"{prefix}-table", "candidate_table", "application/json", table_bytes),
        ]
        for image in sample.images:
            prepared.append(
                self._artifact(
                    f"{prefix}-image-{image.id[:12]}",
                    "candidate_image",
                    image.media_type,
                    image.content,
                )
            )
        transformation = TransformationRecord(
            benchmark_id=MULTIMODALQA_BENCHMARK_ID,
            source_revision=self._source_revision,
            source_task_id=sample.qid,
            transformation="lossless_candidate_context_materialization",
            information_preserved=True,
            order_preserved=True,
            gold_independent=True,
            notes=(
                "All official candidate texts, the full candidate table, and all candidate "
                "images are materialized; private annotations are excluded."
            ),
            audit={
                "question_type": sample.question_type,
                "modalities": list(sample.modalities),
                "text_count": len(sample.texts),
                "image_count": len(sample.images),
                "table_id": sample.table.id,
            },
        )
        task = TaskContract(
            task_id=sample.qid,
            benchmark_id=MULTIMODALQA_BENCHMARK_ID,
            objective=sample.question,
            artifacts=tuple(item.spec for item in prepared),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
            evaluator_id=MULTIMODALQA_EVALUATOR_ID,
        )
        execution = AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=assess_validity(
                (transformation,), query_equivalent=True, evaluator_equivalent=True
            ),
        )
        private = PrivateMultiModalQAEvaluation(
            task_id=sample.qid,
            gold_answers=sample.answers,
            supporting_context=sample.supporting_context,
            intermediate_answers=sample.intermediate_answers,
        )
        return AdaptationBundle(execution, private, tuple(prepared))

    @staticmethod
    def _artifact(
        artifact_id: str, logical_type: str, media_type: str, content: bytes
    ) -> PreparedArtifact:
        spec = ArtifactSpec(
            artifact_id=artifact_id,
            logical_type=logical_type,
            media_type=media_type,
            size_bytes=len(content),
            source_ref=f"prepared://multimodalqa/{artifact_id}",
        )
        return PreparedArtifact.create(spec, content)


def bundle_public_digest(bundle: AdaptationBundle) -> str:
    """Stable digest for the exact Planner/runtime-visible representation."""

    value = {
        "execution": bundle.execution.model_dump(mode="json"),
        "artifacts": [
            {"spec": item.spec.model_dump(mode="json"), "sha256": item.sha256_hex}
            for item in bundle.prepared_artifacts
        ],
    }
    return sha256(_canonical_json(value)).hexdigest()
