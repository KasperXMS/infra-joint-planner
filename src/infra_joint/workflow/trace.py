from datetime import UTC, datetime
from typing import Any

from infra_joint.evaluation.trace import TraceEvent, TraceSink


class WorkflowTraceRecorder:
    """Single-writer trace sequencer shared by planner, orchestrator, and finalizer."""

    def __init__(self, run_id: str, sink: TraceSink | None) -> None:
        self.run_id = run_id
        self._sink = sink
        self._event_index = 0
        self._parent_event_id: str | None = None

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> TraceEvent:
        step_id = f"{self._event_index:06d}-{event_type}"
        event = TraceEvent(
            run_id=self.run_id,
            step_id=step_id,
            parent_id=self._parent_event_id,
            event_type=event_type,
            timestamp=timestamp or datetime.now(UTC),
            payload=payload,
        )
        if self._sink is not None:
            self._sink.append(event)
        self._event_index += 1
        self._parent_event_id = step_id
        return event
