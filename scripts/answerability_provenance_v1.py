"""Source-local, gold-blind article index with record-level provenance.

This is a new study condition. Historical G1 shards and outcomes stay frozen.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast

MAX_DERIVED_INDEX_BYTES = 8 * 1024 * 1024
MAX_SELECTED_READ_BYTES = 262_144


def build_provenanced_index(
    residency: Iterable[Mapping[str, Any]],
    read_original: Callable[[str], bytes],
    *,
    producer: str,
    publisher_groups: frozenset[str],
) -> tuple[bytes, tuple[dict[str, str], ...]]:
    """Build an index from question-named publishers on one owning Worker."""
    if producer not in {"source-a", "source-b"} or not publisher_groups:
        raise ValueError("producer and publisher_groups must be explicit")
    records: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in residency:
        artifact_id = row["artifact_id"]
        if (
            row["resident_agent"] != producer
            or row["source_group"] not in publisher_groups
            or not artifact_id.startswith("multihop:")
        ):
            continue
        if artifact_id in seen:
            raise ValueError(f"duplicate original artifact ID: {artifact_id}")
        seen.add(artifact_id)
        content = read_original(artifact_id)
        digest = hashlib.sha256(content).hexdigest()
        if digest != row["content_hash"]:
            raise ValueError(f"original artifact hash mismatch: {artifact_id}")
        try:
            article_raw: object = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"original article is not JSON: {artifact_id}") from exc
        if not isinstance(article_raw, dict):
            raise ValueError(f"original article is not an object: {artifact_id}")
        article = cast(dict[str, Any], article_raw)
        if not isinstance(article.get("body"), str):
            raise ValueError(f"original article lacks string body: {artifact_id}")
        if not article["body"]:
            raise ValueError(f"original article body is empty: {artifact_id}")
        if not isinstance(article.get("url"), str) or not article["url"]:
            raise ValueError(f"original article lacks URL: {artifact_id}")
        records.append(
            {
                **article,
                "_origin_artifact_id": artifact_id,
                "_origin_content_sha256": digest,
                "_source_collection": row["source_group"],
                "_selection_operator": "bm25_retrieve",
                "_selected_representation": "full-article",
                "_producer": producer,
                "_consumer": "controller-via-source-b" if producer == "source-a" else "controller",
            }
        )
        sources.append(
            {
                "artifact_id": artifact_id,
                "sha256": digest,
                "source_group": row["source_group"],
            }
        )
    content = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if len(content) > MAX_DERIVED_INDEX_BYTES:
        raise ValueError("derived index exceeds bounded setup budget")
    return content, tuple(sources)


def validate_selected_records(
    records: Iterable[Mapping[str, Any]],
    residency: Iterable[Mapping[str, Any]],
    read_original: Callable[[str], bytes],
    *,
    producer: str,
    publisher_groups: frozenset[str],
) -> int:
    """Fail closed if a source-selected record loses original identity or version."""
    allowed = {
        row["artifact_id"]: row
        for row in residency
        if row["resident_agent"] == producer
        and row["source_group"] in publisher_groups
        and row["artifact_id"].startswith("multihop:")
    }
    count = 0
    seen: set[str] = set()
    for record in records:
        artifact_id = record.get("_origin_artifact_id")
        if not isinstance(artifact_id, str):
            raise ValueError("selected record lacks original artifact ID")
        row = allowed.get(artifact_id)
        if row is None:
            raise ValueError("selected record has unknown or shard-only provenance")
        if artifact_id in seen:
            raise ValueError("selected record has duplicate original artifact ID")
        seen.add(artifact_id)
        original = read_original(artifact_id)
        if hashlib.sha256(original).hexdigest() != row["content_hash"]:
            raise ValueError("selected record original artifact hash mismatch")
        try:
            article_raw: object = json.loads(original)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("selected record original article is not JSON") from exc
        if not isinstance(article_raw, dict):
            raise ValueError("selected record original article is not an object")
        article = cast(dict[str, Any], article_raw)
        if any(record.get(key) != value for key, value in article.items()):
            raise ValueError("selected record differs from original article")
        if (
            record.get("_origin_content_sha256") != row["content_hash"]
            or record.get("_source_collection") != row["source_group"]
            or record.get("_producer") != producer
            or record.get("_consumer")
            != ("controller-via-source-b" if producer == "source-a" else "controller")
            or record.get("_selection_operator") != "bm25_retrieve"
            or record.get("_selected_representation") != "full-article"
            or not isinstance(record.get("body"), str)
        ):
            raise ValueError("selected record provenance contract failed")
        count += 1
    return count


def require_readable_output(size_bytes: int, *, limit: int = MAX_SELECTED_READ_BYTES) -> None:
    if size_bytes < 0 or size_bytes > limit:
        raise ValueError(f"selected artifact exceeds bounded read limit: {size_bytes}>{limit}")
