from typing import Any

from infra_joint.operators.registry import OperatorSpec


def invoke_model_spec() -> OperatorSpec:
    return OperatorSpec(
        operator_id="invoke_model",
        description="Invoke a model deployment with a text prompt.",
        argument_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        capability_requirements=frozenset({"model"}),
    )


def unavailable_handler(*_: Any, **__: Any) -> None:
    """Marker binding: execution is delegated to a remote worker."""

    raise RuntimeError("operator must be executed by a worker")
