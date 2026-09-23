import hashlib
import json
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import Field

from infra_joint.core.action import SemanticAction
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


class OperatorInputValidationError(ValueError):
    pass


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

    def contract_digests(self) -> dict[str, str]:
        """Return deterministic hashes of every registered operator contract."""

        return {
            operator_id: hashlib.sha256(
                json.dumps(
                    binding.spec.model_dump(mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            for operator_id, binding in sorted(self._bindings.items())
        }

    def validate_action(self, action: SemanticAction) -> None:
        spec = self.binding(action.operator).spec
        input_schema = spec.input_schema or {
            "type": "array",
            "items": {"type": "string"},
        }
        self._validate_instance(
            list(action.inputs),
            input_schema,
            operator_id=action.operator,
            field="inputs",
        )
        self._validate_instance(
            action.arguments,
            spec.argument_schema or {"type": "object"},
            operator_id=action.operator,
            field="arguments",
        )

    @staticmethod
    def _validate_instance(
        instance: Any,
        schema: dict[str, Any],
        *,
        operator_id: str,
        field: str,
    ) -> None:
        validator = Draft202012Validator(schema)
        errors = cast(
            Iterator[JsonSchemaValidationError],
            validator.iter_errors(instance),  # pyright: ignore[reportUnknownMemberType]
        )
        error = next(errors, None)
        if error is None:
            return
        suffix = (
            ""
            if not error.absolute_path
            else "." + ".".join(str(part) for part in error.absolute_path)
        )
        raise OperatorInputValidationError(
            f"{operator_id} action violates {field}{suffix}: {error.message}"
        )

    def __contains__(self, operator_id: object) -> bool:
        return operator_id in self._bindings

    def __iter__(self) -> Iterator[str]:
        return iter(self._bindings)

    def __len__(self) -> int:
        return len(self._bindings)
