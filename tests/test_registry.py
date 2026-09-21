import pytest

from infra_joint.core.action import SemanticAction
from infra_joint.operators.builtin import invoke_model_spec
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec


def test_registry_drives_planner_schema_and_runtime_binding() -> None:
    registry = OperatorRegistry()

    def handler() -> str:
        return "ok"

    spec = OperatorSpec(
        operator_id="read_artifact",
        description="Read a logical artifact",
        argument_schema={
            "type": "object",
            "properties": {"artifact_id": {"type": "string"}},
            "required": ["artifact_id"],
            "additionalProperties": False,
        },
    )
    registry.register(spec, handler)

    assert registry.binding("read_artifact").handler() == "ok"
    assert registry.planner_tools()[0]["function"]["name"] == "read_artifact"
    parameters = registry.planner_tools()[0]["function"]["parameters"]
    assert set(parameters["properties"]) == {"inputs", "arguments"}

    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec, handler)


def test_registry_validates_planner_action_against_operator_schema() -> None:
    registry = OperatorRegistry()
    registry.register(invoke_model_spec(), lambda: None)

    registry.validate_action(SemanticAction(operator="invoke_model", arguments={"prompt": "hello"}))

    with pytest.raises(ValueError, match="required property"):
        registry.validate_action(SemanticAction(operator="invoke_model"))

    with pytest.raises(ValueError, match="inputs"):
        registry.validate_action(
            SemanticAction(
                operator="invoke_model",
                inputs=("unexpected",),
                arguments={"prompt": "hello"},
            )
        )
