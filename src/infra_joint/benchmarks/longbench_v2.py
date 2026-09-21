import json
import math
import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from itertools import pairwise
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    PreparedArtifact,
    PrivateChoiceEvaluation,
    TransformationRecord,
    assess_validity,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract

LONGBENCH_V2_BENCHMARK_ID = "longbench_v2"
LONGBENCH_V2_EVALUATOR_ID = "longbench_v2_exact_choice_v1"
CHOICE_LABELS = ("A", "B", "C", "D")


class LongBenchV2Sample(ContractModel):
    sample_id: str = Field(
        min_length=1,
        validation_alias=AliasChoices("_id", "sample_id"),
        serialization_alias="_id",
    )
    domain: str = Field(min_length=1)
    sub_domain: str = Field(min_length=1)
    difficulty: Literal["easy", "hard"]
    length: Literal["short", "medium", "long"]
    question: str = Field(min_length=1)
    choice_A: str = Field(min_length=1)
    choice_B: str = Field(min_length=1)
    choice_C: str = Field(min_length=1)
    choice_D: str = Field(min_length=1)
    answer: Literal["A", "B", "C", "D"]
    context: str = Field(min_length=1)

    def choices(self) -> tuple[tuple[str, str], ...]:
        return (
            ("A", self.choice_A),
            ("B", self.choice_B),
            ("C", self.choice_C),
            ("D", self.choice_D),
        )


class IdentityContext(ContractModel):
    kind: Literal["identity"] = "identity"
    artifact_id: str = "context"


class MultiDocumentContext(ContractModel):
    kind: Literal["multi_document"] = "multi_document"
    delimiter: str = Field(min_length=1)
    artifact_prefix: str = Field(default="document", min_length=1)


class FixedWidthType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"


class FixedWidthColumn(ContractModel):
    name: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    value_type: FixedWidthType = FixedWidthType.STRING
    nullable: bool = False

    @model_validator(mode="after")
    def interval_is_positive(self) -> "FixedWidthColumn":
        if self.end_char <= self.start_char:
            raise ValueError("column end_char must be greater than start_char")
        return self


class FixedWidthStructuredContext(ContractModel):
    kind: Literal["fixed_width_structured"] = "fixed_width_structured"
    columns: tuple[FixedWidthColumn, ...] = Field(min_length=1)
    header_lines: int = Field(default=1, ge=0)
    artifact_id: str = Field(default="records", min_length=1)

    @field_validator("columns")
    @classmethod
    def columns_are_unique_and_non_overlapping(
        cls, columns: tuple[FixedWidthColumn, ...]
    ) -> tuple[FixedWidthColumn, ...]:
        names = [column.name for column in columns]
        if len(names) != len(set(names)):
            raise ValueError("fixed-width column names must be unique")
        ordered = sorted(columns, key=lambda column: column.start_char)
        if any(
            previous.end_char > current.start_char
            for previous, current in zip(ordered, ordered[1:], strict=False)
        ):
            raise ValueError("fixed-width columns must not overlap")
        return columns


ContextRepresentation = Annotated[
    IdentityContext | MultiDocumentContext | FixedWidthStructuredContext,
    Field(discriminator="kind"),
]


class LongBenchV2Adapter:
    def __init__(self, source_revision: str) -> None:
        if not source_revision:
            raise ValueError("source_revision must be pinned")
        self._source_revision = source_revision

    def adapt(
        self,
        sample: LongBenchV2Sample,
        representation: ContextRepresentation | None = None,
    ) -> AdaptationBundle:
        selected = representation or IdentityContext()
        prepared, transformation = self._adapt_context(sample, selected)
        task = TaskContract(
            task_id=sample.sample_id,
            benchmark_id=LONGBENCH_V2_BENCHMARK_ID,
            objective=self._objective(sample),
            artifacts=tuple(artifact.spec for artifact in prepared),
            output_contract=OutputContract(
                format=OutputFormat.CHOICE,
                choices=CHOICE_LABELS,
            ),
            evaluator_id=LONGBENCH_V2_EVALUATOR_ID,
        )
        execution = AdaptedExecutionCase(
            task=task,
            transformations=(transformation,),
            validity=assess_validity(
                (transformation,),
                query_equivalent=True,
                evaluator_equivalent=True,
            ),
        )
        private_evaluation = PrivateChoiceEvaluation(
            task_id=sample.sample_id,
            evaluator_id=LONGBENCH_V2_EVALUATOR_ID,
            gold_answer=sample.answer,
        )
        return AdaptationBundle(execution, private_evaluation, prepared)

    def _adapt_context(
        self,
        sample: LongBenchV2Sample,
        representation: ContextRepresentation,
    ) -> tuple[tuple[PreparedArtifact, ...], TransformationRecord]:
        if isinstance(representation, IdentityContext):
            content = sample.context.encode("utf-8")
            artifact = self._text_artifact(
                sample.sample_id,
                representation.artifact_id,
                "long_context",
                content,
            )
            digest = sha256(content).hexdigest()
            return (artifact,), self._record(
                sample,
                transformation="identity_context",
                audit={
                    "source_sha256": digest,
                    "adapted_sha256": digest,
                    "byte_count": len(content),
                },
            )
        if isinstance(representation, MultiDocumentContext):
            return self._split_documents(sample, representation)
        return self._convert_fixed_width(sample, representation)

    def _split_documents(
        self,
        sample: LongBenchV2Sample,
        representation: MultiDocumentContext,
    ) -> tuple[tuple[PreparedArtifact, ...], TransformationRecord]:
        starts = [0]
        starts.extend(
            match.start()
            for match in re.finditer(re.escape(representation.delimiter), sample.context)
            if match.start() != 0
        )
        boundaries = [*starts, len(sample.context)]
        documents: list[PreparedArtifact] = []
        for index, (start, end) in enumerate(pairwise(boundaries), start=1):
            content = sample.context[start:end].encode("utf-8")
            documents.append(
                self._text_artifact(
                    sample.sample_id,
                    f"{representation.artifact_prefix}-{index:04d}",
                    "document",
                    content,
                )
            )
        reconstructed = b"".join(document.content for document in documents)
        source = sample.context.encode("utf-8")
        information_preserved = reconstructed == source
        return tuple(documents), self._record(
            sample,
            transformation="deterministic_document_boundary_restoration",
            information_preserved=information_preserved,
            audit={
                "document_count": len(documents),
                "source_sha256": sha256(source).hexdigest(),
                "reconstructed_sha256": sha256(reconstructed).hexdigest(),
                "delimiter": representation.delimiter,
            },
        )

    def _convert_fixed_width(
        self,
        sample: LongBenchV2Sample,
        representation: FixedWidthStructuredContext,
    ) -> tuple[tuple[PreparedArtifact, ...], TransformationRecord]:
        lines = sample.context.splitlines()
        if len(lines) < representation.header_lines:
            raise ValueError("context has fewer lines than declared headers")
        if representation.header_lines:
            header = lines[representation.header_lines - 1]
            self._assert_columns_cover_line(
                header,
                representation.columns,
                representation.header_lines,
            )
            for column in representation.columns:
                actual = header[column.start_char : column.end_char].strip()
                if actual != column.name:
                    raise ValueError(f"fixed-width header does not match column: {column.name}")
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            lines[representation.header_lines :],
            start=representation.header_lines + 1,
        ):
            if not line.strip():
                continue
            self._assert_columns_cover_line(line, representation.columns, line_number)
            record = {
                column.name: self._parse_fixed_width_value(
                    line[column.start_char : column.end_char].strip(),
                    column,
                    line_number,
                )
                for column in representation.columns
            }
            records.append(record)
        content = json.dumps(
            records,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        artifact = self._json_artifact(
            sample.sample_id,
            representation.artifact_id,
            content,
        )
        return (artifact,), self._record(
            sample,
            transformation="fixed_width_text_to_typed_json_records",
            audit={
                "source_record_count": len(records),
                "adapted_record_count": len(records),
                "columns": [column.name for column in representation.columns],
                "columns_preserved": True,
                "values_preserved": True,
                "numeric_normalization": "deterministic",
                "adapted_sha256": artifact.sha256_hex,
            },
        )

    @staticmethod
    def _assert_columns_cover_line(
        line: str,
        columns: tuple[FixedWidthColumn, ...],
        line_number: int,
    ) -> None:
        covered = [False] * len(line)
        for column in columns:
            for index in range(column.start_char, min(column.end_char, len(line))):
                covered[index] = True
        remainder = "".join(character for index, character in enumerate(line) if not covered[index])
        if remainder.strip():
            raise ValueError(f"unmapped fixed-width data on line {line_number}")

    @staticmethod
    def _parse_fixed_width_value(
        raw: str,
        column: FixedWidthColumn,
        line_number: int,
    ) -> str | int | float | None:
        if column.value_type == FixedWidthType.STRING:
            return raw
        if not raw:
            if column.nullable:
                return None
            raise ValueError(f"empty numeric value for {column.name} on line {line_number}")
        if column.value_type == FixedWidthType.INTEGER:
            if re.fullmatch(r"[+-]?\d+", raw) is None:
                raise ValueError(f"invalid integer for {column.name} on line {line_number}")
            return int(raw)
        try:
            decimal = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(f"invalid number for {column.name} on line {line_number}") from exc
        if not decimal.is_finite():
            raise ValueError(f"non-finite number for {column.name} on line {line_number}")
        converted = float(decimal)
        if not math.isfinite(converted) or Decimal(str(converted)) != decimal:
            raise ValueError(f"number loses precision for {column.name} on line {line_number}")
        return converted

    def _record(
        self,
        sample: LongBenchV2Sample,
        *,
        transformation: str,
        audit: dict[str, Any],
        information_preserved: bool = True,
    ) -> TransformationRecord:
        return TransformationRecord(
            benchmark_id=LONGBENCH_V2_BENCHMARK_ID,
            source_revision=self._source_revision,
            source_task_id=sample.sample_id,
            transformation=transformation,
            information_preserved=information_preserved,
            order_preserved=True,
            gold_independent=True,
            notes="Context representation changed without exposing a derived execution plan.",
            audit=audit,
        )

    @staticmethod
    def _text_artifact(
        sample_id: str,
        artifact_id: str,
        logical_type: str,
        content: bytes,
    ) -> PreparedArtifact:
        spec = ArtifactSpec(
            artifact_id=artifact_id,
            logical_type=logical_type,
            media_type="text/plain",
            size_bytes=len(content),
            source_ref=f"prepared://longbench-v2/{sample_id}/{artifact_id}",
        )
        return PreparedArtifact.create(spec, content)

    @staticmethod
    def _json_artifact(
        sample_id: str,
        artifact_id: str,
        content: bytes,
    ) -> PreparedArtifact:
        spec = ArtifactSpec(
            artifact_id=artifact_id,
            logical_type="structured_records",
            media_type="application/json",
            size_bytes=len(content),
            source_ref=f"prepared://longbench-v2/{sample_id}/{artifact_id}",
        )
        return PreparedArtifact.create(spec, content)

    @staticmethod
    def _objective(sample: LongBenchV2Sample) -> str:
        choices = "\n".join(f"{label}. {text}" for label, text in sample.choices())
        return f"{sample.question}\n\n{choices}"
