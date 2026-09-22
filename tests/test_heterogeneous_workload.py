import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from infra_joint.heterogeneous.workload import (
    DEFAULT_EVIDENCE_EXCERPT_BYTES_PER_SOURCE,
    ContextPreflightConstraint,
    SemanticWorkloadManifest,
    freeze_semantic_workload,
)
from infra_joint.operators.catalog import build_operator_catalog
from scripts.heterogeneous_experiment_v1 import build_bundle


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def source_document(title: str, body: str) -> dict[str, str]:
    return {
        "title": title,
        "body": body,
        "author": "Author",
        "source": "Publisher",
        "published_at": "2026-01-01T00:00:00+00:00",
        "category": "technology",
        "url": f"https://example.test/{title}",
    }


def write_fixture(root: Path, *, omit_support: bool = False) -> tuple[dict[str, str], ...]:
    documents = (
        source_document("one", "evidence one " * 80),
        source_document("two", "evidence two " * 80),
    )
    ids = ("mhr-doc-one", "mhr-doc-two")
    for document_id, document in zip(ids, documents, strict=True):
        if omit_support and document_id == "mhr-doc-two":
            continue
        (root / f"{document_id}.json").write_bytes(canonical(document))
    task = {
        "task_id": "multihop-task",
        "dataset": "MultiHop-RAG",
        "query": "Compare the two reports.",
        "instruction": "Return a concise answer.",
        "evaluator_type": "multihop_rag_official_token_intersection",
        "artifact_ids": list(ids),
    }
    candidates = {
        "candidates": [
            {
                "task_id": "multihop-task",
                "query": task["query"],
                "candidate_document_ids": list(ids),
                "evaluator_only": {
                    "answer": "Private Gold",
                    "supporting_document_ids": list(ids),
                },
            }
        ]
    }
    (root / "task.json").write_bytes(canonical(task))
    (root / "candidates.json").write_bytes(canonical(candidates))
    return documents


def json_records(path: Path) -> list[dict[str, Any]]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(value, list)
    return cast(list[dict[str, Any]], value)


def test_freeze_is_deterministic_derived_and_keeps_private_evaluation_separate(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source = write_fixture(data_dir)
    targets = {"S": 8_000, "M": 16_000, "L": 32_000}

    first = freeze_semantic_workload(
        data_dir=data_dir,
        output_dir=tmp_path / "first",
        payload_targets=targets,
        context_window_tokens=16_000,
        reserved_output_tokens=1_000,
        prompt_token_upper_bound=2_000,
    )
    second = freeze_semantic_workload(
        data_dir=data_dir,
        output_dir=tmp_path / "second",
        payload_targets=targets,
        context_window_tokens=16_000,
        reserved_output_tokens=1_000,
        prompt_token_upper_bound=2_000,
    )

    assert first == second
    legacy = first.model_dump(mode="json")
    legacy["schema_version"] = "heterogeneous-semantic-workload-freeze-v1"
    legacy.pop("evidence_excerpt_policy")
    for payload in legacy["payloads"]:
        payload["derived_label"] = "derived_deterministic_semantic_replication_v1"
    legacy["workflow_template"]["context_preflight"].pop(
        "projected_reduced_artifact_upper_bound_bytes"
    )
    parsed_legacy = SemanticWorkloadManifest.model_validate(legacy)
    assert parsed_legacy.schema_version == "heterogeneous-semantic-workload-freeze-v1"
    assert parsed_legacy.evidence_excerpt_policy is None
    assert first.source_candidate_document_count == 2
    assert first.materialized_source_document_count == 2
    assert first.private_evaluation.planner_visible is False
    assert first.workflow_template.same_synthesis_model_for_all_payloads is True
    assert first.workflow_template.nodes[0].arguments["top_k"] == 100_000
    assert first.workflow_template.nodes[1].arguments["top_k"] == 100_000
    assert first.workflow_template.nodes[3].arguments["top_k"] == 2
    assert first.workflow_template.nodes[3].outputs == ("{payload}.ranked-evidence",)
    assert first.workflow_template.nodes[4].operator == "select_fields"
    assert first.workflow_template.context_preflight.max_reduced_artifact_bytes == 13_000
    projected_bound = (
        first.workflow_template.context_preflight
        .projected_reduced_artifact_upper_bound_bytes
    )
    assert projected_bound is not None
    assert projected_bound <= 13_000
    assert first.workflow_template.context_preflight.silent_truncation is False
    assert first.schema_version == "heterogeneous-semantic-workload-freeze-v2"
    assert first.evidence_excerpt_policy is not None
    assert (
        first.evidence_excerpt_policy.max_utf8_bytes_per_source
        == DEFAULT_EVIDENCE_EXCERPT_BYTES_PER_SOURCE
    )
    task = build_bundle(tmp_path / "first" / "manifest.json", first, "S").execution.task
    task_json = task.model_dump_json()
    assert "A4" not in task_json
    assert "A5" not in task_json
    assert "A28" not in task_json
    assert "strong-4090" not in task_json

    source_bodies = {document["body"] for document in source}
    for payload in first.payloads:
        assert abs(payload.actual_bytes - payload.target_bytes) < 2_000
        assert {shard.placement_agent for shard in payload.shards} == {"A4", "A5"}
        records = [
            record
            for shard in payload.shards
            for record in json_records(tmp_path / "first" / shard.path)
        ]
        assert len(records) == payload.record_count
        assert len({record["derived_document_id"] for record in records}) == len(records)
        assert {record["body"] for record in records} == source_bodies
        assert {record["derived_label"] for record in records} == {
            "derived_deterministic_semantic_replication_v2"
        }
        assert all(record["derived_document_id"].startswith("mhr-derived-") for record in records)
        assert all(shard.artifact_id.startswith("heterogeneous-v2-") for shard in payload.shards)
        canonical = [record for record in records if record["replica_index"] == 0]
        assert {record["source_document_id"] for record in canonical} == {
            "mhr-doc-one",
            "mhr-doc-two",
        }
        assert all(record["retrieval_text"] == record["body"] for record in canonical)
        assert all(record["evidence_excerpt"] for record in records)
        for shard in payload.shards:
            first_bytes = (tmp_path / "first" / shard.path).read_bytes()
            second_bytes = (tmp_path / "second" / shard.path).read_bytes()
            assert first_bytes == second_bytes
            assert hashlib.sha256(first_bytes).hexdigest() == shard.sha256

    public_text = (tmp_path / "first" / "manifest.json").read_text(encoding="utf-8")
    public_text += "".join(
        (tmp_path / "first" / shard.path).read_text(encoding="utf-8")
        for payload in first.payloads
        for shard in payload.shards
    )
    assert "Private Gold" not in public_text
    assert "supporting_document_ids" not in public_text
    private = json.loads(
        (tmp_path / "first" / "private-evaluation.json").read_text(encoding="utf-8")
    )
    assert private["gold_answer"] == "Private Gold"
    assert private["supporting_document_ids"] == ["mhr-doc-one", "mhr-doc-two"]

    registry = build_operator_catalog()
    for node in first.workflow_template.nodes:
        registry.validate_action(node.semantic_action())


def test_v2_freeze_expands_meaningful_source_prefixes_with_a_hard_context_bound(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_fixture(data_dir)
    for index, document_id in enumerate(("mhr-doc-one", "mhr-doc-two"), start=1):
        path = data_dir / f"{document_id}.json"
        document = cast(dict[str, str], json.loads(path.read_text(encoding="utf-8")))
        document["body"] = (
            f"Source {index} opening evidence explains the report. " * 220
            + f"Source {index} later evidence remains meaningful. " * 80
        )
        path.write_bytes(canonical(document))

    frozen = freeze_semantic_workload(
        data_dir=data_dir,
        output_dir=tmp_path / "expanded",
        payload_targets={"S": 40_000},
        context_window_tokens=16_000,
        reserved_output_tokens=1_000,
        prompt_token_upper_bound=2_000,
    )

    records = [
        record
        for shard in frozen.payloads[0].shards
        for record in json_records(tmp_path / "expanded" / shard.path)
        if record["replica_index"] == 0
    ]
    assert len(records) == 2
    for record in records:
        excerpt = cast(str, record["evidence_excerpt"])
        assert excerpt == cast(str, record["body"])[: len(excerpt)]
        assert 5_900 <= len(excerpt.encode("utf-8")) <= 6_000

    context = [
        {field: record[field] for field in ("source_document_id", "title", "evidence_excerpt")}
        for record in records
    ]
    actual_context_bytes = len(canonical(context))
    projected = (
        frozen.workflow_template.context_preflight
        .projected_reduced_artifact_upper_bound_bytes
    )
    assert projected is not None
    assert 11_800 <= actual_context_bytes <= projected <= 13_000


def test_v2_freeze_fails_before_writing_when_projected_context_exceeds_budget(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_fixture(data_dir)
    for document_id in ("mhr-doc-one", "mhr-doc-two"):
        path = data_dir / f"{document_id}.json"
        document = cast(dict[str, str], json.loads(path.read_text(encoding="utf-8")))
        document["body"] = "meaningful evidence from the source " * 400
        path.write_bytes(canonical(document))

    output_dir = tmp_path / "must-not-exist"
    with pytest.raises(ValidationError, match="exceeds the fail-closed context byte budget"):
        freeze_semantic_workload(
            data_dir=data_dir,
            output_dir=output_dir,
            payload_targets={"S": 40_000},
            context_window_tokens=8_000,
            reserved_output_tokens=1_000,
            prompt_token_upper_bound=2_000,
        )
    assert not output_dir.exists()


def test_freeze_fails_closed_when_relevant_evidence_is_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_fixture(data_dir, omit_support=True)

    with pytest.raises(ValueError, match="omits supporting documents"):
        freeze_semantic_workload(
            data_dir=data_dir,
            output_dir=tmp_path / "output",
            payload_targets={"S": 8_000},
        )


def test_context_preflight_rejects_non_positive_or_inexact_budget() -> None:
    with pytest.raises(ValidationError, match="leaves no room"):
        ContextPreflightConstraint(
            context_window_tokens=2_000,
            reserved_output_tokens=1_000,
            prompt_token_upper_bound=1_000,
            max_reduced_artifact_bytes=1,
            final_bm25_top_k=2,
        )

    with pytest.raises(ValidationError, match="must equal"):
        ContextPreflightConstraint(
            context_window_tokens=8_000,
            reserved_output_tokens=1_000,
            prompt_token_upper_bound=1_000,
            max_reduced_artifact_bytes=5_999,
            final_bm25_top_k=2,
        )

    with pytest.raises(ValidationError, match="exceeds the fail-closed"):
        ContextPreflightConstraint(
            context_window_tokens=8_000,
            reserved_output_tokens=1_000,
            prompt_token_upper_bound=1_000,
            max_reduced_artifact_bytes=6_000,
            projected_reduced_artifact_upper_bound_bytes=6_001,
            final_bm25_top_k=2,
        )
