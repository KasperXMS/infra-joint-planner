"""Exclusive all193 final bundle through the explicit derived-field extension.

The original scanner and global inactivity guard remain unchanged. This adapter
does not complete semantic, manual or Q1-Q10 review or authorize a replacement.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_derived_environment_v1 as environment
import large_scale_resident_phase2_derived_field_review_v1 as derived
import large_scale_resident_phase2_final_audit_v1 as previous

from infra_joint.control.provenance import provenance_sha256

private = previous.private
VERSION = "resident-phase2-derived-final-evidence-bundle-v1"


def copied(original: Any, namespace: dict[str, Any]) -> Any:
    """Bind only a private namespace, retaining defaults and keyword defaults."""
    bound = FunctionType(original.__code__, {**original.__globals__, **namespace},
                         original.__name__, original.__defaults__, original.__closure__)
    bound.__kwdefaults__ = dict(original.__kwdefaults__ or {})
    return bound


def _source_modules() -> dict[str, ModuleType]:
    """Pin the actual imported closure, including the unchanged native scanner."""
    original = private.previous.private
    scanner = sys.modules[original.scan_store.__module__]
    pending = [sys.modules[__name__], environment, derived, previous, private,
               private.previous, original, scanner]
    seen: set[str] = set()
    result: dict[str, ModuleType] = {}
    while pending:
        module = pending.pop()
        if module.__name__ in seen:
            continue
        seen.add(module.__name__)
        if module.__file__ is None:
            raise RuntimeError("final audit requires file-backed source modules")
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
    return {name: environment.cadence.digest(Path(cast(str, module.__file__)))
            for name, module in _source_modules().items()}


def audit_source_paths() -> dict[str, str]:
    return {name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in _source_modules().items()}


def _review_control(control: dict[str, Any], sidecars: dict[str, str]) -> dict[str, Any]:
    if "derived_field_sidecars" in control and control["derived_field_sidecars"] != sidecars:
        raise RuntimeError("control/manifest derived review map drift")
    return {**control, "derived_field_sidecars": dict(sidecars)}


def _environment_view(sidecars: dict[str, str]) -> SimpleNamespace:
    """Adapt old helper signatures to the manifest's exact third review map."""
    expected = dict(sidecars)

    def full_control(control: Path, sidecar: Path) -> Any:
        return environment.full_control(control, sidecar, expected)

    def membership(value: dict[str, Any], cells: tuple[Any, ...], sidecar: Path, *,
                   require_dispatch_ready: bool) -> Any:
        return environment.membership(_review_control(value, expected), cells, sidecar,
                                      require_dispatch_ready=require_dispatch_ready)

    return SimpleNamespace(**{**vars(previous.environment), **vars(environment),
                              "full_control": full_control, "membership": membership,
                              "audit_wire": previous.environment.audit_wire})


def reconcile(projection: dict[str, Any], ledger: Any, control: dict[str, Any],
              derived_sidecars: dict[str, str]) -> dict[str, Any]:
    """Reconcile verified proof counts without modifying original admissions."""
    groups = (control["model_json_sidecars"], control["initial_field_sidecars"],
              derived_sidecars, {previous.environment.RUN + ".json": None})
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
        original = raw[run]
        if (cell != original.cell_id or record["attempt_index"] != original.attempt_index
                or record["execution_sha256"] != original.execution_sha256
                or record["original_disposition"] != original.disposition
                or record["original_receipt_sha256"] != original.receipt_sha256):
            raise RuntimeError("review reconciliation original identity drift")
    result: dict[str, Any] = copied(previous.reconcile, {
        "environment": _environment_view(derived_sidecars)})(projection, ledger, control)
    reviewed_records = {a["run_id"]: a for row in result["rows"] for a in row["attempts"]}
    for name, sha in derived_sidecars.items():
        run = name.removesuffix(".json")
        if name != run + ".json" or Path(name).name != name or run not in raw:
            raise RuntimeError("derived review sidecar run/namespace drift")
        path = environment.frozen.ROOT / derived.DIRECTORY / name
        if environment.cadence.digest(path) != sha:
            raise RuntimeError("derived review sidecar hash drift")
        proof = derived.verify_sidecar(path, raw[run])
        record = reviewed_records[run]
        if (proof["run_id"] != run or raw[run].disposition != "confounder"
                or proof["original_admission_sha256"] != raw[run].receipt_sha256
                or proof["original_execution_sha256"] != raw[run].execution_sha256
                or record["disposition"] != "valid"
                or proof["reviewed_admission_sha256"] != record["receipt_sha256"]):
            raise RuntimeError("derived review original/effective attempt binding drift")
        entries = proof["derived_field_proof"]
        if not isinstance(entries, list) or not entries:
            raise RuntimeError("derived review requires exact nonempty failure proof")
        count = len(cast(list[Any], entries))
        record.update(original_rejection_preserved=True,
                      phase2_derived_field_sidecar_sha256=sha,
                      confirmed_absent_derived_record_field_failures=count,
                      confirmed_absent_record_field_failures=count)
    return result


def audit_phase_two(manifest: Path, manifest_sha256: str,
                    derived_sidecars: dict[str, str]) -> dict[str, Any]:
    """Route guarded private diagnostics through the extension, scanner unchanged."""
    routed = _environment_view(derived_sidecars)

    def collect(value: dict[str, Any], ledger: Any) -> dict[str, Any]:
        projection = environment.collect(value, ledger)
        copied(vars(previous)["_inventory"], {"environment": routed})(projection)
        return projection

    routed.collect = collect
    return cast(dict[str, Any], copied(private.audit_phase_two, {
        "environment": routed})(manifest, manifest_sha256))


def create_bundle(manifest: Path, manifest_sha256: str, audit_source_sha256: str,
                  output: Path) -> dict[str, Any]:
    root = environment.frozen.ROOT
    private.previous.private.assert_inactive(root)  # First, before source/control/output reads.
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
    sidecars = value["derived_field_sidecars"]
    if not isinstance(sidecars, dict) or not sidecars:
        raise RuntimeError("explicit nonempty derived review map required")
    sidecars = cast(dict[str, str], sidecars)
    control, sidecar = Path(value["control_path"]), Path(value["sidecar_path"])
    routed = _environment_view(sidecars)
    parent, cells = routed.full_control(control, sidecar)
    if parent != value["parent"] or len(cells) != 192:
        raise RuntimeError("final bundle parent/schedule drift")
    control_value = environment.read(control)
    ledger = routed.membership(control_value, cells, sidecar, require_dispatch_ready=True)
    projection = environment.collect(value, ledger)
    runs = copied(vars(previous)["_inventory"], {"environment": routed})(projection)
    reviewed = reconcile(projection, ledger, control_value, sidecars)
    recipients = routed.audit_wire(projection, sidecar)
    recipient_runs = [r["run_id"] for r in recipients["records"]]
    if len(recipient_runs) != 193 or set(recipient_runs) != set(runs):
        raise RuntimeError("final all-attempt recipient inventory drift")
    for receipt in recipients["records"]:
        if (receipt["effective_disposition"] != runs[receipt["run_id"]]["disposition"]
                or receipt["original_admission_sha256"]
                != runs[receipt["run_id"]]["original_receipt_sha256"]):
            raise RuntimeError("final recipient admission binding drift")
    diagnostics = audit_phase_two(manifest, manifest_sha256, sidecars)
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
              "derived_field_sidecars": copy.deepcopy(sidecars),
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
