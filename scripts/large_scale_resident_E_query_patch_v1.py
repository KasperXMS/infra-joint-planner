# pyright: reportPrivateUsage=false
"""Execution004: only E/B tool isolation, exact provenance, unchanged Worker003."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from infra_joint.control.provenance import provenance_sha256

APP_NAME = "app-E-query-contract-repair-004"
PARENT_APP_NAME = "app-input-cardinality-repair-003"
PARENT_SHA256 = "09f0a5e978623c145b1c075ecb575ed6ea54eec20110c0b7059e1db2b5b905e6"
PARENT_FILE_SHA256 = "015b9b4f6a64b27b0ebdd6094954568b853158d4dfc6b7e8b36da10acea74636"
BUG_SHA256 = "6ee115bbae667060bb19209cb7e1cbf1ae1c3e641d7d2378f55addb7a2cc111c"
DRAIN_SHA256 = "8f8ec012d1600ef6ece5090209dabc2e37fff18fb20202e186b6a35302628c75"
SOURCE = "src/infra_joint/control/bde_native.py"
SOURCE_SHA256 = "daa78d0ced1f9a1588995f4ce213a46adb56645a46d6d829aa0b658964909a60"
ALLOWED_DELTA = frozenset({SOURCE, "scripts/large_scale_resident_queue_v1.py",
                           "scripts/large_scale_resident_E_query_patch_v1.py"})


def validate_source_delta(parent: dict[str, str], current: dict[str, str]) -> dict[str, Any]:
    changed = frozenset(p for p in parent.keys() | current.keys()
                        if parent.get(p) != current.get(p))
    if changed != ALLOWED_DELTA or current.get(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("E repair requires only the exact audited tool-isolation delta")
    return {p: {"parent_sha256": parent.get(p), "patched_sha256": current.get(p)}
            for p in sorted(changed)}


def repaired_execution_freeze(app: Path) -> dict[str, Any]:
    import large_scale_resident_queue_v1 as frozen

    root = frozen.ROOT
    if app.resolve() != (root / APP_NAME).resolve():
        raise RuntimeError("E repair requires a separate immutable execution004 archive")
    parent_path = root / "execution-freeze-003.json"
    parent = json.loads(parent_path.read_text())
    if (frozen.sha256(parent_path) != PARENT_FILE_SHA256
            or provenance_sha256(parent) != PARENT_SHA256):
        raise RuntimeError("parent execution003 freeze drift")
    for relative, digest in parent["source_sha256"].items():
        if frozen.sha256(root / PARENT_APP_NAME / relative) != digest:
            raise RuntimeError("immutable parent execution003 source drift")
    current = {str(p.relative_to(app)): frozen.sha256(p)
               for folder in ("src", "scripts", "configs") for p in (app / folder).rglob("*")
               if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    delta = validate_source_delta(parent["source_sha256"], current)
    proof_path = root / "adjudications/E-query-contract-confounder-001.json"
    drain_path = root / "analysis/resident-E-query-contract-drain-completed-001.json"
    proof, drain = json.loads(proof_path.read_text()), json.loads(drain_path.read_text())
    if (frozen.sha256(proof_path) != BUG_SHA256 or frozen.sha256(drain_path) != DRAIN_SHA256
            or len(proof["affected_effective_run_ids"]) != 14 or not drain["atomic_workers_exited"]
            or not drain["lease_absent"] or not drain["next_cell_not_reserved"]):
        raise RuntimeError("exact affected-only contract proof and safe drain are required")
    with (root / "phase1-attempts.jsonl").open("rb") as stream:
        prefix = b"".join(stream.readline() for _ in range(drain["journal_records"]))
    if hashlib.sha256(prefix).hexdigest() != drain["journal_file_sha256"]:
        raise RuntimeError("safe-drained historical journal prefix drift")
    tests_path = root / "readiness/E-query-contract-validation-001.json"
    tests = json.loads(tests_path.read_text())
    if (tests["commit_sha"] != frozen.frozen._revision() or tests["passed"] is not True
            or tests["source_delta"] != delta
            or not all(tests["checks"][k]["passed"] for k in
                       ("pytest", "ruff", "pyright", "diff_check", "linux_sdk_tools"))):
        raise RuntimeError("complete source-bound E regression/full validation required")
    ready = root / "readiness/worker-surface-004"
    validation = json.loads((ready / "validation.json").read_text())
    shutdown = json.loads((ready / "shutdown-verified.json").read_text())
    if (not validation["passed"] or validation["workers"] != 4
            or validation["deployments"] != 5 or not shutdown["passed"]
            or validation["execution_app"] != str(app)
            or validation["capability_sha256"] != parent["capability_sha256"]):
        raise RuntimeError("actual unchanged Worker003 surface and fresh-store validation required")
    if (frozen.sha256(app / frozen.BLOCK.harness_manifest)
            != parent["harness_manifest_sha256"]
            or frozen.schedule_sha256(frozen.schedule()) != parent["phase1_schedule_sha256"]
            or frozen.verified_prices(frozen.PREDECESSOR, app)[1] != parent["pricing_sha256"]
            or frozen.calibration_receipts() != parent["calibration_receipts"]
            or frozen.environment_fingerprint(frozen.PREDECESSOR) != parent["decoder"]
            or frozen.sha256(frozen.PREDECESSOR / "phase1-attempts.jsonl")
            != frozen.OLD_JOURNAL_SHA256):
        raise RuntimeError("unchanged harness/tasks/profiles/models/prices/environment required")
    return {**parent, "version": "large-scale-resident-E-query-contract-repair-v4",
            "commit_sha": frozen.frozen._revision(), "source_sha256": current,
            "parent_execution_sha256": PARENT_SHA256,
            "parent_execution_file_sha256": PARENT_FILE_SHA256,
            "execution_app": str(app), "worker_app": str(root / PARENT_APP_NAME),
            "source_delta": delta, "bug_review_sha256": BUG_SHA256,
            "validation_receipt_sha256": frozen.sha256(tests_path),
            "readiness_sha256": {name: frozen.sha256(ready / name) for name in (
                "worker-states.json", "static-capability.json", "validation.json",
                "shutdown-verified.json")},
            "affected_original_runs": proof["affected_effective_run_ids"],
            "repair_repetitions": 1, "E_optional_queries_removed": True,
            "ordinary_semantic_retries": False, "worker_code_changed": False,
            "operator_vocabulary_changed": False, "operator_handlers_changed": False,
            "planner_prompt_changed": False, "budgets_changed": False, "scheduler_changed": False,
            "preserved_substrate_source_sha256": {
                p: h for p, h in parent["preserved_substrate_source_sha256"].items()
                if p != SOURCE}}
