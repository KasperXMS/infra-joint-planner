"""Exclusive all193 bundle through the source-bound filtered-field extension.

Original inactivity, inventory, recipient and private-body scanners are reused
unchanged. This offline adapter does not settle semantic/manual/Q1-Q10 review.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_filtered_environment_v1 as environment
import large_scale_resident_phase2_filtered_field_review_v1 as filtered
import large_scale_resident_phase2_renewed_final_audit_v1 as previous

from infra_joint.control.provenance import provenance_sha256

VERSION = "resident-phase2-filtered-final-evidence-bundle-v1"
private = previous.private
derived = previous.derived
copied = previous.copied
original = previous.previous.previous


def _source_modules() -> dict[str, ModuleType]:
    # Start actual-import traversal at this module, retaining every old source.
    return cast(dict[str, ModuleType], copied(previous.SOURCE_MODULES, {
        "__name__": __name__, "__file__": __file__, "environment": environment,
        "derived": derived, "previous": previous})())


def audit_sources() -> dict[str, str]:
    return {name: environment.cadence.digest(Path(cast(str, module.__file__)))
            for name, module in _source_modules().items()}


def audit_source_paths() -> dict[str, str]:
    return {name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in _source_modules().items()}


def _review_control(control: dict[str, Any], derived_sidecars: dict[str, str],
                    filtered_sidecars: dict[str, str]) -> dict[str, Any]:
    for key, sidecars in (("derived_field_sidecars", derived_sidecars),
                         ("filtered_field_sidecars", filtered_sidecars)):
        if key in control and control[key] != sidecars:
            raise RuntimeError("control/manifest review map drift")
    return {**control, "derived_field_sidecars": dict(derived_sidecars),
            "filtered_field_sidecars": dict(filtered_sidecars)}


def _environment_view(derived_sidecars: dict[str, str],
                      filtered_sidecars: dict[str, str]) -> SimpleNamespace:
    """Route original helpers through the two explicit extension maps."""
    derived_map, filtered_map = dict(derived_sidecars), dict(filtered_sidecars)

    def full_control(control: Path, sidecar: Path) -> Any:
        return environment.full_control(control, sidecar, derived_map, filtered_map)

    def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
                   require_dispatch_ready: bool) -> Any:
        return environment.membership(_review_control(value, derived_map, filtered_map),
                                      cells, sidecar,
                                      require_dispatch_ready=require_dispatch_ready)

    return SimpleNamespace(**{**vars(original.environment), **vars(environment),
                              "full_control": full_control, "membership": membership,
                              "audit_wire": original.environment.audit_wire})


def reconcile(projection: dict[str, Any], ledger: Any, control: dict[str, Any],
              derived_sidecars: dict[str, str],
              filtered_sidecars: dict[str, str]) -> dict[str, Any]:
    """Preserve original/effective identities and verify every review exactly."""
    groups = (control["model_json_sidecars"], control["initial_field_sidecars"],
              derived_sidecars, filtered_sidecars, {original.environment.RUN + ".json": None})
    names: set[str] = set()
    for group in groups:
        if names & set(group):
            raise RuntimeError("review namespaces must be disjoint")
        names.update(group)
    raw = {a.run_id: a for a in ledger.original_attempts}
    records = {a["run_id"]: (row["condition"]["cell_id"], a)
               for row in projection["rows"] for a in row["attempts"]}
    if (len(raw) != len(ledger.original_attempts) or set(raw) != set(records)
            or names != {a.run_id + ".json" for a in raw.values()
                         if a.disposition == "confounder"}):
        raise RuntimeError("review reconciliation original inventory drift")
    for run, (cell, record) in records.items():
        saved = raw[run]
        if (cell != saved.cell_id or record["attempt_index"] != saved.attempt_index
                or record["execution_sha256"] != saved.execution_sha256
                or record["original_disposition"] != saved.disposition
                or record["original_receipt_sha256"] != saved.receipt_sha256):
            raise RuntimeError("review reconciliation original identity drift")
    routed = _environment_view(derived_sidecars, filtered_sidecars)
    result = cast(dict[str, Any], copied(original.reconcile, {
        "environment": routed})(projection, ledger, control))
    reviewed = {a["run_id"]: a for row in result["rows"] for a in row["attempts"]}
    for kind, reviewer, sidecars in (("derived", derived, derived_sidecars),
                                    ("filtered", filtered, filtered_sidecars)):
        for name, sha in sidecars.items():
            run = name.removesuffix(".json")
            if name != run + ".json" or Path(name).name != name or run not in raw:
                raise RuntimeError("extension review sidecar run/namespace drift")
            path = environment.frozen.ROOT / reviewer.DIRECTORY / name
            if environment.cadence.digest(path) != sha:
                raise RuntimeError("extension review sidecar hash drift")
            proof = reviewer.verify_sidecar(path, raw[run])
            record = reviewed[run]
            if (proof["run_id"] != run or raw[run].disposition != "confounder"
                    or proof["original_admission_sha256"] != raw[run].receipt_sha256
                    or proof["original_execution_sha256"] != raw[run].execution_sha256
                    or record["disposition"] != "valid"
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                raise RuntimeError("extension review original/effective attempt binding drift")
            entries = proof["derived_field_proof"]
            if not isinstance(entries, list) or not entries:
                raise RuntimeError("extension review requires exact nonempty failure proof")
            count = len(cast(list[Any], entries))
            record.update(original_rejection_preserved=True,
                          confirmed_absent_record_field_failures=count)
            record["phase2_" + kind + "_field_sidecar_sha256"] = sha
            record["confirmed_absent_" + kind + "_record_field_failures"] = count
            if kind == "filtered":
                record["filtered_field_review_source_sha256"] = copy.deepcopy(
                    proof["reviewer_sources_sha256"])
                record["filtered_field_execution_source_sha256"] = copy.deepcopy(
                    proof["execution_sources_sha256"])
                record["filtered_field_transformation_source_sha256"] = copy.deepcopy(
                    proof["tested_transformation_sources_sha256"])
                record["filtered_field_original_admission_sha256"] = (
                    proof["original_admission_sha256"])
                record["filtered_field_reviewed_admission_sha256"] = (
                    proof["reviewed_admission_sha256"])
    return result


def audit_phase_two(manifest: Path, manifest_sha256: str,
                    derived_sidecars: dict[str, str],
                    filtered_sidecars: dict[str, str]) -> dict[str, Any]:
    """Rebind only metadata routing; retain the native private scanner and guard."""
    routed = _environment_view(derived_sidecars, filtered_sidecars)

    def collect(value: dict[str, Any], ledger: Any) -> dict[str, Any]:
        projection = environment.collect(value, ledger)
        copied(vars(original)["_inventory"], {"environment": routed})(projection)
        return projection

    routed.collect = collect
    return cast(dict[str, Any], copied(private.audit_phase_two, {
        "environment": routed})(manifest, manifest_sha256))


def create_bundle(manifest: Path, manifest_sha256: str, audit_source_sha256: str,
                  output: Path) -> dict[str, Any]:
    root = environment.frozen.ROOT
    private.previous.private.assert_inactive(root)  # First, before every file read.
    if (output.is_symlink() or output.parent.is_symlink()
            or output.resolve().parent != root / "analysis"):
        raise RuntimeError("final bundle stays in owned remote analysis")
    if output.exists():
        raise FileExistsError("final bundle creator must not repeat")
    environment.frozen.require_remote()
    sources, source_paths = audit_sources(), audit_source_paths()
    if provenance_sha256(sources) != audit_source_sha256:
        raise RuntimeError("externally pinned final audit source drift")
    value = environment.read(manifest)
    environment.fence(manifest, manifest_sha256, value)
    derived_sidecars, filtered_sidecars = (value["derived_field_sidecars"],
                                         value["filtered_field_sidecars"])
    if not isinstance(derived_sidecars, dict) or not isinstance(filtered_sidecars, dict):
        raise RuntimeError("explicit derived and filtered review maps required")
    derived_sidecars = cast(dict[str, str], derived_sidecars)
    filtered_sidecars = cast(dict[str, str], filtered_sidecars)
    if not filtered_sidecars:
        raise RuntimeError("explicit nonempty filtered review map required")
    control, sidecar = Path(value["control_path"]), Path(value["sidecar_path"])
    routed = _environment_view(derived_sidecars, filtered_sidecars)
    parent, cells = routed.full_control(control, sidecar)
    if parent != value["parent"] or len(cells) != 192:
        raise RuntimeError("final bundle parent/schedule drift")
    control_value = environment.read(control)
    ledger = routed.membership(control_value, cells, sidecar, require_dispatch_ready=True)
    projection = environment.collect(value, ledger)
    runs = copied(vars(original)["_inventory"], {"environment": routed})(projection)
    reviewed = reconcile(projection, ledger, control_value, derived_sidecars, filtered_sidecars)
    recipients = routed.audit_wire(projection, sidecar)
    recipient_runs = [r["run_id"] for r in recipients["records"]]
    if len(recipient_runs) != 193 or set(recipient_runs) != set(runs):
        raise RuntimeError("final all-attempt recipient inventory drift")
    for receipt in recipients["records"]:
        if (receipt["effective_disposition"] != runs[receipt["run_id"]]["disposition"]
                or receipt["original_admission_sha256"]
                != runs[receipt["run_id"]]["original_receipt_sha256"]):
            raise RuntimeError("final recipient admission binding drift")
    diagnostics = audit_phase_two(manifest, manifest_sha256, derived_sidecars, filtered_sidecars)
    diagnostic_runs = [r["run_id"] for r in diagnostics["records"]]
    if (len(diagnostic_runs) != 193 or set(diagnostic_runs) != set(runs)
            or diagnostics["journal_sha256"] != projection["journal_sha256"]
            or diagnostics["manifest_sha256"] != manifest_sha256
            or diagnostics["semantic_audit_complete"] is not False):
        raise RuntimeError("final guarded private diagnostic binding drift")
    private.previous.private.assert_inactive(root)
    environment.fence(manifest, manifest_sha256, value)
    if (audit_sources() != sources or audit_source_paths() != source_paths
            or environment.cadence.digest(ledger.path) != projection["journal_sha256"]):
        raise RuntimeError("final bundle source/journal changed")
    components = {"projection": reviewed, "recipient_audit": recipients,
                  "private_diagnostics": diagnostics}
    bundle: dict[str, Any] = {"version": VERSION, **components,
              "component_sha256": {k: provenance_sha256(v) for k, v in components.items()},
              "source_sha256": sources, "source_file_paths": source_paths,
              "audit_source_sha256": audit_source_sha256,
              "manifest_sha256": manifest_sha256, "journal_sha256": projection["journal_sha256"],
              "derived_field_sidecars": copy.deepcopy(derived_sidecars),
              "filtered_field_sidecars": copy.deepcopy(filtered_sidecars),
              "semantic_audit_complete": False, "manual_audit_complete": False,
              "q1_q10_complete": False, "goal_complete": False, "planner_or_model_calls": 0,
              "artifact_bodies_exported": False, "measured_execution_modified": False,
              "excluded_attempt_omitted": False, "score_aggregation": "not performed"}
    environment.frozen.write_new(output, bundle)
    return bundle


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--audit-source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    create_bundle(args.manifest, args.manifest_sha256, args.audit_source_sha256, args.output)
    print(json.dumps({"preserved_attempts": 193, "model_calls": 0, "goal_complete": False}))


if __name__ == "__main__":
    main()
