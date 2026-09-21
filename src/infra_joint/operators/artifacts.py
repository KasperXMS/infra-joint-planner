import json
from typing import Any

from pydantic import Field, TypeAdapter, ValidationError

from infra_joint.core.base import ContractModel
from infra_joint.worker.artifact_store import ArtifactStore, StoredArtifact

RECORDS_ADAPTER = TypeAdapter(list[dict[str, Any]])


class ProducedArtifact(ContractModel):
    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256_hex: str = Field(pattern=r"^[0-9a-f]{64}$")


def load_json(store: ArtifactStore, artifact_id: str) -> Any:
    artifact = store.get(artifact_id)
    if artifact.media_type not in {"application/json", "application/jsonl"}:
        raise ValueError(f"artifact is not JSON: {artifact_id}")
    try:
        return json.loads(artifact.content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"artifact contains invalid JSON: {artifact_id}") from exc


def load_records(store: ArtifactStore, artifact_id: str) -> list[dict[str, Any]]:
    value = load_json(store, artifact_id)
    try:
        return RECORDS_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ValueError(f"artifact must contain a JSON array of objects: {artifact_id}") from exc


def store_json(store: ArtifactStore, artifact_id: str, value: Any) -> ProducedArtifact:
    content = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    artifact = StoredArtifact.create(artifact_id, "application/json", content)
    store.put(artifact)
    return ProducedArtifact(
        artifact_id=artifact.artifact_id,
        media_type=artifact.media_type,
        size_bytes=len(artifact.content),
        sha256_hex=artifact.sha256_hex,
    )
