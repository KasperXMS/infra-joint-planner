from __future__ import annotations

import asyncio
from typing import Protocol
from uuid import uuid4

from infra_joint.control.contracts import LogicalAction, PhysicalProfileView
from infra_joint.control.physical import PhysicalExecutionOutcome, PhysicalExecutionService
from infra_joint.control.validation import SemanticActionValidator


class ActionGateway(Protocol):
    """The only execution entry point available to logical agents."""

    def validate_batch(self, actions: tuple[LogicalAction, ...]) -> None: ...

    async def execute_batch(
        self,
        actions: tuple[LogicalAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]: ...

    async def profile_overview(self) -> PhysicalProfileView: ...


class RuntimeActionGateway:
    def __init__(
        self,
        validator: SemanticActionValidator,
        physical: PhysicalExecutionService,
    ) -> None:
        self._validator = validator
        self._physical = physical

    @property
    def validator(self) -> SemanticActionValidator:
        return self._validator

    def validate_batch(self, actions: tuple[LogicalAction, ...]) -> None:
        self._validator.validate_batch(actions)

    async def profile_overview(self) -> PhysicalProfileView:
        return await self._physical.profile_overview()

    async def execute_batch(
        self,
        actions: tuple[LogicalAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        self._validator.validate_batch(actions)
        self._validator.reserve_batch(actions)
        physical_object: object = self._physical
        if not isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
            physical_object,
            PhysicalExecutionService,
        ):
            return await self._execute_legacy_test_double(actions, expose_profile=expose_profile)
        before = await self._physical.observe_infrastructure()
        prepared = self._physical.prepare_batch(
            actions,
            before,
            batch_id=str(uuid4()),
            expose_profile=expose_profile,
        )
        outcomes = tuple(
            await asyncio.gather(
                *(
                    self._physical.execute_prepared(item, before)
                    for item in prepared
                )
            )
        )
        after = await self._physical.observe_infrastructure()
        outcomes = tuple(
            item.model_copy(update={"infrastructure_after": after}) for item in outcomes
        )
        self._complete(actions, outcomes)
        return outcomes

    async def _execute_legacy_test_double(
        self,
        actions: tuple[LogicalAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        outcomes = tuple(
            await asyncio.gather(
                *(
                    self._physical.execute(action, expose_profile=expose_profile)
                    for action in actions
                )
            )
        )
        self._complete(actions, outcomes)
        return outcomes

    def _complete(
        self,
        actions: tuple[LogicalAction, ...],
        outcomes: tuple[PhysicalExecutionOutcome, ...],
    ) -> None:
        self._validator.complete_batch(
            actions,
            frozenset(
                item.observation.action_id
                for item in outcomes
                if item.observation.succeeded
            ),
        )
