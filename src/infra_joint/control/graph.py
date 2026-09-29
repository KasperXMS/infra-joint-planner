from __future__ import annotations

from dataclasses import dataclass

from infra_joint.control.contracts import (
    GraphEdgeView,
    GraphNodeView,
    LogicalAction,
    LogicalModelAction,
    WorkflowGraphSnapshot,
)


@dataclass(slots=True)
class _MutableNode:
    action: LogicalAction
    status: str = "pending"


class ExecutionGrownGraph:
    """Append-only executed/pending history; it does not predict the full future."""

    def __init__(self) -> None:
        self._version = 0
        self._nodes: dict[str, _MutableNode] = {}
        self._edges: list[GraphEdgeView] = []
        self._producer_by_artifact: dict[str, str] = {}
        self._snapshots: list[WorkflowGraphSnapshot] = [self.snapshot()]

    @property
    def snapshots(self) -> tuple[WorkflowGraphSnapshot, ...]:
        return tuple(self._snapshots)

    def add(self, actions: tuple[LogicalAction, ...]) -> WorkflowGraphSnapshot:
        for action in actions:
            if action.action_id in self._nodes:
                raise ValueError(f"duplicate graph action: {action.action_id}")
            self._nodes[action.action_id] = _MutableNode(action)
            explicit = set(action.depends_on)
            for producer in sorted(explicit):
                self._edges.append(
                    GraphEdgeView(
                        producer_action_id=producer,
                        consumer_action_id=action.action_id,
                        information_id="control-dependency",
                    )
                )
            for artifact_id in action.inputs:
                producer = self._producer_by_artifact.get(artifact_id)
                if producer is not None and producer not in explicit:
                    self._edges.append(
                        GraphEdgeView(
                            producer_action_id=producer,
                            consumer_action_id=action.action_id,
                            information_id=artifact_id,
                        )
                    )
            for output in action.outputs:
                self._producer_by_artifact[output.artifact_id] = action.action_id
        return self._record()

    def mark_running(self, action_ids: tuple[str, ...]) -> WorkflowGraphSnapshot:
        self._set_status(action_ids, "running")
        return self._record()

    def mark_finished(
        self,
        succeeded: tuple[str, ...],
        failed: tuple[str, ...],
    ) -> WorkflowGraphSnapshot:
        self._set_status(succeeded, "succeeded")
        self._set_status(failed, "failed")
        return self._record()

    def snapshot(self) -> WorkflowGraphSnapshot:
        return WorkflowGraphSnapshot(
            version=self._version,
            nodes=tuple(
                GraphNodeView(
                    action_id=item.action.action_id,
                    owner_agent_id=item.action.owner_agent_id,
                    action_type=item.action.action_type,
                    operator=(
                        "invoke_model"
                        if isinstance(item.action, LogicalModelAction)
                        else item.action.operator
                    ),
                    status=item.status,  # type: ignore[arg-type]
                    inputs=item.action.inputs,
                    outputs=tuple(value.artifact_id for value in item.action.outputs),
                )
                for item in self._nodes.values()
            ),
            edges=tuple(self._edges),
        )

    def _set_status(self, action_ids: tuple[str, ...], status: str) -> None:
        for action_id in action_ids:
            self._nodes[action_id].status = status

    def _record(self) -> WorkflowGraphSnapshot:
        self._version += 1
        value = self.snapshot()
        self._snapshots.append(value)
        return value
