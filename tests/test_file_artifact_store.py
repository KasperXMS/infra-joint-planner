import pytest

from infra_joint.worker.artifact_store import (
    ArtifactCorruptionError,
    ArtifactMetadata,
    FileArtifactStore,
    StoredArtifact,
)


def test_file_artifact_store_persists_across_instances(tmp_path) -> None:
    store = FileArtifactStore(tmp_path)
    artifact = StoredArtifact.create("../../logical/id", "text/plain", b"evidence")
    store.put(artifact)

    reopened = FileArtifactStore(tmp_path)
    assert reopened.ids() == ("../../logical/id",)
    assert reopened.metadata() == (
        ArtifactMetadata(
            artifact_id="../../logical/id",
            media_type="text/plain",
            size_bytes=8,
            sha256_hex=artifact.sha256_hex,
        ),
    )
    assert reopened.get("../../logical/id") == artifact
    assert not (tmp_path.parent / "logical").exists()


def test_file_artifact_store_delete_is_idempotent_and_root_confined(tmp_path) -> None:
    store = FileArtifactStore(tmp_path)
    store.put(StoredArtifact.create("../../logical/id", "text/plain", b"evidence"))

    assert store.delete("../../logical/id") is True
    assert store.delete("../../logical/id") is False
    assert store.ids() == ()
    assert not (tmp_path.parent / "logical").exists()


def test_file_artifact_store_detects_tampering(tmp_path) -> None:
    store = FileArtifactStore(tmp_path)
    store.put(StoredArtifact.create("doc", "text/plain", b"original"))
    metadata_path = next(tmp_path.glob("*.json"))
    blob_path = tmp_path / f"{metadata_path.stem}.blob"
    blob_path.write_bytes(b"tampered")

    with pytest.raises(ArtifactCorruptionError, match="content mismatch"):
        store.get("doc")


def test_file_artifact_store_metadata_detects_size_mismatch_without_reading_blob(
    tmp_path,
) -> None:
    store = FileArtifactStore(tmp_path)
    store.put(StoredArtifact.create("doc", "text/plain", b"original"))
    metadata_path = next(tmp_path.glob("*.json"))
    blob_path = tmp_path / f"{metadata_path.stem}.blob"
    blob_path.write_bytes(b"different-size")

    with pytest.raises(ArtifactCorruptionError, match="size mismatch"):
        store.metadata()
