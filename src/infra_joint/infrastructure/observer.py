from typing import Protocol

from infra_joint.core.state import InfrastructureState


class InfrastructureObserver(Protocol):
    async def observe(self) -> InfrastructureState: ...


class StaticObserver:
    """Deterministic observer used until live worker probing is introduced."""

    def __init__(self, state: InfrastructureState) -> None:
        self._state = state

    async def observe(self) -> InfrastructureState:
        return self._state
