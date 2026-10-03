"""Spent-only accounting; no forecasts, physical identities or semantic guidance."""

from math import fsum
from typing import Literal, cast

from pydantic import Field

from infra_joint.control.contracts import LogicalAction, LogicalModelAction
from infra_joint.control.loop import AgentLoopBudget, AgentLoopUsage
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.core.base import ContractModel

LEDGER_MESSAGE_PREFIX = "Measured execution spending so far (not a forecast): "


def is_ledger_message(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    message = cast(dict[str, object], item)
    content = message.get("content")
    return message.get("role") == "user" and isinstance(content, str) and content.startswith(
        LEDGER_MESSAGE_PREFIX
    )


class ObservedWork(ContractModel):
    observed_sum: float = Field(ge=0)
    measured_receipts: int = Field(ge=0)
    unknown_receipts: int = Field(ge=0)
    complete_total: float | None = Field(default=None, ge=0)


class SpentCostSnapshot(ContractModel):
    schema_version: Literal["spent-cost-ledger-v0"] = "spent-cost-ledger-v0"
    completed_actions: int = Field(ge=0)
    successful_tools: int = Field(ge=0)
    successful_models: int = Field(ge=0)
    failed_tools: int = Field(ge=0)
    failed_models: int = Field(ge=0)
    confirmed_inference_calls: int = Field(ge=0)
    unknown_inference_calls: int = Field(ge=0)
    action_transfer_bytes: ObservedWork
    action_transfer_work_ms: ObservedWork
    tool_wrapper_work_ms: ObservedWork
    model_service_work_ms: ObservedWork
    manager_turns_completed_or_started: int = Field(ge=0)
    specialist_reasoning_turns: int = Field(ge=0)
    created_specialists: int = Field(ge=0)
    physical_calls_submitted: int = Field(ge=0)
    remaining_manager_turns: int = Field(ge=0)
    remaining_physical_calls: int = Field(ge=0)
    remaining_verifier_calls: int = Field(ge=0)
    logical_loop_elapsed_ms: float = Field(ge=0)
    initial_placement_included: Literal[False] = False
    work_sums_are_e2e: Literal[False] = False


class _Receipt(ContractModel):
    is_model: bool
    succeeded: bool
    inference: bool | None
    transfer_bytes: int | None = Field(default=None, ge=0)
    transfer_ms: float | None = Field(default=None, ge=0)
    tool_wrapper_ms: float | None = Field(default=None, ge=0)
    model_service_ms: float | None = Field(default=None, ge=0)


class SpentCostLedger:
    """Retain numeric receipts only; duplicate delivery cannot double-count work."""

    def __init__(self) -> None:
        self._receipts: dict[str, _Receipt] = {}

    def record(self, action: LogicalAction, outcome: PhysicalExecutionOutcome) -> None:
        if outcome.observation.action_id != action.action_id:
            raise ValueError("ledger action/observation ID mismatch")
        execution = outcome.execution
        model = isinstance(action, LogicalModelAction)
        inference: bool | None = False
        if model:
            if execution is not None and execution.model_telemetry is not None:
                inference = True
            elif (
                outcome.failure is not None and outcome.failure.stage == "selection"
            ) or outcome.observation.failure_code in {
                "context_limit_exceeded", "unsupported_modality", "deployment_required",
            }:
                inference = False
            else:
                # A backend failure or incomplete receipt does not prove zero inference.
                inference = None
        receipt = _Receipt(
            is_model=model,
            succeeded=outcome.observation.succeeded,
            inference=inference,
            transfer_bytes=(
                sum(item.bytes_transferred for item in execution.transfers)
                if execution is not None else None
            ),
            transfer_ms=(
                fsum(item.duration_ms for item in execution.transfers)
                if execution is not None else None
            ),
            tool_wrapper_ms=(
                execution.operator_latency_ms if execution is not None and not model else None
            ),
            model_service_ms=(
                execution.model_telemetry.service_latency_ms
                if execution is not None and execution.model_telemetry is not None
                else (0 if inference is False else None)
            ),
        )
        previous = self._receipts.get(action.action_id)
        if previous is not None and previous != receipt:
            raise ValueError("conflicting ledger receipt for an already recorded action")
        self._receipts[action.action_id] = receipt

    def snapshot(
        self,
        *,
        usage: AgentLoopUsage,
        budget: AgentLoopBudget,
        logical_loop_elapsed_ms: float,
    ) -> SpentCostSnapshot:
        receipts = tuple(self._receipts.values())
        models = tuple(item for item in receipts if item.is_model)
        tools = tuple(item for item in receipts if not item.is_model)
        return SpentCostSnapshot(
            completed_actions=len(receipts),
            successful_tools=sum(item.succeeded for item in tools),
            successful_models=sum(item.succeeded for item in models),
            failed_tools=sum(not item.succeeded for item in tools),
            failed_models=sum(not item.succeeded for item in models),
            confirmed_inference_calls=sum(item.inference is True for item in models),
            unknown_inference_calls=sum(item.inference is None for item in models),
            action_transfer_bytes=_observed(tuple(item.transfer_bytes for item in receipts)),
            action_transfer_work_ms=_observed(tuple(item.transfer_ms for item in receipts)),
            tool_wrapper_work_ms=_observed(tuple(item.tool_wrapper_ms for item in tools)),
            model_service_work_ms=_observed(tuple(item.model_service_ms for item in models)),
            manager_turns_completed_or_started=usage.manager_turns,
            specialist_reasoning_turns=usage.subagent_turns,
            created_specialists=usage.created_subagents,
            physical_calls_submitted=usage.tool_model_calls,
            remaining_manager_turns=max(0, budget.max_manager_turns - usage.manager_turns),
            remaining_physical_calls=max(0, budget.max_tool_model_calls - usage.tool_model_calls),
            remaining_verifier_calls=max(0, budget.max_verifier_calls - usage.verifier_calls),
            logical_loop_elapsed_ms=logical_loop_elapsed_ms,
        )


def _observed(values: tuple[int | float | None, ...]) -> ObservedWork:
    known = tuple(item for item in values if item is not None)
    observed = fsum(known)
    return ObservedWork(
        observed_sum=observed,
        measured_receipts=len(known),
        unknown_receipts=len(values) - len(known),
        complete_total=observed if len(known) == len(values) else None,
    )
