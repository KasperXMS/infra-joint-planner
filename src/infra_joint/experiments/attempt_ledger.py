"""Append-only formal attempt accounting, outside the frozen Agent control plane.

A failed observation/poll never grants a retry. An outstanding reservation stops
admission until its actual process/evidence is reconciled. Wrong answers and
ordinary semantic failures are valid substantive samples, not exclusions.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from infra_joint.experiments.large_scale_protocol import GLOBAL_CAP

Disposition = Literal["valid", "operational_excluded", "confounder"]
OPERATIONAL_REASONS = frozenset({
    "provider_outage", "connection_reset", "worker_crash", "tc_prerun_failure",
    "external_model_service_failure",
})


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()


def _require_digest(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("a frozen SHA-256 receipt is required")


@dataclass(frozen=True)
class Attempt:
    cell_id: str
    run_id: str
    attempt_index: int
    execution_sha256: str
    disposition: Disposition | None = None
    reason: str | None = None
    receipt_sha256: str | None = None


class AttemptLedger:
    """Single-writer journal. Callers must hold the exclusive queue lease.

    The schedule is immutable and includes only authorized substantive cells.
    Every append is fsynced and hash-linked. Reading rejects a damaged tail rather
    than dropping it or silently re-starting a possibly live attempt.
    """

    def __init__(self, path: Path, cells: tuple[str, ...], schedule_sha256: str) -> None:
        if not cells or len(set(cells)) != len(cells) or len(cells) > GLOBAL_CAP:
            raise ValueError("a unique authorized schedule within the substantive cap is required")
        _require_digest(schedule_sha256)
        self.path, self.cells, self.schedule_sha256 = path, cells, schedule_sha256
        self._records: list[dict[str, object]] = []
        self._attempts: dict[str, Attempt] = {}
        if path.exists():
            self._load()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create: concurrent processes must never initialize twice.
            with path.open("x", encoding="utf-8"):
                pass
            self._append({"event": "freeze", "cells": list(cells),
                          "schedule_sha256": schedule_sha256, "cap": GLOBAL_CAP})

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        return tuple(self._attempts.values())

    @property
    def completed_cells(self) -> tuple[str, ...]:
        return tuple(cell for cell in self.cells if any(
            item.cell_id == cell and item.disposition == "valid" for item in self.attempts))

    @property
    def pending(self) -> tuple[Attempt, ...]:
        return tuple(item for item in self.attempts if item.disposition is None)

    def _load(self) -> None:
        raw = self.path.read_text(encoding="utf-8")
        if not raw or not raw.endswith("\n"):
            raise RuntimeError("empty or torn attempt journal; reconcile, never auto-restart")
        previous = "0" * 64
        for index, line in enumerate(raw.splitlines()):
            record = cast(dict[str, object], json.loads(line))
            payload = {key: value for key, value in record.items() if key != "sha256"}
            if (record.get("sequence") != index or record.get("previous_sha256") != previous
                    or record.get("sha256") != _digest(payload)):
                raise RuntimeError("attempt journal hash chain failed")
            self._apply(record)
            self._records.append(record)
            previous = str(record["sha256"])

    def _apply(self, record: dict[str, object]) -> None:
        event = record["event"]
        if not self._records and event != "freeze":
            raise RuntimeError("attempt journal must begin with its schedule freeze")
        if event == "freeze":
            if (self._records or record.get("cells") != list(self.cells)
                    or record.get("schedule_sha256") != self.schedule_sha256
                    or record.get("cap") != GLOBAL_CAP):
                raise RuntimeError("schedule drift or duplicate freeze")
        elif event == "reserved":
            cell, run = str(record["cell_id"]), str(record["run_id"])
            if run in self._attempts:
                raise RuntimeError("duplicate attempt identity")
            self._check_reservation(cell)
            prior = [item for item in self.attempts if item.cell_id == cell]
            if record["attempt_index"] != len(prior) + 1:
                raise RuntimeError("attempt index drift")
            execution = str(record["execution_sha256"])
            _require_digest(execution)
            if prior and prior[-1].execution_sha256 != execution:
                raise RuntimeError("operational replacement must use identical execution freeze")
            self._attempts[run] = Attempt(cell, run, len(prior) + 1, execution)
        elif event == "settled":
            run = str(record["run_id"])
            current = self._attempts.get(run)
            if current is None or current.disposition is not None:
                raise RuntimeError("cannot settle an unreserved or already settled attempt")
            disposition = str(record["disposition"])
            reason, receipt = str(record["reason"]), str(record["receipt_sha256"])
            _require_digest(receipt)
            if disposition not in {"valid", "operational_excluded", "confounder"}:
                raise ValueError("unknown attempt disposition")
            if disposition == "operational_excluded" and reason not in OPERATIONAL_REASONS:
                raise ValueError("ordinary Agent failure does not authorize replacement")
            self._attempts[run] = Attempt(
                current.cell_id, run, current.attempt_index, current.execution_sha256,
                cast(Disposition, disposition), reason, receipt,
            )
        else:
            raise RuntimeError("unknown journal event")

    def _append(self, event: dict[str, object]) -> None:
        record = {**event, "sequence": len(self._records),
                  "previous_sha256": self._records[-1]["sha256"] if self._records else "0" * 64,
                  "timestamp_utc": datetime.now(UTC).isoformat()}
        record["sha256"] = _digest(record)
        # Validate before disk mutation. Disk failure ends this process; subsequent
        # readers must reconcile the durable tail, never infer completion.
        self._apply(record)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._records.append(record)

    def _check_reservation(self, cell_id: str) -> None:
        if cell_id not in self.cells:
            raise ValueError("task replacement/new cell is outside the frozen schedule")
        if self.pending:
            raise RuntimeError("outstanding attempt: verify its process and reconcile evidence")
        if any(item.disposition == "confounder" for item in self.attempts):
            raise RuntimeError("unresolved system confounder prohibits queue continuation")
        if cell_id in self.completed_cells:
            raise RuntimeError("valid nominal cell must not be repeated")
        prior = [item for item in self.attempts if item.cell_id == cell_id]
        if len(prior) >= 2:
            raise RuntimeError("one operational replacement exhausted; stop affected block")
        if prior and prior[-1].disposition != "operational_excluded":
            raise RuntimeError("only an audited operational exclusion allows replacement")
        remaining = [cell for cell in self.cells if cell not in self.completed_cells]
        if not remaining or cell_id != remaining[0]:
            raise RuntimeError("frozen order cannot be skipped or reordered")

    def reserve(self, cell_id: str, run_id: str, execution_sha256: str) -> Attempt:
        if not run_id.strip():
            raise ValueError("new nonempty run ID is required")
        self._append({"event": "reserved", "cell_id": cell_id, "run_id": run_id,
                      "attempt_index": 1 + sum(item.cell_id == cell_id for item in self.attempts),
                      "execution_sha256": execution_sha256})
        return self._attempts[run_id]

    def settle(self, run_id: str, disposition: Disposition, reason: str,
               receipt_sha256: str) -> None:
        self._append({"event": "settled", "run_id": run_id, "disposition": disposition,
                      "reason": reason, "receipt_sha256": receipt_sha256})


class QueueLease:
    """Exclusive process ownership. A stale lease requires explicit reconciliation."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._identity: str | None = None

    def __enter__(self) -> "QueueLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._identity = json.dumps({"pid": os.getpid(), "started": datetime.now(UTC).isoformat()})
        with self.path.open("x", encoding="utf-8") as stream:
            stream.write(self._identity)
            stream.flush()
            os.fsync(stream.fileno())
        return self

    def __exit__(self, *args: object) -> None:
        if self._identity is None or self.path.read_text(encoding="utf-8") != self._identity:
            raise RuntimeError("queue lease ownership changed; no automatic removal")
        self.path.unlink()
