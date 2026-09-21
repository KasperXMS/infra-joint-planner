import pytest

from infra_joint.worker.artifact_store import (
    ArtifactCorruptionError,
    FileArtifactStore,
    StoredArtifact,
)


def test_file_artifact_store_persists_across_instances(tmp_path) -> None:
    store = FileArtifactStore(tmp_path)
    artifact = StoredArtifact.create("../../logical/id", "text/plain", b"evidence")
    store.put(artifact)

    reopened = FileArtifactStore(tmp_path)
    assert reopened.ids() == ("../../logical/id",)
    assert reopened.get("../../logical/id") == artifact
    assert not (tmp_path.parent / "logical").exists()


def test_file_artifact_store_detects_tampering(tmp_path) -> None:
    store = FileArtifactStore(tmp_path)
    store.put(StoredArtifact.create("doc", "text/plain", b"original"))
    metadata_path = next(tmp_path.glob("*.json"))
    blob_path = tmp_path / f"{metadata_path.stem}.blob"
    blob_path.write_bytes(b"tampered")

    with pytest.raises(ArtifactCorruptionError, match="content mismatch"):
        store.get("doc")
