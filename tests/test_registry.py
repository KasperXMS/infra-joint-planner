import pytest

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

    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec, handler)
