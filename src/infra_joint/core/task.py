from enum import StrEnum
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from infra_joint.core.base import ContractModel


class OutputFormat(StrEnum):
    CHOICE = "choice"
    SHORT_TEXT = "short_text"
    JSON = "json"
    STRUCTURED = "structured"


class OutputContract(ContractModel):
    format: OutputFormat
    schema_definition: dict[str, Any] | None = Field(
        default=None,
        validation_alias="schema",
        serialization_alias="schema",
    )
    choices: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def validate_format_details(self) -> "OutputContract":
        if self.format == OutputFormat.CHOICE and not self.choices:
            raise ValueError("choice output requires non-empty choices")
        if self.format != OutputFormat.CHOICE and self.choices is not None:
            raise ValueError("choices are only valid for choice output")
        if self.format in {OutputFormat.JSON, OutputFormat.STRUCTURED}:
            if self.schema_definition is None:
                raise ValueError("structured output requires a schema")
        elif self.schema_definition is not None:
            raise ValueError("schema is only valid for json or structured output")
        return self


class ArtifactContentSchema(ContractModel):
    """Planner-safe semantic shape and bounded-size facts for one artifact.

    This is intentionally about content rather than storage. It must not contain a
    source URI, physical placement, or evaluator-private evidence.
    """

    kind: str = Field(min_length=1)
    fields: dict[str, str] = Field(default_factory=dict)
    text_field: str | None = Field(default=None, min_length=1)
    record_count: int | None = Field(default=None, ge=0)
    max_record_bytes: int | None = Field(default=None, ge=0)
    codec: str | None = Field(default=None, min_length=1)
    duration_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def text_field_is_declared(self) -> "ArtifactContentSchema":
        if self.text_field is not None and self.text_field not in self.fields:
            raise ValueError("artifact text_field must name a declared field")
        return self


class PartitionSemantics(StrEnum):
    NON_SEMANTIC = "non_semantic"
    SEMANTIC = "semantic"


class CollectionCompleteness(StrEnum):
    UNION_IS_COMPLETE = "union_is_complete"
    MEMBERS_ARE_INDEPENDENT = "members_are_independent"


class ArtifactCollectionRelation(ContractModel):
    """Planner-visible logical relationship between collection members.

    The relation describes information coverage only. It deliberately contains no
    source URI, placement, transfer, or infrastructure fields.
    """

    collection_id: str = Field(min_length=1)
    partition_index: int = Field(ge=0)
    partition_count: int = Field(gt=0)
    partition_method: str = Field(min_length=1)
    partition_semantics: PartitionSemantics
    completeness: CollectionCompleteness

    @model_validator(mode="after")
    def partition_index_is_in_range(self) -> Self:
        if self.partition_index >= self.partition_count:
            raise ValueError("partition_index must be less than partition_count")
        return self


class ArtifactSpec(ContractModel):
    artifact_id: str = Field(min_length=1)
    logical_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    content_schema: ArtifactContentSchema | None = None
    collection: ArtifactCollectionRelation | None = None
    source_ref: str | None = None


class TaskContract(ContractModel):
    task_id: str = Field(min_length=1)
    benchmark_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    artifacts: tuple[ArtifactSpec, ...]
    output_contract: OutputContract
    evaluator_id: str = Field(min_length=1)

    @field_validator("artifacts")
    @classmethod
    def artifact_ids_are_unique(
        cls, artifacts: tuple[ArtifactSpec, ...]
    ) -> tuple[ArtifactSpec, ...]:
        ids = [artifact.artifact_id for artifact in artifacts]
        if len(ids) != len(set(ids)):
            raise ValueError("artifact_id values must be unique")
        collections: dict[str, list[ArtifactCollectionRelation]] = {}
        for artifact in artifacts:
            if artifact.collection is not None:
                collections.setdefault(
                    artifact.collection.collection_id, []
                ).append(artifact.collection)
        for collection_id, members in collections.items():
            expected_count = members[0].partition_count
            signature = {
                (
                    member.partition_count,
                    member.partition_method,
                    member.partition_semantics,
                    member.completeness,
                )
                for member in members
            }
            if len(signature) != 1:
                raise ValueError(
                    f"collection members disagree on partition contract: {collection_id}"
                )
            indices = {member.partition_index for member in members}
            if members[0].completeness == CollectionCompleteness.UNION_IS_COMPLETE and (
                len(members) != expected_count or indices != set(range(expected_count))
            ):
                raise ValueError(
                    f"complete collection must declare every partition exactly once: "
                    f"{collection_id}"
                )
        return artifacts
