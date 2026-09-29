from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Literal

from infra_joint.control.contracts import (
    StaticCapabilityContract,
    StaticModelCapabilityClass,
    StaticOperatorCapability,
)
from infra_joint.core.state import EnvironmentSpec
from infra_joint.operators.registry import OperatorRegistry

QualityClass = Literal["standard", "high_quality", "low_latency"]


def build_static_capability_contract(
    environment: EnvironmentSpec,
    registry: OperatorRegistry,
    available_operations: Iterable[str],
    *,
    deployment_quality_classes: Mapping[str, frozenset[QualityClass]] | None = None,
) -> StaticCapabilityContract:
    """Aggregate immutable semantic feasibility without exposing physical identities."""

    operations = tuple(sorted(set(available_operations)))
    unknown = tuple(item for item in operations if item not in registry)
    if unknown:
        raise ValueError(f"static capability contract references unknown operators: {unknown}")
    operators = tuple(
        _operator_capability(registry, operator)
        for operator in operations
    )

    agents = {item.agent_id: item for item in environment.agents}
    quality = dict(deployment_quality_classes or {})
    signatures: dict[
        tuple[
            tuple[str, ...],
            tuple[str, ...],
            int,
            int,
            tuple[QualityClass, ...],
        ],
        list[str],
    ] = defaultdict(list)
    for deployment in environment.deployments:
        host = agents[deployment.agent_id]
        signature = (
            tuple(sorted(deployment.modalities)),
            tuple(sorted(host.capabilities)),
            deployment.context_window,
            deployment.reserved_output_tokens,
            tuple(sorted(quality.get(deployment.deployment_id, frozenset()))),
        )
        signatures[signature].append(deployment.deployment_id)

    model_classes = tuple(
        StaticModelCapabilityClass(
            capability_class=f"model-class-{index:02d}",
            modalities=frozenset(signature[0]),
            capabilities=frozenset(signature[1]),
            context_window=signature[2],
            reserved_output_tokens=signature[3],
            quality_classes=frozenset(signature[4]),
        )
        for index, signature in enumerate(sorted(signatures), start=1)
    )
    return StaticCapabilityContract(
        operators=operators,
        model_classes=model_classes,
    )


def _operator_capability(
    registry: OperatorRegistry,
    operator: str,
) -> StaticOperatorCapability:
    spec = registry.binding(operator).spec
    return StaticOperatorCapability(
        operator=operator,
        description=spec.description,
        input_schema=spec.input_schema or {"type": "array"},
        argument_schema=spec.argument_schema or {"type": "object"},
        output_schema=spec.output_schema or {},
        required_capabilities=spec.capability_requirements,
    )
