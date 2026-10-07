"""Exclusive offline evidence bundle; semantic/manual/Q1-Q10 review remains required."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, cast

import large_scale_resident_phase2_environment_private_v1 as private
import large_scale_resident_phase2_environment_v1 as environment

from infra_joint.control.provenance import provenance_sha256


def _source_modules() -> dict[str, ModuleType]:
    """Find actual imports across immutable namespaces, never assumed archive copies."""
    original = private.previous.private
    scanner = sys.modules[original.scan_store.__module__]
    pending = [sys.modules[__name__], environment, private, private.previous, original, scanner]
    seen: set[str] = set()
    result: dict[str, ModuleType] = {}
    while pending:
        module = pending.pop()
        if module.__name__ in seen:
            continue
        seen.add(module.__name__)
        if module.__file__ is None:
            raise RuntimeError("final audit requires file-backed source modules")
        # Actual imports can live in different immutable audit namespaces. Module
        # names keep the externally pinned inventory independent of installation paths.
        name = Path(__file__).stem if module.__name__ == "__main__" else module.__name__
        result[name] = module
        for value in vars(module).values():
            dependency = value if isinstance(value, ModuleType) else (
                sys.modules.get(value.__module__)
                if isinstance(value, (FunctionType, type)) else None)
            if dependency is not None and dependency.__name__.startswith((
                    "large_scale_", "cost_guidance_", "resident_model_pool_", "infra_joint")):
                pending.append(dependency)
    return result


def audit_sources() -> dict[str, str]:
    """Canonical module-name hashes are independent of remote installation paths."""
    return {name: environment.cadence.digest(Path(cast(str, module.__file__)))
            for name, module in _source_modules().items()}


def audit_source_paths() -> dict[str, str]:
    return {name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in _source_modules().items()}


def _inventory(projection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (projection["scheduled_cells"] != 192 or projection["admitted_cells"] != 192
            or projection["attempt_count"] != 193 or not projection["phase2_complete"]
            or projection["pending_count"] or projection["confounded_attempts"]
            or projection["operational_excluded_attempts"] != 1
            or len(projection["rows"]) != 192):
        raise RuntimeError("final bundle requires all192 resolved and all193 preserved")
    runs: dict[str, dict[str, Any]] = {}
    cells: set[str] = set()
    excluded: list[str] = []
    for row in projection["rows"]:
        cell = row["condition"]["cell_id"]
        if cell in cells or row["pending_run_ids"]:
            raise RuntimeError("final cell inventory duplicates or pending actions")
        cells.add(cell)
        if sum(a["disposition"] == "valid" for a in row["attempts"]) != 1:
            raise RuntimeError("every final nominal cell requires one valid attempt")
        for attempt in row["attempts"]:
            run = attempt["run_id"]
            if run in runs or attempt["execution_sha256"] != projection["execution_freeze_sha256"]:
                raise RuntimeError("final attempt identity/source drift")
            if attempt["disposition"] != "valid":
                if (run != environment.RUN or cell != environment.CELL
                        or attempt["attempt_index"] != 1
                        or attempt["disposition"] != "operational_excluded"
                        or attempt["original_disposition"] != "confounder"):
                    raise RuntimeError("only exact excluded original71 is permitted")
                excluded.append(run)
            directory = environment.frozen.ROOT / "evidence" / cell / (
                "attempt" + str(attempt["attempt_index"]))
            if environment.read(directory / "worker-shutdown.json")["verified_exited"] is not True:
                raise RuntimeError("every final Worker must have verified exit")
            runs[run] = attempt
    if len(runs) != 193 or excluded != [environment.RUN]:
        raise RuntimeError("excluded original must remain in all193 inventory")
    return runs


def reconcile(projection: dict[str, Any], ledger: Any,
              control: dict[str, Any]) -> dict[str, Any]:
    """Copy only proved review metadata; original outcomes/admissions remain untouched."""
    result = copy.deepcopy(projection)
    records = {a["run_id"]: a for row in result["rows"] for a in row["attempts"]}
    raw = {a.run_id: a for a in ledger.original_attempts}
    if set(raw) != set(records):
        raise RuntimeError("review reconciliation original inventory drift")
    models, fields = control["model_json_sidecars"], control["initial_field_sidecars"]
    if set(models) & set(fields):
        raise RuntimeError("review namespaces must be disjoint")
    for model, sidecars in ((True, models), (False, fields)):
        reviewer = environment.field.core if model else environment.field.review
        for name, sha in sidecars.items():
            run = name.removesuffix(".json")
            if name != run + ".json" or Path(name).name != name or run not in raw:
                raise RuntimeError("review sidecar run/namespace drift")
            path = environment.frozen.ROOT / reviewer.DIRECTORY / name
            if environment.cadence.digest(path) != sha:
                raise RuntimeError("review sidecar hash drift")
            proof = reviewer.verify_sidecar(path, raw[run])
            record = records[run]
            if (proof["run_id"] != run or raw[run].disposition != "confounder"
                    or proof["original_admission_sha256"] != raw[run].receipt_sha256
                    or proof["original_execution_sha256"] != raw[run].execution_sha256
                    or record["disposition"] != "valid"
                    or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
                raise RuntimeError("review original/effective attempt binding drift")
            entries = proof["proof" if model else "field_misuse_proof"]
            if not isinstance(entries, list) or not entries:
                raise RuntimeError("review requires exact nonempty failure proof")
            count = len(cast(list[Any], entries))
            record["original_rejection_preserved"] = True
            key = "phase2_model_json_sidecar_sha256" if model else "phase2_field_sidecar_sha256"
            record[key] = sha
            if model:
                record["confirmed_post_inference_json_failures"] = count
                record["post_inference_failed_service_tokens"] = None
            else:
                record["confirmed_absent_record_field_failures"] = count
    return result


def create_bundle(manifest: Path, manifest_sha256: str, audit_source_sha256: str,
                  output: Path) -> dict[str, Any]:
    root = environment.frozen.ROOT
    private.previous.private.assert_inactive(root)  # First, before any evidence/control reads.
    if (output.is_symlink() or output.parent.is_symlink()
            or output.resolve().parent != root / "analysis"):
        raise RuntimeError("final bundle stays in owned remote analysis")
    if output.exists():
        raise FileExistsError("final bundle creator must not repeat")
    environment.frozen.require_remote()
    sources = audit_sources()
    source_paths = audit_source_paths()
    if provenance_sha256(sources) != audit_source_sha256:
        raise RuntimeError("externally pinned final audit source drift")
    value = environment.read(manifest)
    environment.fence(manifest, manifest_sha256, value)
    control = Path(value["control_path"])
    parent, cells = environment.full_control(control, Path(value["sidecar_path"]))
    if parent != value["parent"] or len(cells) != 192:
        raise RuntimeError("final bundle parent/schedule drift")
    control_value = environment.read(control)
    ledger = environment.membership(control_value, cells, Path(value["sidecar_path"]),
                                    require_dispatch_ready=True)
    projection = environment.collect(value, ledger)
    runs = _inventory(projection)
    reviewed = reconcile(projection, ledger, control_value)
    recipients = environment.audit_wire(projection, Path(value["sidecar_path"]))
    recipient_runs = [r["run_id"] for r in recipients["records"]]
    if len(recipient_runs) != 193 or set(recipient_runs) != set(runs):
        raise RuntimeError("final all-attempt recipient inventory drift")
    for receipt in recipients["records"]:
        if (receipt["effective_disposition"] != runs[receipt["run_id"]]["disposition"]
                or receipt["original_admission_sha256"]
                != runs[receipt["run_id"]]["original_receipt_sha256"]):
            raise RuntimeError("final recipient admission binding drift")
    diagnostics = private.audit_phase_two(manifest, manifest_sha256)
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
    bundle = {"version": "resident-phase2-final-evidence-bundle-v1", **components,
              "component_sha256": {k: provenance_sha256(v) for k, v in components.items()},
              "source_sha256": sources, "source_file_paths": source_paths,
              "audit_source_sha256": audit_source_sha256,
              "manifest_sha256": manifest_sha256, "journal_sha256": projection["journal_sha256"],
              "semantic_audit_complete": False, "manual_audit_complete": False,
              "q1_q10_complete": False, "goal_complete": False, "planner_or_model_calls": 0,
              "artifact_bodies_exported": False, "measured_execution_modified": False,
              "excluded_attempt_omitted": False, "score_aggregation": "not performed"}
    environment.frozen.write_new(output, bundle)
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--audit-source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_bundle(args.manifest, args.manifest_sha256, args.audit_source_sha256, args.output)
    print(json.dumps({"preserved_attempts": 193, "model_calls": 0, "goal_complete": False}))
