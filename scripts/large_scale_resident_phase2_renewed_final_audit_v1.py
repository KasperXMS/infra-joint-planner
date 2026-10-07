"""Exclusive final bundle through the renewed, source-bound review control.

Retain the derived final adapter's all192/all193 gates, original private scanner,
global inactivity guard, and incomplete semantic/manual/Q1-Q10 review status.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import large_scale_resident_phase2_derived_final_audit_v1 as previous
import large_scale_resident_phase2_renewed_environment_v1 as environment

VERSION = "resident-phase2-renewed-final-evidence-bundle-v1"
private = previous.private
derived = previous.derived
copied = previous.copied
SOURCE_MODULES = vars(previous)["_source_modules"]
ENVIRONMENT_VIEW = vars(previous)["_environment_view"]
RECONCILE = previous.reconcile
AUDIT_PHASE_TWO = previous.audit_phase_two
CREATE_BUNDLE = previous.create_bundle


def _source_modules() -> dict[str, ModuleType]:
    # Root the existing actual-import traversal at this module. That includes
    # both renewed modules and every original reviewer, guard and scanner.
    return cast(dict[str, ModuleType], copied(SOURCE_MODULES, {
        "__name__": __name__, "__file__": __file__,
        "environment": environment})())


def audit_sources() -> dict[str, str]:
    return {name: environment.cadence.digest(Path(cast(str, module.__file__)))
            for name, module in _source_modules().items()}


def audit_source_paths() -> dict[str, str]:
    return {name: str(Path(cast(str, module.__file__)).resolve())
            for name, module in _source_modules().items()}


def _environment_view(sidecars: dict[str, str]) -> SimpleNamespace:
    return cast(SimpleNamespace, copied(ENVIRONMENT_VIEW, {
        "environment": environment})(sidecars))


def reconcile(projection: dict[str, Any], ledger: Any, control: dict[str, Any],
              derived_sidecars: dict[str, str]) -> dict[str, Any]:
    return cast(dict[str, Any], copied(RECONCILE, {
        "environment": environment, "_environment_view": _environment_view})(
            projection, ledger, control, derived_sidecars))


def audit_phase_two(manifest: Path, manifest_sha256: str,
                    derived_sidecars: dict[str, str]) -> dict[str, Any]:
    return cast(dict[str, Any], copied(AUDIT_PHASE_TWO, {
        "environment": environment, "_environment_view": _environment_view})(
            manifest, manifest_sha256, derived_sidecars))


def create_bundle(manifest: Path, manifest_sha256: str, audit_source_sha256: str,
                  output: Path) -> dict[str, Any]:
    return cast(dict[str, Any], copied(CREATE_BUNDLE, {
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
