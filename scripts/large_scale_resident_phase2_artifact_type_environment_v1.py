"""Append-only model artifact type proofs in the unchanged five-group authority.

Historical source maps and proof reviewers remain exact. Only the derived map
accepts an explicitly versioned additional reviewer, with no new proof group,
execution change, wildcard waiver, retry authority or private guard relaxation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_artifact_type_review_v1 as derived
import large_scale_resident_phase2_derived_companion_environment_v3 as ancestor
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
MODULE = "large_scale_resident_phase2_artifact_type_environment_v1"
PREFIX = "phase2-artifact-type-environment-cadence-freeze-"
VERSION = "resident-phase2-five-group-model-artifact-type-renewal-v1"
BASE_VERSION = previous.BASE_VERSION
PARENT_NAME = "phase2-derived-companion-v3-environment-cadence-freeze-001.json"
PARENT_SHA = "9d68b6af24554d2a977a8b38073df15f8a4908844513e75fe278888350979050"
_raw_attempts = vars(previous)["_raw_attempts"]
_directories = vars(previous)["_directories"]


def sources() -> dict[str, str]:
    return {
        **previous.sources(),
        **derived.sources(),
        **ancestor.sources(),
        Path(__file__).name: cadence.digest(Path(__file__)),
    }


def _review_pairs(
    groups: Inventory, raw: dict[str, Attempt]
) -> tuple[tuple[Attempt, Attempt], ...]:
    ancestor = previous.previous
    reviewers = (
        (field.core.verify_sidecar, field.core.legacy.REVIEW_REASON),
        (field.review.verify_sidecar, field.review.field.REASON),
        (derived.verify_sidecar, derived.REASON),
        (ancestor.filtered.filtered.verify_sidecar, ancestor.filtered.filtered.REASON),
        (ancestor.native.verify_sidecar, ancestor.native.REASON),
    )
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
            pairs.append(
                (
                    attempt,
                    replace(
                        attempt,
                        disposition="valid",
                        reason=reason,
                        receipt_sha256=proof["reviewed_admission_sha256"],
                    ),
                )
            )
    return tuple(pairs)


def membership(
    value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *, require_dispatch_ready: bool
) -> EnvironmentLedger:
    return cast(
        EnvironmentLedger,
        copied(previous.membership, {"_review_pairs": _review_pairs})(
            value, cells, sidecar, require_dispatch_ready=require_dispatch_ready
        ),
    )


def full_control(
    control: Path,
    sidecar: Path,
    derived_sidecars: dict[str, str] | None = None,
    filtered_sidecars: dict[str, str] | None = None,
    native_argument_sidecars: dict[str, str] | None = None,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    return cast(
        tuple[dict[str, Any], tuple[Any, ...]],
        copied(previous.full_control, {"membership": membership})(
            control, sidecar, derived_sidecars, filtered_sidecars, native_argument_sidecars
        ),
    )


def collect(value: dict[str, Any], ledger: EnvironmentLedger) -> dict[str, Any]:
    """Exact version-specific projection; no artifact-type proof becomes a field proof."""
    native = previous.previous
    filtered = native.filtered

    def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
        if attempt.reason == native.native.REASON:
            return native.native.effective_admission(root, attempt)
        if attempt.reason == filtered.filtered.REASON:
            return filtered.filtered.effective_admission(root, attempt)
        return derived.effective_admission(root, attempt)

    proxy = SimpleNamespace(**{**vars(field.review), "effective_admission": effective_admission})
    field_proxy = SimpleNamespace(**{**vars(field), "review": proxy})
    result = cast(
        dict[str, Any], copied(environment.collect, {"field": field_proxy})(value, ledger)
    )
    categories = (
        (
            "initial",
            "initial_field_sidecars",
            field.review,
            field.review.field.REASON,
            "field_misuse_proof",
        ),
        ("derived", "derived_field_sidecars", derived, derived.REASON, "derived_field_proof"),
        (
            "filtered",
            "filtered_field_sidecars",
            filtered.filtered,
            filtered.filtered.REASON,
            "derived_field_proof",
        ),
        (
            "native",
            "native_argument_sidecars",
            native.native,
            native.native.REASON,
            "native_argument_proof",
        ),
    )
    artifact_attempts = artifact_failures = context_failures = companions = 0
    for label, key, reviewer, reason, proof_key in categories:
        confirmed = reviewed = 0
        for row in result["rows"]:
            for record in row["attempts"]:
                if record["reason"] != reason:
                    continue
                path = frozen.ROOT / reviewer.DIRECTORY / (record["run_id"] + ".json")
                proof = read(path)
                sha = cadence.digest(path)
                if (
                    sha != value[key].get(path.name)
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]
                ):
                    raise RuntimeError("projection exact proof/receipt drift")
                if label == "derived" and proof.get("version") == derived.VERSION:
                    if (
                        not proof.get("artifact_type_misuse_proof")
                        or not proof.get("context_preflight_proof")
                        or not proof.get("model_output_materialization_proof")
                    ):
                        raise RuntimeError("artifact type projection requires every exact proof")
                    for key in (
                        "confirmed_absent_record_field_failures",
                        "derived_record_field_proof_count",
                    ):
                        if key in record:
                            if record[key] != 0:
                                raise RuntimeError(
                                    "artifact type projection cannot claim field misuse"
                                )
                            record.pop(key)
                    record.update(
                        artifact_type_review_version=proof["version"],
                        artifact_type_misuse_count=len(proof["artifact_type_misuse_proof"]),
                        artifact_context_preflight_count=len(proof["context_preflight_proof"]),
                        model_output_materialization_count=len(
                            proof["model_output_materialization_proof"]
                        ),
                        phase2_artifact_type_sidecar_sha256=sha,
                    )
                    artifact_attempts += 1
                    artifact_failures += len(proof["artifact_type_misuse_proof"])
                    context_failures += len(proof["context_preflight_proof"])
                    continue
                if label == "derived" and proof.get("version") not in derived.OLD_VERSIONS:
                    raise RuntimeError("unsupported historical derived projection version")
                entries = proof[proof_key]
                if not isinstance(entries, list) or not entries:
                    raise RuntimeError("historical projection requires its exact nonempty proof")
                count = len(cast(list[Any], entries))
                if label == "native":
                    record.update(
                        native_argument_proof_count=count, native_argument_sidecar_sha256=sha
                    )
                else:
                    record.update(
                        confirmed_absent_record_field_failures=count,
                        **{label + "_record_field_proof_count": count},
                    )
                if label == "derived" and proof["version"] != derived.ancestor.OLD_VERSION:
                    record.update(
                        derived_companion_review_version=proof["version"],
                        read_artifact_limit_proof_count=len(proof["read_artifact_limit_proof"]),
                        output_collision_proof_count=len(proof["output_collision_proof"]),
                    )
                    companions += 1
                reviewed += 1
                confirmed += count
        result[
            "confirmed_"
            + label
            + ("_argument_failures" if label == "native" else "_absent_record_field_failures")
        ] = confirmed
        result[
            label
            + ("_argument_reviewed_attempts" if label == "native" else "_field_reviewed_attempts")
        ] = reviewed
    result.update(
        artifact_type_reviewed_attempts=artifact_attempts,
        confirmed_artifact_type_misuse_failures=artifact_failures,
        confirmed_artifact_context_preflight_failures=context_failures,
        artifact_type_review_source_sha256=derived.sources(),
        derived_field_sidecars=value["derived_field_sidecars"],
        filtered_field_sidecars=value["filtered_field_sidecars"],
        native_argument_sidecars=value["native_argument_sidecars"],
        derived_field_proof_source_sha256=filtered.renewed.previous.derived.sources(),
        derived_companion_reviewed_attempts=companions,
        derived_companion_proof_source_sha256=derived.ancestor.sources(),
        filtered_field_proof_source_sha256=filtered.filtered.sources(),
        native_argument_proof_source_sha256=native.native.sources(),
        original_admissions_preserved=True,
        new_store_or_corpus_body_decoded=False,
        new_model_calls=0,
        atomic_execution_changed=False,
    )
    return result


def _initial_parent(path: Path, sha: str) -> None:
    if not path.name.startswith(PREFIX) and (path.name != PARENT_NAME or sha != PARENT_SHA):
        raise RuntimeError(
            "initial derived companion requires pinned derived companion v3 authority"
        )


def history_fence(
    path: Path, sha: str, successor: Inventory, seen: frozenset[Path] = frozenset()
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        copied(
            previous.history_fence,
            {
                "previous": ancestor,
                "VERSION": VERSION,
                "PREFIX": PREFIX,
                "sources": sources,
                "history_fence": history_fence,
                "_initial_parent": _initial_parent,
                "_review_pairs": _review_pairs,
            },
        )(path, sha, successor, seen),
    )


def fence(path: Path, sha: str, value: dict[str, Any]) -> None:
    copied(previous.fence, {"VERSION": VERSION, "PREFIX": PREFIX, "history_fence": history_fence})(
        path, sha, value
    )


def _checked_candidate(
    control: Path, candidate: dict[str, Any], sidecar: Path, current: Inventory
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    return cast(
        tuple[dict[str, Any], tuple[Any, ...]],
        copied(vars(previous)["_checked_candidate"], {"full_control": full_control})(
            control, candidate, sidecar, current
        ),
    )


def freeze(
    old_path: Path, old_sha: str, control: Path, receipt: Path, output: Path
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        copied(
            previous.freeze,
            {
                "PREFIX": PREFIX,
                "VERSION": VERSION,
                "_initial_parent": _initial_parent,
                "history_fence": history_fence,
                "membership": membership,
                "full_control": full_control,
                "collect": collect,
                "sources": sources,
                "_checked_candidate": _checked_candidate,
            },
        )(old_path, old_sha, control, receipt, output),
    )


def run(path: Path, expected_sha: str) -> None:
    copied(
        environment.run,
        {
            "MODULE": MODULE,
            "PREFIX": PREFIX,
            "sources": sources,
            "membership": membership,
            "full_control": full_control,
            "collect": collect,
            "fence": fence,
        },
    )(path, expected_sha)


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
        if any(
            a is None
            for a in (args.parent_manifest, args.parent_manifest_sha256, args.control, args.ledger)
        ):
            parser.error("freeze requires pinned parent and control/ledger")
        freeze(
            args.parent_manifest,
            args.parent_manifest_sha256,
            args.control,
            args.ledger,
            args.manifest,
        )
        print(json.dumps({"manifest": str(args.manifest), "sha256": cadence.digest(args.manifest)}))
    else:
        if args.manifest_sha256 is None:
            parser.error("queue requires externally pinned manifest digest")
        run(args.manifest, args.manifest_sha256)
