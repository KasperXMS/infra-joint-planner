from collections import defaultdict
from enum import StrEnum
from math import prod
from typing import Any

from pydantic import Field, model_validator

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.operators.artifacts import load_records, store_json
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.worker.artifact_store import ArtifactStore


class ComparisonOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    CONTAINS = "contains"


class FilterArguments(ContractModel):
    field: str = Field(min_length=1)
    op: ComparisonOperator
    value: Any
    output_artifact_id: str = Field(min_length=1)


class SelectFieldsArguments(ContractModel):
    fields: tuple[str, ...] = Field(min_length=1)
    output_artifact_id: str = Field(min_length=1)


class DeriveOperation(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class Derivation(ContractModel):
    target: str = Field(min_length=1)
    operation: DeriveOperation
    sources: tuple[str, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def source_count_matches_operation(self) -> "Derivation":
        if (
            self.operation in {DeriveOperation.SUBTRACT, DeriveOperation.DIVIDE}
            and len(self.sources) != 2
        ):
            raise ValueError(f"{self.operation} requires exactly two sources")
        return self


class DeriveFieldsArguments(ContractModel):
    derivations: tuple[Derivation, ...] = Field(min_length=1)
    output_artifact_id: str = Field(min_length=1)


class AggregateOperation(StrEnum):
    COUNT = "count"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    AVG = "avg"


class Aggregation(ContractModel):
    operation: AggregateOperation
    output_field: str = Field(min_length=1)
    field: str | None = None

    @model_validator(mode="after")
    def field_is_present_when_required(self) -> "Aggregation":
        if self.operation != AggregateOperation.COUNT and self.field is None:
            raise ValueError(f"{self.operation} requires a field")
        return self


class AggregateRecordsArguments(ContractModel):
    group_by: tuple[str, ...] = ()
    aggregations: tuple[Aggregation, ...] = Field(min_length=1)
    output_artifact_id: str = Field(min_length=1)


class TopKArguments(ContractModel):
    field: str = Field(min_length=1)
    k: int = Field(gt=0)
    descending: bool = True
    output_artifact_id: str = Field(min_length=1)


class AggregateArtifactsArguments(ContractModel):
    output_artifact_id: str = Field(min_length=1)


def _single_input(action: SemanticAction) -> str:
    if len(action.inputs) != 1:
        raise ValueError(f"{action.operator} requires exactly one input artifact")
    return action.inputs[0]


def _compare(actual: Any, operator: ComparisonOperator, expected: Any) -> bool:
    if operator == ComparisonOperator.EQ:
        return actual == expected
    if operator == ComparisonOperator.NE:
        return actual != expected
    if operator == ComparisonOperator.CONTAINS:
        if not isinstance(actual, (str, list, tuple, dict)):
            raise ValueError("contains requires a string, array, or object field")
        return expected in actual
    try:
        if operator == ComparisonOperator.LT:
            return actual < expected
        if operator == ComparisonOperator.LTE:
            return actual <= expected
        if operator == ComparisonOperator.GT:
            return actual > expected
        if operator == ComparisonOperator.GTE:
            return actual >= expected
    except TypeError as exc:
        raise ValueError("comparison operands have incompatible types") from exc
    raise ValueError(f"unsupported comparison operator: {operator}")


def _numeric(record: dict[str, Any], field: str) -> float:
    value = record.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"field must be numeric: {field}")
    return float(value)


def _apply_aggregation(records: list[dict[str, Any]], aggregation: Aggregation) -> Any:
    if aggregation.operation == AggregateOperation.COUNT:
        return len(records)
    if aggregation.field is None:
        raise ValueError("aggregation field is required")
    values = [_numeric(record, aggregation.field) for record in records]
    if not values:
        return None
    if aggregation.operation == AggregateOperation.SUM:
        return sum(values)
    if aggregation.operation == AggregateOperation.MIN:
        return min(values)
    if aggregation.operation == AggregateOperation.MAX:
        return max(values)
    if aggregation.operation == AggregateOperation.AVG:
        return sum(values) / len(values)
    raise ValueError(f"unsupported aggregation operation: {aggregation.operation}")


def _operator_spec(
    operator_id: str,
    description: str,
    argument_model: type[ContractModel],
) -> OperatorSpec:
    return OperatorSpec(
        operator_id=operator_id,
        description=description,
        input_schema={
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        argument_schema=argument_model.model_json_schema(),
        output_schema={"$ref": "ProducedArtifact"},
        capability_requirements=frozenset({"structured"}),
    )


def structured_operator_specs() -> tuple[OperatorSpec, ...]:
    return (
        _operator_spec(
            "filter_records",
            "Filter JSON records by one predicate.",
            FilterArguments,
        ),
        _operator_spec(
            "select_fields",
            "Project declared fields from JSON records without shortening field values.",
            SelectFieldsArguments,
        ),
        _operator_spec(
            "derive_fields",
            "Derive numeric fields without arbitrary code execution.",
            DeriveFieldsArguments,
        ),
        _operator_spec(
            "aggregate_records",
            "Group and aggregate JSON records.",
            AggregateRecordsArguments,
        ),
        _operator_spec(
            "top_k_records",
            "Select top-k JSON records by a field.",
            TopKArguments,
        ),
        _operator_spec(
            "aggregate_artifacts",
            (
                "Concatenate complete record arrays from JSON artifacts. This preserves all "
                "records and does not summarize, truncate, group, or reduce their size."
            ),
            AggregateArtifactsArguments,
        ),
    )


def register_structured_operators(registry: OperatorRegistry, store: ArtifactStore) -> None:
    def filter_records(action: SemanticAction) -> dict[str, Any]:
        arguments = FilterArguments.model_validate(action.arguments)
        records = load_records(store, _single_input(action))
        if any(arguments.field not in record for record in records):
            raise ValueError(f"filter field is missing: {arguments.field}")
        filtered = [
            record
            for record in records
            if _compare(record.get(arguments.field), arguments.op, arguments.value)
        ]
        return store_json(store, arguments.output_artifact_id, filtered).model_dump()

    def select_fields(action: SemanticAction) -> dict[str, Any]:
        arguments = SelectFieldsArguments.model_validate(action.arguments)
        records = load_records(store, _single_input(action))
        missing = {field for record in records for field in arguments.fields if field not in record}
        if missing:
            raise ValueError(f"selected fields are missing: {sorted(missing)}")
        selected = [{field: record[field] for field in arguments.fields} for record in records]
        return store_json(store, arguments.output_artifact_id, selected).model_dump()

    def derive_fields(action: SemanticAction) -> dict[str, Any]:
        arguments = DeriveFieldsArguments.model_validate(action.arguments)
        records = load_records(store, _single_input(action))
        derived: list[dict[str, Any]] = []
        for original in records:
            record = dict(original)
            for derivation in arguments.derivations:
                values = [_numeric(record, field) for field in derivation.sources]
                if derivation.operation == DeriveOperation.ADD:
                    result = sum(values)
                elif derivation.operation == DeriveOperation.SUBTRACT:
                    result = values[0] - values[1]
                elif derivation.operation == DeriveOperation.MULTIPLY:
                    result = prod(values)
                else:
                    if values[1] == 0:
                        raise ValueError("division by zero")
                    result = values[0] / values[1]
                record[derivation.target] = result
            derived.append(record)
        return store_json(store, arguments.output_artifact_id, derived).model_dump()

    def aggregate_records(action: SemanticAction) -> dict[str, Any]:
        arguments = AggregateRecordsArguments.model_validate(action.arguments)
        records = load_records(store, _single_input(action))
        grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            missing = [field for field in arguments.group_by if field not in record]
            if missing:
                raise ValueError(f"group-by fields are missing: {missing}")
            try:
                key = tuple(record[field] for field in arguments.group_by)
                grouped[key].append(record)
            except TypeError as exc:
                raise ValueError("group-by fields must contain scalar values") from exc
        if not records and not arguments.group_by:
            grouped[()] = []
        output: list[dict[str, Any]] = []
        for key, group in grouped.items():
            row = dict(zip(arguments.group_by, key, strict=True))
            for aggregation in arguments.aggregations:
                row[aggregation.output_field] = _apply_aggregation(group, aggregation)
            output.append(row)
        return store_json(store, arguments.output_artifact_id, output).model_dump()

    def top_k_records(action: SemanticAction) -> dict[str, Any]:
        arguments = TopKArguments.model_validate(action.arguments)
        records = load_records(store, _single_input(action))
        if any(arguments.field not in record for record in records):
            raise ValueError(f"top-k field is missing: {arguments.field}")
        values = [record[arguments.field] for record in records]
        numbers = all(
            isinstance(value, (int, float)) and not isinstance(value, bool) for value in values
        )
        strings = all(isinstance(value, str) for value in values)
        if values and not (numbers or strings):
            raise ValueError("top-k field values must be consistently numeric or string")
        ranked = sorted(
            records,
            key=lambda record: record[arguments.field],
            reverse=arguments.descending,
        )
        return store_json(store, arguments.output_artifact_id, ranked[: arguments.k]).model_dump()

    def aggregate_artifacts(action: SemanticAction) -> dict[str, Any]:
        arguments = AggregateArtifactsArguments.model_validate(action.arguments)
        if not action.inputs:
            raise ValueError("aggregate_artifacts requires at least one input")
        records = [
            record for artifact_id in action.inputs for record in load_records(store, artifact_id)
        ]
        return store_json(store, arguments.output_artifact_id, records).model_dump()

    handlers = {
        "filter_records": filter_records,
        "select_fields": select_fields,
        "derive_fields": derive_fields,
        "aggregate_records": aggregate_records,
        "top_k_records": top_k_records,
        "aggregate_artifacts": aggregate_artifacts,
    }
    for spec in structured_operator_specs():
        registry.register(spec, handlers[spec.operator_id])
