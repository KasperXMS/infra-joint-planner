from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from infra_joint.core.action import JointDecision
from infra_joint.core.task import TaskContract
from infra_joint.runtime.executor import ExecutionResult


@dataclass(frozen=True, slots=True)
class BlindPlannerContext:
    """Planner view that deliberately contains no infrastructure state."""

    task: TaskContract
    decisions: tuple[JointDecision, ...]
    observations: tuple[ExecutionResult, ...]
    remaining_steps: int


class BlindPlanner(Protocol):
    async def decide(self, context: BlindPlannerContext) -> JointDecision: ...


class ScriptedBlindPlanner:
    """Deterministic planner used to validate the execution substrate."""

    def __init__(self, decisions: Iterable[JointDecision]) -> None:
        self._decisions = deque(decisions)

    async def decide(self, context: BlindPlannerContext) -> JointDecision:
        del context
        if not self._decisions:
            raise RuntimeError("scripted planner has no decision remaining")
        return self._decisions.popleft()
