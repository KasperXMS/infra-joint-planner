"""Append-only renewal of the existing five source-bound review groups.

Any nonempty independently reproduced addition may renew the authority. All
historical sources, admissions, proof pairs, execution and cadence stay pinned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_native_environment_v1 as previous
import large_scale_resident_phase2_native_field_review_v1 as review

from infra_joint.control.provenance import provenance_sha256
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
membership = previous.membership
full_control = previous.full_control
collect = previous.collect
GROUPS = previous.GROUPS
Inventory = dict[str, dict[str, str]]
MODULE = "large_scale_resident_phase2_native_renewed_environment_v1"
PREFIX = "phase2-native-renewed-environment-cadence-freeze-"
VERSION = "resident-phase2-native-five-group-source-bound-renewal-v1"
BASE_VERSION = previous.BASE_VERSION
PARENT_NAME = "phase2-native-environment-cadence-freeze-001.json"
PARENT_SHA = "b3c48708b7595812dcac624dbfc82942bc6b7bf5cc17bcf581aa674e506ff96d"
_raw_attempts = cast(Callable[[], dict[str, Attempt]], vars(previous)["_raw_attempts"])
_review_pairs = cast(Callable[[Inventory, dict[str, Attempt]],
                             tuple[tuple[Attempt, Attempt], ...]], vars(previous)["_review_pairs"])


def sources() -> dict[str, str]:
    return {**previous.sources(), **review.sources(),
            Path(__file__).name: cadence.digest(Path(__file__))}


def _directories() -> tuple[str, ...]:
    return (field.core.DIRECTORY, field.review.DIRECTORY,
            previous.filtered.renewed.previous.derived.DIRECTORY,
            previous.filtered.filtered.DIRECTORY, previous.native.DIRECTORY)


def _initial_parent(path: Path, sha: str) -> None:
    if not path.name.startswith(PREFIX) and (path.name != PARENT_NAME or sha != PARENT_SHA):
        raise RuntimeError("initial five-group renewal requires pinned native001 authority")


def history_fence(path: Path, sha: str, successor: Inventory,
                  seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.parent != frozen.ROOT or resolved in seen or cadence.digest(path) != sha:
        raise RuntimeError("owned pinned acyclic historical manifest required")
    value = read(path)
    if value.get("extension_version") != VERSION:
        _initial_parent(path, sha)
        return previous.history_fence(path, sha, successor, seen)
    if any(k not in value for k in GROUPS):
        raise RuntimeError("all five exact review groups required")
    snapshot = inventory(value)
    extension_delta(snapshot, successor)
    if (not path.name.startswith(PREFIX) or value["version"] != BASE_VERSION
            or value["interval"] != cadence.INTERVAL or value["source_sha256"] != sources()
            or any(cadence.digest(Path(p)) != h for p, h in value["bound_metadata_files"].items())
            or provenance_sha256(frozen.reference()) != value["reference_sha256"]
            or frozen.verify_freeze() != value["parent"]["execution_freeze_sha256"]
            or value["maximum_cell71_replacements"] != 1
            or value["atomic_execution_changed"] is not False
            or value["private_body_guard_changed"] is not False
            or value["semantic_tuning"] is not False
            or value["new_findings_stop_immediately"] is not True
            or value.get("new_retry_authority") is not False
            or value.get("new_store_or_corpus_body_decoded") is not False):
        raise RuntimeError("five-group historical environment source/config/metadata drift")
    for key, directory in zip(GROUPS, _directories(), strict=True):
        if any(cadence.digest(frozen.ROOT / directory / n) != h for n, h in snapshot[key].items()):
            raise RuntimeError("historical review sidecar removed or changed")
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    cadence.digest(journal)
    if hashlib.sha256(journal.read_bytes()[:value["baseline_journal_bytes"]]).hexdigest() != (
            value["baseline_journal_sha256"]):
        raise RuntimeError("historical journal prefix changed")
    historical_control(value)
    parent_path = Path(value["parent_environment_manifest_path"])
    parent_sha = value["parent_environment_manifest_sha256"]
    _initial_parent(parent_path, parent_sha)
    if value["bound_metadata_files"].get(str(parent_path)) != parent_sha:
        raise RuntimeError("historical parent manifest metadata pin missing")
    parent = history_fence(parent_path, parent_sha, snapshot, seen | {resolved})
    if (value["parent"] != parent["parent"] or value["exclusion"] != parent["exclusion"]
            or value["sidecar_path"] != parent["sidecar_path"]
            or value["baseline_run_ids"] != parent["baseline_run_ids"]):
        raise RuntimeError("historical execution/exclusion/stage authority changed")
    delta = extension_delta(inventory(parent), snapshot)
    if value["new_review_sidecars"] != delta or not any(delta.values()):
        raise RuntimeError("five-group renewal requires its exact nonempty additions")
    old_reviews = parent["historical_reviews"]
    if value["historical_reviews"][:len(old_reviews)] != old_reviews:
        raise RuntimeError("historical review ordering or pairs changed")
    actual = {a.run_id: {"raw": asdict(a), "effective": asdict(b)}
              for a, b in _review_pairs(snapshot, _raw_attempts())}
    saved = {r["raw"]["run_id"]: r for r in value["historical_reviews"]}
    if len(saved) != len(value["historical_reviews"]) or saved != actual:
        raise RuntimeError("five-group historical raw/effective review pairs changed")
    return value


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    if (value.get("extension_version") != VERSION or not path.name.startswith(PREFIX)
            or any(k not in value for k in GROUPS)
            or read(path) != value or current_inventory() != inventory(value)):
        raise RuntimeError("current five-group renewal manifest/inventory drift")
    history_fence(path, sha, inventory(value))


def _checked_candidate(control: Path, candidate: dict[str, Any], sidecar: Path,
                       current: Inventory) -> tuple[dict[str, Any], tuple[Any, ...]]:
    """Run the unchanged complete gate against an owned in-memory control."""
    def read_candidate(**_kwargs: Any) -> str:
        return json.dumps(candidate)

    candidate_path = SimpleNamespace(
        name=control.name, is_symlink=control.is_symlink, resolve=control.resolve,
        read_text=read_candidate)
    return full_control(cast(Path, candidate_path), sidecar, current["derived_field_sidecars"],
                        current["filtered_field_sidecars"], current["native_argument_sidecars"])


def freeze(old_path: Path, old_sha: str, control: Path, receipt: Path,
           output: Path) -> dict[str, Any]:
    frozen.require_remote()
    inactive = field.core.previous.gate.evidence.private.assert_inactive
    inactive(frozen.ROOT)
    field.owned(control, field.CONTROL_PREFIX)
    field.owned(receipt, field.LEDGER_PREFIX)
    if (output.resolve().parent != frozen.ROOT or output.is_symlink()
            or not output.name.startswith(PREFIX)):
        raise RuntimeError("owned exclusive five-group renewal manifest required")
    if any(p.exists() for p in (control, receipt, output)):
        raise FileExistsError("five-group renewal creators require all three targets absent")
    _initial_parent(old_path, old_sha)
    environment.require_strata_stopped()
    current = current_inventory()
    old = history_fence(old_path, old_sha, current)
    delta = extension_delta(inventory(old), current)
    if not any(delta.values()):
        raise RuntimeError("source-bound nonempty five-group review additions required")
    old_control = historical_control(old)
    parent_path = Path(old_control["parent_control_path"])
    parent, cells = field.core.previous.checked_control(parent_path)
    if parent != old["parent"]:
        raise RuntimeError("complete original gate/schedule drift")
    candidate = field.control_bindings(parent_path, parent,
                                      Path(old_control["preserved_model_control_path"]),
                                      Path(old_control["preserved_model_ledger_path"]))
    membership_value = {**candidate, **{k: current[k] for k in GROUPS[2:]}}
    if inventory(membership_value) != current:
        raise RuntimeError("current original control inventory mismatch")
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    sidecar = Path(old["sidecar_path"])
    ledger = membership(membership_value, cells, sidecar, require_dispatch_ready=True)
    raw = {a.run_id: a for a in ledger.original_attempts}
    pairs = {a.run_id: {"raw": asdict(raw[a.run_id]), "effective": asdict(a)}
             for a in ledger.attempts if a != raw[a.run_id] and a != ledger.exclusion[1]}
    preserved = {r["raw"]["run_id"]: r for r in old["historical_reviews"]}
    old_names = {name[:-5] for group in inventory(old).values() for name in group}
    if (len(preserved) != len(old["historical_reviews"]) or set(preserved) != old_names
            or any(pairs.get(run) != r for run, r in preserved.items())
            or old["exclusion"] != {"raw": asdict(ledger.exclusion[0]),
                                    "effective": asdict(ledger.exclusion[1])}):
        raise RuntimeError("historical review/exclusion pairs changed")
    additions = [pair for run, pair in pairs.items() if run not in preserved]
    if {r["raw"]["run_id"] + ".json" for r in additions} != {
            name for group in delta.values() for name in group}:
        raise RuntimeError("every new review requires its independently reproduced raw pair")
    saved, checked_cells = _checked_candidate(control, candidate, sidecar, current)
    if saved != parent or checked_cells != cells:
        raise RuntimeError("complete renewed gate/schedule drift")
    references = {old_path, control, receipt, sidecar,
                  *(Path(p) for p in old["bound_metadata_files"]),
                  *(frozen.ROOT / directory / n
                    for k, directory in zip(GROUPS, _directories(), strict=True)
                    for n in current[k])}
    # Audit the fully reproduced projection before creating any new authority.
    projection_value = {**old, **current}
    environment.audit_wire(collect(projection_value, ledger), sidecar)
    history_fence(old_path, old_sha, current)
    if before != journal.read_bytes() or current_inventory() != current:
        raise RuntimeError("five-group journal or review inventory advanced")
    inactive(frozen.ROOT)
    frozen.write_new(control, candidate)
    frozen.write_new(receipt, field.freeze_value(control))
    field.validate(control, receipt)
    saved, checked_cells = full_control(control, sidecar, current["derived_field_sidecars"],
                                       current["filtered_field_sidecars"],
                                       current["native_argument_sidecars"])
    if saved != parent or checked_cells != cells:
        raise RuntimeError("complete renewed gate/schedule drift")
    result = {**old, **current, "control_path": str(control), "ledger_path": str(receipt),
              "extension_version": VERSION, "created_utc": datetime.now(UTC).isoformat(),
              "source_sha256": sources(), "parent_environment_manifest_path": str(old_path),
              "parent_environment_manifest_sha256": old_sha,
              "historical_reviews": [*old["historical_reviews"], *additions],
              "new_review_sidecars": delta, "baseline_journal_bytes": len(before),
              "baseline_journal_sha256": cadence.digest(journal),
              "continuation_baseline_run_ids": [a.run_id for a in ledger.original_attempts],
              "bound_metadata_files": {str(p): cadence.digest(p) for p in sorted(references)},
              "historical_inventories_are_immutable_subsets": True,
              "current_inventory_and_all_raw_findings_are_exact": True,
              "new_store_or_corpus_body_decoded": False, "new_retry_authority": False}
    if before != journal.read_bytes() or current_inventory() != current:
        raise RuntimeError("five-group journal or review inventory advanced")
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
