from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import Field

from infra_joint.core.base import ContractModel

OperatorHandler = Callable[..., Any]


class OperatorSpec(ContractModel):
    operator_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    argument_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    capability_requirements: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class OperatorBinding:
    spec: OperatorSpec
    handler: OperatorHandler


class OperatorRegistry:
    """Single source of truth for planner-visible tools and runtime handlers."""

    def __init__(self) -> None:
        self._bindings: dict[str, OperatorBinding] = {}

    def register(self, spec: OperatorSpec, handler: OperatorHandler) -> None:
        if spec.operator_id in self._bindings:
            raise ValueError(f"operator already registered: {spec.operator_id}")
        self._bindings[spec.operator_id] = OperatorBinding(spec=spec, handler=handler)

    def binding(self, operator_id: str) -> OperatorBinding:
        try:
            return self._bindings[operator_id]
        except KeyError as exc:
            raise KeyError(f"unknown operator: {operator_id}") from exc

    def specs(self) -> Mapping[str, OperatorSpec]:
        return {key: binding.spec for key, binding in self._bindings.items()}

    def planner_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for operator_id in sorted(self._bindings):
            spec = self._bindings[operator_id].spec
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.operator_id,
                        "description": spec.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "inputs": spec.input_schema
                                or {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "arguments": spec.argument_schema,
                            },
                            "required": ["inputs", "arguments"],
                            "additionalProperties": False,
                        },
                    },
                }
            )
        return tools

    def __contains__(self, operator_id: object) -> bool:
        return operator_id in self._bindings

    def __iter__(self) -> Iterator[str]:
        return iter(self._bindings)

    def __len__(self) -> int:
        return len(self._bindings)
