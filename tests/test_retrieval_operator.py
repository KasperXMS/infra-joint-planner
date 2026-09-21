import json

from infra_joint.core.action import SemanticAction
from infra_joint.operators.artifacts import store_json
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.operators.retrieval import register_retrieval_operators
from infra_joint.worker.artifact_store import InMemoryArtifactStore


def test_bm25_retrieval_is_deterministic_and_registers_artifact() -> None:
    store = InMemoryArtifactStore()
    store_json(
        store,
        "corpus",
        [
            {"id": "d1", "text": "edge model inference"},
            {"id": "d2", "text": "distributed retrieval over an edge network"},
            {"id": "d3", "text": "video frame sampling"},
        ],
    )
    registry = OperatorRegistry()
    register_retrieval_operators(registry, store)

    result = registry.binding("bm25_retrieve").handler(
        SemanticAction(
            operator="bm25_retrieve",
            inputs=("corpus",),
            arguments={
                "query": "edge network retrieval",
                "top_k": 2,
                "output_artifact_id": "hits",
            },
        )
    )

    assert result["artifact_id"] == "hits"
    hits = json.loads(store.get("hits").content)
    assert [hit["id"] for hit in hits] == ["d2", "d1"]
    assert hits[0]["_bm25_score"] > hits[1]["_bm25_score"] > 0


def test_bm25_ties_keep_corpus_order() -> None:
    store = InMemoryArtifactStore()
    store_json(
        store,
        "corpus",
        [
            {"id": "first", "text": "unrelated"},
            {"id": "second", "text": "also unrelated"},
        ],
    )
    registry = OperatorRegistry()
    register_retrieval_operators(registry, store)
    registry.binding("bm25_retrieve").handler(
        SemanticAction(
            operator="bm25_retrieve",
            inputs=("corpus",),
            arguments={
                "query": "missing",
                "top_k": 2,
                "output_artifact_id": "hits",
            },
        )
    )

    hits = json.loads(store.get("hits").content)
    assert [hit["id"] for hit in hits] == ["first", "second"]
