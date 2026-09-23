from pydantic import Field

from infra_joint.core.base import ContractModel


class InformationObjectRef(ContractModel):
    object_id: str = Field(min_length=1)
    producer_agent_id: str = Field(min_length=1)
    producer_node_id: str = Field(min_length=1)
    semantic_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)


class InformationObject(InformationObjectRef):
    """Typed logical information backed by the existing artifact substrate."""

    size_bytes: int = Field(ge=0)
    sha256_hex: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    locations: tuple[str, ...]
    provenance: tuple[str, ...] = ()

    def reference(self) -> InformationObjectRef:
        return InformationObjectRef(
            object_id=self.object_id,
            producer_agent_id=self.producer_agent_id,
            producer_node_id=self.producer_node_id,
            semantic_type=self.semantic_type,
            media_type=self.media_type,
        )
