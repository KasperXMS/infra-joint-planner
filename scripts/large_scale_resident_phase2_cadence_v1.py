"""User-authorized 16-cell audit cadence, outside the frozen execution plane.

Keep the original execute_cell/admission and all historical sources unchanged.
Reuse only fully proved historical review metadata between full checkpoints.
New findings stop immediately; this controller never grants a retry or waiver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_field_queue_v1 as field
import large_scale_resident_phase2_field_snapshot_v1 as snapshot

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, AttemptLedger, QueueLease

INTERVAL = 16
MODULE = "large_scale_resident_phase2_cadence_v1"
PREFIX = "phase2-audit-cadence-freeze-"
frozen = field.frozen


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("existing non-symlink bound file required")
    return field.core.legacy.sha256(path)


class BatchLedger(AttemptLedger):
    """Immutable, source-proved old reviews; all new attempts remain raw.

The raw hash-linked journal is neither rewritten nor masked for new findings.
Disk continuity is checked before and after every append. Historical proof is
renewed at full checkpoints, not each property access within a 16-cell batch.
"""

    def __init__(self, path: Path, cells: tuple[str, ...], schedule: str,
                 reviews: tuple[tuple[Attempt, Attempt], ...]) -> None:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("cadence controller cannot initialize a journal")
        self._reviews = {raw.run_id: (raw, effective) for raw, effective in reviews}
        if len(self._reviews) != len(reviews) or any(
            raw.disposition != "confounder" or effective.disposition != "valid"
            or (raw.cell_id, raw.run_id, raw.attempt_index, raw.execution_sha256)
            != (effective.cell_id, effective.run_id, effective.attempt_index,
                effective.execution_sha256) for raw, effective in reviews
        ):
            raise RuntimeError("only exact previously proved historical reviews allowed")
        self._expected_bytes = path.read_bytes()
        super().__init__(path, cells, schedule)
        self.check_disk()
        if not set(self._reviews).issubset({a.run_id for a in self.original_attempts}):
            raise RuntimeError("review cannot refer to an absent raw attempt")
        if any(a.run_id in self._reviews and a != self._reviews[a.run_id][0]
               for a in self.original_attempts):
            raise RuntimeError("proved historical raw attempt changed")

    @property
    def original_attempts(self) -> tuple[Attempt, ...]:
        return super().attempts

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for raw in self.original_attempts:
            pair = self._reviews.get(raw.run_id)
            if pair is not None and raw.disposition is not None:
                if raw != pair[0]:
                    raise RuntimeError("proved historical raw attempt changed")
                result.append(pair[1])
            else:
                result.append(raw)
        return tuple(result)

    def check_disk(self) -> None:
        if self.path.is_symlink() or self.path.read_bytes() != self._expected_bytes:
            raise RuntimeError("journal changed outside this single-writer controller")

    def _append(self, event: dict[str, object]) -> None:
        self.check_disk()
        super()._append(event)
        self._expected_bytes += (json.dumps(self._records[-1], sort_keys=True,
                                           ensure_ascii=False) + "\n").encode("utf-8")
        self.check_disk()


def assert_startup_safe(root: Path, *, proc_root: Path = Path("/proc"),
                        own_pid: int | None = None) -> None:
    current = os.getpid() if own_pid is None else own_pid
    handles = [root / "queue-lease.json", *root.glob("queue-process-*.json"),
               *root.glob("evidence/*/attempt*/process.json")]
    for handle in handles:
        if not handle.exists():
            continue
        if handle.is_symlink():
            raise RuntimeError("startup handles must be owned files")
        pid = json.loads(handle.read_text(encoding="utf-8"))["pid"]
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise RuntimeError("startup process identity invalid")
        command = proc_root / str(pid) / "cmdline"
        if not command.exists() or root.name.encode() not in command.read_bytes():
            continue
        if (pid != current or handle.parent != root
                or not handle.name.startswith("queue-process-")
                or MODULE.encode() not in command.read_bytes()):
            raise RuntimeError("another live controller/atomic/lease prohibits startup")


def source_bindings() -> dict[str, str]:
    return {**field.sources(), MODULE + ".py": digest(Path(__file__)),
            "large_scale_resident_feedback_wire_v1.py": digest(
                Path(__file__).with_name("large_scale_resident_feedback_wire_v1.py"))}


def fresh_membership(value: dict[str, Any], cells: tuple[Any, ...], *,
                     require_dispatch_ready: bool) -> BatchLedger:
    """One actual original proof per sidecar per checkpoint, not per replay step."""
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    if journal.is_symlink() or not journal.is_file():
        raise RuntimeError("existing owned journal required")
    with journal.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    reserved = {r["run_id"]: r for r in rows if r["event"] == "reserved"}
    raw = {}
    for row in rows:
        if row["event"] == "settled":
            r = reserved[row["run_id"]]
            raw[row["run_id"]] = Attempt(r["cell_id"], r["run_id"], r["attempt_index"],
                                          r["execution_sha256"], row["disposition"],
                                          row["reason"], row["receipt_sha256"])
    models, fields = value["model_json_sidecars"], value["initial_field_sidecars"]
    if (set(models) & set(fields) or set(models) | set(fields)
            != {a.run_id + ".json" for a in raw.values() if a.disposition == "confounder"}):
        raise RuntimeError("every original finding requires its disjoint exact review")
    pairs = []
    for name in sorted(set(models) | set(fields)):
        attempt = raw[name[:-5]]
        is_model = name in models
        directory = field.core.DIRECTORY if is_model else field.review.DIRECTORY
        path = frozen.ROOT / directory / name
        if digest(path) != (models if is_model else fields)[name]:
            raise RuntimeError("checkpoint sidecar drift")
        proof = (field.core.verify_sidecar if is_model else field.review.verify_sidecar)(
            path, attempt)  # Original actual evidence/source proof, never a hash-only waiver.
        reason = field.core.legacy.REVIEW_REASON if is_model else field.review.field.REASON
        pairs.append((attempt, replace(attempt, disposition="valid", reason=reason,
                                       receipt_sha256=proof["reviewed_admission_sha256"])))
    ledger = BatchLedger(journal, tuple(c.cell_id for c in cells),
                         value["phase2_schedule_sha256"], tuple(pairs))
    if require_dispatch_ready and (ledger.pending
                                  or any(a.disposition != "valid" for a in ledger.attempts)):
        raise RuntimeError("pending/unresolved attempt prohibits continuation")
    return ledger


def full_control(control: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    original = field.checked_control
    namespace = {**original.__globals__, "checked_membership": fresh_membership}
    bound = FunctionType(original.__code__, namespace, original.__name__,
                         original.__defaults__, original.__closure__)
    result: tuple[dict[str, Any], tuple[Any, ...]] = bound(control)
    return result


def full_projection(root: Path, control: Path) -> dict[str, Any]:
    inputs = field.projection_inputs
    bound_inputs = FunctionType(inputs.__code__,
                                {**inputs.__globals__, "checked_membership": fresh_membership},
                                inputs.__name__, inputs.__defaults__, inputs.__closure__)
    queue_view = SimpleNamespace(**{**vars(field), "projection_inputs": bound_inputs})
    original = snapshot.collect
    bound = FunctionType(original.__code__, {**original.__globals__, "queue": queue_view},
                         original.__name__, original.__defaults__, original.__closure__)
    result: dict[str, Any] = bound(root, control_path=control)
    return result


def freeze_manifest(control: Path, receipt: Path, output: Path) -> dict[str, Any]:
    frozen.require_remote()
    field.core.previous.gate.evidence.private.assert_inactive(frozen.ROOT)
    if (output.resolve().parent != frozen.ROOT or output.is_symlink()
            or not output.name.startswith(PREFIX) or output.exists()):
        raise RuntimeError("exclusive owned cadence manifest required")
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    field.validate(control, receipt)
    saved, cells = full_control(control)  # One complete bootstrap proof.
    value = json.loads(control.read_text(encoding="utf-8"))
    view = fresh_membership(value, cells, require_dispatch_ready=True)
    raw = {a.run_id: a for a in view.original_attempts}
    effective = view.attempts
    pairs = tuple((raw[a.run_id], a) for a in effective if a != raw[a.run_id])
    references = {control, receipt, Path(value["parent_control_path"]),
                  Path(value["preserved_model_control_path"]),
                  Path(value["preserved_model_ledger_path"]), Path(saved["gate_path"]),
                  Path(saved["pricing_path"]), frozen.FREEZE, frozen.RULES,
                  frozen.ROOT / "phase1-attempts.jsonl",
                  *(Path(p) for p in saved["gate_input_paths"].values())}
    result = {
        "version": "resident-phase2-16-cell-audit-cadence-v1", "interval": INTERVAL,
        "aligned_completed_cell_boundaries": True, "final_remainder_audit": True,
        "created_utc": datetime.now(UTC).isoformat(), "control_path": str(control),
        "ledger_path": str(receipt), "parent": saved,
        "baseline_journal_sha256": digest(journal), "baseline_journal_bytes": len(before),
        "baseline_completed_cells": list(view.completed_cells),
        "historical_reviews": [{"raw": asdict(a), "effective": asdict(b)} for a, b in pairs],
        "bound_metadata_files": {str(p): digest(p) for p in sorted(references)},
        "source_sha256": source_bindings(),
        "reference_sha256": provenance_sha256(frozen.reference()),
        "model_json_sidecars": field.sidecars(field.core.DIRECTORY),
        "initial_field_sidecars": field.sidecars(field.review.DIRECTORY),
        "atomic_execution_changed": False, "per_cell_original_admission_preserved": True,
        "historical_proof_metadata_reuse_max_cells": INTERVAL,
        "original_sidecar_proofs_renewed_at_full_checkpoints": True,
        "ancestor_ledger_receipt_is_not_current_dispatch_cadence": True,
        "new_finding_stops_immediately": True, "semantic_tuning": False,
        "new_retry_authority": False, "private_body_guard_changed": False,
    }
    if journal.read_bytes() != before:
        raise RuntimeError("bootstrap journal advanced; no manifest written")
    field.core.previous.gate.evidence.private.assert_inactive(frozen.ROOT)
    frozen.write_new(output, result)
    return result


def metadata_fence(path: Path, expected_sha: str, value: dict[str, Any]) -> None:
    if (digest(path) != expected_sha or source_bindings() != value["source_sha256"]
            or any(digest(Path(p)) != sha for p, sha in value["bound_metadata_files"].items())
            or field.sidecars(field.core.DIRECTORY) != value["model_json_sidecars"]
            or field.sidecars(field.review.DIRECTORY) != value["initial_field_sidecars"]
            or provenance_sha256(frozen.reference()) != value["reference_sha256"]
            or frozen.verify_freeze() != value["parent"]["execution_freeze_sha256"]):
        raise RuntimeError("per-cell immutable source/config/review drift")


def run_batches(cells: tuple[Any, ...], ledger: BatchLedger,
                execute: Callable[[Any], None], quick_check: Callable[[], None],
                full_audit: Callable[[], None]) -> None:
    """Audit after 64/80/... from the transition, plus a final short remainder."""
    completed = len(ledger.completed_cells)
    next_boundary = (completed // INTERVAL + 1) * INTERVAL
    since_audit = 0
    if ledger.pending or any(a.disposition != "valid" for a in ledger.attempts):
        raise RuntimeError("pending/unresolved attempt prohibits cadence dispatch")
    for cell in cells:
        if cell.cell_id in ledger.completed_cells:
            continue
        ledger.check_disk()
        quick_check()
        execute(cell)  # Original atomic + admission; any new confounder raises here.
        ledger.check_disk()
        if ledger.pending or any(a.disposition != "valid" for a in ledger.attempts):
            raise RuntimeError("new finding requires immediate audit before next cell")
        since_audit += 1
        if len(ledger.completed_cells) >= next_boundary:
            full_audit()
            quick_check()
            since_audit = 0
            next_boundary += INTERVAL
    if since_audit or completed == len(cells):
        full_audit()
        quick_check()


def run(manifest_path: Path, expected_manifest_sha256: str) -> None:
    frozen.require_remote()
    root = frozen.ROOT
    assert_startup_safe(root)
    if manifest_path.resolve().parent != root or not manifest_path.name.startswith(PREFIX):
        raise RuntimeError("owned immutable cadence manifest required")
    manifest_sha = expected_manifest_sha256
    if digest(manifest_path) != manifest_sha:
        raise RuntimeError("launch-pinned cadence manifest drift")
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (value["version"] != "resident-phase2-16-cell-audit-cadence-v1"
            or value["interval"] != INTERVAL):
        raise RuntimeError("unexpected cadence contract")
    metadata_fence(manifest_path, manifest_sha, value)
    journal = root / "phase2-attempts.jsonl"
    prefix = journal.read_bytes()[:value["baseline_journal_bytes"]]
    if hashlib.sha256(prefix).hexdigest() != value["baseline_journal_sha256"]:
        raise RuntimeError("historical journal prefix changed")
    saved = value["parent"]
    control, receipt = Path(value["control_path"]), Path(value["ledger_path"])
    gate = json.loads(Path(saved["gate_path"]).read_text(encoding="utf-8"))
    cells = field.core.previous.cells_from_gate(gate)
    pairs = tuple((Attempt(**r["raw"]), Attempt(**r["effective"]))
                  for r in value["historical_reviews"])
    with QueueLease(root / "queue-lease.json"):
        ledger = BatchLedger(journal, tuple(c.cell_id for c in cells),
                             saved["phase2_schedule_sha256"], pairs)

        def quick() -> None:
            metadata_fence(manifest_path, manifest_sha, value)

        def audit() -> None:
            from large_scale_resident_feedback_wire_v1 import audit_feedback

            ledger.check_disk()
            field.validate(control, receipt)
            current, current_cells = full_control(control)
            if current != saved or current_cells != cells:
                raise RuntimeError("complete gate or immutable schedule drift")
            projection = full_projection(root, control)
            if (projection["pending_count"] or projection["confounded_attempts"]
                    or projection["admitted_cells"] != len(ledger.completed_cells)):
                raise RuntimeError("full checkpoint membership mismatch")
            wire = audit_feedback(projection)
            ledger.check_disk()
            quick()
            output = root / "analysis" / (
                manifest_path.stem + f"-cell{len(ledger.completed_cells):04d}.json")
            frozen.write_new(output, {
                "version": "resident-phase2-full-cadence-checkpoint-v1",
                "manifest_sha256": manifest_sha, "source_sha256": source_bindings(),
                "captured_utc": datetime.now(UTC).isoformat(),
                "journal_sha256": digest(journal), "projection": projection,
                "actual_feedback_wire": wire, "new_model_calls": 0,
                "private_semantic_audit_complete": False, "goal_complete": False,
            })

        def execute(cell: Any) -> None:
            original = field.core.previous.execute_cell
            ledger_type = field.core.previous.previous.quote.reviewer.QuoteRepairAttemptLedger
            original(cell, cast(ledger_type, ledger), saved)

        run_batches(cells, ledger, execute, quick, audit)
        frozen.write_new(root / "phase2-queue-completed.json", {
            "schedule_sha256": saved["phase2_schedule_sha256"],
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "cadence_manifest_sha256": manifest_sha,
            "next_required": "complete PhaseII private/failure/recipient/adoption and Q1-Q10 audit",
            "goal_complete": False,
        })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--queue", action="store_true")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--control-freeze", type=Path)
    parser.add_argument("--ledger-freeze", type=Path)
    args = parser.parse_args()
    if args.freeze:
        if args.control_freeze is None or args.ledger_freeze is None:
            parser.error("freeze requires original control and ledger")
        freeze_manifest(args.control_freeze, args.ledger_freeze, args.manifest)
        print(json.dumps({"output": str(args.manifest), "sha256": digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest SHA-256")
        run(args.manifest, args.manifest_sha256)
