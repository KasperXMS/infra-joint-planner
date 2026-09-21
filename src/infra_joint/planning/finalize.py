from typing import Protocol

from infra_joint.core.action import JointDecision
from infra_joint.core.task import TaskContract
from infra_joint.runtime.executor import ExecutionResult


class Finalizer(Protocol):
    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str: ...


class LastModelOutputFinalizer:
    """M1 finalizer that uses existing evidence and cannot call an operator."""

    async def finalize(
        self,
        task: TaskContract,
        decisions: tuple[JointDecision, ...],
        observations: tuple[ExecutionResult, ...],
    ) -> str:
        del task, decisions
        if not observations:
            return ""
        text = observations[-1].output.get("text")
        return text if isinstance(text, str) else ""
