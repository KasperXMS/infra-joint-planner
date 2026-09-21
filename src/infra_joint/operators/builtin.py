from typing import Any

from infra_joint.operators.registry import OperatorSpec


def invoke_model_spec() -> OperatorSpec:
    return OperatorSpec(
        operator_id="invoke_model",
        description="Invoke a model deployment with a prompt and optional text/image artifacts.",
        input_schema={
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 64,
        },
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


def read_artifact_spec() -> OperatorSpec:
    return OperatorSpec(
        operator_id="read_artifact",
        description=(
            "Read only small control or metadata text into planner context. Do not use this "
            "for benchmark evidence intended for model reasoning or for large artifacts."
        ),
        input_schema={
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 1,
        },
        argument_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    )


def unavailable_handler(*_: Any, **__: Any) -> None:
    """Marker binding: execution is delegated to a remote worker."""

    raise RuntimeError("operator must be executed by a worker")
