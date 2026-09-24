import json
import re
from hashlib import sha256
from typing import Literal

from pydantic import Field, computed_field, field_validator, model_validator

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    TransformationRecord,
    assess_validity,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import (
    ArtifactCollectionRelation,
    ArtifactContentSchema,
    ArtifactSpec,
    CollectionCompleteness,
    OutputContract,
    OutputFormat,
    PartitionSemantics,
    TaskContract,
)
from infra_joint.evaluation.evaluator import EvaluationResult, Evaluator

MULTIHOP_FULL_CORPUS_ID = "multihop_full_corpus"
MULTIHOP_FIXED_CANDIDATE_ID = "multihop_fixed_candidate"
MULTIHOP_EVALUATOR_ID = "multihop_rag_official_token_overlap_v1"

QuestionType = Literal[
    "inference_query",
    "comparison_query",
    "temporal_query",
    "null_query",
]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _query_sha256(query: str) -> str:
    return sha256(query.encode("utf-8")).hexdigest()


class MultiHopEvidence(ContractModel):
    """Official supporting evidence, retained only in the private evaluation side."""

    author: str | None
    category: str
    fact: str = Field(min_length=1)
    published_at: str
    source: str
    title: str
    url: str


class MultiHopRAGSample(ContractModel):
    query: str = Field(min_length=1)
    evidence_list: tuple[MultiHopEvidence, ...]
    question_type: QuestionType
    answer: str = Field(min_length=1)
    sample_id: str | None = Field(default=None, min_length=1)

    @computed_field
    @property
    def task_id(self) -> str:
        return self.sample_id or f"multihop-{_query_sha256(self.query)[:16]}"


class MultiHopCorpusDocument(ContractModel):
    """The seven fields present in the benchmark's official corpus JSON."""

    title: str
    body: str
    author: str | None
    source: str
    published_at: str
    category: str
    url: str

    def stable_id(self) -> str:
        return sha256(_canonical_json(self.model_dump())).hexdigest()


class FullCorpusSetting(ContractModel):
    kind: Literal["full_corpus"] = "full_corpus"
    corpus: tuple[MultiHopCorpusDocument, ...] = Field(min_length=1)
    shard_count: int = Field(default=1, ge=1)
    artifact_prefix: str = Field(default="corpus-shard", min_length=1)
    max_chunk_chars: int | None = Field(default=None, ge=256)

    @field_validator("corpus")
    @classmethod
    def documents_are_unique(
        cls, corpus: tuple[MultiHopCorpusDocument, ...]
    ) -> tuple[MultiHopCorpusDocument, ...]:
        identifiers = [document.stable_id() for document in corpus]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("full corpus contains duplicate documents")
        return corpus


class CandidateSelectionRecord(ContractModel):
    """Provenance for an offline candidate selector; gold dependence is forbidden."""

    selector_id: str = Field(min_length=1)
    selector_revision: str = Field(min_length=1)
    source_corpus_revision: str = Field(min_length=1)
    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    top_n: int = Field(gt=0)
    gold_independent: Literal[True] = True


class FixedCandidate(ContractModel):
    rank: int = Field(gt=0)
    score: float | None = Field(default=None, allow_inf_nan=False)
    document: MultiHopCorpusDocument


class FixedCandidateSetting(ContractModel):
    kind: Literal["fixed_candidate"] = "fixed_candidate"
    candidates: tuple[FixedCandidate, ...] = Field(min_length=1)
    selection: CandidateSelectionRecord
    artifact_id: str = Field(default="candidate-bundle", min_length=1)

    @model_validator(mode="after")
    def ranking_is_complete_and_unique(self) -> "FixedCandidateSetting":
        ranks = [candidate.rank for candidate in self.candidates]
        if ranks != list(range(1, len(self.candidates) + 1)):
            raise ValueError("candidate ranks must be ordered and contiguous from 1")
        identifiers = [candidate.document.stable_id() for candidate in self.candidates]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("candidate bundle contains duplicate documents")
        if len(self.candidates) > self.selection.top_n:
            raise ValueError("candidate count exceeds selector top_n")
        return self


class MultiHopOfficialTokenOverlapEvaluator:
    """Faithful port of the benchmark's current qa_evaluate.py success rule."""

    _answer_pattern = re.compile(r'The answer to the question is "(.*?)"')

    def __init__(self, gold_answer: str) -> None:
        self._gold_answer = gold_answer

    @classmethod
    def extract_answer(cls, answer: str) -> str:
        match = cls._answer_pattern.search(answer)
        return match.group(1) if match else answer

    async def evaluate(self, task: TaskContract, answer: str) -> EvaluationResult:
        if task.output_contract.format != OutputFormat.SHORT_TEXT:
            return EvaluationResult(
                format_valid=False,
                benchmark_score=0.0,
                details="task does not declare a short-text output contract",
            )
        extracted = self.extract_answer(answer)
        prediction_tokens = set(extracted.lower().split())
        gold_tokens = set(self._gold_answer.lower().split())
        matched = bool(prediction_tokens.intersection(gold_tokens))
        return EvaluationResult(
            format_valid=True,
            benchmark_score=float(matched),
            details="official lowercase whitespace-token intersection",
        )


class PrivateMultiHopEvaluation(ContractModel):
    task_id: str = Field(min_length=1)
    evaluator_id: str = Field(default=MULTIHOP_EVALUATOR_ID, min_length=1)
    gold_answer: str = Field(min_length=1)
    question_type: QuestionType
    supporting_evidence: tuple[MultiHopEvidence, ...]

    def build_evaluator(self) -> Evaluator:
        return MultiHopOfficialTokenOverlapEvaluator(self.gold_answer)


class MultiHopRAGAdapter:
    def __init__(self, source_revision: str) -> None:
        if not source_revision:
            raise ValueError("source_revision must be pinned")
        self._source_revision = source_revision

    def adapt(
        self,
        sample: MultiHopRAGSample,
        setting: FullCorpusSetting | FixedCandidateSetting,
    ) -> AdaptationBundle:
        if isinstance(setting, FullCorpusSetting):
            benchmark_id = MULTIHOP_FULL_CORPUS_ID
            prepared, transformation = self._prepare_full_corpus(sample, setting)
        else:
            benchmark_id = MULTIHOP_FIXED_CANDIDATE_ID
            prepared, transformation = self._prepare_candidates(sample, setting)

        task = TaskContract(
            task_id=sample.task_id,
            benchmark_id=benchmark_id,
            objective=sample.query,
            artifacts=tuple(artifact.spec for artifact in prepared),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
            evaluator_id=MULTIHOP_EVALUATOR_ID,
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
        private_evaluation = PrivateMultiHopEvaluation(
            task_id=sample.task_id,
            gold_answer=sample.answer,
            question_type=sample.question_type,
            supporting_evidence=sample.evidence_list,
        )
        return AdaptationBundle(execution, private_evaluation, prepared)

    def _prepare_full_corpus(
        self,
        sample: MultiHopRAGSample,
        setting: FullCorpusSetting,
    ) -> tuple[tuple[PreparedArtifact, ...], TransformationRecord]:
        shard_count = min(setting.shard_count, len(setting.corpus))
        shards: list[list[dict[str, object]]] = [[] for _ in range(shard_count)]
        for document in setting.corpus:
            shard_index = int(document.stable_id(), 16) % shard_count
            shards[shard_index].extend(self._document_records(document, setting.max_chunk_chars))

        collection_id = f"{sample.task_id}:complete-corpus"
        prepared = tuple(
            self._json_artifact(
                sample.task_id,
                f"{setting.artifact_prefix}-{index + 1:04d}",
                "corpus_shard",
                _canonical_json(shard),
                content_schema=ArtifactContentSchema(
                    kind="record_array",
                    fields={
                        "title": "string",
                        "body": "string",
                        "author": "string|null",
                        "source": "string",
                        "published_at": "string",
                        "category": "string",
                        "url": "string",
                        **(
                            {
                                "document_id": "string",
                                "chunk_index": "integer",
                                "chunk_count": "integer",
                            }
                            if setting.max_chunk_chars is not None
                            else {}
                        ),
                    },
                    text_field="body",
                    record_count=len(shard),
                    max_record_bytes=max(
                        (len(_canonical_json(record)) for record in shard),
                        default=0,
                    ),
                ),
                collection=ArtifactCollectionRelation(
                    collection_id=collection_id,
                    partition_index=index,
                    partition_count=shard_count,
                    partition_method="sha256(document) modulo partition_count",
                    partition_semantics=PartitionSemantics.NON_SEMANTIC,
                    completeness=CollectionCompleteness.UNION_IS_COMPLETE,
                ),
            )
            for index, shard in enumerate(shards)
        )
        corpus_digest = self._corpus_digest(setting.corpus)
        adapted_digest = corpus_digest
        record_count = sum(len(shard) for shard in shards)
        record = TransformationRecord(
            benchmark_id=MULTIHOP_FULL_CORPUS_ID,
            source_revision=self._source_revision,
            source_task_id=sample.task_id,
            transformation=(
                "deterministic_full_corpus_sharding"
                if setting.max_chunk_chars is None
                else "deterministic_full_corpus_sharding_and_lossless_chunking"
            ),
            information_preserved=True,
            order_preserved=False,
            gold_independent=True,
            notes="Every corpus document is available; sharding uses only document content.",
            audit={
                "setting_id": MULTIHOP_FULL_CORPUS_ID,
                "corpus_document_count": len(setting.corpus),
                "adapted_document_count": len(setting.corpus),
                "adapted_record_count": record_count,
                "shard_count": shard_count,
                "max_chunk_chars": setting.max_chunk_chars,
                "source_corpus_sha256": corpus_digest,
                "adapted_corpus_sha256": adapted_digest,
                "shard_assignment": "sha256(document) modulo shard_count",
            },
        )
        return prepared, record

    def _prepare_candidates(
        self,
        sample: MultiHopRAGSample,
        setting: FixedCandidateSetting,
    ) -> tuple[tuple[PreparedArtifact, ...], TransformationRecord]:
        if setting.selection.source_corpus_revision != self._source_revision:
            raise ValueError(
                "candidate source corpus revision does not match adapter source revision"
            )
        if setting.selection.query_sha256 != _query_sha256(sample.query):
            raise ValueError("candidate selection query hash does not match sample query")
        records = [
            {
                "document": candidate.document.model_dump(),
                "rank": candidate.rank,
                "score": candidate.score,
                "text": candidate.document.body,
            }
            for candidate in setting.candidates
        ]
        artifact = self._json_artifact(
            sample.task_id,
            setting.artifact_id,
            "ranked_candidate_bundle;text_field=text",
            _canonical_json(records),
            content_schema=ArtifactContentSchema(
                kind="record_array",
                fields={
                    "document": "object",
                    "rank": "integer",
                    "score": "number|null",
                    "text": "string",
                },
                text_field="text",
                record_count=len(records),
                max_record_bytes=max(
                    (len(_canonical_json(record)) for record in records),
                    default=0,
                ),
            ),
        )
        record = TransformationRecord(
            benchmark_id=MULTIHOP_FIXED_CANDIDATE_ID,
            source_revision=self._source_revision,
            source_task_id=sample.task_id,
            transformation="offline_gold_independent_top_n_candidates",
            information_preserved=False,
            order_preserved=True,
            gold_independent=True,
            notes=(
                "MultiHop-RAG-derived fixed-candidate setting; it is not a full-corpus "
                "end-to-end result."
            ),
            audit={
                "setting_id": MULTIHOP_FIXED_CANDIDATE_ID,
                "candidate_count": len(setting.candidates),
                "top_n": setting.selection.top_n,
                "selector_id": setting.selection.selector_id,
                "selector_revision": setting.selection.selector_revision,
                "source_corpus_revision": setting.selection.source_corpus_revision,
                "selection_query_sha256": setting.selection.query_sha256,
                "gold_independent": setting.selection.gold_independent,
                "candidate_bundle_sha256": artifact.sha256_hex,
            },
        )
        return (artifact,), record

    @staticmethod
    def _corpus_digest(corpus: tuple[MultiHopCorpusDocument, ...]) -> str:
        records = sorted(
            (document.model_dump() for document in corpus),
            key=lambda record: sha256(_canonical_json(record)).hexdigest(),
        )
        return sha256(_canonical_json(records)).hexdigest()

    @staticmethod
    def _document_records(
        document: MultiHopCorpusDocument,
        max_chunk_chars: int | None,
    ) -> list[dict[str, object]]:
        base = document.model_dump()
        if max_chunk_chars is None:
            return [base]
        chunks = [
            document.body[start : start + max_chunk_chars]
            for start in range(0, len(document.body), max_chunk_chars)
        ]
        document_id = document.stable_id()
        return [
            {
                **base,
                "body": chunk,
                "document_id": document_id,
                "chunk_index": index,
                "chunk_count": len(chunks),
            }
            for index, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _json_artifact(
        task_id: str,
        artifact_id: str,
        logical_type: str,
        content: bytes,
        *,
        content_schema: ArtifactContentSchema | None = None,
        collection: ArtifactCollectionRelation | None = None,
    ) -> PreparedArtifact:
        spec = ArtifactSpec(
            artifact_id=artifact_id,
            logical_type=logical_type,
            media_type="application/json",
            size_bytes=len(content),
            content_schema=content_schema,
            collection=collection,
            source_ref=f"prepared://multihop-rag/{task_id}/{artifact_id}",
        )
        return PreparedArtifact.create(spec, content)
