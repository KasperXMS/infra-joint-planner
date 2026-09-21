from enum import StrEnum
from typing import Any

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


class ArtifactSpec(ContractModel):
    artifact_id: str = Field(min_length=1)
    logical_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
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
        return artifacts
