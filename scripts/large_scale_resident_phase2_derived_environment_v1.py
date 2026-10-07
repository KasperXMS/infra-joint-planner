"""Source-bound derived-field continuation outside immutable execution sources.

Renew every original proof and preserve the single authorized cell71 exclusion.
Only exact verified sidecars affect the historical view; new findings still stop
the unchanged environment runner immediately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import large_scale_resident_phase2_derived_field_review_v1 as derived
import large_scale_resident_phase2_environment_v1 as environment

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

field = environment.field
cadence = environment.cadence
frozen = environment.frozen
EnvironmentLedger = environment.EnvironmentLedger
MODULE = "large_scale_resident_phase2_derived_environment_v1"
PREFIX = "phase2-derived-environment-cadence-freeze-"
VERSION = "resident-phase2-source-bound-derived-environment-continuation-v1"
read = environment.read


def copied(original: Any, namespace: dict[str, Any]) -> Any:
    """Bind a private namespace without modifying any historical module."""
    bound = FunctionType(original.__code__, {**original.__globals__, **namespace},
                         original.__name__, original.__defaults__, original.__closure__)
    bound.__kwdefaults__ = dict(original.__kwdefaults__ or {})
    return bound


def sources() -> dict[str, str]:
    return {**environment.sources(), **derived.sources(),
            Path(__file__).name: cadence.digest(Path(__file__))}


def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
               require_dispatch_ready: bool) -> EnvironmentLedger:
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    cadence.digest(journal)
    rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    reserved = {r["run_id"]: r for r in rows if r["event"] == "reserved"}
    raw: dict[str, Attempt] = {}
    for row in rows:
        if row["event"] == "settled":
            r = reserved[row["run_id"]]
            raw[row["run_id"]] = Attempt(r["cell_id"], r["run_id"], r["attempt_index"],
                                          r["execution_sha256"], row["disposition"],
                                          row["reason"], row["receipt_sha256"])
    groups = (value["model_json_sidecars"], value["initial_field_sidecars"],
              value["derived_field_sidecars"], {environment.RUN + ".json": None})
    names: set[str] = set()
    for group in groups:
        if names & set(group):
            raise RuntimeError("every raw finding needs its disjoint exact proof")
        names.update(group)
    if names != {a.run_id + ".json" for a in raw.values() if a.disposition == "confounder"}:
        raise RuntimeError("every raw finding needs its disjoint exact proof")
    reviewers = ((field.core.DIRECTORY, field.core.verify_sidecar,
                  field.core.legacy.REVIEW_REASON),
                 (field.review.DIRECTORY, field.review.verify_sidecar, field.review.field.REASON),
                 (derived.DIRECTORY, derived.verify_sidecar, derived.REASON))
    pairs: list[tuple[Attempt, Attempt]] = []
    for group, (directory, verify, reason) in zip(groups[:3], reviewers, strict=True):
        for name in sorted(group):
            path = frozen.ROOT / directory / name
            if cadence.digest(path) != group[name]:
                raise RuntimeError("historical sidecar drift")
            attempt = raw[name[:-5]]
            proof = verify(path, attempt)
            pairs.append((attempt, replace(attempt, disposition="valid", reason=reason,
                                           receipt_sha256=proof["reviewed_admission_sha256"])))
    environment.verify_exclusion(sidecar, raw[environment.RUN])
    exclusion: tuple[Attempt, Attempt] = (raw[environment.RUN], replace(raw[environment.RUN],
                 disposition="operational_excluded", reason=environment.REASON,
                 receipt_sha256=cadence.digest(sidecar)))
    ledger = EnvironmentLedger(journal, tuple(c.cell_id for c in cells),
                               value["phase2_schedule_sha256"], tuple(pairs), exclusion)
    if require_dispatch_ready:
        environment.dispatch_ready(ledger)
    return ledger


def full_control(control: Path, sidecar: Path,
                 derived_sidecars: dict[str, str] | None = None
                 ) -> tuple[dict[str, Any], tuple[Any, ...]]:
    expected = (field.sidecars(derived.DIRECTORY) if derived_sidecars is None
                else derived_sidecars)

    def checked(value: dict[str, Any], cells: tuple[Any, ...], *,
                require_dispatch_ready: bool) -> EnvironmentLedger:
        return membership({**value, "derived_field_sidecars": expected}, cells, sidecar,
                          require_dispatch_ready=require_dispatch_ready)

    result: tuple[dict[str, Any], tuple[Any, ...]] = copied(
        field.checked_control, {"checked_membership": checked})(control)
    return result


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
        if attempt.reason == derived.REASON:
            return derived.effective_admission(root, attempt)
        return field.review.effective_admission(root, attempt)

    review = SimpleNamespace(**{**vars(field.review), "effective_admission": effective_admission})
    proxy = SimpleNamespace(**{**vars(field), "review": review})
    result: dict[str, Any] = copied(environment.collect, {"field": proxy})(value, ledger)
    confirmed = 0
    for row in result["rows"]:
        for record in row["attempts"]:
            if record["reason"] != derived.REASON:
                continue
            path = frozen.ROOT / derived.DIRECTORY / (record["run_id"] + ".json")
            proof = read(path)
            if (cadence.digest(path) != value["derived_field_sidecars"].get(path.name)
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                raise RuntimeError("projection derived proof/receipt drift")
            count = len(proof["derived_field_proof"])
            record["confirmed_absent_record_field_failures"] = count
            record["derived_record_field_proof_count"] = count
            confirmed += count
    result.update(derived_field_reviewed_attempts=sum(
        a.reason == derived.REASON and a.disposition == "valid" for a in ledger.attempts),
        confirmed_derived_absent_record_field_failures=confirmed,
        derived_field_sidecars=value["derived_field_sidecars"],
        derived_field_proof_source_sha256=derived.sources(),
        original_admissions_preserved=True, new_store_or_corpus_body_decoded=False,
        new_model_calls=0, atomic_execution_changed=False)
    return result


def parent_fence(path: Path, sha: str) -> dict[str, Any]:
    if (path.resolve().parent != frozen.ROOT
            or not path.name.startswith(environment.PREFIX)):
        raise RuntimeError("owned pinned original environment manifest required")
    value = read(path)
    if value["version"] != "resident-phase2-user-authorized-environment-continuation-v1":
        raise RuntimeError("original environmental authority required")
    environment.fence(path, sha, value)
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    cadence.digest(journal)
    if hashlib.sha256(journal.read_bytes()[:value["baseline_journal_bytes"]]).hexdigest() != value[
            "baseline_journal_sha256"]:
        raise RuntimeError("original environment journal prefix changed")
    return value


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    if (value.get("extension_version") != VERSION or cadence.digest(path) != sha
            or sources() != value["source_sha256"]
            or any(cadence.digest(Path(p)) != h for p, h in value["bound_metadata_files"].items())
            or field.sidecars(field.core.DIRECTORY) != value["model_json_sidecars"]
            or field.sidecars(field.review.DIRECTORY) != value["initial_field_sidecars"]
            or field.sidecars(derived.DIRECTORY) != value["derived_field_sidecars"]
            or frozen.verify_freeze() != value["parent"]["execution_freeze_sha256"]
            or provenance_sha256(frozen.reference()) != value["reference_sha256"]):
        raise RuntimeError("derived environment immutable source/evidence drift")
    parent_fence(Path(value["parent_environment_manifest_path"]),
                 value["parent_environment_manifest_sha256"])


def freeze(old_manifest: Path, old_sha: str, output: Path) -> dict[str, Any]:
    frozen.require_remote()
    inactive = field.core.previous.gate.evidence.private.assert_inactive
    inactive(frozen.ROOT)
    if (output.resolve().parent != frozen.ROOT or output.is_symlink()
            or not output.name.startswith(PREFIX)):
        raise RuntimeError("owned exclusive derived environment manifest required")
    if output.exists():
        raise FileExistsError("derived environment manifest creator must not repeat")
    environment.require_strata_stopped()
    old = parent_fence(old_manifest, old_sha)
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    control, receipt, sidecar = (Path(old[key]) for key in
                                 ("control_path", "ledger_path", "sidecar_path"))
    field.validate(control, receipt)
    derived_sidecars = field.sidecars(derived.DIRECTORY)
    if not derived_sidecars:
        raise RuntimeError("actual source-bound derived field sidecars required")
    parent, cells = full_control(control, sidecar, derived_sidecars)
    if parent != old["parent"]:
        raise RuntimeError("complete original gate/schedule drift")
    membership_value = {**read(control), "derived_field_sidecars": derived_sidecars}
    ledger = membership(membership_value, cells, sidecar, require_dispatch_ready=True)
    raw = {a.run_id: a for a in ledger.original_attempts}
    pairs = [{"raw": asdict(raw[a.run_id]), "effective": asdict(a)} for a in ledger.attempts
             if a != raw[a.run_id] and a != ledger.exclusion[1]]
    old_pairs = {r["raw"]["run_id"]: r for r in pairs
                 if r["raw"]["run_id"] + ".json" not in derived_sidecars}
    preserved = {r["raw"]["run_id"]: r for r in old["historical_reviews"]}
    if (len(preserved) != len(old["historical_reviews"]) or old_pairs != preserved
            or old["exclusion"] != {
            "raw": asdict(ledger.exclusion[0]), "effective": asdict(ledger.exclusion[1])}):
        raise RuntimeError("original historical review/exclusion pairs changed")
    pairs = [*old["historical_reviews"], *(r for r in pairs
             if r["raw"]["run_id"] + ".json" in derived_sidecars)]
    references = {old_manifest, *(Path(p) for p in old["bound_metadata_files"]),
                  *(frozen.ROOT / derived.DIRECTORY / name for name in derived_sidecars)}
    result = {**old, "extension_version": VERSION,
              "created_utc": datetime.now(UTC).isoformat(), "source_sha256": sources(),
              "parent_environment_manifest_path": str(old_manifest),
              "parent_environment_manifest_sha256": old_sha,
              "derived_field_sidecars": derived_sidecars, "historical_reviews": pairs,
              "baseline_journal_bytes": len(before),
              "baseline_journal_sha256": cadence.digest(journal),
              "continuation_baseline_run_ids": [a.run_id for a in ledger.original_attempts],
              "bound_metadata_files": {str(p): cadence.digest(p) for p in sorted(references)},
              "derived_field_proofs_renewed_at_full_checkpoints": True,
              "new_store_or_corpus_body_decoded": False, "new_retry_authority": False}
    projection = collect(result, ledger)
    environment.audit_wire(projection, sidecar)
    parent_fence(old_manifest, old_sha)
    if before != journal.read_bytes():
        raise RuntimeError("derived environment freeze journal advanced")
    inactive(frozen.ROOT)
    frozen.write_new(output, result)
    return result


def run(path: Path, expected_sha: str) -> None:
    copied(environment.run, {"MODULE": MODULE, "PREFIX": PREFIX, "sources": sources,
                            "membership": membership, "full_control": full_control,
                            "collect": collect, "fence": fence})(path, expected_sha)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--parent-manifest", type=Path)
    parser.add_argument("--parent-manifest-sha256")
    args = parser.parse_args()
    if args.freeze:
        if args.parent_manifest is None or args.parent_manifest_sha256 is None:
            parser.error("freeze requires externally pinned original environment manifest")
        freeze(args.parent_manifest, args.parent_manifest_sha256, args.manifest)
        print(json.dumps({"manifest": str(args.manifest), "sha256": cadence.digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest digest")
        run(args.manifest, args.manifest_sha256)
