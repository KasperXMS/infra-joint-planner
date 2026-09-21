import json

import pytest

from infra_joint.core.action import SemanticAction
from infra_joint.operators.artifacts import store_json
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.operators.structured import register_structured_operators
from infra_joint.worker.artifact_store import ArtifactConflictError, InMemoryArtifactStore


def execute(
    registry: OperatorRegistry,
    operator: str,
    input_id: str,
    arguments: dict[str, object],
) -> None:
    registry.binding(operator).handler(
        SemanticAction(operator=operator, inputs=(input_id,), arguments=arguments)
    )


def records(store: InMemoryArtifactStore, artifact_id: str) -> list[dict[str, object]]:
    value = json.loads(store.get(artifact_id).content)
    assert isinstance(value, list)
    return value


def test_structured_operator_pipeline() -> None:
    store = InMemoryArtifactStore()
    store_json(
        store,
        "records",
        [
            {"team": "a", "revenue": 10, "cost": 4, "unused": 1},
            {"team": "a", "revenue": 7, "cost": 2, "unused": 2},
            {"team": "b", "revenue": 20, "cost": 15, "unused": 3},
        ],
    )
    registry = OperatorRegistry()
    register_structured_operators(registry, store)

    execute(
        registry,
        "filter_records",
        "records",
        {"field": "revenue", "op": "gte", "value": 7, "output_artifact_id": "filtered"},
    )
    execute(
        registry,
        "derive_fields",
        "filtered",
        {
            "derivations": [
                {"target": "profit", "operation": "subtract", "sources": ["revenue", "cost"]}
            ],
            "output_artifact_id": "derived",
        },
    )
    execute(
        registry,
        "aggregate_records",
        "derived",
        {
            "group_by": ["team"],
            "aggregations": [
                {"operation": "sum", "field": "profit", "output_field": "total_profit"},
                {"operation": "count", "output_field": "rows"},
            ],
            "output_artifact_id": "aggregated",
        },
    )
    execute(
        registry,
        "top_k_records",
        "aggregated",
        {"field": "total_profit", "k": 1, "output_artifact_id": "top"},
    )
    execute(
        registry,
        "select_fields",
        "top",
        {"fields": ["team", "total_profit"], "output_artifact_id": "selected"},
    )

    assert records(store, "aggregated") == [
        {"rows": 2, "team": "a", "total_profit": 11.0},
        {"rows": 1, "team": "b", "total_profit": 5.0},
    ]
    assert records(store, "selected") == [{"team": "a", "total_profit": 11.0}]


def test_aggregate_artifacts_preserves_input_order() -> None:
    store = InMemoryArtifactStore()
    store_json(store, "one", [{"id": 1}])
    store_json(store, "two", [{"id": 2}])
    registry = OperatorRegistry()
    register_structured_operators(registry, store)

    registry.binding("aggregate_artifacts").handler(
        SemanticAction(
            operator="aggregate_artifacts",
            inputs=("two", "one"),
            arguments={"output_artifact_id": "combined"},
        )
    )

    assert records(store, "combined") == [{"id": 2}, {"id": 1}]


def test_operator_cannot_silently_overwrite_artifact() -> None:
    store = InMemoryArtifactStore()
    store_json(store, "records", [{"id": 1}])
    store_json(store, "output", [{"existing": True}])
    registry = OperatorRegistry()
    register_structured_operators(registry, store)

    with pytest.raises(ArtifactConflictError, match="already contains different content"):
        execute(
            registry,
            "select_fields",
            "records",
            {"fields": ["id"], "output_artifact_id": "output"},
        )


def test_select_fields_rejects_missing_field_instead_of_dropping_it() -> None:
    store = InMemoryArtifactStore()
    store_json(store, "records", [{"id": 1}, {"id": 2, "name": "two"}])
    registry = OperatorRegistry()
    register_structured_operators(registry, store)

    with pytest.raises(ValueError, match="selected fields are missing"):
        execute(
            registry,
            "select_fields",
            "records",
            {"fields": ["id", "name"], "output_artifact_id": "output"},
        )
