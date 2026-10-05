"""Strict supplemental freeze for the tested transport-receipt repair only.

Never waive admission, rewrite an old freeze, or authorize a retry on its own.
The unchanged journal requires a separate full-audit affected-cell repair entry.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from large_scale_repair_freeze_v1 import sha256

from infra_joint.control.provenance import provenance_sha256

NAME = "execution-freeze-003.json"
PARENT_SHA256 = "50e2fbcac51693695e551f0b09bd83f332891a1e4c2e6a48b393fd3874d569d8"
AUDIT_NAME = "transport-repair-audit-001.json"
NATIVE = "src/infra_joint/control/native_agents.py"
PHYSICAL = "src/infra_joint/control/physical.py"
HARNESS_PARENT = "configs/experiments/infra-aware-predecision-v1-isolation-patch1.yaml"
HARNESS = "configs/experiments/infra-aware-predecision-v1-transport-receipts-patch2.yaml"
CHANGED = frozenset({NATIVE, PHYSICAL, "scripts/large_scale_queue_v1.py",
                     "scripts/large_scale_execution_v1.py"})
ADDED = frozenset({HARNESS, "scripts/large_scale_transport_freeze_v1.py"})
TESTED_CORE = {
    NATIVE: "81d9e80233f24ccbf115999799e438a52d3151e119f67f7e8e95d7ddc6b66af8",
    PHYSICAL: "9702a386b286cbba2a1c565635153529d570ff877f192c110a08f7b51d685cc0",
}


def source_delta(parent: dict[str, str], current: dict[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(current.keys() - parent.keys()),
        "removed": sorted(parent.keys() - current.keys()),
        "changed": sorted(k for k in parent.keys() & current.keys() if parent[k] != current[k]),
    }


def validate_harness_repair(parent: dict[str, Any], repaired: dict[str, Any]) -> None:
    expected = deepcopy(parent)
    runtime = expected["runtime"]
    runtime["parent_native_source_sha256"] = runtime["source_sha256"]
    runtime["source_sha256"] = TESTED_CORE[NATIVE]
    runtime["transport_receipt_patch"] = "interrupted-physical-receipt-v1"
    runtime.setdefault("component_sha256", {})[PHYSICAL] = TESTED_CORE[PHYSICAL]
    if repaired != expected:
        raise RuntimeError("transport repair cannot change harness semantics/models/tools/budgets")


def validate_execution_repair(parent: dict[str, Any], current: dict[str, Any]) -> None:
    delta = source_delta(parent["source_sha256"], current["source_sha256"])
    if delta != {"added": sorted(ADDED), "removed": [], "changed": sorted(CHANGED)}:
        raise RuntimeError("transport execution contains an unaudited source/config change")
    if any(current["source_sha256"][p] != h for p, h in TESTED_CORE.items()):
        raise RuntimeError("transport core does not match the tested receipt-only repair")
    ignored = {"commit_sha", "source_sha256"}
    if ({k: v for k, v in parent.items() if k not in ignored}
            != {k: v for k, v in current.items() if k not in ignored}):
        raise RuntimeError("task/model/network/pricing/history/rules/schedule/environment drift")
    if current["commit_sha"] == parent["commit_sha"]:
        raise RuntimeError("a distinct tested repair revision is required")


def _read_audit(root: Path, parent: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    audit_path = root / "readiness" / AUDIT_NAME
    if audit_path.is_symlink():
        raise RuntimeError("repair audit must be an immutable owned file")
    audit = json.loads(audit_path.read_text())
    if (audit.get("version") != "transport-receipt-repair-audit-v1"
            or audit.get("parent_execution_sha256") != provenance_sha256(parent)
            or audit.get("repaired_execution_candidate_sha256") != provenance_sha256(current)
            or audit.get("allowed_source_delta") != source_delta(
                parent["source_sha256"], current["source_sha256"])
            or audit.get("semantic_contracts_unchanged") is not True
            or audit.get("original_evidence_unchanged") is not True
            or audit.get("queue_and_attempt_absent") is not True
            or audit.get("test_gates") != {"pytest": "passed", "ruff": "passed",
                                           "strict_pyright": "passed", "diff_check": "passed"}):
        raise RuntimeError("repair audit does not establish the exact tested execution delta")
    directory = root / "evidence" / audit["cell_id"] / f"attempt{audit['attempt_index']}"
    if not directory.resolve().is_relative_to((root / "evidence").resolve()):
        raise RuntimeError("affected attempt escapes its owned evidence namespace")
    bindings = audit["original_evidence_file_sha256"]
    if (not bindings or set(bindings) != {str(p.relative_to(directory))
                                         for p in directory.rglob("*") if p.is_file()}):
        raise RuntimeError("repair must preserve and bind every original evidence file")
    for relative, digest in bindings.items():
        file = directory / relative
        if (file.is_symlink() or not file.resolve().is_relative_to(directory.resolve())
                or sha256(file) != digest):
            raise RuntimeError("affected attempt original evidence drift")
    original = json.loads((directory / "admission.json").read_text())
    if (provenance_sha256(original) != audit["original_admission_sha256"]
            or original.get("disposition") != "confounder"
            or original.get("problems") != [
                "typed_action_failure_requires_audit:physical_execution_failed"]
            or original.get("operational_incidents")):
        raise RuntimeError("transport repair cannot authorize an unrelated or mixed failure")
    return audit


def execution_value(root: Path, app: Path) -> dict[str, Any]:
    import large_scale_queue_v1 as queue

    queue.require_remote(root)
    queue.frozen.validate_runtime_import_root()
    if app.resolve() != Path(queue.__file__).resolve().parents[1]:
        raise RuntimeError("transport freeze app/import root mismatch")
    parent_path = root / "execution-freeze-002.json"
    if parent_path.is_symlink():
        raise RuntimeError("parent execution freeze must remain an immutable owned receipt")
    parent = json.loads(parent_path.read_text())
    if provenance_sha256(parent) != PARENT_SHA256:
        raise RuntimeError("parent execution freeze drift")
    current = queue.execution_freeze()
    validate_execution_repair(parent, current)
    parent_harness = yaml.safe_load((app / HARNESS_PARENT).read_text(encoding="utf-8"))
    repaired_harness = yaml.safe_load((app / HARNESS).read_text(encoding="utf-8"))
    validate_harness_repair(parent_harness, repaired_harness)
    if queue.frozen.protocol()["harness_manifest"] != HARNESS_PARENT:
        raise RuntimeError("unexpected parent harness reference")
    audit = _read_audit(root, parent, current)
    return {
        **current,
        "version": "large-scale-transport-receipt-repair-v1",
        "parent_execution_sha256": PARENT_SHA256,
        "transport_repair_audit_sha256": sha256(root / "readiness" / AUDIT_NAME),
        "transport_affected_run_id": audit["run_id"],
        "selected_harness_manifest": HARNESS,
        "selected_harness_sha256": sha256(app / HARNESS),
        "parent_formal_runs_at_execution_freeze": current["formal_runs_at_execution_freeze"],
        "formal_runs_at_execution_freeze": audit["classified_nominal_cells_at_repair"],
    }


def verify(root: Path, app: Path, path: Path) -> str:
    if (path.is_symlink() or path.resolve().parent != root.resolve() or path.name != NAME):
        raise RuntimeError("transport execution freeze must be its new exact owned namespace")
    saved = json.loads(path.read_text())
    if saved != execution_value(root, app):
        raise RuntimeError("transport execution/config/provenance drift; queue stopped")
    return provenance_sha256(saved)


def harness_for_attempt(root: Path, app: Path, path: Path | None) -> Path:
    if path is None or path.name != NAME:
        return app / HARNESS_PARENT
    verify(root, app, path)
    return app / HARNESS
