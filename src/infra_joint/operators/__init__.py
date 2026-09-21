"""Logical operator definitions and runtime bindings."""

from infra_joint.operators.builtin import invoke_model_spec, read_artifact_spec
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec

__all__ = [
    "OperatorRegistry",
    "OperatorSpec",
    "build_operator_catalog",
    "invoke_model_spec",
    "read_artifact_spec",
]
