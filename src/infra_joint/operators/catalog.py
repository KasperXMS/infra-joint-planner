from infra_joint.operators.builtin import (
    invoke_model_spec,
    read_artifact_spec,
    unavailable_handler,
)
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.operators.retrieval import bm25_retrieve_spec
from infra_joint.operators.structured import structured_operator_specs


def build_operator_catalog() -> OperatorRegistry:
    """Build the planner/runtime catalog from the same immutable operator specs."""

    registry = OperatorRegistry()
    specs = (
        invoke_model_spec(),
        read_artifact_spec(),
        bm25_retrieve_spec(),
        *structured_operator_specs(),
    )
    for spec in specs:
        registry.register(spec, unavailable_handler)
    return registry
