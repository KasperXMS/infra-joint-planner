from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    LogicalToolAction,
)
from infra_joint.core.action import SemanticAction
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry


class SemanticValidationError(ValueError):
    """A logical action violates the finite system-owned semantic contract."""


class SemanticActionValidator:
    """Validate semantics without reading EnvironmentSpec or infrastructure state."""

    def __init__(
        self,
        task: TaskContract,
        registry: OperatorRegistry,
        available_operations: Iterable[str],
    ) -> None:
        self._registry = registry
        self._available_operations = frozenset(available_operations)
        unknown = sorted(item for item in self._available_operations if item not in registry)
        if unknown:
            raise SemanticValidationError(
                f"system action space references unknown operators: {unknown}"
            )
        self._task_artifacts = frozenset(item.artifact_id for item in task.artifacts)
        self._produced_by: dict[str, str] = {}
        self._declared_outputs: dict[str, str] = {}
        self._known_actions: set[str] = set()

    @property
    def known_artifacts(self) -> frozenset[str]:
        return self._task_artifacts | frozenset(self._produced_by)

    def validate_batch(self, actions: tuple[LogicalAction, ...]) -> None:
        action_ids = [item.action_id for item in actions]
        if len(action_ids) != len(set(action_ids)):
            raise SemanticValidationError("logical action IDs must be unique within a step")
        repeated = sorted(set(action_ids) & self._known_actions)
        if repeated:
            raise SemanticValidationError(f"logical action IDs already exist: {repeated}")

        batch_outputs = [
            output.artifact_id for action in actions for output in action.outputs
        ]
        if len(batch_outputs) != len(set(batch_outputs)):
            raise SemanticValidationError("logical outputs must have one producer")
        collisions = sorted(
            set(batch_outputs) & (self._task_artifacts | self._declared_outputs.keys())
        )
        if collisions:
            raise SemanticValidationError(
                f"logical outputs collide with existing artifacts: {collisions}"
            )

        batch_ids = set(action_ids)
        for action in actions:
            missing_dependencies = sorted(
                set(action.depends_on) - self._known_actions - batch_ids
            )
            if missing_dependencies:
                raise SemanticValidationError(
                    f"action references unknown dependencies: {missing_dependencies}"
                )
            if set(action.depends_on) & batch_ids:
                raise SemanticValidationError(
                    "actions in one parallel step cannot depend on each other"
                )
            missing_inputs = sorted(set(action.inputs) - self.known_artifacts)
            if missing_inputs:
                raise SemanticValidationError(
                    f"action references unknown input artifacts: {missing_inputs}"
                )
            self._validate_one(action)

    def reserve_batch(self, actions: tuple[LogicalAction, ...]) -> None:
        for action in actions:
            self._known_actions.add(action.action_id)
            for output in action.outputs:
                self._declared_outputs[output.artifact_id] = action.action_id

    def complete_batch(
        self,
        actions: tuple[LogicalAction, ...],
        succeeded_action_ids: frozenset[str],
    ) -> None:
        for action in actions:
            if action.action_id not in succeeded_action_ids:
                continue
            for output in action.outputs:
                self._produced_by[output.artifact_id] = action.action_id

    def producer_of(self, artifact_id: str) -> str | None:
        return self._produced_by.get(artifact_id)

    def _validate_one(self, action: LogicalAction) -> None:
        operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
        if operator not in self._registry:
            raise SemanticValidationError(f"logical action uses unknown operator: {operator}")
        if operator not in self._available_operations:
            raise SemanticValidationError(
                f"operator {operator} is outside the system action space"
            )
        semantic = semantic_action(action)
        try:
            self._registry.validate_action(semantic)
        except (KeyError, ValueError) as exc:
            raise SemanticValidationError(str(exc)) from exc
        if isinstance(action, LogicalToolAction):
            requirements = self._registry.binding(action.operator).spec.capability_requirements
            if "model" in requirements:
                raise SemanticValidationError(
                    "model-capability operators must use LogicalModelAction"
                )


def semantic_action(action: LogicalAction) -> SemanticAction:
    if isinstance(action, LogicalToolAction):
        return SemanticAction(
            operator=action.operator,
            inputs=action.inputs,
            arguments=action.arguments,
        )
    arguments: dict[str, Any] = {"prompt": action.prompt}
    if action.outputs:
        output = action.outputs[0]
        arguments.update(
            {
                "output_artifact_id": output.artifact_id,
                "output_semantic_type": output.semantic_type,
                "output_media_type": output.media_type,
            }
        )
    return SemanticAction(
        operator="invoke_model",
        inputs=action.inputs,
        arguments=arguments,
    )
