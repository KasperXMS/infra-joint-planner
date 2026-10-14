import hashlib
import json

import httpx
import pytest

from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.server import create_worker_app
from scripts.answerability_provenance_v1 import (
    MAX_SELECTED_READ_BYTES,
    build_provenanced_index,
    require_readable_output,
    validate_selected_records,
)


def fixture_source():
    articles = {
        "multihop:a": {"body": "first complete body", "url": "https://example.org/a", "title": "A"},
        "multihop:b": {
            "body": "second complete body",
            "url": "https://example.org/b",
            "title": "B",
        },
    }
    blobs = {key: json.dumps(value).encode() for key, value in articles.items()}
    residency = [
        {
            "artifact_id": key,
            "resident_agent": "source-a",
            "source_group": "publisher-one",
            "content_hash": hashlib.sha256(value).hexdigest(),
        }
        for key, value in blobs.items()
    ]
    return residency, blobs


def test_source_local_index_preserves_identity_and_full_original_content():
    residency, blobs = fixture_source()
    content, sources = build_provenanced_index(
        residency,
        blobs.__getitem__,
        producer="source-a",
        publisher_groups=frozenset({"publisher-one"}),
    )
    records = json.loads(content)
    assert len(records) == len(sources) == 2
    assert (
        validate_selected_records(
            records,
            residency,
            blobs.__getitem__,
            producer="source-a",
            publisher_groups=frozenset({"publisher-one"}),
        )
        == 2
    )
    assert {record["_origin_artifact_id"] for record in records} == set(blobs)
    assert all(record["_selected_representation"] == "full-article" for record in records)
    assert "gold" not in content.decode().lower()


@pytest.mark.parametrize(
    "field,value",
    [
        ("_origin_artifact_id", "shard-only"),
        ("_origin_content_sha256", "wrong"),
        ("_source_collection", "other-publisher"),
        ("_consumer", "unknown"),
        ("body", "tampered"),
    ],
)
def test_selected_record_fails_closed_on_provenance_or_body_change(field, value):
    residency, blobs = fixture_source()
    content, _ = build_provenanced_index(
        residency,
        blobs.__getitem__,
        producer="source-a",
        publisher_groups=frozenset({"publisher-one"}),
    )
    records = json.loads(content)
    records[0][field] = value
    with pytest.raises(ValueError):
        validate_selected_records(
            records,
            residency,
            blobs.__getitem__,
            producer="source-a",
            publisher_groups=frozenset({"publisher-one"}),
        )


def test_original_hash_and_duplicate_selection_fail_closed():
    residency, blobs = fixture_source()
    wrong = [dict(row) for row in residency]
    wrong[0]["content_hash"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        build_provenanced_index(
            wrong,
            blobs.__getitem__,
            producer="source-a",
            publisher_groups=frozenset({"publisher-one"}),
        )
    content, _ = build_provenanced_index(
        residency,
        blobs.__getitem__,
        producer="source-a",
        publisher_groups=frozenset({"publisher-one"}),
    )
    selected = json.loads(content)
    with pytest.raises(ValueError, match="duplicate"):
        validate_selected_records(
            selected + selected[:1],
            residency,
            blobs.__getitem__,
            producer="source-a",
            publisher_groups=frozenset({"publisher-one"}),
        )


def test_bounded_selected_artifact_limit():
    require_readable_output(91_164)
    require_readable_output(MAX_SELECTED_READ_BYTES)
    with pytest.raises(ValueError, match="bounded read limit"):
        require_readable_output(MAX_SELECTED_READ_BYTES + 1)


@pytest.mark.asyncio
async def test_worker_read_limit_accepts_historical_size_and_rejects_oversize():
    inside = b"a" * 91_164
    outside = b"b" * (MAX_SELECTED_READ_BYTES + 1)
    store = InMemoryArtifactStore(
        (
            StoredArtifact.create("inside", "text/plain", inside),
            StoredArtifact.create("outside", "text/plain", outside),
        )
    )
    app = create_worker_app(
        "worker", {}, artifact_store=store, max_read_artifact_bytes=MAX_SELECTED_READ_BYTES
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as client:

        async def read(artifact_id):
            return await client.post(
                "/execute/operator",
                json={
                    "action": {
                        "operator": "read_artifact",
                        "inputs": [artifact_id],
                        "arguments": {},
                    }
                },
            )

        accepted = await read("inside")
        rejected = await read("outside")
    assert accepted.status_code == 200
    assert rejected.status_code == 413
    assert rejected.json()["detail"]["code"] == "artifact_too_large"
    assert store.get("inside").sha256_hex == hashlib.sha256(inside).hexdigest()
