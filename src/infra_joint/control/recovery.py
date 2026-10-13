"""Explicit fail-closed interruption policy; SDK conversation resume is unsupported."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from infra_joint.core.base import ContractModel
from infra_joint.runtime.action_receipts import ActionReceiptStore


class RunRecoverySnapshot(ContractModel):
    schema_version: Literal["run-recovery-v2"] = "run-recovery-v2"
    run_id: str = Field(min_length=1)
    interrupted: bool
    resume_supported: Literal[False] = False
    indeterminate_action_ids: tuple[str, ...] = ()
    confirmed_action_ids: tuple[str, ...] = ()
    receipt_statuses: dict[str, str] = Field(default_factory=dict)


def interrupted_snapshot(run_id: str, receipts: ActionReceiptStore) -> RunRecoverySnapshot:
    entries = receipts.list_receipts()
    return RunRecoverySnapshot(
        run_id=run_id,
        interrupted=True,
        indeterminate_action_ids=tuple(
            item.action_id for item in entries if item.status in {"started", "indeterminate"}
        ),
        confirmed_action_ids=tuple(
            item.action_id for item in entries if item.effective_status in {"succeeded", "failed"}
        ),
        receipt_statuses={item.action_id: item.status for item in entries},
    )


def reject_resume(snapshot: RunRecoverySnapshot) -> None:
    raise RuntimeError(
        f"run {snapshot.run_id} is interrupted; SDK conversation resume is unsupported. "
        "Inspect durable receipts and start a new, separately identified run only if the "
        "experiment protocol permits it. Never replay an indeterminate action."
    )
