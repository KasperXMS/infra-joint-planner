from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from pydantic import Field

from infra_joint.core.base import ContractModel


class ArtifactNotFoundError(KeyError):
    pass


class ArtifactCorruptionError(RuntimeError):
    pass


class ArtifactConflictError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    artifact_id: str
    media_type: str
    content: bytes
    sha256_hex: str

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.media_type:
            raise ValueError("artifact_id and media_type must not be empty")
        actual = sha256(self.content).hexdigest()
        if self.sha256_hex != actual:
            raise ValueError("artifact checksum does not match content")

    @classmethod
    def create(cls, artifact_id: str, media_type: str, content: bytes) -> "StoredArtifact":
        return cls(
            artifact_id=artifact_id,
            media_type=media_type,
            content=content,
            sha256_hex=sha256(content).hexdigest(),
        )


class ArtifactStore(Protocol):
    def put(self, artifact: StoredArtifact) -> None: ...

    def get(self, artifact_id: str) -> StoredArtifact: ...

    def delete(self, artifact_id: str) -> bool: ...

    def ids(self) -> tuple[str, ...]: ...

    def metadata(self) -> tuple["ArtifactMetadata", ...]: ...


class InMemoryArtifactStore:
    def __init__(self, artifacts: tuple[StoredArtifact, ...] = ()) -> None:
        self._artifacts = {artifact.artifact_id: artifact for artifact in artifacts}

    def put(self, artifact: StoredArtifact) -> None:
        existing = self._artifacts.get(artifact.artifact_id)
        if existing is not None:
            if existing == artifact:
                return
            raise ArtifactConflictError(
                f"artifact ID already contains different content: {artifact.artifact_id}"
            )
        self._artifacts[artifact.artifact_id] = artifact

    def get(self, artifact_id: str) -> StoredArtifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(artifact_id) from exc

    def delete(self, artifact_id: str) -> bool:
        return self._artifacts.pop(artifact_id, None) is not None

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._artifacts))

    def metadata(self) -> tuple["ArtifactMetadata", ...]:
        return tuple(
            ArtifactMetadata(
                artifact_id=artifact.artifact_id,
                media_type=artifact.media_type,
                size_bytes=len(artifact.content),
                sha256_hex=artifact.sha256_hex,
            )
            for artifact in sorted(
                self._artifacts.values(), key=lambda item: item.artifact_id
            )
        )


class ArtifactMetadata(ContractModel):
    artifact_id: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256_hex: str = Field(pattern=r"^[0-9a-f]{64}$")


class FileArtifactStore:
    """Persistent store using hashed filenames so logical IDs cannot escape the root."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, artifact: StoredArtifact) -> None:
        blob_path, metadata_path = self._paths(artifact.artifact_id)
        if blob_path.exists() or metadata_path.exists():
            try:
                existing = self.get(artifact.artifact_id)
            except ArtifactNotFoundError as exc:
                raise ArtifactCorruptionError(
                    f"partial artifact exists: {artifact.artifact_id}"
                ) from exc
            if existing == artifact:
                return
            raise ArtifactConflictError(
                f"artifact ID already contains different content: {artifact.artifact_id}"
            )
        metadata = ArtifactMetadata(
            artifact_id=artifact.artifact_id,
            media_type=artifact.media_type,
            size_bytes=len(artifact.content),
            sha256_hex=artifact.sha256_hex,
        )
        blob_temp = blob_path.with_suffix(".blob.tmp")
        metadata_temp = metadata_path.with_suffix(".json.tmp")
        blob_temp.write_bytes(artifact.content)
        metadata_temp.write_text(metadata.model_dump_json(), encoding="utf-8")
        blob_temp.replace(blob_path)
        metadata_temp.replace(metadata_path)

    def get(self, artifact_id: str) -> StoredArtifact:
        blob_path, metadata_path = self._paths(artifact_id)
        if not blob_path.is_file() or not metadata_path.is_file():
            raise ArtifactNotFoundError(artifact_id)
        try:
            metadata = ArtifactMetadata.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except ValueError as exc:
            raise ArtifactCorruptionError(f"invalid metadata for artifact: {artifact_id}") from exc
        if metadata.artifact_id != artifact_id:
            raise ArtifactCorruptionError(f"artifact ID mismatch: {artifact_id}")
        content = blob_path.read_bytes()
        content_mismatch = (
            len(content) != metadata.size_bytes
            or sha256(content).hexdigest() != metadata.sha256_hex
        )
        if content_mismatch:
            raise ArtifactCorruptionError(f"artifact content mismatch: {artifact_id}")
        return StoredArtifact(
            artifact_id=metadata.artifact_id,
            media_type=metadata.media_type,
            content=content,
            sha256_hex=metadata.sha256_hex,
        )

    def ids(self) -> tuple[str, ...]:
        return tuple(item.artifact_id for item in self.metadata())

    def metadata(self) -> tuple[ArtifactMetadata, ...]:
        artifacts: list[ArtifactMetadata] = []
        for metadata_path in self._root.glob("*.json"):
            try:
                metadata = ArtifactMetadata.model_validate_json(
                    metadata_path.read_text(encoding="utf-8")
                )
            except ValueError as exc:
                raise ArtifactCorruptionError(
                    f"invalid artifact metadata file: {metadata_path.name}"
                ) from exc
            blob_path, expected_metadata_path = self._paths(metadata.artifact_id)
            if expected_metadata_path != metadata_path or not blob_path.is_file():
                raise ArtifactCorruptionError(
                    f"partial or misplaced artifact metadata: {metadata.artifact_id}"
                )
            if blob_path.stat().st_size != metadata.size_bytes:
                raise ArtifactCorruptionError(
                    f"artifact size mismatch: {metadata.artifact_id}"
                )
            artifacts.append(metadata)
        return tuple(sorted(artifacts, key=lambda item: item.artifact_id))

    def delete(self, artifact_id: str) -> bool:
        blob_path, metadata_path = self._paths(artifact_id)
        existed = blob_path.exists() or metadata_path.exists()
        blob_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        return existed

    def _paths(self, artifact_id: str) -> tuple[Path, Path]:
        if not artifact_id:
            raise ValueError("artifact_id must not be empty")
        key = sha256(artifact_id.encode("utf-8")).hexdigest()
        return self._root / f"{key}.blob", self._root / f"{key}.json"
