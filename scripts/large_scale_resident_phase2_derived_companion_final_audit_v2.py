"""Offline final adapter for versioned derived proofs in the same five groups.

Reuse the all193/all192 reconciliation, exact recipient scanner and first-action
inactivity guard. The bundle never claims semantic/manual/Q1-Q10 completion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_derived_companion_environment_v2 as environment
import large_scale_resident_phase2_derived_companion_final_audit_v1 as ancestor
import large_scale_resident_phase2_derived_companion_review_v2 as derived
import large_scale_resident_phase2_native_renewed_final_audit_v1 as previous

VERSION = "resident-phase2-derived-companion-final-evidence-bundle-v2"
private = previous.private
native = previous.native
filtered = previous.filtered
original = previous.original
copied = previous.copied
base = previous.previous
ANCESTOR_SOURCE_ADAPTER = ancestor


def _source_modules() -> dict[str, ModuleType]:
    traversal = base.previous.previous.SOURCE_MODULES
    return cast(dict[str, ModuleType], copied(traversal, {
        "__name__": __name__, "__file__": __file__, "environment": environment,
        "derived": derived, "previous": previous})())


def audit_sources() -> dict[str, str]:
    return {name: environment.cadence.digest(Path(cast(str, module.__file__)))
            for name, module in _source_modules().items()}


def audit_source_paths() -> dict[str, str]:
    return {name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in _source_modules().items()}


def _environment_view(derived_sidecars: dict[str, str],
                      filtered_sidecars: dict[str, str],
                      native_sidecars: dict[str, str]) -> SimpleNamespace:
    return cast(SimpleNamespace, copied(previous.ENVIRONMENT_VIEW, {
        "environment": environment})(derived_sidecars, filtered_sidecars, native_sidecars))


def reconcile(projection: dict[str, Any], ledger: Any, control: dict[str, Any],
              derived_sidecars: dict[str, str], filtered_sidecars: dict[str, str],
              native_sidecars: dict[str, str]) -> dict[str, Any]:
    return cast(dict[str, Any], copied(base.reconcile, {
        "environment": environment, "derived": derived,
        "_environment_view": _environment_view})(projection, ledger, control,
            derived_sidecars, filtered_sidecars, native_sidecars))


def audit_phase_two(manifest: Path, manifest_sha256: str,
                    derived_sidecars: dict[str, str], filtered_sidecars: dict[str, str],
                    native_sidecars: dict[str, str]) -> dict[str, Any]:
    return cast(dict[str, Any], copied(base.audit_phase_two, {
        "environment": environment, "_environment_view": _environment_view,
        "reconcile": reconcile})(manifest, manifest_sha256,
                                 derived_sidecars, filtered_sidecars, native_sidecars))


def create_bundle(manifest: Path, manifest_sha256: str, audit_source_sha256: str,
                  output: Path) -> dict[str, Any]:
    return cast(dict[str, Any], copied(base.create_bundle, {
        "environment": environment, "_environment_view": _environment_view,
        "audit_sources": audit_sources, "audit_source_paths": audit_source_paths,
        "reconcile": reconcile, "audit_phase_two": audit_phase_two, "VERSION": VERSION})(
            manifest, manifest_sha256, audit_source_sha256, output))


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
