"""Exact pre-execution launch repair, not an operational/semantic retry waiver.

Original confounder and complete-run admissions stay unchanged. A separate
hash-linked journal authorization permits one identical measured execution only
after an independently frozen, tested launch-environment correction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import large_scale_resident_field_policy_review_v1 as previous
import large_scale_resident_launch_environment_v1 as environment

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = previous.DIRECTORY
AUTH_DIRECTORY = "preexecution-launch-repair-adjudications"
EVENT = "preexecution_launch_repair"
methods, records, policy = previous.methods, previous.records, previous.policy
sha256 = previous.sha256
FAILURE = {"code": "attempt_prerun_failed", "exception_type": "RuntimeError",
           "message": "code revision is unavailable; set INFRA_JOINT_CODE_REVISION "
           "for archive deploys"}


def owned_file(root: Path, relative: str) -> Path:
    path = root / relative
    if (Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())):
        raise RuntimeError("launch proof path escaped its owned namespace")
    return path


def verify_repair_freeze(root: Path, relative: str, digest: str) -> dict[str, Any]:
    path = owned_file(root, relative)
    if sha256(path) != digest:
        raise RuntimeError("launch correction freeze changed")
    value = json.loads(path.read_text())
    if (value.get("version") != "exact-preexecution-provenance-launch-repair-v1"
            or type(value.get("max_affected_reexecutions")) is not int
            or value.get("max_affected_reexecutions") != 1
            or value.get("measured_execution_changed") is not False
            or value.get("semantic_tuning") is not False):
        raise RuntimeError("launch repair must preserve the measured comparison")
    for name, expected in value["repair_sources_sha256"].items():
        if sha256(owned_file(root, name)) != expected:
            raise RuntimeError("launch correction source drift")
    actual = {str(Path(p).resolve().relative_to(root.resolve())): sha256(Path(p))
              for p in (__file__, environment.__file__)}
    if any(value["repair_sources_sha256"].get(p) != d for p, d in actual.items()):
        raise RuntimeError("launch correction requires the actual reviewer and environment source")
    freeze = owned_file(root, value["execution_freeze_file"])
    env = environment.pinned_environment(
        owned_file(root, value["archive_app"]), freeze,
        value["execution_freeze_file_sha256"], {})
    if (env[environment.REVISION_VARIABLE] != value["code_revision"]
            or provenance_sha256(json.loads(freeze.read_text())) != value["execution_sha256"]):
        raise RuntimeError("launch repair cannot substitute measured execution")
    receipts = {}
    for key, ref in value["validation_receipts"].items():
        receipt = owned_file(root, ref["filename"])
        if sha256(receipt) != ref["sha256"]:
            raise RuntimeError("launch repair validation receipt drift")
        receipts[key] = json.loads(receipt.read_text())
    local, linux = receipts["full_local"], receipts["linux"]
    if (type(local.get("pytest_passed")) is not int or local["pytest_passed"] <= 0
            or any(local.get(k) != 0 for k in ("pytest_returncode", "ruff_returncode",
                                              "strict_pyright_returncode", "diff_returncode"))
            or linux.get("pytest_returncode") != 0
            or type(linux.get("pytest_passed")) is not int or linux["pytest_passed"] <= 0
            or linux.get("preflight_returncode") != 0
            or linux.get("preflight_execution_sha256") != value["execution_sha256"]
            or local.get("repair_sources_sha256") != value["repair_sources_sha256"]
            or linux.get("repair_sources_sha256") != value["repair_sources_sha256"]):
        raise RuntimeError("launch repair requires source-bound full tests and real preflight")
    return value


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.name != AUTH_DIRECTORY
            or path.name != attempt.run_id + ".json"
            or attempt.disposition != "confounder" or attempt.reason != "admission_unverifiable"
            or attempt.attempt_index != 1):
        raise RuntimeError("launch repair requires an original unresolved pre-execution attempt")
    value = json.loads(path.read_text())
    correction = verify_repair_freeze(root, value["repair_freeze_file"],
                                     value["repair_freeze_file_sha256"])
    directory = root / "evidence" / attempt.cell_id / "attempt1"
    raw = json.loads((directory / "admission.json").read_text())
    if (raw != {"disposition": "confounder", "reason": "admission_unverifiable",
               "problems": ["FileNotFoundError"]}
            or provenance_sha256(raw) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["run_id"] != attempt.run_id
            or value["original_execution_sha256"] != attempt.execution_sha256
            or correction["execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))):
        raise RuntimeError("launch repair identity/admission/source mismatch")
    expected_files = {"admission.json", "console.log", "attempt-error.json", "process.json",
                      "process-exit.json", str(Path("runs") / attempt.run_id / "result.json"),
                      str(Path("runs") / attempt.run_id / "trace.jsonl")}
    files = methods.evidence_files(directory)
    if set(files) != expected_files or files != value["original_evidence_file_sha256"]:
        raise RuntimeError("pre-execution proof requires all and only the seven original files")
    result = json.loads((directory / "runs" / attempt.run_id / "result.json").read_text())
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").open(encoding="utf-8")]
    error = json.loads((directory / "attempt-error.json").read_text())
    process = json.loads((directory / "process.json").read_text())
    exit_value = json.loads((directory / "process-exit.json").read_text())
    if (result.get("failure") != FAILURE or result.get("execution_completed") is not False
            or result.get("evaluation") is not None or result.get("final_answer") is not None
            or result.get("loop") is not None or result.get("telemetry") is not None
            or [e["event_type"] for e in events] != ["run.start", "run.failed"]
            or events[0]["payload"] != {"attempt_before_runner": True}
            or events[1]["payload"] != {"failure": FAILURE}
            or error != {"exception_type": "RuntimeError", "message": FAILURE["message"],
                         "before_runner": True}
            or process.get("run_id") != attempt.run_id or type(process.get("pid")) is not int
            or process["pid"] <= 0
            or exit_value.get("pid") != process.get("pid")
            or type(exit_value.get("returncode")) is not int or exit_value["returncode"] == 0):
        raise RuntimeError("launch repair cannot waive an executed Agent/different setup failure")
    return value


class ProjectionAttemptLedger(previous.ProjectionAttemptLedger):
    def __init__(self, path: Path, cells: tuple[str, ...], schedule_sha256: str) -> None:
        self.launch_repairs: dict[str, str] = {}
        super().__init__(path, cells, schedule_sha256)

    def _apply(self, record: dict[str, object]) -> None:
        if record["event"] != EVENT:
            super()._apply(record)
            return
        run = str(record["run_id"])
        original = next((a for a in self.attempts if a.run_id == run), None)
        if original is None or run in self.launch_repairs or self.pending:
            raise RuntimeError("launch repair requires a unique settled original")
        sidecar = self.path.parent / AUTH_DIRECTORY / (run + ".json")
        value = verify_sidecar(sidecar, original)
        if (record["original_admission_sha256"] != original.receipt_sha256
                or record["repair_file_sha256"] != sha256(sidecar)
                or record["repair_freeze_file_sha256"] != value["repair_freeze_file_sha256"]
                or record["execution_sha256"] != original.execution_sha256):
            raise RuntimeError("launch authorization journal/source mismatch")
        self.launch_repairs[run] = sha256(sidecar)

    def _check_reservation(self, cell_id: str) -> None:
        for run, digest in self.launch_repairs.items():
            attempt = next(a for a in self.attempts if a.run_id == run)
            path = self.path.parent / AUTH_DIRECTORY / (run + ".json")
            verify_sidecar(path, attempt)
            if sha256(path) != digest:
                raise RuntimeError("launch authorization changed before reservation")
            if (attempt.cell_id == cell_id
                    and sum(a.cell_id == cell_id for a in self.attempts) >= 2):
                raise RuntimeError("one pre-execution launch repair exhausted")
        original_repairs = dict(self._repairs)
        try:
            # Bridge the existing generic-repair reservation guard only while it
            # validates. The separate journal event is not a new model/code epoch.
            self._repairs.update({run: next(a.execution_sha256 for a in self.attempts
                                           if a.run_id == run) for run in self.launch_repairs})
            super()._check_reservation(cell_id)
        finally:
            self._repairs = original_repairs

    def authorize_launch_repair(self, run_id: str) -> None:
        original = next(a for a in self.attempts if a.run_id == run_id)
        path = self.path.parent / AUTH_DIRECTORY / (run_id + ".json")
        value = verify_sidecar(path, original)
        self._append({"event": EVENT, "run_id": run_id,
                      "original_admission_sha256": original.receipt_sha256,
                      "repair_file_sha256": sha256(path),
                      "repair_freeze_file_sha256": value["repair_freeze_file_sha256"],
                      "execution_sha256": original.execution_sha256})


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    # Never mark this original launch failure valid or an operational outage.
    return previous.effective_admission(root, attempt)
