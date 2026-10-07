"""Append-only review renewal with immutable historical inventory snapshots.

Historical manifests retain their original sidecar populations and source pins.
The current authority admits only an exact, fully reproduced review population.
Execution, cadence, original admissions, and cell71's replacement cap are reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import large_scale_resident_phase2_derived_environment_v1 as previous

from infra_joint.control.provenance import provenance_sha256

environment = previous.environment
field = previous.field
cadence = previous.cadence
frozen = previous.frozen
read = previous.read
EnvironmentLedger = previous.EnvironmentLedger
membership = previous.membership
full_control = previous.full_control
copied = previous.copied
MODULE = "large_scale_resident_phase2_renewed_environment_v1"
PREFIX = "phase2-renewed-environment-cadence-freeze-"
VERSION = "resident-phase2-append-only-environment-review-renewal-v1"
BASE_VERSION = "resident-phase2-user-authorized-environment-continuation-v1"
GROUPS = ("model_json_sidecars", "initial_field_sidecars", "derived_field_sidecars")
Inventory = dict[str, dict[str, str]]


def sources() -> dict[str, str]:
    return {**previous.sources(), Path(__file__).name: cadence.digest(Path(__file__))}


def inventory(value: dict[str, Any]) -> Inventory:
    result: Inventory = {}
    names = {environment.RUN + ".json"}
    for key in GROUPS:
        raw_group = value.get(key, {}) if key == "derived_field_sidecars" else value[key]
        if not isinstance(raw_group, dict):
            raise RuntimeError("owned disjoint exact review inventories required")
        group = cast(dict[Any, Any], raw_group)
        if (any(
                not isinstance(name, str) or Path(name).name != name
                or not name.endswith(".json") or not isinstance(sha, str)
                or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha)
                for name, sha in group.items()) or names & set(group)):
            raise RuntimeError("owned disjoint exact review inventories required")
        result[key] = cast(dict[str, str], dict(group))
        names.update(group)
    return result


def current_inventory() -> Inventory:
    return dict(zip(GROUPS, (field.sidecars(field.core.DIRECTORY),
                            field.sidecars(field.review.DIRECTORY),
                            field.sidecars(previous.derived.DIRECTORY)), strict=True))


def extension_delta(old: Inventory, new: Inventory) -> Inventory:
    if any(new[key].get(name) != sha for key in GROUPS for name, sha in old[key].items()):
        raise RuntimeError("historical review sidecar removed or changed")
    return {key: {name: sha for name, sha in new[key].items() if name not in old[key]}
            for key in GROUPS}


def historical_control(value: dict[str, Any]) -> dict[str, Any]:
    """Reproduce original control bindings at its pinned historical population."""
    control, receipt = Path(value["control_path"]), Path(value["ledger_path"])
    field.owned(control, field.CONTROL_PREFIX)
    field.validate(control, receipt)
    saved = read(control)
    parent_path = Path(saved["parent_control_path"])
    parent = read(parent_path)
    if parent != value["parent"]:
        raise RuntimeError("historical original gate/control changed")
    snapshot = inventory(value)

    def sidecars(directory: str) -> dict[str, str]:
        if directory == field.core.DIRECTORY:
            return dict(snapshot["model_json_sidecars"])
        if directory == field.review.DIRECTORY:
            return dict(snapshot["initial_field_sidecars"])
        raise RuntimeError("unexpected historical sidecar directory")

    expected = copied(field.control_bindings, {"sidecars": sidecars})(
        parent_path, parent, Path(saved["preserved_model_control_path"]),
        Path(saved["preserved_model_ledger_path"]))
    if saved != expected:
        raise RuntimeError("historical original control/source/inventory drift")
    return saved


def history_fence(path: Path, sha: str, successor: Inventory,
                  seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    """Check each ancestor's exact bytes and subset bounded by its successor."""
    resolved = path.resolve()
    if resolved.parent != frozen.ROOT or resolved in seen or cadence.digest(path) != sha:
        raise RuntimeError("owned pinned acyclic historical manifest required")
    value = read(path)
    extension = value.get("extension_version")
    if extension is None:
        prefix, bound_sources = environment.PREFIX, environment.sources()
    elif extension == previous.VERSION:
        prefix, bound_sources = previous.PREFIX, previous.sources()
    elif extension == VERSION:
        prefix, bound_sources = PREFIX, sources()
    else:
        raise RuntimeError("unknown historical environment authority")
    snapshot = inventory(value)
    extension_delta(snapshot, successor)
    if (not path.name.startswith(prefix) or value["version"] != BASE_VERSION
            or value["interval"] != cadence.INTERVAL
            or value["source_sha256"] != bound_sources
            or any(cadence.digest(Path(p)) != h for p, h in value[
                "bound_metadata_files"].items())
            or provenance_sha256(frozen.reference()) != value["reference_sha256"]
            or frozen.verify_freeze() != value["parent"]["execution_freeze_sha256"]
            or value["maximum_cell71_replacements"] != 1
            or value["atomic_execution_changed"] is not False
            or value["private_body_guard_changed"] is not False
            or value["semantic_tuning"] is not False
            or value["new_findings_stop_immediately"] is not True):
        raise RuntimeError("historical environment source/config/metadata drift")
    directories = (field.core.DIRECTORY, field.review.DIRECTORY, previous.derived.DIRECTORY)
    for key, directory in zip(GROUPS, directories, strict=True):
        if any(cadence.digest(frozen.ROOT / directory / name) != h
               for name, h in snapshot[key].items()):
            raise RuntimeError("historical review sidecar removed or changed")
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    cadence.digest(journal)
    if hashlib.sha256(journal.read_bytes()[:value["baseline_journal_bytes"]]).hexdigest() != value[
            "baseline_journal_sha256"]:
        raise RuntimeError("historical journal prefix changed")
    historical_control(value)
    if extension is not None:
        parent_path = Path(value["parent_environment_manifest_path"])
        parent_sha = value["parent_environment_manifest_sha256"]
        if value["bound_metadata_files"].get(str(parent_path)) != parent_sha:
            raise RuntimeError("historical parent manifest metadata pin missing")
        parent = history_fence(parent_path, parent_sha, snapshot, seen | {resolved})
        if (value["parent"] != parent["parent"] or value["exclusion"] != parent["exclusion"]
                or value["sidecar_path"] != parent["sidecar_path"]
                or value["baseline_run_ids"] != parent["baseline_run_ids"]):
            raise RuntimeError("historical execution/exclusion/stage authority changed")
        if extension == VERSION:
            delta = extension_delta(inventory(parent), snapshot)
            if value["new_review_sidecars"] != delta or not any(delta.values()):
                raise RuntimeError("renewal must bind its exact nonempty review additions")
            old_reviews = parent["historical_reviews"]
            if value["historical_reviews"][:len(old_reviews)] != old_reviews:
                raise RuntimeError("renewal cannot change historical review ordering or pairs")
    return value


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    result = previous.collect(value, ledger)
    confirmed = 0
    for row in result["rows"]:
        for record in row["attempts"]:
            if record["reason"] != field.review.field.REASON:
                continue
            path = frozen.ROOT / field.review.DIRECTORY / (record["run_id"] + ".json")
            proof = read(path)
            if (cadence.digest(path) != value["initial_field_sidecars"].get(path.name)
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                raise RuntimeError("projection initial-field proof/receipt drift")
            count = len(proof["field_misuse_proof"])
            record["confirmed_absent_record_field_failures"] = count
            record["initial_record_field_proof_count"] = count
            confirmed += count
    result["confirmed_initial_absent_record_field_failures"] = confirmed
    return result


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    if (value.get("extension_version") != VERSION or not path.name.startswith(PREFIX)
            or read(path) != value or current_inventory() != inventory(value)):
        raise RuntimeError("current renewal manifest/inventory drift")
    history_fence(path, sha, inventory(value))


def freeze(old_path: Path, old_sha: str, control: Path, receipt: Path,
           output: Path) -> dict[str, Any]:
    frozen.require_remote()
    inactive = field.core.previous.gate.evidence.private.assert_inactive
    inactive(frozen.ROOT)
    field.owned(control, field.CONTROL_PREFIX)
    field.owned(receipt, field.LEDGER_PREFIX)
    if (output.resolve().parent != frozen.ROOT or output.is_symlink()
            or not output.name.startswith(PREFIX)):
        raise RuntimeError("owned exclusive renewal manifest required")
    if output.exists():
        raise FileExistsError("renewal manifest creator must not repeat")
    if control.exists() != receipt.exists():
        raise RuntimeError("renewal control and receipt must both exist or both be new")
    environment.require_strata_stopped()
    current = current_inventory()
    old = history_fence(old_path, old_sha, current)
    delta = extension_delta(inventory(old), current)
    if not any(delta.values()):
        raise RuntimeError("source-bound new review sidecars required for renewal")
    old_control = historical_control(old)
    parent_path = Path(old_control["parent_control_path"])
    parent, cells = field.core.previous.checked_control(parent_path)
    if parent != old["parent"]:
        raise RuntimeError("complete original gate/schedule drift")
    candidate = field.control_bindings(parent_path, parent,
                                      Path(old_control["preserved_model_control_path"]),
                                      Path(old_control["preserved_model_ledger_path"]))
    if inventory({**candidate, "derived_field_sidecars": current["derived_field_sidecars"]}) != (
            current):
        raise RuntimeError("current original control inventory mismatch")
    if control.exists():
        if read(control) != candidate:
            raise RuntimeError("provided renewal control differs from original bindings")
        field.validate(control, receipt)
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    before = journal.read_bytes()
    sidecar = Path(old["sidecar_path"])
    ledger = membership({**candidate, "derived_field_sidecars": current["derived_field_sidecars"]},
                        cells, sidecar, require_dispatch_ready=True)
    raw = {a.run_id: a for a in ledger.original_attempts}
    pairs = {a.run_id: {"raw": asdict(raw[a.run_id]), "effective": asdict(a)}
             for a in ledger.attempts if a != raw[a.run_id] and a != ledger.exclusion[1]}
    preserved = {r["raw"]["run_id"]: r for r in old["historical_reviews"]}
    old_names = {name[:-5] for group in inventory(old).values() for name in group}
    if (len(preserved) != len(old["historical_reviews"]) or set(preserved) != old_names
            or any(pairs.get(run) != review for run, review in preserved.items())
            or old["exclusion"] != {"raw": asdict(ledger.exclusion[0]),
                                    "effective": asdict(ledger.exclusion[1])}):
        raise RuntimeError("historical review/exclusion pairs changed")
    additions = [pair for run, pair in pairs.items() if run not in preserved]
    if {r["raw"]["run_id"] + ".json" for r in additions} != {
            name for group in delta.values() for name in group}:
        raise RuntimeError("every new review requires its independently reproduced raw pair")
    projection_value = {**old, **current, "control_path": str(control),
                        "ledger_path": str(receipt)}
    if not control.exists():
        if before != journal.read_bytes():
            raise RuntimeError("renewal proof journal advanced")
        inactive(frozen.ROOT)
        frozen.write_new(control, candidate)
        frozen.write_new(receipt, field.freeze_value(control))
    field.validate(control, receipt)
    saved, checked_cells = full_control(control, sidecar, current["derived_field_sidecars"])
    if saved != parent or checked_cells != cells:
        raise RuntimeError("complete renewed gate/schedule drift")
    directories = (field.core.DIRECTORY, field.review.DIRECTORY, previous.derived.DIRECTORY)
    references = {old_path, control, receipt, sidecar,
                  *(Path(p) for p in old["bound_metadata_files"]),
                  *(frozen.ROOT / directory / name
                    for key, directory in zip(GROUPS, directories, strict=True)
                    for name in current[key])}
    result = {**projection_value, "extension_version": VERSION,
              "created_utc": datetime.now(UTC).isoformat(), "source_sha256": sources(),
              "parent_environment_manifest_path": str(old_path),
              "parent_environment_manifest_sha256": old_sha,
              "historical_reviews": [*old["historical_reviews"], *additions],
              "new_review_sidecars": delta, "baseline_journal_bytes": len(before),
              "baseline_journal_sha256": cadence.digest(journal),
              "continuation_baseline_run_ids": [a.run_id for a in ledger.original_attempts],
              "bound_metadata_files": {str(p): cadence.digest(p) for p in sorted(references)},
              "historical_inventories_are_immutable_subsets": True,
              "current_inventory_and_all_raw_findings_are_exact": True,
              "new_store_or_corpus_body_decoded": False, "new_retry_authority": False}
    projection = collect(result, ledger)
    environment.audit_wire(projection, sidecar)
    history_fence(old_path, old_sha, current)
    if before != journal.read_bytes() or current_inventory() != current:
        raise RuntimeError("renewal journal or review inventory advanced")
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
        if any(arg is None for arg in (args.parent_manifest, args.parent_manifest_sha256,
                                      args.control, args.ledger)):
            parser.error("freeze requires pinned parent manifest and renewal control/ledger")
        freeze(args.parent_manifest, args.parent_manifest_sha256,
               args.control, args.ledger, args.manifest)
        print(json.dumps({"manifest": str(args.manifest), "sha256": cadence.digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest digest")
        run(args.manifest, args.manifest_sha256)
