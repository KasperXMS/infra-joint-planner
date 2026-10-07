"""Explicit one-attempt environmental exclusion outside frozen execution.

The user authorized exactly one identical replacement of cell71 after Strata
was coordinated off. Raw admissions, journal history, atomic execution and all
future residency gates remain unchanged. No semantic retry or general waiver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FunctionType
from typing import Any, cast

import large_scale_resident_feedback_wire_v2 as wire
import large_scale_resident_phase2_cadence_v1 as cadence
import resident_model_pool_attestation_v1 as resident

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

field = cadence.field
frozen = cadence.frozen
MODULE = "large_scale_resident_phase2_environment_v1"
PREFIX = "phase2-environment-cadence-freeze-"
DIRECTORY = "phase2-environment-adjudications-v2"
CELL = "phase2-video_mme-5-332db0bfa03dd109-p1-slow-E"
RUN = frozen.ROOT.name + "-" + CELL + "-attempt1"
RAW_SHA = "96d977ddfd2bfc7256537439838cec0631a9d9b4f45c87d1e7c8ab305e7c1b4c"
REASON = "user_authorized_external_gpu_contention"
MESSAGE = "external GPU compute contention changed during the cell"


def read(path: Path) -> dict[str, Any]:
    cadence.digest(path)
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def sources() -> dict[str, str]:
    return {**cadence.source_bindings(), **{Path(p).name: cadence.digest(Path(p)) for p in (
        __file__, wire.__file__, resident.__file__,
        Path(__file__).with_name("large_scale_resident_phase2_environment_private_v1.py"))}}


def prove_exclusion(attempt: Attempt, authorization: Path) -> dict[str, Any]:
    """Reproduce actual archived admission and residency rejection, without gold."""
    root = frozen.ROOT
    approval = read(authorization)
    if (authorization.resolve().parent != root or approval != {
        "version": "cell71-environment-replacement-user-authorization-v1",
        "run_id": RUN, "cell_id": CELL, "original_admission_sha256": RAW_SHA,
        "maximum_replacements": 1, "identical_execution_required": True,
        "original_attempt_preserved_as_invalid": True, "strata_coordinated_stopped": True,
        "semantic_retries": False,
    } or attempt.run_id != RUN or attempt.cell_id != CELL or attempt.attempt_index != 1
            or attempt.disposition != "confounder" or attempt.receipt_sha256 != RAW_SHA):
        raise RuntimeError("exact user-approved cell71 exclusion required")
    directory = root / "evidence" / CELL / "attempt1"
    original = read(directory / "admission.json")
    if (original != {"disposition": "confounder", "reason": "admission_unverifiable",
                     "problems": ["FileNotFoundError"]}
            or provenance_sha256(original) != RAW_SHA
            or read(directory / "attempt-error.json") != {
                "exception_type": "RuntimeError", "message": MESSAGE, "before_runner": False}
            or read(directory / "process-exit.json")["returncode"] != 1
            or read(directory / "worker-shutdown.json")["verified_exited"] is not True
            or (directory / "private/residency-validation.json").exists()):
        raise RuntimeError("original environmental failure/cleanup provenance changed")
    tc = read(directory / "tc-attestation.json")
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        raise RuntimeError("environmental exclusion cannot waive tc cleanup")
    bound = field.core.bindings.frozen_sources(root, attempt, (
        "scripts/resident_model_pool_attestation_v1.py",
        "scripts/resident_model_pool_service_v1.py"))
    if bound["scripts/resident_model_pool_attestation_v1.py"] != cadence.digest(
            Path(resident.__file__)):
        raise RuntimeError("original residency implementation must remain identical")
    before = read(directory / "private/residency-before.json")
    after = read(directory / "private/residency-after.json")
    if set(before) != {"A4", "A5", "A28", "strong-4090"} or before.keys() != after.keys():
        raise RuntimeError("complete original resident surface required")
    rejected = []
    for node in before:
        try:
            resident.compare_residency(before[node], after[node])
        except RuntimeError as error:
            if node != "strong-4090" or str(error) != MESSAGE:
                raise
            rejected.append(node)
    if rejected != ["strong-4090"]:
        raise RuntimeError("only the actual external GPU set change can be excluded")
    parent = read(root / "phase2-control-freeze-001.json")
    if attempt.execution_sha256 != parent["execution_freeze_sha256"]:
        raise RuntimeError("original execution freeze mismatch")
    config = frozen.frozen._yaml(root / "cell-configs" / (RUN + ".yaml"))
    base_admission = field.core.previous.execute_cell.__globals__["admission"](
        directory, config, Path(parent["pricing_path"]))
    if base_admission["disposition"] != "valid" or base_admission.get("problems"):
        raise RuntimeError("environmental exclusion cannot waive other admission problems")
    events = field.base.JsonlTraceWriter(directory / "runs" / RUN / "trace.jsonl").read_all()
    field.core.previous.execute_cell.__globals__["method_contract"].assert_E_tool_isolation(
        directory, events)
    return {
        "version": "cell71-source-bound-environment-exclusion-v1",
        "raw": asdict(attempt), "reason": REASON, "maximum_replacements": 1,
        "authorization_path": str(authorization),
        "authorization_sha256": cadence.digest(authorization), "source_sha256": sources(),
        "execution_source_sha256": bound,
        "original_evidence_file_sha256": field.core.bindings.evidence_files(directory),
        "reproduced_base_admission": base_admission,
        "original_residency_validation_missing": True,
        "original_result_is_not_valid_baseline_sample": True,
        "new_model_calls": 0, "new_private_semantic_body_scan": False,
        "atomic_execution_changed": False,
    }


def verify_exclusion(path: Path, attempt: Attempt) -> dict[str, Any]:
    if (path.resolve().parent != frozen.ROOT / DIRECTORY
            or path.parent.is_symlink() or path.name != RUN + ".json"):
        raise RuntimeError("owned exact environmental sidecar required")
    value = read(path)
    if value != prove_exclusion(attempt, Path(value["authorization_path"])):
        raise RuntimeError("environmental source/evidence proof cannot be reproduced")
    return value


class EnvironmentLedger(cadence.BatchLedger):
    def __init__(self, path: Path, cells: tuple[str, ...], schedule: str,
                 reviews: tuple[tuple[Attempt, Attempt], ...],
                 exclusion: tuple[Attempt, Attempt]) -> None:
        raw, effective = exclusion
        if (raw.run_id != RUN or raw.cell_id != CELL or raw.attempt_index != 1
                or raw.disposition != "confounder" or raw.receipt_sha256 != RAW_SHA
                or effective != replace(raw, disposition="operational_excluded", reason=REASON,
                                        receipt_sha256=effective.receipt_sha256)
                or not effective.receipt_sha256):
            raise RuntimeError("only the exact authorized environmental pair is allowed")
        self.exclusion = exclusion
        super().__init__(path, cells, schedule, reviews)
        if raw not in self.original_attempts:
            raise RuntimeError("environmental proof refers to an absent/changed raw attempt")

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result = []
        for raw in super().attempts:
            if raw.run_id == self.exclusion[0].run_id and raw.disposition is not None:
                if raw != self.exclusion[0]:
                    raise RuntimeError("original environmental attempt changed")
                result.append(self.exclusion[1])
            else:
                result.append(raw)
        return tuple(result)

    def _check_reservation(self, cell_id: str) -> None:
        if cell_id == CELL and sum(a.cell_id == CELL for a in self.attempts) >= 2:
            raise RuntimeError("one authorized environmental replacement exhausted")
        super()._check_reservation(cell_id)


def dispatch_ready(ledger: EnvironmentLedger) -> None:
    if ledger.pending or any(a.disposition != "valid" and a != ledger.exclusion[1]
                             for a in ledger.attempts):
        raise RuntimeError("pending/new finding prohibits continuation")


def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
               require_dispatch_ready: bool) -> EnvironmentLedger:
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    reserved = {r["run_id"]: r for r in rows if r["event"] == "reserved"}
    raw = {}
    for row in rows:
        if row["event"] == "settled":
            r = reserved[row["run_id"]]
            raw[row["run_id"]] = Attempt(r["cell_id"], r["run_id"], r["attempt_index"],
                                          r["execution_sha256"], row["disposition"],
                                          row["reason"], row["receipt_sha256"])
    models, fields = value["model_json_sidecars"], value["initial_field_sidecars"]
    if (set(models) & set(fields) or set(models) | set(fields) | {RUN + ".json"}
            != {a.run_id + ".json" for a in raw.values() if a.disposition == "confounder"}):
        raise RuntimeError("every raw finding needs its disjoint exact proof")
    pairs = []
    for name in sorted(set(models) | set(fields)):
        model = name in models
        path = frozen.ROOT / (field.core.DIRECTORY if model else field.review.DIRECTORY) / name
        if cadence.digest(path) != (models if model else fields)[name]:
            raise RuntimeError("historical sidecar drift")
        attempt = raw[name[:-5]]
        proof = (field.core.verify_sidecar if model else field.review.verify_sidecar)(path, attempt)
        reason = field.core.legacy.REVIEW_REASON if model else field.review.field.REASON
        pairs.append((attempt, replace(attempt, disposition="valid", reason=reason,
                                       receipt_sha256=proof["reviewed_admission_sha256"])))
    verify_exclusion(sidecar, raw[RUN])
    exclusion = (raw[RUN], replace(raw[RUN], disposition="operational_excluded", reason=REASON,
                                  receipt_sha256=cadence.digest(sidecar)))
    ledger = EnvironmentLedger(journal, tuple(c.cell_id for c in cells),
                               value["phase2_schedule_sha256"], tuple(pairs), exclusion)
    if require_dispatch_ready:
        dispatch_ready(ledger)
    return ledger


def full_control(control: Path, sidecar: Path) -> tuple[dict[str, Any], tuple[Any, ...]]:
    def checked(value: dict[str, Any], cells: tuple[Any, ...], *,
                require_dispatch_ready: bool) -> EnvironmentLedger:
        return membership(value, cells, sidecar, require_dispatch_ready=require_dispatch_ready)

    original = field.checked_control
    bound = FunctionType(original.__code__, {**original.__globals__, "checked_membership": checked},
                         original.__name__, original.__defaults__, original.__closure__)
    result: tuple[dict[str, Any], tuple[Any, ...]] = bound(control)
    return result


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    ledger.check_disk()
    before = ledger.path.read_bytes()
    parent = value["parent"]
    gate = read(Path(parent["gate_path"]))
    raw = {a.run_id: a for a in ledger.original_attempts}
    records = []
    for condition in gate["schedule"]:
        attempts = []
        for attempt in ledger.attempts:
            if attempt.cell_id != condition["cell_id"] or attempt.disposition is None:
                continue
            original = raw[attempt.run_id]
            record = field.base.settled(frozen.ROOT, original, parent["execution_freeze_sha256"])
            record.update(original_disposition=original.disposition,
                          original_reason=original.reason,
                          original_receipt_sha256=original.receipt_sha256,
                          disposition=attempt.disposition, reason=attempt.reason,
                          receipt_sha256=attempt.receipt_sha256, adjudicated=attempt != original,
                          effective_admission=(
                              {"disposition": "operational_excluded", "reason": REASON}
                              if attempt == ledger.exclusion[1]
                              else field.review.effective_admission(frozen.ROOT, attempt)),
                          environment_stage=("strata-transition" if attempt.run_id == RUN
                                             else "pre-strata" if attempt.run_id in
                                             value["baseline_run_ids"] else "post-strata"))
            attempts.append(record)
        records.append({"condition": condition, "attempts": attempts, "pending_run_ids": [
            a.run_id for a in ledger.pending if a.cell_id == condition["cell_id"]]})
    if before != ledger.path.read_bytes():
        raise RuntimeError("projection journal advanced")
    return {"version": "resident-phase2-environment-reviewed-projection-v1", "rows": records,
            "journal_sha256": cadence.digest(ledger.path), "scheduled_cells": len(records),
            "admitted_cells": len(ledger.completed_cells), "pending_count": len(ledger.pending),
            "attempt_count": len(ledger.attempts), "phase2_complete": len(ledger.completed_cells)
            == len(records), "confounded_attempts": sum(a.disposition == "confounder"
                                                        for a in ledger.attempts),
            "operational_excluded_attempts": 1,
            "execution_freeze_sha256": parent["execution_freeze_sha256"],
            "phase2_schedule_sha256": parent["phase2_schedule_sha256"],
            "control_file_sha256": cadence.digest(Path(value["control_path"])),
            "private_semantic_audit_complete": False, "score_aggregation": "not performed"}


def audit_wire(projection: dict[str, Any], sidecar: Path) -> dict[str, Any]:
    proof = read(sidecar)
    raw = Attempt(**proof["raw"])
    verify_exclusion(sidecar, raw)

    def resolve(directory: Path, original: dict[str, Any],
                reproduced: dict[str, Any]) -> dict[str, Any]:
        if directory != frozen.ROOT / "evidence" / CELL / "attempt1":
            return original
        if (provenance_sha256(original) != RAW_SHA
                or reproduced != proof["reproduced_base_admission"]):
            raise RuntimeError("excluded original recipient/admission drift")
        return reproduced  # Scan all original requests, never claim the sample valid.

    return wire.audit_feedback(projection, resolve)


def require_strata_stopped() -> None:
    state = subprocess.run(["systemctl", "--user", "show", "strata.service",
                            "--property=ActiveState,SubState,MainPID"], capture_output=True,
                           text=True, check=True, timeout=15).stdout
    values = dict(line.split("=", 1) for line in state.splitlines())
    gpu = subprocess.run(["nvidia-smi", "--query-compute-apps=process_name",
                          "--format=csv,noheader"], capture_output=True, text=True,
                         check=True, timeout=15).stdout
    if values != {"ActiveState": "inactive", "SubState": "dead", "MainPID": "0"} or any(
            Path(line.strip()).name == "strata" for line in gpu.splitlines()):
        raise RuntimeError("coordinated-off Strata boundary changed; do not dispatch")


def freeze(control: Path, receipt: Path, authorization: Path, output: Path) -> dict[str, Any]:
    frozen.require_remote()
    field.core.previous.gate.evidence.private.assert_inactive(frozen.ROOT)
    if output.resolve().parent != frozen.ROOT or not output.name.startswith(PREFIX):
        raise RuntimeError("owned exclusive environment manifest required")
    if output.exists():
        raise FileExistsError("environment manifest creator must not repeat")
    require_strata_stopped()
    field.validate(control, receipt)
    parent = read(frozen.ROOT / "phase2-control-freeze-001.json")
    gate = read(Path(parent["gate_path"]))
    cells = field.core.previous.cells_from_gate(gate)
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    old = read(frozen.ROOT / "phase2-audit-cadence-freeze-003.json")
    pairs = tuple((Attempt(**r["raw"]), Attempt(**r["effective"]))
                  for r in old["historical_reviews"])
    view = cadence.BatchLedger(journal, tuple(c.cell_id for c in cells),
                               parent["phase2_schedule_sha256"], pairs)
    original = next(a for a in view.original_attempts if a.run_id == RUN)
    sidecar = frozen.ROOT / DIRECTORY / (RUN + ".json")
    proof = prove_exclusion(original, authorization)
    frozen.write_new(sidecar, proof)
    saved, checked_cells = full_control(control, sidecar)
    if saved != parent or checked_cells != cells:
        raise RuntimeError("complete original gate/schedule drift")
    ledger = membership(read(control), cells, sidecar, require_dispatch_ready=True)
    references = {control, receipt, authorization, sidecar,
                  frozen.ROOT / "phase2-audit-cadence-freeze-003.json",
                  *(Path(p) for p in old["bound_metadata_files"])}
    result = {"version": "resident-phase2-user-authorized-environment-continuation-v1",
              "created_utc": datetime.now(UTC).isoformat(), "interval": cadence.INTERVAL,
              "parent": parent, "control_path": str(control), "ledger_path": str(receipt),
              "sidecar_path": str(sidecar), "source_sha256": sources(),
              "baseline_journal_bytes": len(before),
              "baseline_journal_sha256": cadence.digest(journal),
              "baseline_run_ids": [a.run_id for a in ledger.original_attempts],
              "bound_metadata_files": {str(p): cadence.digest(p) for p in sorted(references)},
              "reference_sha256": provenance_sha256(frozen.reference()),
              "historical_reviews": old["historical_reviews"],
              "exclusion": {"raw": asdict(ledger.exclusion[0]),
                            "effective": asdict(ledger.exclusion[1])},
              "model_json_sidecars": old["model_json_sidecars"],
              "initial_field_sidecars": old["initial_field_sidecars"],
              "new_environment_stage": "post-strata", "atomic_execution_changed": False,
              "new_findings_stop_immediately": True, "maximum_cell71_replacements": 1,
              "private_body_guard_changed": False, "semantic_tuning": False}
    projection = collect(result, ledger)
    audit_wire(projection, sidecar)  # All71 preserved traces/actual SDK requests, not just64.
    if before != journal.read_bytes():
        raise RuntimeError("freeze journal advanced")
    field.core.previous.gate.evidence.private.assert_inactive(frozen.ROOT)
    frozen.write_new(output, result)
    return result


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    if (cadence.digest(path) != sha or sources() != value["source_sha256"]
            or any(cadence.digest(Path(p)) != h for p, h in value["bound_metadata_files"].items())
            or field.sidecars(field.core.DIRECTORY) != value["model_json_sidecars"]
            or field.sidecars(field.review.DIRECTORY) != value["initial_field_sidecars"]
            or frozen.verify_freeze() != value["parent"]["execution_freeze_sha256"]
            or provenance_sha256(frozen.reference()) != value["reference_sha256"]):
        raise RuntimeError("environment controller immutable source/evidence drift")


def run_batches(cells: tuple[Any, ...], ledger: EnvironmentLedger,
                execute: Callable[[Any], None], quick: Callable[[], None],
                audit: Callable[[], None]) -> None:
    dispatch_ready(ledger)
    boundary = (len(ledger.completed_cells) // cadence.INTERVAL + 1) * cadence.INTERVAL
    since_audit = 0
    for cell in cells:
        if cell.cell_id in ledger.completed_cells:
            continue
        ledger.check_disk()
        quick()
        execute(cell)
        ledger.check_disk()
        dispatch_ready(ledger)
        since_audit += 1
        if len(ledger.completed_cells) >= boundary:
            audit()
            quick()
            since_audit = 0
            boundary += cadence.INTERVAL
    if since_audit:
        audit()
        quick()


def run(path: Path, expected_sha: str) -> None:
    frozen.require_remote()
    # Registered self exemption is startup-only; original private global guard unchanged.
    original = cadence.assert_startup_safe
    safe = FunctionType(original.__code__, {**original.__globals__, "MODULE": MODULE},
                        original.__name__, original.__defaults__, original.__closure__)
    safe.__kwdefaults__ = dict(original.__kwdefaults__ or {})
    safe(frozen.ROOT)
    if path.resolve().parent != frozen.ROOT or not path.name.startswith(PREFIX):
        raise RuntimeError("owned launch-pinned environment manifest required")
    value = read(path)
    if value["version"] != "resident-phase2-user-authorized-environment-continuation-v1":
        raise RuntimeError("unexpected environmental authority")
    fence(path, expected_sha, value)
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    if hashlib.sha256(journal.read_bytes()[:value["baseline_journal_bytes"]]).hexdigest() != value[
            "baseline_journal_sha256"]:
        raise RuntimeError("original journal prefix changed")
    parent = value["parent"]
    cells = field.core.previous.cells_from_gate(read(Path(parent["gate_path"])))
    reviews = tuple((Attempt(**r["raw"]), Attempt(**r["effective"]))
                    for r in value["historical_reviews"])
    exclusion = value["exclusion"]
    with QueueLease(frozen.ROOT / "queue-lease.json"):
        ledger = EnvironmentLedger(journal, tuple(c.cell_id for c in cells),
                                   parent["phase2_schedule_sha256"], reviews,
                                   (Attempt(**exclusion["raw"]), Attempt(**exclusion["effective"])))

        def quick() -> None:
            fence(path, expected_sha, value)
            require_strata_stopped()

        def audit() -> None:
            field.validate(Path(value["control_path"]), Path(value["ledger_path"]))
            saved, current = full_control(Path(value["control_path"]), Path(value["sidecar_path"]))
            if saved != parent or current != cells:
                raise RuntimeError("full original gate changed")
            projection = collect(value, ledger)
            actual_wire = audit_wire(projection, Path(value["sidecar_path"]))
            ledger.check_disk()
            quick()
            frozen.write_new(frozen.ROOT / "analysis" / (
                path.stem + f"-cell{len(ledger.completed_cells):04d}.json"), {
                    "version": "resident-phase2-environment-full-cadence-checkpoint-v1",
                    "manifest_sha256": expected_sha, "source_sha256": sources(),
                    "captured_utc": datetime.now(UTC).isoformat(),
                    "journal_sha256": cadence.digest(journal), "projection": projection,
                    "actual_feedback_wire": actual_wire, "new_model_calls": 0,
                    "private_semantic_audit_complete": False, "goal_complete": False})

        def execute(cell: Any) -> None:
            ledger_type = field.core.previous.previous.quote.reviewer.QuoteRepairAttemptLedger
            field.core.previous.execute_cell(cell, cast(ledger_type, ledger), parent)

        run_batches(cells, ledger, execute, quick, audit)
        frozen.write_new(frozen.ROOT / "phase2-queue-completed.json", {
            "completed_cells": ledger.completed_cells, "attempt_count": len(ledger.attempts),
            "environment_manifest_sha256": expected_sha, "goal_complete": False,
            "next_required": (
                "strict-inactive full private/failure/recipient/adoption/Q1-Q10 audit")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--control", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    if args.freeze:
        if any(x is None for x in (args.control, args.ledger, args.authorization)):
            parser.error("freeze requires exact prior control/ledger/user authorization")
        freeze(args.control, args.ledger, args.authorization, args.manifest)
        print(json.dumps({"manifest": str(args.manifest), "sha256": cadence.digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest digest")
        run(args.manifest, args.manifest_sha256)
