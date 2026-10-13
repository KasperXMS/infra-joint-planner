"""Fail-closed, versioned receipts for one logical action ID.

The file implementation is for one worker/controller process per directory. A shared
multi-process directory needs an external transactional store and is unsupported.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Literal, Protocol, Self
from uuid import uuid4

from pydantic import Field, model_validator

from infra_joint.core.base import ContractModel

ReceiptStatus = Literal["reserved", "started", "succeeded", "failed", "indeterminate", "reconciled"]


class ActionReceipt(ContractModel):
    schema_version: Literal["action-receipt-v2"] = "action-receipt-v2"
    action_id: str = Field(min_length=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: ReceiptStatus
    resolution: Literal["succeeded", "failed"] | None = None
    response: dict[str, object] | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    http_status: int | None = None

    @model_validator(mode="after")
    def valid_resolution(self) -> Self:
        if (self.status == "reconciled") != (self.resolution is not None):
            raise ValueError("reconciled receipt requires exactly one resolution")
        if (
            self.status in {"succeeded", "reconciled"}
            and self.resolution != "failed"
            and self.response is None
        ):
            raise ValueError("successful receipt needs a response")
        return self

    @property
    def effective_status(self) -> str:
        if self.status == "reconciled":
            assert self.resolution is not None
            return self.resolution
        return self.status


class ReceiptConflictError(ValueError):
    pass


class ActionReceiptStore(Protocol):
    def get(self, action_id: str) -> ActionReceipt | None: ...

    def put(self, receipt: ActionReceipt) -> None: ...

    def list_receipts(self) -> tuple[ActionReceipt, ...]: ...


_NEXT: dict[str, frozenset[str]] = {
    "reserved": frozenset({"started", "failed", "indeterminate"}),
    "started": frozenset({"succeeded", "failed", "indeterminate"}),
    "indeterminate": frozenset({"reconciled"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "reconciled": frozenset(),
}


def validate_transition(previous: ActionReceipt | None, current: ActionReceipt) -> None:
    if previous is None:
        if current.status != "reserved":
            raise ReceiptConflictError("first action receipt must be reserved")
        return
    if previous.action_id != current.action_id or previous.request_sha256 != current.request_sha256:
        raise ReceiptConflictError("action ID reused for a different request")
    if previous == current:
        return
    if current.status not in _NEXT[previous.status]:
        raise ReceiptConflictError(
            f"illegal action receipt transition: {previous.status} -> {current.status}"
        )


class MemoryActionReceiptStore:
    def __init__(self) -> None:
        self._items: dict[str, ActionReceipt] = {}

    def get(self, action_id: str) -> ActionReceipt | None:
        return self._items.get(action_id)

    def put(self, receipt: ActionReceipt) -> None:
        validate_transition(self.get(receipt.action_id), receipt)
        self._items[receipt.action_id] = receipt

    def list_receipts(self) -> tuple[ActionReceipt, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


class FileActionReceiptStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, action_id: str) -> Path:
        return self.root / f"{hashlib.sha256(action_id.encode('utf-8')).hexdigest()}.json"

    def get(self, action_id: str) -> ActionReceipt | None:
        path = self._path(action_id)
        if not path.exists():
            return None
        receipt = ActionReceipt.model_validate_json(path.read_bytes())
        if receipt.action_id != action_id:
            raise ReceiptConflictError("receipt path and action ID disagree")
        return receipt

    def put(self, receipt: ActionReceipt) -> None:
        validate_transition(self.get(receipt.action_id), receipt)
        path = self._path(receipt.action_id)
        temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        payload = receipt.model_dump_json().encode("utf-8")
        try:
            with temporary.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def list_receipts(self) -> tuple[ActionReceipt, ...]:
        return tuple(
            ActionReceipt.model_validate_json(path.read_bytes())
            for path in sorted(self.root.glob("*.json"))
        )


def request_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
