from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol


class ArtifactNotFoundError(KeyError):
    pass


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    artifact_id: str
    media_type: str
    content: bytes
    sha256_hex: str

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

    def ids(self) -> tuple[str, ...]: ...


class InMemoryArtifactStore:
    def __init__(self, artifacts: tuple[StoredArtifact, ...] = ()) -> None:
        self._artifacts = {artifact.artifact_id: artifact for artifact in artifacts}

    def put(self, artifact: StoredArtifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact

    def get(self, artifact_id: str) -> StoredArtifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(artifact_id) from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._artifacts))
