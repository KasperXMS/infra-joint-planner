"""Append-only filtered-provenance authority; all historical v1 sources stay pinned.

The fourth, disjoint proof group is explicit throughout membership, projection,
checkpoint and history fencing. This offline extension never changes execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_filtered_field_review_v1 as filtered
import large_scale_resident_phase2_renewed_environment_v1 as renewed

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

previous = renewed
environment = renewed.environment
field = renewed.field
cadence = renewed.cadence
frozen = renewed.frozen
read = renewed.read
copied = renewed.copied
EnvironmentLedger = renewed.EnvironmentLedger
MODULE = "large_scale_resident_phase2_filtered_environment_v1"
PREFIX = "phase2-filtered-environment-cadence-freeze-"
VERSION = "resident-phase2-source-bound-filtered-environment-continuation-v1"
BASE_VERSION = renewed.BASE_VERSION
GROUPS = (*renewed.GROUPS, "filtered_field_sidecars")
Inventory = dict[str, dict[str, str]]
PARENT_NAME = "phase2-renewed-environment-cadence-freeze-003.json"
PARENT_SHA = "bfa91c544184fbaa473b0b0251ce3fc49931676b064e545b00e91f5a159dcc55"


def sources() -> dict[str, str]:
    return {**renewed.sources(), **filtered.sources(),
            Path(__file__).name: cadence.digest(Path(__file__))}


def inventory(value: dict[str, Any]) -> Inventory:
    result = renewed.inventory(value)
    raw = value.get("filtered_field_sidecars", {})
    if not isinstance(raw, dict):
        raise RuntimeError("owned disjoint exact filtered review inventory required")
    group = cast(dict[Any, Any], raw)
    names = {environment.RUN + ".json", *(n for g in result.values() for n in g)}
    if (any(not isinstance(n, str) or Path(n).name != n or not n.endswith(".json")
            or not isinstance(h, str) or len(h) != 64
            or any(c not in "0123456789abcdef" for c in h) for n, h in group.items())
            or names & set(group)):
        raise RuntimeError("owned disjoint exact filtered review inventory required")
    return {**result, "filtered_field_sidecars": cast(dict[str, str], dict(group))}


def current_inventory() -> Inventory:
    return {**renewed.current_inventory(),
            "filtered_field_sidecars": field.sidecars(filtered.DIRECTORY)}


def extension_delta(old: Inventory, new: Inventory) -> Inventory:
    if set(old) != set(GROUPS) or set(new) != set(GROUPS):
        raise RuntimeError("all four exact review groups required")
    if any(new[k].get(n) != h for k in GROUPS for n, h in old[k].items()):
        raise RuntimeError("historical review sidecar removed or changed")
    return {k: {n: h for n, h in new[k].items() if n not in old[k]} for k in GROUPS}


def historical_control(value: dict[str, Any]) -> dict[str, Any]:
    # The original control covers only its original two groups. Its complete
    # gate is separately combined with all four groups by full_control below.
    result: dict[str, Any] = copied(renewed.historical_control, {"inventory": inventory})(value)
    return result


def _directories() -> tuple[str, ...]:
    return (field.core.DIRECTORY, field.review.DIRECTORY,
            renewed.previous.derived.DIRECTORY, filtered.DIRECTORY)


def history_fence(path: Path, sha: str, successor: Inventory,
                  seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.parent != frozen.ROOT or resolved in seen or cadence.digest(path) != sha:
        raise RuntimeError("owned pinned acyclic historical manifest required")
    value = read(path)
    if value.get("extension_version") != VERSION:
        if value.get("filtered_field_sidecars"):
            raise RuntimeError("historical v1 cannot claim filtered proof authority")
        return renewed.history_fence(path, sha, {k: successor[k] for k in renewed.GROUPS}, seen)
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
            or value["new_findings_stop_immediately"] is not True):
        raise RuntimeError("filtered historical environment source/config/metadata drift")
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
    if value["bound_metadata_files"].get(str(parent_path)) != parent_sha:
        raise RuntimeError("historical parent manifest metadata pin missing")
    parent = history_fence(parent_path, parent_sha, snapshot, seen | {resolved})
    if (value["parent"] != parent["parent"] or value["exclusion"] != parent["exclusion"]
            or value["sidecar_path"] != parent["sidecar_path"]
            or value["baseline_run_ids"] != parent["baseline_run_ids"]):
        raise RuntimeError("historical execution/exclusion/stage authority changed")
    delta = extension_delta(inventory(parent), snapshot)
    if value["new_review_sidecars"] != delta or not any(delta.values()):
        raise RuntimeError("filtered extension requires its exact nonempty additions")
    old_reviews = parent["historical_reviews"]
    if value["historical_reviews"][:len(old_reviews)] != old_reviews:
        raise RuntimeError("historical review ordering or pairs changed")
    return value


def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
               require_dispatch_ready: bool) -> EnvironmentLedger:
    journal = frozen.ROOT / "phase2-attempts.jsonl"
    cadence.digest(journal)
    rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    reservations = [r for r in rows if r["event"] == "reserved"]
    settled = [r for r in rows if r["event"] == "settled"]
    reserved = {r["run_id"]: r for r in reservations}
    if len(reserved) != len(reservations) or len({r["run_id"] for r in settled}) != len(settled):
        raise RuntimeError("duplicate raw reservation or settlement")
    raw: dict[str, Attempt] = {}
    for s in settled:
        r = reserved[s["run_id"]]
        raw[s["run_id"]] = Attempt(r["cell_id"], r["run_id"], r["attempt_index"],
                                   r["execution_sha256"], s["disposition"],
                                   s["reason"], s["receipt_sha256"])
    groups = inventory(value)
    names = {environment.RUN + ".json", *(n for g in groups.values() for n in g)}
    if names != {a.run_id + ".json" for a in raw.values() if a.disposition == "confounder"}:
        raise RuntimeError("every raw finding needs its disjoint exact proof")
    reviewers = ((field.core.verify_sidecar, field.core.legacy.REVIEW_REASON),
                 (field.review.verify_sidecar, field.review.field.REASON),
                 (renewed.previous.derived.verify_sidecar, renewed.previous.derived.REASON),
                 (filtered.verify_sidecar, filtered.REASON))
    pairs: list[tuple[Attempt, Attempt]] = []
    for key, directory, (verify, reason) in zip(GROUPS, _directories(), reviewers, strict=True):
        for name, sha in sorted(groups[key].items()):
            path = frozen.ROOT / directory / name
            if cadence.digest(path) != sha:
                raise RuntimeError("historical sidecar drift")
            attempt = raw[name[:-5]]
            proof = verify(path, attempt)
            pairs.append((attempt, replace(attempt, disposition="valid", reason=reason,
                                           receipt_sha256=proof["reviewed_admission_sha256"])))
    environment.verify_exclusion(sidecar, raw[environment.RUN])
    exclusion = (raw[environment.RUN], replace(raw[environment.RUN],
                 disposition="operational_excluded", reason=environment.REASON,
                 receipt_sha256=cadence.digest(sidecar)))
    ledger = EnvironmentLedger(journal, tuple(c.cell_id for c in cells),
                               value["phase2_schedule_sha256"], tuple(pairs), exclusion)
    if require_dispatch_ready:
        environment.dispatch_ready(ledger)
    return ledger


def full_control(control: Path, sidecar: Path,
                 derived_sidecars: dict[str, str] | None = None,
                 filtered_sidecars: dict[str, str] | None = None
                 ) -> tuple[dict[str, Any], tuple[Any, ...]]:
    current = current_inventory()
    derived_group = (current["derived_field_sidecars"] if derived_sidecars is None
                     else derived_sidecars)
    filtered_group = (current["filtered_field_sidecars"] if filtered_sidecars is None
                      else filtered_sidecars)

    def checked(value: dict[str, Any], cells: tuple[Any, ...], *,
                require_dispatch_ready: bool) -> EnvironmentLedger:
        return membership({**value, "derived_field_sidecars": derived_group,
                           "filtered_field_sidecars": filtered_group}, cells, sidecar,
                          require_dispatch_ready=require_dispatch_ready)

    result: tuple[dict[str, Any], tuple[Any, ...]] = copied(
        field.checked_control, {"checked_membership": checked})(control)
    return result


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
        if attempt.reason == filtered.REASON:
            return filtered.effective_admission(root, attempt)
        return renewed.previous.derived.effective_admission(root, attempt)

    review_proxy = SimpleNamespace(**{**vars(field.review),
                                     "effective_admission": effective_admission})
    field_proxy = SimpleNamespace(**{**vars(field), "review": review_proxy})
    result: dict[str, Any] = copied(environment.collect, {"field": field_proxy})(value, ledger)
    categories = (("initial", "initial_field_sidecars", field.review.DIRECTORY,
                   field.review.field.REASON, "field_misuse_proof"),
                  ("derived", "derived_field_sidecars", renewed.previous.derived.DIRECTORY,
                   renewed.previous.derived.REASON, "derived_field_proof"),
                  ("filtered", "filtered_field_sidecars", filtered.DIRECTORY,
                   filtered.REASON, "derived_field_proof"))
    for label, key, directory, reason, proof_key in categories:
        confirmed = 0
        for row in result["rows"]:
            for record in row["attempts"]:
                if record["reason"] != reason:
                    continue
                path = frozen.ROOT / directory / (record["run_id"] + ".json")
                proof = read(path)
                if (cadence.digest(path) != value[key].get(path.name)
                        or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                    raise RuntimeError("projection field proof/receipt drift")
                count = len(proof[proof_key])
                record.update(confirmed_absent_record_field_failures=count,
                              **{label + "_record_field_proof_count": count})
                confirmed += count
        result["confirmed_" + label + "_absent_record_field_failures"] = confirmed
        result[label + "_field_reviewed_attempts"] = sum(
            a.reason == reason and a.disposition == "valid" for a in ledger.attempts)
    result.update(filtered_field_sidecars=value["filtered_field_sidecars"],
                  filtered_field_proof_source_sha256=filtered.sources(),
                  derived_field_sidecars=value["derived_field_sidecars"],
                  derived_field_proof_source_sha256=renewed.previous.derived.sources(),
                  original_admissions_preserved=True, new_store_or_corpus_body_decoded=False,
                  new_model_calls=0, atomic_execution_changed=False)
    return result


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    if (value.get("extension_version") != VERSION or not path.name.startswith(PREFIX)
            or read(path) != value or current_inventory() != inventory(value)):
        raise RuntimeError("current filtered manifest/inventory drift")
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
        raise RuntimeError("owned exclusive filtered manifest required")
    if output.exists():
        raise FileExistsError("filtered manifest creator must not repeat")
    if control.exists() != receipt.exists():
        raise RuntimeError("filtered control and receipt must both exist or both be new")
    if (not old_path.name.startswith(PREFIX)
            and (old_path.name != PARENT_NAME or old_sha != PARENT_SHA)):
        raise RuntimeError("initial filtered extension requires pinned renewed003 authority")
    environment.require_strata_stopped()
    current = current_inventory()
    old = history_fence(old_path, old_sha, current)
    delta = extension_delta(inventory(old), current)
    if not any(delta.values()) or not delta["filtered_field_sidecars"]:
        raise RuntimeError("source-bound filtered review additions required")
    old_control = historical_control(old)
    parent_path = Path(old_control["parent_control_path"])
    parent, cells = field.core.previous.checked_control(parent_path)
    if parent != old["parent"]:
        raise RuntimeError("complete original gate/schedule drift")
    candidate = field.control_bindings(parent_path, parent,
                                      Path(old_control["preserved_model_control_path"]),
                                      Path(old_control["preserved_model_ledger_path"]))
    membership_value = {**candidate, "derived_field_sidecars": current["derived_field_sidecars"],
                        "filtered_field_sidecars": current["filtered_field_sidecars"]}
    if inventory(membership_value) != current:
        raise RuntimeError("current original control inventory mismatch")
    if control.exists():
        if read(control) != candidate:
            raise RuntimeError("provided filtered control differs from original bindings")
        field.validate(control, receipt)
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
    if not control.exists():
        if before != journal.read_bytes():
            raise RuntimeError("filtered proof journal advanced")
        inactive(frozen.ROOT)
        frozen.write_new(control, candidate)
        frozen.write_new(receipt, field.freeze_value(control))
    field.validate(control, receipt)
    saved, checked_cells = full_control(control, sidecar, current["derived_field_sidecars"],
                                       current["filtered_field_sidecars"])
    if saved != parent or checked_cells != cells:
        raise RuntimeError("complete filtered gate/schedule drift")
    references = {old_path, control, receipt, sidecar,
                  *(Path(p) for p in old["bound_metadata_files"]),
                  *(frozen.ROOT / directory / n
                    for k, directory in zip(GROUPS, _directories(), strict=True)
                    for n in current[k])}
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
    environment.audit_wire(collect(result, ledger), sidecar)
    history_fence(old_path, old_sha, current)
    if before != journal.read_bytes() or current_inventory() != current:
        raise RuntimeError("filtered journal or review inventory advanced")
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
