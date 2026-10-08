"""Create an unchanged initial-field proof under the five-group authority.

Offline only: preserve all original journals, execution, SDK semantics, native
argument reviews and the sole environmental exclusion. No retry or feedback.
"""

from __future__ import annotations

import argparse
import hashlib
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_native_environment_v1 as previous
import large_scale_resident_phase2_renewed_field_review_v1 as original

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt, QueueLease

review = previous.field.review
core = review.core
DIRECTORY = review.DIRECTORY
INITIAL_JOURNAL_SHA = "c94295590114df5bf148e5054fc4544340e4a931f485f433fdeaef8c003f636f"
HISTORICAL_NAME = (
    "large-scale-cost-guidance-resident-v1-phase1-multihop_rag-2-"
    "2d3129ed85c03f62-p1-fast-B0-attempt1.json")
HISTORICAL_SHA = "0beb9d71b6c71371f683bcc2e7e6680319cb3bf0f8641f65ed7544e82a2e9735"


def sources() -> dict[str, str]:
    return {**previous.sources(), **review.sources(),
            **{Path(p).name: previous.cadence.digest(Path(p))
               for p in (__file__, original.__file__)}}


def pending_ledger(value: dict[str, Any], cells: tuple[Any, ...], journal: Path,
                   run_id: str) -> tuple[previous.EnvironmentLedger, Attempt]:
    return original.pending_ledger(value, cells, journal, run_id)


def _preflight(value: dict[str, Any], expected: dict[str, dict[str, str]],
               path: Path, target: Attempt, candidate: dict[str, Any],
               schedule: tuple[Any, ...]) -> None:
    """Reproduce the complete original gate with one privately bound candidate.

    The candidate digest identifies an unwritten proof only. All historical
    receipts and files retain their real hashes and unchanged reviewers.
    """
    candidate_sha = provenance_sha256(candidate)

    def digest(file: Path) -> str:
        if file == path and not file.exists():
            return candidate_sha
        return previous.cadence.digest(file)

    def verify(file: Path, attempt: Attempt) -> dict[str, Any]:
        if file == path and not file.exists() and attempt == target:
            return candidate
        return review.verify_sidecar(file, attempt)

    reviewer = SimpleNamespace(**{**vars(review), "verify_sidecar": verify})
    field = SimpleNamespace(**{**vars(previous.field), "review": reviewer})
    cadence = SimpleNamespace(**{**vars(previous.cadence), "digest": digest})
    pair_function = cast(Callable[[dict[str, dict[str, str]], dict[str, Attempt]],
                                  tuple[tuple[Attempt, Attempt], ...]],
                         vars(previous)["_review_pairs"])
    pairs = previous.copied(pair_function, {"field": field, "cadence": cadence})
    membership = previous.copied(previous.membership,
                                 {"_review_pairs": pairs, "cadence": cadence})
    groups = {**expected, "initial_field_sidecars": {
        **expected["initial_field_sidecars"], path.name: candidate_sha}}

    def checked(control: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
                require_dispatch_ready: bool) -> previous.EnvironmentLedger:
        ledger: previous.EnvironmentLedger = membership(
            {**control, **groups}, cells, sidecar,
            require_dispatch_ready=require_dispatch_ready)
        raw = {a.run_id: a for a in ledger.original_attempts}
        effective = {a.run_id: a for a in ledger.attempts}
        for pair in value["historical_reviews"]:
            old, reviewed = Attempt(**pair["raw"]), Attempt(**pair["effective"])
            if raw.get(old.run_id) != old or effective.get(old.run_id) != reviewed:
                raise RuntimeError("historical raw/effective initial-field preflight pair changed")
        if ledger.exclusion != (Attempt(**value["exclusion"]["raw"]),
                                Attempt(**value["exclusion"]["effective"])):
            raise RuntimeError("original environmental exclusion changed")
        return ledger

    full_control = previous.copied(previous.full_control, {"membership": checked})
    saved, cells = full_control(Path(value["control_path"]), Path(value["sidecar_path"]),
                                groups["derived_field_sidecars"],
                                groups["filtered_field_sidecars"],
                                groups["native_argument_sidecars"])
    if saved != value["parent"] or cells != schedule:
        raise RuntimeError("complete original parent/schedule changed during field proof")


def create_review(manifest: Path, manifest_sha256: str, run_id: str,
                  historical_path: Path) -> dict[str, Any]:
    environment = import_module("large_scale_resident_phase2_native_renewed_environment_v1")
    previous.frozen.require_remote()
    root = previous.frozen.ROOT
    inactive = core.previous.gate.evidence.private.assert_inactive
    inactive(root)
    value = previous.read(manifest)
    initial = value.get("extension_version") != environment.VERSION

    def fence() -> None:
        if initial:
            if (manifest.name != environment.PARENT_NAME
                    or manifest_sha256 != environment.PARENT_SHA):
                raise RuntimeError("initial field renewal requires pinned native001 authority")
            previous.fence(manifest, manifest_sha256, value)
        else:
            environment.fence(manifest, manifest_sha256, value)

    fence()
    previous.environment.require_strata_stopped()
    directory = root / DIRECTORY
    path = directory / (run_id + ".json")
    if (Path(run_id).name != run_id or not run_id.startswith(root.name + "-phase2-")
            or directory.is_symlink() or path.exists() or path.is_symlink()):
        raise RuntimeError("owned exclusive original initial-field sidecar required")
    journal = root / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    if initial and hashlib.sha256(before).hexdigest() != INITIAL_JOURNAL_SHA:
        raise RuntimeError("initial field renewal requires the exact current journal")
    if initial and (historical_path.name != HISTORICAL_NAME
                    or previous.cadence.digest(historical_path) != HISTORICAL_SHA):
        raise RuntimeError("initial field renewal requires the exact historical shape proof")
    expected = environment.inventory(value)
    with QueueLease(root / "queue-lease.json"):
        parent_path = Path(previous.read(Path(value["control_path"]))["parent_control_path"])
        schedule = core.previous.cells_from_gate(previous.read(Path(value["parent"]["gate_path"])))
        ledger, target = pending_ledger(value, schedule, journal, run_id)
        candidate = review.proof(root, target, parent_path, historical_path)
        _preflight(value, expected, path, target, candidate, schedule)
        ledger.check_disk()
        fence()
        previous.environment.require_strata_stopped()
        inactive(root, allow_current_audit_lease=True)
        if journal.read_bytes() != before or environment.current_inventory() != expected:
            raise RuntimeError("review cannot change the original journal or inventory")
        directory.mkdir(exist_ok=True)
        previous.frozen.write_new(path, candidate)
        review.verify_sidecar(path, target)
        ledger.check_disk()
        if journal.read_bytes() != before:
            raise RuntimeError("review cannot change the original journal")
        delta = environment.extension_delta(expected, environment.current_inventory())
        exact_delta: dict[str, dict[str, str]] = {key: {} for key in environment.GROUPS}
        exact_delta["initial_field_sidecars"] = {path.name: previous.cadence.digest(path)}
        if delta != exact_delta:
            raise RuntimeError("creator may add only the exact target initial-field sidecar")
    inactive(root)
    return {"sidecar_path": str(path), "sha256": previous.cadence.digest(path),
            "creator_source_sha256": previous.cadence.digest(Path(__file__)),
            "parent_manifest_sha256": manifest_sha256,
            "original_journal_sha256": hashlib.sha256(before).hexdigest(),
            "confirmed_field_failures": len(candidate["field_misuse_proof"]),
            "actual_manager_requests": len(candidate["actual_manager_schema_wire_proof"]),
            "retry": False, "new_store_or_corpus_body_decoded": False,
            "new_model_calls": 0, "atomic_execution_changed": False}


if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--historical-sidecar", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create_review(args.manifest, args.manifest_sha256,
                                   args.run_id, args.historical_sidecar)))
