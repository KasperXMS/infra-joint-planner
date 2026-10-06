"""Source-exact resident Quote repair freeze, not a new method/environment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra_joint.control.provenance import provenance_sha256

PARENT_FILE_SHA256 = "c2c474706321e0aeb05eb5238e3ff1f850e0c3b68eab955989732165b2f3da3b"
PARENT_SHA256 = "4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c"
BUG_REVIEW_SHA256 = "46407834f038507051b3a02cf205a424bc9e8d995e1dd7c249ec143c7217d37d"
QUOTE_PATH = "src/infra_joint/control/quote.py"
FIXED_QUOTE_SHA256 = "2714a04007de4ad74150ba1b8c37d76bb2ac833d58a924bc012e5045bae8a485"
ALLOWED_DELTA = frozenset({
    QUOTE_PATH, "scripts/large_scale_resident_queue_v1.py",
    "scripts/large_scale_resident_quote_patch_v1.py",
    "scripts/large_scale_quote_repair_ledger_v1.py",
    "scripts/large_scale_resident_quote_repair_queue_v1.py",
})


def validate_source_delta(parent: dict[str, str], current: dict[str, str]) -> dict[str, Any]:
    changed = {p for p in parent.keys() | current.keys() if parent.get(p) != current.get(p)}
    if changed != ALLOWED_DELTA or current.get(QUOTE_PATH) != FIXED_QUOTE_SHA256:
        raise RuntimeError("Quote repair requires the exact audited delta, not substrate tuning")
    return {p: {"parent_sha256": parent.get(p), "patched_sha256": current.get(p)}
            for p in sorted(changed)}


def repaired_execution_freeze(app: Path) -> dict[str, Any]:
    import large_scale_resident_queue_v1 as frozen

    root = frozen.ROOT
    if app.resolve() != (root / frozen.REPAIR_APP_NAME).resolve():
        raise RuntimeError("repair execution uses its own immutable app, not an in-place overwrite")
    parent_path = root / "execution-freeze-001.json"
    parent = json.loads(parent_path.read_text())
    if (frozen.sha256(parent_path) != PARENT_FILE_SHA256
            or provenance_sha256(parent) != PARENT_SHA256):
        raise RuntimeError("original resident execution freeze changed")
    for path, digest in parent["source_sha256"].items():
        if frozen.sha256(root / "app" / path) != digest:
            raise RuntimeError("immutable original resident source changed")
    current = {str(p.relative_to(app)): frozen.sha256(p)
               for folder in ("src", "scripts", "configs") for p in (app / folder).rglob("*")
               if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    delta = validate_source_delta(parent["source_sha256"], current)
    proof_path = root / "adjudications/quote-hash-confounder-002.json"
    proof = json.loads(proof_path.read_text())
    if (frozen.sha256(proof_path) != BUG_REVIEW_SHA256
            or proof["false_mutation_failure_count"] != 10
            or [a["settlement_ordinal"] for a in proof["affected_attempts"]] != [4, 84]
            or proof["planner_calls"] or proof["model_inference_calls"]):
        raise RuntimeError("exact offline bug proof changed or does not identify affected cells")
    tests_path = root / "readiness/quote-repair-validation-001.json"
    tests = json.loads(tests_path.read_text())
    if (tests["commit_sha"] != frozen.frozen._revision() or tests["passed"] is not True
            or tests["runtime_source_sha256"] != current[QUOTE_PATH]
            or tests["source_delta"] != delta
            or not all(tests["checks"][k]["passed"] for k in
                       ("pytest", "ruff", "pyright", "diff_check"))):
        raise RuntimeError("complete generic patch validation is missing or source-mismatched")
    if frozen.sha256(frozen.PREDECESSOR / "phase1-attempts.jsonl") != frozen.OLD_JOURNAL_SHA256:
        raise RuntimeError("closed historical experiment changed")
    cells = frozen.schedule()
    if frozen.schedule_sha256(cells) != parent["phase1_schedule_sha256"]:
        raise RuntimeError("repair cannot replace/reorder frozen tasks or conditions")
    _, price = frozen.verified_prices(frozen.PREDECESSOR, app)
    if (price != parent["pricing_sha256"]
            or frozen.calibration_receipts() != parent["calibration_receipts"]
            or frozen.environment_fingerprint(frozen.PREDECESSOR) != parent["decoder"]):
        raise RuntimeError("price/calibrated model/decoder environment changed")
    # All configs, prompts, evaluator, tools, scheduler and Worker sources are
    # byte-identical. Workers keep the original app; only control-side quote
    # identity and explicit experiment accounting need the derivative app.
    return {
        **parent, "version": "large-scale-resident-execution-quote-integrity-repair-v2",
        "commit_sha": frozen.frozen._revision(), "source_sha256": current,
        "parent_execution_sha256": PARENT_SHA256,
        "parent_execution_file_sha256": PARENT_FILE_SHA256,
        "execution_app": str(app), "worker_app": str(root / "app"),
        "source_delta": delta, "bug_review_sha256": BUG_REVIEW_SHA256,
        "validation_receipt_sha256": frozen.sha256(tests_path),
        "affected_original_runs": [a["run_id"] for a in proof["affected_attempts"]],
        "repair_repetitions": 1, "ordinary_semantic_retries": False,
        "preserved_substrate_source_sha256": {p: h for p, h in
                                              parent["preserved_substrate_source_sha256"].items()
                                              if p != QUOTE_PATH},
        "model_pool_changed": False, "planner_prompt_changed": False,
        "budgets_changed": False, "scheduler_changed": False,
    }
