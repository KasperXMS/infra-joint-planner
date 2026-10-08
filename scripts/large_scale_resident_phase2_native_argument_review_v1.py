"""Offline Phase II proof of source-bound malformed native specialist JSON.

Preserve the original admission, evidence, request, execution and journals. The
separate fifth review group cannot alter the historical Phase I inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import large_scale_resident_phase2_filtered_field_review_v1 as previous
import large_scale_resident_sdk_argument_review_v1 as sdk

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

core = previous.core
bindings = previous.bindings
renewed = previous.renewed
DIRECTORY = "phase2-native-specialist-json-adjudications"
REASON = sdk.REASON
HISTORICAL_NAME = (
    "large-scale-cost-guidance-resident-v1-phase1-multihop_rag-2-"
    "2d3129ed85c03f62-p1-slow-A-attempt1.json")
HISTORICAL_SHA = "d240e209996860e13fefa34c24f8ceab862c623bc91d8875e8da01bcd7223acc"
INITIAL_JOURNAL_SHA = "03aec69d77d3876121e4a1dd31608c1a4857763893b0482eab26a6949008828c"


def sources() -> dict[str, str]:
    return {**previous.sources(), **{Path(p).name: core.legacy.sha256(Path(p))
            for p in (__file__, sdk.__file__, sdk.previous.__file__)}}


def proof(root: Path, attempt: Attempt, parent_path: Path,
          historical_path: Path) -> dict[str, Any]:
    if (parent_path.is_symlink() or parent_path.resolve().parent != root
            or not parent_path.name.startswith("phase2-control-freeze-")):
        raise RuntimeError("owned original Phase II parent required")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if (parent["source_sha256"] != core.previous.source_bindings()
            or parent["execution_freeze_sha256"] != core.frozen.verify_freeze()):
        raise RuntimeError("original parent/atomic source drift")
    directory = core.evidence(root, attempt)
    original = json.loads((directory / "admission.json").read_text(encoding="utf-8"))
    if (attempt.disposition != "confounder" or attempt.reason != sdk.GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or attempt.execution_sha256 != parent["execution_freeze_sha256"]):
        raise RuntimeError("exact original settled native JSON finding required")
    config = vars(core.frozen.frozen)["_yaml"](
        root / "cell-configs" / (attempt.run_id + ".yaml"))
    if (core.previous.previous.admission(directory, config, Path(parent["pricing_path"]))
            != original
            or json.loads((directory / "process-exit.json").read_text())["returncode"] != 0
            or json.loads((directory / "worker-shutdown.json").read_text())[
                "verified_exited"] is not True
            or json.loads((directory / "private/residency-validation.json").read_text())[
                "passed"] is not True):
        raise RuntimeError("complete original admission/exit/residency must reproduce")
    tc = json.loads((directory / "tc-attestation.json").read_text())
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        raise RuntimeError("native argument proof cannot waive network cleanup")
    if (historical_path.is_symlink() or historical_path.parent.is_symlink()
            or historical_path.resolve().parent != root / sdk.SEMANTIC_DIRECTORY
            or historical_path.name != HISTORICAL_NAME
            or core.legacy.sha256(historical_path) != HISTORICAL_SHA):
        raise RuntimeError("exact pinned historical native argument proof required")
    old_attempt = previous.previous.previous.historical_attempt(root, historical_path.stem)
    historical = sdk.verify_sidecar(historical_path, old_attempt)
    execution = sdk.execution_sources(root)
    if execution != historical["execution_sources"]:
        raise RuntimeError("actual native/SDK lexical and resolved sources must match history")
    evidence = bindings.evidence_files(directory)
    events = JsonlTraceWriter(directory / "runs" / attempt.run_id / "trace.jsonl").read_all()
    verified = sdk.review(original, directory / "private/api", events)
    return {"version": "phase2-source-bound-native-argument-review-v1", **verified,
            "covered_original_findings": [sdk.GATE], "run_id": attempt.run_id,
            "original_admission_sha256": attempt.receipt_sha256,
            "original_execution_sha256": attempt.execution_sha256,
            "parent_control_path": str(parent_path),
            "parent_control_file_sha256": core.legacy.sha256(parent_path),
            "historical_sidecar_path": str(historical_path),
            "historical_sidecar_file_sha256": core.legacy.sha256(historical_path),
            "execution_sources": execution, "reviewer_sources_sha256": sources(),
            "original_evidence_file_sha256": evidence,
            "reviewed_admission_sha256": provenance_sha256(verified["reviewed_admission"]),
            "new_store_or_corpus_body_decoded": False, "online_feedback": False,
            "formal_execution_changed": False, "replacement_authorized": False,
            "missing_model_telemetry_imputed": False, "new_model_calls": 0}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    if (path.is_symlink() or path.parent.is_symlink() or path.parent.name != DIRECTORY
            or path.name != attempt.run_id + ".json"):
        raise RuntimeError("owned exact Phase II native argument sidecar required")
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if value != proof(root, attempt, Path(value["parent_control_path"]),
                      Path(value["historical_sidecar_path"])):
        raise RuntimeError("native argument source/evidence proof drift")
    return value


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous.effective_admission(root, attempt)
    path = root / DIRECTORY / (attempt.run_id + ".json")
    if path.is_symlink() or path.parent.is_symlink():
        raise RuntimeError("owned effective native argument sidecar required")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (attempt.disposition != "valid" or value["run_id"] != attempt.run_id
            or value["reviewed_admission_sha256"] != attempt.receipt_sha256
            or provenance_sha256(value["reviewed_admission"]) != attempt.receipt_sha256):
        raise RuntimeError("effective native argument admission/ledger mismatch")
    admission: dict[str, Any] = value["reviewed_admission"]
    return admission


def pending_ledger(value: dict[str, Any], cells: tuple[Any, ...], journal: Path,
                   run_id: str) -> tuple[Any, Attempt]:
    original = previous.creator.review
    field = SimpleNamespace(**{**vars(original.field), "GATE": sdk.GATE})
    review = SimpleNamespace(**{**vars(original), "field": field})
    return renewed.copied(previous.creator.pending_ledger, {"review": review})(
        value, cells, journal, run_id)


def _preflight(environment: Any, value: dict[str, Any], expected: dict[str, Any],
               path: Path, target: Attempt, candidate: dict[str, Any],
               schedule: tuple[Any, ...]) -> None:
    """Run the complete gate with one exact, privately bound candidate proof.

    Its canonical digest is a preflight identity only. The actual file receipt
    is obtained after exclusive creation; every existing file uses real bytes.
    """
    candidate_sha = provenance_sha256(candidate)

    def digest(file: Path) -> str:
        if file == path and not file.exists():
            return candidate_sha
        return environment.cadence.digest(file)

    def verify(file: Path, attempt: Attempt) -> dict[str, Any]:
        if file == path and not file.exists() and attempt == target:
            return candidate
        return verify_sidecar(file, attempt)

    reviewer = SimpleNamespace(**{**vars(environment.native), "verify_sidecar": verify})
    cadence = SimpleNamespace(**{**vars(environment.cadence), "digest": digest})
    pairs = environment.copied(environment._review_pairs,
                              {"native": reviewer, "cadence": cadence})
    membership = environment.copied(environment.membership,
                                    {"_review_pairs": pairs, "cadence": cadence})
    groups = {**expected, "native_argument_sidecars": {
        **expected["native_argument_sidecars"], path.name: candidate_sha}}

    def checked(control: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
                require_dispatch_ready: bool) -> Any:
        ledger = membership({**control, **groups}, cells, sidecar,
                            require_dispatch_ready=require_dispatch_ready)
        raw = {a.run_id: a for a in ledger.original_attempts}
        effective = {a.run_id: a for a in ledger.attempts}
        for pair in value["historical_reviews"]:
            original, reviewed = Attempt(**pair["raw"]), Attempt(**pair["effective"])
            if raw.get(original.run_id) != original or effective.get(original.run_id) != reviewed:
                raise RuntimeError("historical raw/effective native preflight pair changed")
        if ledger.exclusion != (Attempt(**value["exclusion"]["raw"]),
                                Attempt(**value["exclusion"]["effective"])):
            raise RuntimeError("original environmental exclusion changed")
        return ledger

    full_control = environment.copied(environment.full_control, {"membership": checked})
    saved, cells = full_control(Path(value["control_path"]), Path(value["sidecar_path"]),
                                groups["derived_field_sidecars"],
                                groups["filtered_field_sidecars"],
                                groups["native_argument_sidecars"])
    if saved != value["parent"] or cells != schedule:
        raise RuntimeError("complete original parent changed during native candidate proof")


def create_review(manifest: Path, manifest_sha256: str, run_id: str,
                  historical_path: Path) -> dict[str, Any]:
    environment = import_module("large_scale_resident_phase2_native_environment_v1")
    core.frozen.require_remote()
    root = core.frozen.ROOT
    inactive = core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = renewed.read(manifest)

    def fence() -> None:
        if value.get("extension_version") == environment.VERSION:
            environment.fence(manifest, manifest_sha256, value)
        else:
            if (manifest.name != environment.PARENT_NAME
                    or manifest_sha256 != environment.PARENT_SHA):
                raise RuntimeError("initial native review requires pinned filtered001 authority")
            if environment.current_inventory()["native_argument_sidecars"]:
                raise RuntimeError("filtered001 cannot ignore existing native argument proofs")
            environment.filtered.fence(manifest, manifest_sha256, value)

    fence()
    renewed.environment.require_strata_stopped()
    directory = root / DIRECTORY
    path = directory / (run_id + ".json")
    if (Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase2-")
            or directory.is_symlink() or path.exists() or path.is_symlink()):
        raise RuntimeError("owned exclusive original native argument sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    if (value.get("extension_version") != environment.VERSION
            and hashlib.sha256(before).hexdigest() != INITIAL_JOURNAL_SHA):
        raise RuntimeError("initial native review requires the exact current journal")
    expected = environment.inventory(value)
    with QueueLease(root / "queue-lease.json"):
        parent_path = Path(renewed.read(Path(value["control_path"]))["parent_control_path"])
        schedule = core.previous.cells_from_gate(renewed.read(Path(value["parent"]["gate_path"])))
        ledger, target = pending_ledger(value, schedule, journal, run_id)
        verified = proof(root, target, parent_path, historical_path)
        _preflight(environment, value, expected, path, target, verified, schedule)
        ledger.check_disk()
        fence()
        renewed.environment.require_strata_stopped()
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before or environment.current_inventory() != expected:
            raise RuntimeError("review cannot change the original journal or inventory")
        directory.mkdir(exist_ok=True)
        core.frozen.write_new(path, verified)
        verify_sidecar(path, target)
        ledger.check_disk()
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change the original journal")
        delta = environment.extension_delta(expected, environment.current_inventory())
        exact_delta: dict[str, dict[str, str]] = {key: {} for key in environment.GROUPS}
        exact_delta["native_argument_sidecars"] = {path.name: renewed.cadence.digest(path)}
        if delta != exact_delta:
            raise RuntimeError("creator may add only the exact target native argument sidecar")
    inactive(root)
    return {"sidecar_path": str(path), "sha256": renewed.cadence.digest(path),
            "creator_source_sha256": renewed.cadence.digest(Path(__file__)),
            "parent_manifest_sha256": manifest_sha256,
            "original_journal_sha256": hashlib.sha256(before).hexdigest(),
            "confirmed_native_argument_failures": len(verified["native_argument_proof"]),
            "retry": False, "new_store_or_corpus_body_decoded": False,
            "new_model_calls": 0, "atomic_execution_changed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.manifest, args.manifest_sha256,
                                   args.run_id, args.historical_sidecar)))
