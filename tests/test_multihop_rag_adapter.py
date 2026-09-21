import json
from hashlib import sha256

import pytest
from pydantic import ValidationError

from infra_joint.benchmarks.base import BenchmarkSettingKind
from infra_joint.benchmarks.multihop_rag import (
    MULTIHOP_FIXED_CANDIDATE_ID,
    MULTIHOP_FULL_CORPUS_ID,
    CandidateSelectionRecord,
    FixedCandidate,
    FixedCandidateSetting,
    FullCorpusSetting,
    MultiHopCorpusDocument,
    MultiHopRAGAdapter,
    MultiHopRAGSample,
)


def official_sample() -> MultiHopRAGSample:
    return MultiHopRAGSample.model_validate(
        {
            "query": "Do both reports name the same company?",
            "evidence_list": [
                {
                    "author": "Reporter One",
                    "category": "technology",
                    "fact": "PRIVATE_SUPPORTING_FACT_SENTINEL",
                    "published_at": "2023-11-01T00:00:00+00:00",
                    "source": "Source One",
                    "title": "Evidence title",
                    "url": "https://example.test/evidence",
                }
            ],
            "question_type": "comparison_query",
            "answer": "Yes",
        }
    )


def corpus_document(index: int) -> MultiHopCorpusDocument:
    return MultiHopCorpusDocument(
        title=f"Article {index}",
        body=f"Complete article body {index}",
        author=f"Author {index}",
        source="News Wire",
        published_at=f"2023-11-{index + 1:02d}T00:00:00+00:00",
        category="business",
        url=f"https://example.test/{index}",
    )


def query_hash(sample: MultiHopRAGSample) -> str:
    return sha256(sample.query.encode("utf-8")).hexdigest()


def test_full_corpus_setting_shards_every_document_without_gold() -> None:
    sample = official_sample()
    corpus = tuple(corpus_document(index) for index in range(5))
    bundle = MultiHopRAGAdapter("yixuantt/MultiHopRAG@revision").adapt(
        sample,
        FullCorpusSetting(corpus=corpus, shard_count=3),
    )

    task = bundle.execution.task
    assert task.task_id.startswith("multihop-")
    assert task.benchmark_id == MULTIHOP_FULL_CORPUS_ID
    assert task.objective == sample.query
    assert len(bundle.prepared_artifacts) == 3
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.OFFICIAL_EQUIVALENT

    adapted_records = [
        record for artifact in bundle.prepared_artifacts for record in json.loads(artifact.content)
    ]
    assert sorted(adapted_records, key=lambda record: record["url"]) == sorted(
        (document.model_dump() for document in corpus),
        key=lambda record: record["url"],
    )
    audit = bundle.execution.transformations[0].audit
    assert audit["corpus_document_count"] == audit["adapted_document_count"] == 5
    assert audit["source_corpus_sha256"] == audit["adapted_corpus_sha256"]

    execution_json = json.dumps(
        {
            "execution": bundle.execution.model_dump(mode="json"),
            "artifacts": [json.loads(artifact.content) for artifact in bundle.prepared_artifacts],
        }
    )
    assert sample.answer not in task.model_dump_json()
    assert "evidence_list" not in execution_json
    assert "PRIVATE_SUPPORTING_FACT_SENTINEL" not in execution_json


def test_full_corpus_sharding_is_deterministic() -> None:
    sample = official_sample()
    setting = FullCorpusSetting(
        corpus=tuple(corpus_document(index) for index in range(4)),
        shard_count=2,
    )
    adapter = MultiHopRAGAdapter("revision")

    first = adapter.adapt(sample, setting)
    second = adapter.adapt(sample, setting)

    assert [artifact.content for artifact in first.prepared_artifacts] == [
        artifact.content for artifact in second.prepared_artifacts
    ]


def test_fixed_candidates_are_always_labeled_derived() -> None:
    sample = official_sample()
    setting = FixedCandidateSetting(
        candidates=(
            FixedCandidate(rank=1, score=4.5, document=corpus_document(1)),
            FixedCandidate(rank=2, score=3.0, document=corpus_document(2)),
        ),
        selection=CandidateSelectionRecord(
            selector_id="bm25",
            selector_revision="rank-bm25@revision",
            source_corpus_revision="yixuantt/MultiHopRAG@revision",
            query_sha256=query_hash(sample),
            top_n=2,
        ),
    )
    bundle = MultiHopRAGAdapter("yixuantt/MultiHopRAG@revision").adapt(sample, setting)

    assert bundle.execution.task.benchmark_id == MULTIHOP_FIXED_CANDIDATE_ID
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.DERIVED
    assert not bundle.execution.validity.information_equivalent
    assert "derived fixed-candidate" in bundle.execution.transformations[0].notes
    records = json.loads(bundle.prepared_artifacts[0].content)
    assert [record["rank"] for record in records] == [1, 2]
    assert [record["score"] for record in records] == [4.5, 3.0]
    assert [record["text"] for record in records] == [
        corpus_document(1).body,
        corpus_document(2).body,
    ]
    assert bundle.prepared_artifacts[0].spec.logical_type == (
        "ranked_candidate_bundle;text_field=text"
    )


def test_fixed_candidates_reject_gold_dependent_selection() -> None:
    with pytest.raises(ValidationError, match="gold_independent"):
        CandidateSelectionRecord(
            selector_id="oracle",
            selector_revision="v1",
            source_corpus_revision="revision",
            query_sha256="0" * 64,
            top_n=1,
            gold_independent=False,
        )


def test_fixed_candidates_reject_non_finite_scores() -> None:
    with pytest.raises(ValidationError, match="finite number"):
        FixedCandidate(rank=1, score=float("nan"), document=corpus_document(1))


def test_fixed_candidates_reject_selection_for_another_query() -> None:
    sample = official_sample()
    setting = FixedCandidateSetting(
        candidates=(FixedCandidate(rank=1, document=corpus_document(1)),),
        selection=CandidateSelectionRecord(
            selector_id="bm25",
            selector_revision="v1",
            source_corpus_revision="revision",
            query_sha256="0" * 64,
            top_n=1,
        ),
    )

    with pytest.raises(ValueError, match="query hash"):
        MultiHopRAGAdapter("revision").adapt(sample, setting)


def test_fixed_candidates_reject_another_corpus_revision() -> None:
    sample = official_sample()
    setting = FixedCandidateSetting(
        candidates=(FixedCandidate(rank=1, document=corpus_document(1)),),
        selection=CandidateSelectionRecord(
            selector_id="bm25",
            selector_revision="v1",
            source_corpus_revision="different-revision",
            query_sha256=query_hash(sample),
            top_n=1,
        ),
    )

    with pytest.raises(ValueError, match="corpus revision"):
        MultiHopRAGAdapter("revision").adapt(sample, setting)


def test_null_query_allows_empty_evidence_list() -> None:
    sample = MultiHopRAGSample(
        query="Which report confirms the claim?",
        evidence_list=(),
        question_type="null_query",
        answer="Insufficient information.",
    )

    assert sample.evidence_list == ()


@pytest.mark.asyncio
async def test_private_evaluator_reproduces_official_token_overlap_rule() -> None:
    sample = official_sample()
    bundle = MultiHopRAGAdapter("revision").adapt(
        sample,
        FullCorpusSetting(corpus=(corpus_document(1),)),
    )
    evaluator = bundle.private_evaluation.build_evaluator()

    exact = await evaluator.evaluate(bundle.execution.task, "Yes")
    official_phrase = await evaluator.evaluate(
        bundle.execution.task,
        'Reasoning. The answer to the question is "Yes".',
    )
    markdown = await evaluator.evaluate(bundle.execution.task, "**Yes — both do.**")

    assert exact.benchmark_score == 1.0
    assert official_phrase.benchmark_score == 1.0
    assert markdown.benchmark_score == 0.0
