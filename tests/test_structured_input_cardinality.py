from typing import Any

import pytest
from jsonschema import Draft202012Validator

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import LogicalToolAction
from infra_joint.control.native_agents import _native_tool_schema
from infra_joint.control.validation import SemanticActionValidator, SemanticValidationError
from infra_joint.core.action import SemanticAction
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.operators.registry import OperatorInputValidationError

SINGLE_INPUT_ARGUMENTS: dict[str, dict[str, Any]] = {
    "filter_records": {"field": "body", "op": "contains", "value": "needle"},
    "select_fields": {"fields": ["body"]},
    "derive_fields": {
        "derivations": [{"target": "total", "operation": "add", "sources": ["x", "y"]}],
    },
    "aggregate_records": {
        "aggregations": [{"operation": "count", "output_field": "count"}],
    },
    "top_k_records": {"field": "x", "k": 1},
}


@pytest.mark.parametrize("operator", SINGLE_INPUT_ARGUMENTS)
def test_single_input_structured_contract_matches_runtime_cardinality(operator: str) -> None:
    registry = build_operator_catalog()
    spec = registry.binding(operator).spec
    arguments = {**SINGLE_INPUT_ARGUMENTS[operator], "output_artifact_id": "result"}
    assert spec.input_schema["minItems"] == spec.input_schema["maxItems"] == 1
    registry.validate_action(
        SemanticAction(operator=operator, inputs=("one",), arguments=arguments)
    )
    for inputs in ((), ("one", "two"), ("one", "two", "three")):
        with pytest.raises(OperatorInputValidationError):
            registry.validate_action(
                SemanticAction(operator=operator, inputs=inputs, arguments=arguments)
            )


@pytest.mark.parametrize("operator", SINGLE_INPUT_ARGUMENTS)
def test_sdk_and_anonymous_static_view_expose_same_single_input_constraint(operator: str) -> None:
    registry = build_operator_catalog()
    spec = registry.binding(operator).spec
    schema = _native_tool_schema(spec)
    contract = build_static_capability_contract(
        EnvironmentSpec(agents=(), deployments=()),
        registry,
        (operator,),
    )
    assert schema["properties"]["inputs"] == contract.operators[0].input_schema == spec.input_schema
    arguments = {**SINGLE_INPUT_ARGUMENTS[operator], "output_artifact_id": "result"}
    validator = Draft202012Validator(schema)
    assert validator.is_valid({"inputs": ["one"], "arguments": arguments})
    assert not validator.is_valid({"inputs": ["one", "two", "three"], "arguments": arguments})


@pytest.mark.parametrize("operator", SINGLE_INPUT_ARGUMENTS)
def test_invalid_cardinality_is_rejected_before_physical_execution(operator: str) -> None:
    registry = build_operator_catalog()
    task = TaskContract(
        task_id="synthetic",
        benchmark_id="synthetic",
        objective="Test generic contracts",
        evaluator_id="private",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=name,
                logical_type="records",
                media_type="application/json",
                size_bytes=2,
            )
            for name in ("one", "two", "three")
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
    )
    validator = SemanticActionValidator(task, registry, (operator,))
    arguments = {**SINGLE_INPUT_ARGUMENTS[operator], "output_artifact_id": "result"}
    valid = LogicalToolAction(
        action_id="valid",
        owner_agent_id="manager",
        operator=operator,
        inputs=("one",),
        arguments=arguments,
    )
    validator.validate_batch((valid,))
    invalid = valid.model_copy(update={"action_id": "invalid", "inputs": ("one", "two", "three")})
    with pytest.raises(SemanticValidationError, match="violates inputs"):
        validator.validate_batch((invalid,))
    assert validator.known_artifacts == frozenset({"one", "two", "three"})
    assert validator.producer_of("result") is None


def test_aggregate_artifacts_remains_multi_input_in_every_contract() -> None:
    registry = build_operator_catalog()
    spec = registry.binding("aggregate_artifacts").spec
    assert "maxItems" not in spec.input_schema
    action = SemanticAction(
        operator="aggregate_artifacts",
        inputs=("one", "two", "three"),
        arguments={"output_artifact_id": "result"},
    )
    registry.validate_action(action)
    assert Draft202012Validator(_native_tool_schema(spec)).is_valid(
        {"inputs": list(action.inputs), "arguments": action.arguments},
    )
