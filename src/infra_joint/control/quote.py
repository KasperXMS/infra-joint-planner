"""Single-use ready-action quotes; commits still use the unchanged ActionGateway."""

import asyncio
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic, perf_counter
from typing import Any
from uuid import uuid4

from pydantic import Field

from infra_joint.control.consequence import ActionConsequence, ActionConsequenceEstimator
from infra_joint.control.contracts import LogicalAction
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.ledger_native import LedgerActionGateway
from infra_joint.control.physical import PhysicalExecutionOutcome, PhysicalExecutionService
from infra_joint.core.base import ContractModel


class QuoteProtocolError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ActionQuote(ContractModel):
    quote_id: str = Field(min_length=1)
    action_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consequence: ActionConsequence
    expires_after_seconds: float = Field(gt=0, allow_inf_nan=False)
    quote_control_latency_ms: float = Field(ge=0, allow_inf_nan=False)
    next_step: str = "commit_quote to execute this exact action, or discard_quote and propose anew"


@dataclass
class _PendingQuote:
    quote: ActionQuote
    action: LogicalAction
    created_at: float
    payload_json: str
    operator: str
    status: str = "pending"


def action_sha256(action: LogicalAction) -> str:
    payload = json.dumps(action.model_dump(mode="json"), ensure_ascii=False,
                         separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


class ReadyActionQuotes:
    def __init__(
        self, *, physical: PhysicalExecutionService, estimator: ActionConsequenceEstimator,
        gateway: ActionGateway, owner_agent_id: str,
        emit: Callable[[str, dict[str, Any]], object],
        quote_ttl_seconds: float = 120, max_proposals: int = 128,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if quote_ttl_seconds <= 0 or max_proposals < 1:
            raise ValueError("invalid quote protocol safety bounds")
        self.physical = physical
        self.estimator = estimator
        self.gateway = gateway
        self.owner_agent_id = owner_agent_id
        self.emit = emit
        self.quote_ttl_seconds = quote_ttl_seconds
        self.max_proposals = max_proposals
        self.clock = clock
        self.proposals = 0
        self.control_calls = 0
        self.control_work_ms = 0.0
        self._quotes: dict[str, _PendingQuote] = {}
        self._authorized: dict[str, _PendingQuote] = {}
        self._lock = asyncio.Lock()

    async def propose(
        self, action: LogicalAction, *, payload_json: str, operator: str,
    ) -> ActionQuote:
        started = perf_counter()
        succeeded = False
        try:
            quote = await self._propose(action, payload_json=payload_json, operator=operator)
            succeeded = True
            return quote
        finally:
            self._record_control("propose", action.action_id, started, succeeded)

    async def _propose(
        self, action: LogicalAction, *, payload_json: str, operator: str,
    ) -> ActionQuote:
        if action.owner_agent_id != self.owner_agent_id:
            raise QuoteProtocolError("quote_owner_mismatch")
        async with self._lock:
            if self.proposals >= self.max_proposals:
                raise QuoteProtocolError("quote_proposal_budget_exhausted")
            self.proposals += 1
        self.gateway.validate_batch((action,))  # No reservation or output materialization.
        started = perf_counter()
        snapshot = await self.physical.observe_infrastructure()
        quote_id = f"quote-{uuid4().hex}"
        prepared = self.physical.prepare_batch((action,), snapshot, batch_id=quote_id,
                                              expose_profile=False)[0]
        consequence = self.estimator.evaluate(prepared, snapshot)
        quote = ActionQuote(
            quote_id=quote_id, action_sha256=action_sha256(action), consequence=consequence,
            expires_after_seconds=self.quote_ttl_seconds,
            quote_control_latency_ms=(perf_counter() - started) * 1000,
        )
        self._quotes[quote_id] = _PendingQuote(quote, action.model_copy(deep=True), self.clock(),
                                              payload_json, operator)
        self.emit("physical.cost_quote.prepared", {
            "quote_id": quote_id, "action_id": action.action_id,
            "snapshot_sha256": prepared.shared_snapshot_sha256,
            "selection": prepared.selection.model_dump(mode="json") if prepared.selection else None,
            "failure": (prepared.preparation_failure.model_dump(mode="json")
                        if prepared.preparation_failure else None),
        })
        self.emit("logical.cost_quote.created", {
            "quote": quote.model_dump(mode="json"), "action": action.model_dump(mode="json"),
        })
        return quote

    def _pending(self, quote_id: str, owner: str) -> _PendingQuote:
        if owner != self.owner_agent_id:
            raise QuoteProtocolError("quote_owner_mismatch")
        pending = self._quotes.get(quote_id)
        if pending is None:
            raise QuoteProtocolError("unknown_quote")
        if pending.status != "pending":
            raise QuoteProtocolError("quote_already_consumed")
        if self.clock() - pending.created_at > self.quote_ttl_seconds:
            pending.status = "expired"
            raise QuoteProtocolError("quote_expired")
        return pending

    async def authorize(self, quote_id: str, *, owner: str) -> _PendingQuote:
        started = perf_counter()
        succeeded = False
        try:
            pending = await self._authorize(quote_id, owner=owner)
            succeeded = True
            return pending
        finally:
            self._record_control("authorize", quote_id, started, succeeded)

    async def _authorize(self, quote_id: str, *, owner: str) -> _PendingQuote:
        async with self._lock:
            pending = self._pending(quote_id, owner)
            pending.status = "checking"
        started = perf_counter()
        try:
            if action_sha256(pending.action) != pending.quote.action_sha256:
                raise QuoteProtocolError("quoted_action_mutated")
            self.gateway.validate_batch((pending.action,))
            snapshot = await self.physical.observe_infrastructure()
            prepared = self.physical.prepare_batch((pending.action,), snapshot,
                                                  batch_id=quote_id, expose_profile=False)[0]
            current = self.estimator.evaluate(prepared, snapshot)
            if current != pending.quote.consequence:
                pending.status = "stale"
                self.emit("logical.cost_quote.stale", {"quote_id": quote_id,
                                                       "current_consequence": current.model_dump(
                                                           mode="json")})
                raise QuoteProtocolError("quote_consequence_changed_requote_required")
            if self.clock() - pending.created_at > self.quote_ttl_seconds:
                raise QuoteProtocolError("quote_expired")
            if pending.action.action_id in self._authorized:
                raise QuoteProtocolError("quote_action_already_authorized")
            pending.status = "authorized"
            self._authorized[pending.action.action_id] = pending
            self.emit("logical.cost_quote.commit_authorized", {
                "quote_id": quote_id, "action_id": pending.action.action_id,
                "action_sha256": pending.quote.action_sha256,
                "age_ms": (self.clock() - pending.created_at) * 1000,
                "commit_validation_latency_ms": (perf_counter() - started) * 1000,
                "physical_binding_pinned": False,
            })
            return pending
        except BaseException:
            if pending.status == "checking":
                pending.status = "rejected"
            raise

    def consume_authorization(self, action: LogicalAction) -> _PendingQuote:
        pending = self._authorized.pop(action.action_id, None)
        if pending is None or pending.status != "authorized":
            raise QuoteProtocolError("action_requires_explicit_quote_commit")
        pending.status = "consumed"
        if action_sha256(action) != pending.quote.action_sha256:
            raise QuoteProtocolError("committed_action_differs_from_quote")
        return pending

    def discard(self, quote_id: str, *, owner: str) -> None:
        pending = self._pending(quote_id, owner)
        pending.status = "discarded"
        self.emit("logical.cost_quote.discarded", {"quote_id": quote_id,
                                                  "action_id": pending.action.action_id})

    def observe(self, pending: _PendingQuote, outcome: PhysicalExecutionOutcome) -> None:
        execution = outcome.execution
        actual_bytes = (sum(item.bytes_transferred for item in execution.transfers)
                        if execution is not None else None)
        transfer_ms = (sum(item.duration_ms for item in execution.transfers)
                       if execution is not None else None)
        service_ms = (execution.model_telemetry.service_latency_ms
                      if execution is not None and execution.model_telemetry is not None else None)
        movement = pending.quote.consequence.movement
        predicted_bytes = movement.bytes_upper_bound if movement is not None else None
        self.emit("logical.cost_quote.observed", {
            "quote_id": pending.quote.quote_id, "action_id": pending.action.action_id,
            "succeeded": outcome.observation.succeeded,
            "failure_code": outcome.observation.failure_code,
            "actual_transfer_bytes": actual_bytes, "actual_transfer_work_ms": transfer_ms,
            "actual_model_service_ms": service_ms,
            "predicted_transfer_bytes": predicted_bytes,
            "transfer_bytes_error": (actual_bytes - predicted_bytes
                                     if actual_bytes is not None and predicted_bytes is not None
                                     else None),
            "predicted_consequence": pending.quote.consequence.model_dump(mode="json"),
            "physical_selection_may_change_after_authorization": True,
        })

    def _record_control(
        self, operation: str, identifier: str, started: float, succeeded: bool,
    ) -> None:
        elapsed = (perf_counter() - started) * 1000
        self.control_calls += 1
        self.control_work_ms += elapsed
        self.emit("logical.cost_quote.control_timing", {
            "operation": operation, "identifier": identifier, "succeeded": succeeded,
            "control_work_ms": elapsed, "includes_physical_execution": False,
        })

    def summary(self) -> dict[str, object]:
        return {"proposal_attempts": self.proposals, "created_quotes": len(self._quotes),
                "quote_states": dict(Counter(item.status for item in self._quotes.values())),
                "timed_control_calls": self.control_calls, "control_work_ms": self.control_work_ms,
                "control_work_is_e2e": False}


class QuoteLedgerGateway(LedgerActionGateway):
    def __init__(self, delegate: ActionGateway, quotes: ReadyActionQuotes) -> None:
        super().__init__(delegate)
        self.quotes = quotes

    async def execute_batch(
        self, actions: tuple[LogicalAction, ...], *, expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        if expose_profile:
            raise ValueError("Quote variant does not expose raw dynamic profiles")
        authorized = {
            action.action_id: self.quotes.consume_authorization(action) for action in actions
            if action.owner_agent_id == self.quotes.owner_agent_id
        }
        outcomes = await super().execute_batch(actions, expose_profile=False)
        for outcome in outcomes:
            pending = authorized.get(outcome.observation.action_id)
            if pending is not None:
                self.quotes.observe(pending, outcome)
        return outcomes
