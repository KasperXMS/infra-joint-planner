"""Append-only versioned derived proofs in the unchanged five-group authority.

Historical source maps and proof reviewers remain exact. Only the derived map
accepts an explicitly versioned additional reviewer, with no new proof group,
execution change, wildcard waiver, retry authority or private guard relaxation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import large_scale_resident_phase2_derived_companion_review_v1 as derived
import large_scale_resident_phase2_native_renewed_environment_v1 as previous

from infra_joint.experiments.attempt_ledger import Attempt

environment = previous.environment
field = previous.field
cadence = previous.cadence
frozen = previous.frozen
read = previous.read
copied = previous.copied
EnvironmentLedger = previous.EnvironmentLedger
inventory = previous.inventory
current_inventory = previous.current_inventory
extension_delta = previous.extension_delta
historical_control = previous.historical_control
GROUPS = previous.GROUPS
Inventory = dict[str, dict[str, str]]
MODULE = "large_scale_resident_phase2_derived_companion_environment_v1"
PREFIX = "phase2-derived-companion-environment-cadence-freeze-"
VERSION = "resident-phase2-five-group-versioned-derived-companion-renewal-v1"
BASE_VERSION = previous.BASE_VERSION
PARENT_NAME = "phase2-native-renewed-environment-cadence-freeze-001.json"
PARENT_SHA = "16cc82e2be37a24a20cdbdad28e340ed2c84a04443154895391d42bd7700903a"
_raw_attempts = vars(previous)["_raw_attempts"]
_directories = vars(previous)["_directories"]


def sources() -> dict[str, str]:
    return {**previous.sources(), **derived.sources(),
            Path(__file__).name: cadence.digest(Path(__file__))}


def _review_pairs(groups: Inventory, raw: dict[str, Attempt]
                  ) -> tuple[tuple[Attempt, Attempt], ...]:
    ancestor = previous.previous
    reviewers = ((field.core.verify_sidecar, field.core.legacy.REVIEW_REASON),
                 (field.review.verify_sidecar, field.review.field.REASON),
                 (derived.verify_sidecar, derived.REASON),
                 (ancestor.filtered.filtered.verify_sidecar, ancestor.filtered.filtered.REASON),
                 (ancestor.native.verify_sidecar, ancestor.native.REASON))
    pairs: list[tuple[Attempt, Attempt]] = []
    for key, directory, (verify, reason) in zip(GROUPS, _directories(), reviewers, strict=True):
        for name, sha in sorted(groups[key].items()):
            path = frozen.ROOT / directory / name
            if cadence.digest(path) != sha:
                raise RuntimeError("historical sidecar drift")
            attempt = raw[name[:-5]]
            if attempt.disposition != "confounder":
                raise RuntimeError("review authority requires its exact raw confounder")
            proof = verify(path, attempt)
            pairs.append((attempt, replace(attempt, disposition="valid", reason=reason,
                                           receipt_sha256=proof["reviewed_admission_sha256"])))
    return tuple(pairs)


def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
               require_dispatch_ready: bool) -> EnvironmentLedger:
    return cast(EnvironmentLedger, copied(previous.membership, {
        "_review_pairs": _review_pairs})(value, cells, sidecar,
                                         require_dispatch_ready=require_dispatch_ready))


def full_control(control: Path, sidecar: Path,
                 derived_sidecars: dict[str, str] | None = None,
                 filtered_sidecars: dict[str, str] | None = None,
                 native_argument_sidecars: dict[str, str] | None = None
                 ) -> tuple[dict[str, Any], tuple[Any, ...]]:
    return cast(tuple[dict[str, Any], tuple[Any, ...]], copied(previous.full_control, {
        "membership": membership})(control, sidecar, derived_sidecars,
                                     filtered_sidecars, native_argument_sidecars))


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    # Admission reason/receipt schema is unchanged; the frozen collector keeps
    # every historical row intact. Add provenance only for explicitly new proofs.
    result = previous.collect(value, ledger)
    count = 0
    for row in result["rows"]:
        for record in row["attempts"]:
            if record["reason"] != derived.REASON:
                continue
            path = frozen.ROOT / derived.DIRECTORY / (record["run_id"] + ".json")
            proof = read(path)
            if proof.get("version") == derived.OLD_VERSION:
                continue
            if (proof.get("version") != derived.VERSION
                    or cadence.digest(path) != value["derived_field_sidecars"].get(path.name)
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                raise RuntimeError("projection derived companion version/receipt drift")
            record.update(derived_companion_review_version=derived.VERSION,
                          read_artifact_limit_proof_count=len(proof["read_artifact_limit_proof"]),
                          output_collision_proof_count=len(proof["output_collision_proof"]))
            count += 1
    result.update(derived_companion_reviewed_attempts=count,
                  derived_companion_proof_source_sha256=derived.sources())
    return result


def _initial_parent(path: Path, sha: str) -> None:
    if not path.name.startswith(PREFIX) and (path.name != PARENT_NAME or sha != PARENT_SHA):
        raise RuntimeError("initial derived companion requires pinned renewed001 authority")


def history_fence(path: Path, sha: str, successor: Inventory,
                  seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    return cast(dict[str, Any], copied(previous.history_fence, {
        "previous": previous, "VERSION": VERSION, "PREFIX": PREFIX,
        "sources": sources, "history_fence": history_fence,
        "_initial_parent": _initial_parent, "_review_pairs": _review_pairs})(
            path, sha, successor, seen))


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    copied(previous.fence, {"VERSION": VERSION, "PREFIX": PREFIX,
                           "history_fence": history_fence})(path, sha, value)


def _checked_candidate(control: Path, candidate: dict[str, Any], sidecar: Path,
                       current: Inventory) -> tuple[dict[str, Any], tuple[Any, ...]]:
    return cast(tuple[dict[str, Any], tuple[Any, ...]], copied(
        vars(previous)["_checked_candidate"], {"full_control": full_control})(
            control, candidate, sidecar, current))


def freeze(old_path: Path, old_sha: str, control: Path, receipt: Path,
           output: Path) -> dict[str, Any]:
    return cast(dict[str, Any], copied(previous.freeze, {
        "PREFIX": PREFIX, "VERSION": VERSION, "_initial_parent": _initial_parent,
        "history_fence": history_fence, "membership": membership,
        "full_control": full_control, "collect": collect, "sources": sources,
        "_checked_candidate": _checked_candidate})(old_path, old_sha, control, receipt, output))


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
    parser.add_argument("--control", type=Path)
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    if args.freeze:
        if any(a is None for a in (args.parent_manifest, args.parent_manifest_sha256,
                                  args.control, args.ledger)):
            parser.error("freeze requires pinned parent and control/ledger")
        freeze(args.parent_manifest, args.parent_manifest_sha256,
               args.control, args.ledger, args.manifest)
        print(json.dumps({"manifest": str(args.manifest), "sha256": cadence.digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest digest")
        run(args.manifest, args.manifest_sha256)
