from __future__ import annotations

from collections import defaultdict, deque

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    LogicalToolAction,
    StaticCapabilityContract,
)
from infra_joint.control.static_feasibility import (
    StaticFeasibilityError,
    analyze_static_workflow,
)
from infra_joint.control.validation import semantic_action
from infra_joint.control.workflow import (
    AddAction,
    AddDependency,
    RemovePendingAction,
    ReplacePendingAction,
    SemanticWorkflowPlan,
    WorkflowDependency,
    WorkflowPatch,
    WorkflowRuntimeState,
)
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry


class WorkflowValidationError(ValueError):
    """A semantic workflow or bounded revision violates the formal contract."""


def validate_semantic_workflow(
    plan: SemanticWorkflowPlan,
    task: TaskContract,
    capabilities: StaticCapabilityContract,
    registry: OperatorRegistry,
) -> None:
    """Validate a complete semantic plan without reading infrastructure state."""

    actions = plan.action_map()
    if not actions:
        raise WorkflowValidationError("semantic workflow must contain actions")
    terminal = actions.get(plan.terminal_action_id)
    if terminal is None:
        raise WorkflowValidationError("terminal action does not exist")
    if not isinstance(terminal, LogicalModelAction):
        raise WorkflowValidationError("terminal action must be a logical model action")

    operator_contracts = {item.operator: item for item in capabilities.operators}
    task_artifacts = {item.artifact_id for item in task.artifacts}
    producer_by_artifact: dict[str, str] = {}
    for action in plan.actions:
        operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
        if operator not in operator_contracts:
            raise WorkflowValidationError(
                f"action uses operator outside static capability contract: {operator}"
            )
        try:
            registry.validate_action(semantic_action(action))
        except (KeyError, ValueError) as exc:
            raise WorkflowValidationError(str(exc)) from exc
        if isinstance(action, LogicalToolAction) and "model" in (
            operator_contracts[operator].required_capabilities
        ):
            raise WorkflowValidationError("model-capability operators must use LogicalModelAction")
        if isinstance(action, LogicalModelAction) and not (
            capabilities.matching_model_classes(action.requirements)
        ):
            raise WorkflowValidationError(
                f"model action is statically infeasible: {action.action_id}"
            )
        for output in action.outputs:
            if output.artifact_id in task_artifacts:
                raise WorkflowValidationError(
                    f"workflow output collides with task artifact: {output.artifact_id}"
                )
            prior = producer_by_artifact.setdefault(output.artifact_id, action.action_id)
            if prior != action.action_id:
                raise WorkflowValidationError(
                    f"artifact has multiple producers: {output.artifact_id}"
                )

    dependencies = tuple(plan.dependencies)
    incoming: dict[str, list[WorkflowDependency]] = defaultdict(list)
    successors: dict[str, set[str]] = defaultdict(set)
    for dependency in dependencies:
        if dependency.producer_action_id not in actions:
            raise WorkflowValidationError("dependency references unknown producer action")
        if dependency.consumer_action_id not in actions:
            raise WorkflowValidationError("dependency references unknown consumer action")
        incoming[dependency.consumer_action_id].append(dependency)
        successors[dependency.producer_action_id].add(dependency.consumer_action_id)
        if dependency.dependency_type == "artifact":
            information_id = dependency.information_id
            assert information_id is not None
            if producer_by_artifact.get(information_id) != dependency.producer_action_id:
                raise WorkflowValidationError(
                    "artifact dependency does not reference its declared producer"
                )
            if information_id not in actions[dependency.consumer_action_id].inputs:
                raise WorkflowValidationError(
                    "artifact dependency is not consumed by its declared consumer"
                )

    known_artifacts = task_artifacts | set(producer_by_artifact)
    for action in plan.actions:
        missing = set(action.inputs) - known_artifacts
        if missing:
            raise WorkflowValidationError(f"action has dangling input artifacts: {sorted(missing)}")
        for artifact_id in set(action.inputs) - task_artifacts:
            producer = producer_by_artifact[artifact_id]
            if not any(
                item.dependency_type == "artifact"
                and item.producer_action_id == producer
                and item.information_id == artifact_id
                for item in incoming[action.action_id]
            ):
                raise WorkflowValidationError(
                    f"generated input lacks artifact dependency: {artifact_id}"
                )
        declared = set(action.depends_on)
        explicit = {item.producer_action_id for item in incoming[action.action_id]}
        if not declared <= explicit:
            raise WorkflowValidationError(
                f"action depends_on contains undeclared dependencies: {action.action_id}"
            )

    ordered = _topological_order(plan)
    if len(ordered) != len(actions):
        raise WorkflowValidationError("semantic workflow graph must be acyclic")
    reachable = _reverse_reachable(plan.terminal_action_id, dependencies)
    unreachable = sorted(set(actions) - reachable)
    if unreachable:
        raise WorkflowValidationError(f"all actions must reach the terminal action: {unreachable}")
    try:
        analyze_static_workflow(plan, task, capabilities)
    except StaticFeasibilityError as exc:
        raise WorkflowValidationError(str(exc)) from exc


def validate_workflow_revision(
    current: SemanticWorkflowPlan,
    proposed: SemanticWorkflowPlan,
    state: WorkflowRuntimeState,
    task: TaskContract,
    capabilities: StaticCapabilityContract,
    registry: OperatorRegistry,
) -> None:
    """Enforce immutable completed/running semantics, then validate the full next plan."""

    state.validate_against(current)
    if proposed.workflow_id != current.workflow_id:
        raise WorkflowValidationError("workflow revision changed workflow_id")
    if proposed.version != current.version + 1:
        raise WorkflowValidationError("workflow revision must increment version exactly once")
    current_actions = current.action_map()
    proposed_actions = proposed.action_map()
    locked = set(state.completed_action_ids) | set(state.running_action_ids)
    removed = sorted(locked - set(proposed_actions))
    if removed:
        raise WorkflowValidationError(f"revision removed immutable actions: {removed}")
    modified = sorted(
        action_id
        for action_id in locked
        if current_actions[action_id] != proposed_actions[action_id]
    )
    if modified:
        raise WorkflowValidationError(f"revision modified immutable actions: {modified}")

    locked_incoming = set(state.completed_action_ids) | set(state.running_action_ids)
    current_edges = frozenset(
        item for item in current.dependencies if item.consumer_action_id in locked_incoming
    )
    proposed_edges = frozenset(
        item for item in proposed.dependencies if item.consumer_action_id in locked_incoming
    )
    if current_edges != proposed_edges:
        raise WorkflowValidationError(
            "revision changed dependencies of completed/running consumers"
        )
    validate_semantic_workflow(proposed, task, capabilities, registry)


def apply_workflow_patch(
    current: SemanticWorkflowPlan,
    state: WorkflowRuntimeState,
    patch: WorkflowPatch,
    task: TaskContract,
    capabilities: StaticCapabilityContract,
    registry: OperatorRegistry,
) -> SemanticWorkflowPlan:
    """Apply the finite edit vocabulary to only the pending suffix, fail closed."""

    state.validate_against(current)
    actions = {item.action_id: item for item in current.actions}
    order = [item.action_id for item in current.actions]
    dependencies = list(current.dependencies)
    pending = set(state.pending_action_ids)
    locked = set(state.completed_action_ids) | set(state.running_action_ids)
    for edit in patch.edits:
        if isinstance(edit, AddAction):
            action_id = edit.action.action_id
            if action_id in actions:
                raise WorkflowValidationError(f"patch adds duplicate action: {action_id}")
            actions[action_id] = edit.action
            order.append(action_id)
            pending.add(action_id)
        elif isinstance(edit, RemovePendingAction):
            _require_pending(edit.action_id, pending)
            if any(
                edit.action_id
                in {
                    item.producer_action_id,
                    item.consumer_action_id,
                }
                for item in dependencies
            ):
                raise WorkflowValidationError(
                    "remove dependencies before removing a pending action"
                )
            del actions[edit.action_id]
            order.remove(edit.action_id)
            pending.remove(edit.action_id)
        elif isinstance(edit, ReplacePendingAction):
            _require_pending(edit.action_id, pending)
            actions[edit.action_id] = edit.replacement
        elif isinstance(edit, AddDependency):
            dependency = edit.dependency
            if dependency in dependencies:
                raise WorkflowValidationError("patch adds duplicate dependency")
            if dependency.consumer_action_id not in pending:
                raise WorkflowValidationError("new dependency consumer must be a pending action")
            if dependency.producer_action_id not in actions:
                raise WorkflowValidationError("new dependency producer does not exist")
            dependencies.append(dependency)
        else:
            dependency = edit.dependency
            if dependency.consumer_action_id not in pending:
                raise WorkflowValidationError("removed dependency consumer must be pending")
            try:
                dependencies.remove(dependency)
            except ValueError as exc:
                raise WorkflowValidationError("dependency to remove does not exist") from exc
    if locked & pending:
        raise WorkflowValidationError("patch changed immutable runtime partitions")
    proposed = SemanticWorkflowPlan(
        workflow_id=current.workflow_id,
        version=current.version + 1,
        actions=tuple(actions[action_id] for action_id in order),
        dependencies=tuple(dependencies),
        terminal_action_id=current.terminal_action_id,
    )
    validate_workflow_revision(
        current,
        proposed,
        state,
        task,
        capabilities,
        registry,
    )
    return proposed


def ready_frontier(
    plan: SemanticWorkflowPlan,
    state: WorkflowRuntimeState,
) -> tuple[LogicalAction, ...]:
    state.validate_against(plan)
    completed = set(state.completed_action_ids)
    pending = set(state.pending_action_ids)
    predecessors: dict[str, set[str]] = defaultdict(set)
    for dependency in plan.dependencies:
        predecessors[dependency.consumer_action_id].add(dependency.producer_action_id)
    return tuple(
        action
        for action in plan.actions
        if action.action_id in pending and predecessors[action.action_id] <= completed
    )


def predecessor_ids(plan: SemanticWorkflowPlan, action_id: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            item.producer_action_id
            for item in plan.dependencies
            if item.consumer_action_id == action_id
        )
    )


def _require_pending(action_id: str, pending: set[str]) -> None:
    if action_id not in pending:
        raise WorkflowValidationError(
            f"workflow patch may modify only pending actions: {action_id}"
        )


def _topological_order(plan: SemanticWorkflowPlan) -> tuple[str, ...]:
    action_ids = [item.action_id for item in plan.actions]
    declared = {action_id: index for index, action_id in enumerate(action_ids)}
    indegree = dict.fromkeys(action_ids, 0)
    successors: dict[str, list[str]] = defaultdict(list)
    for dependency in plan.dependencies:
        indegree[dependency.consumer_action_id] += 1
        successors[dependency.producer_action_id].append(dependency.consumer_action_id)
    ready = deque(
        sorted(
            (action_id for action_id, count in indegree.items() if count == 0),
            key=declared.__getitem__,
        )
    )
    result: list[str] = []
    while ready:
        action_id = ready.popleft()
        result.append(action_id)
        for successor in successors[action_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    return tuple(result)


def _reverse_reachable(
    terminal_action_id: str,
    dependencies: tuple[WorkflowDependency, ...],
) -> set[str]:
    predecessors: dict[str, set[str]] = defaultdict(set)
    for item in dependencies:
        predecessors[item.consumer_action_id].add(item.producer_action_id)
    reachable = {terminal_action_id}
    stack = [terminal_action_id]
    while stack:
        consumer = stack.pop()
        for producer in predecessors[consumer]:
            if producer not in reachable:
                reachable.add(producer)
                stack.append(producer)
    return reachable
