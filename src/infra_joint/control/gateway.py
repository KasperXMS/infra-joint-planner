from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Protocol
from uuid import uuid4

from infra_joint.control.contracts import LogicalAction, PhysicalProfileView
from infra_joint.control.physical import (
    PhysicalExecutionOutcome,
    PhysicalExecutionService,
    PreparedPhysicalAction,
)
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.core.state import InfrastructureState
from infra_joint.infrastructure.diagnostics import observer_diagnostic_scope
from infra_joint.runtime.action_receipts import (
    ActionReceipt,
    ActionReceiptStore,
    MemoryActionReceiptStore,
    ReceiptConflictError,
    request_sha256,
)


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
        *,
        receipt_store: ActionReceiptStore | None = None,
    ) -> None:
        self._validator = validator
        self._physical = physical
        self._receipts = receipt_store or MemoryActionReceiptStore()

    @property
    def receipts(self) -> ActionReceiptStore:
        return self._receipts

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
        digests = {
            action.action_id: request_sha256(action.model_dump(mode="json")) for action in actions
        }
        for action in actions:
            if self._receipts.get(action.action_id) is not None:
                raise ReceiptConflictError(f"action ID already has a receipt: {action.action_id}")
        for action in actions:
            self._receipts.put(
                ActionReceipt(
                    action_id=action.action_id,
                    request_sha256=digests[action.action_id],
                    status="reserved",
                )
            )
        self._validator.reserve_batch(actions)
        physical_object: object = self._physical
        if not isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
            physical_object,
            PhysicalExecutionService,
        ):
            return await self._execute_legacy_test_double(actions, expose_profile=expose_profile)
        with observer_diagnostic_scope(tuple(action.action_id for action in actions)):
            try:
                before = await self._physical.observe_infrastructure()
                prepared = self._physical.prepare_batch(
                    actions,
                    before,
                    batch_id=str(uuid4()),
                    expose_profile=expose_profile,
                )
            except BaseException:
                self._mark_unstarted(actions, digests)
                raise
            operations = tuple(self._physical.execute_prepared(item, before) for item in prepared)
            outcomes = await self._execute_and_settle(
                actions, operations, digests, prepared=prepared, before=before
            )
            try:
                after = await self._physical.observe_infrastructure()
            except Exception as exc:
                exc.__dict__["_infra_joint_settled_outcomes"] = outcomes
                raise
        return tuple(item.model_copy(update={"infrastructure_after": after}) for item in outcomes)

    async def _execute_legacy_test_double(
        self,
        actions: tuple[LogicalAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        digests = {
            action.action_id: request_sha256(action.model_dump(mode="json")) for action in actions
        }
        return await self._execute_and_settle(
            actions,
            tuple(
                self._physical.execute(action, expose_profile=expose_profile) for action in actions
            ),
            digests,
        )

    async def _execute_and_settle(
        self,
        actions: tuple[LogicalAction, ...],
        operations: tuple[Awaitable[PhysicalExecutionOutcome], ...],
        digests: dict[str, str],
        *,
        prepared: tuple[PreparedPhysicalAction, ...] | None = None,
        before: InfrastructureState | None = None,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        if len(actions) != len(operations):
            raise ValueError("action/physical operation count mismatch")
        for action in actions:
            self._receipts.put(
                ActionReceipt(
                    action_id=action.action_id,
                    request_sha256=digests[action.action_id],
                    status="started",
                )
            )
        tasks = tuple(asyncio.ensure_future(operation) for operation in operations)
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            for task in tasks:
                if not task.done():
                    task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            await self._settle_results(actions, tuple(results), digests, prepared, before)
            raise
        return await self._settle_results(actions, tuple(results), digests, prepared, before)

    async def _settle_results(
        self,
        actions: tuple[LogicalAction, ...],
        results: tuple[PhysicalExecutionOutcome | BaseException, ...],
        digests: dict[str, str],
        prepared: tuple[PreparedPhysicalAction, ...] | None,
        before: InfrastructureState | None,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        outcomes: list[PhysicalExecutionOutcome] = []
        first_error: BaseException | None = None
        for index, (action, result) in enumerate(zip(actions, results, strict=True)):
            outcome: PhysicalExecutionOutcome | None = None
            if isinstance(result, PhysicalExecutionOutcome):
                outcome = result
            else:
                if first_error is None:
                    first_error = result
                if prepared is not None and before is not None:
                    try:
                        outcome = await self._physical.reconcile_prepared(prepared[index], before)
                    except Exception:
                        outcome = None
            if outcome is None:
                self._receipts.put(
                    ActionReceipt(
                        action_id=action.action_id,
                        request_sha256=digests[action.action_id],
                        status="indeterminate",
                        failure_code=type(result).__name__,
                    )
                )
                continue
            if outcome.observation.action_id != action.action_id:
                raise ValueError("physical outcome/action ID mismatch")
            status = "succeeded" if outcome.observation.succeeded else "failed"
            if isinstance(result, BaseException):
                self._receipts.put(
                    ActionReceipt(
                        action_id=action.action_id,
                        request_sha256=digests[action.action_id],
                        status="indeterminate",
                        failure_code=type(result).__name__,
                    )
                )
            self._receipts.put(
                ActionReceipt(
                    action_id=action.action_id,
                    request_sha256=digests[action.action_id],
                    status="reconciled" if isinstance(result, BaseException) else status,
                    resolution=status if isinstance(result, BaseException) else None,
                    response=outcome.model_dump(mode="json") if status == "succeeded" else None,
                    failure_code=outcome.observation.failure_code,
                    failure_message=outcome.observation.failure_message,
                )
            )
            self._complete((action,), (outcome,))
            outcomes.append(outcome)
        if first_error is not None and len(outcomes) != len(actions):
            if isinstance(first_error, Exception):
                first_error.__dict__["_infra_joint_settled_outcomes"] = tuple(outcomes)
            raise first_error
        return tuple(outcomes)

    def _mark_unstarted(self, actions: tuple[LogicalAction, ...], digests: dict[str, str]) -> None:
        for action in actions:
            self._receipts.put(
                ActionReceipt(
                    action_id=action.action_id,
                    request_sha256=digests[action.action_id],
                    status="failed",
                    failure_code="preparation_failed",
                )
            )

    def _complete(
        self,
        actions: tuple[LogicalAction, ...],
        outcomes: tuple[PhysicalExecutionOutcome, ...],
    ) -> None:
        self._validator.complete_batch(
            actions,
            frozenset(
                item.observation.action_id for item in outcomes if item.observation.succeeded
            ),
        )
