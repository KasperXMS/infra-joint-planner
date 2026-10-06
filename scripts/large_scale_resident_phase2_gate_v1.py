"""Offline evidence gate, not an Agent policy or a measured runtime change.

The pure schedule constructor checks digest syntax, not actual audit completion.
This external entrypoint verifies real source-bound reports before freezing the
held-out schedule. It never chooses surviving methods or launches executions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import large_scale_resident_cardinality_private_evidence_v1 as evidence

from infra_joint.experiments.large_scale_protocol import (
    METHODS,
    Method,
    PhaseOneGate,
    SelectedTask,
    phase_one_schedule,
    phase_two_schedule,
    schedule_sha256,
)

FAILURES = {
    "semantic_reasoning_failure", "retrieval_failure", "evidence_selection_failure",
    "semantic_coverage_loss", "verifier_failure", "stopping_over_expansion",
    "context_recovery", "budget_exhaustion", "provider_failure", "physical_runtime_failure",
    "observer_failure", "serialization_evaluator_failure", "privacy_violation", "mixed",
}
CHECKS = ("semantic_review_complete", "failure_review_complete",
          "recipient_review_complete", "adoption_review_complete")
REPORTS = {"phase1_results", "phase1_failure_audit", "phase1_semantic_audit",
           "phase1_adoption_audit", "phase1_method_screening", "phase1_method_pruning"}
PRUNING_BASES = {"interface_unused", "dominant_intrinsic_overhead", "quality_regression",
                 "mechanism_not_exercised", "diagnostic_only"}
PRIOR_SUBSTANTIVE_CELLS = 42


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed(rows: list[dict[str, Any]], expected: set[str]) -> dict[str, dict[str, Any]]:
    result = {r["cell_id"]: r for r in rows}
    if len(result) != len(rows) or set(result) != expected:
        raise RuntimeError("audit requires exactly one record per effective PhaseI cell")
    return result


def validate_bundle(
    snapshot: dict[str, Any], private: dict[str, Any], audit: dict[str, Any],
    pruning: dict[str, Any], selection: dict[str, Any],
    hashes: dict[str, str], bindings: dict[str, dict[str, str]],
    reports: dict[str, str],
) -> dict[str, Any]:
    """Validate actual audit membership/proofs, not a 64-character placeholder.

    `hashes`, `bindings` and `reports` are computed by the file-owning offline
    caller. No user-supplied digest is accepted as its own evidence.
    """
    selected = evidence.source_bound_membership(snapshot)
    if (audit.get("version") != "resident-comprehensive-phase1-audit-v1"
            or audit.get("complete") is not True
            or audit.get("unresolved_confounders") != []
            or audit.get("journal_sha256") != snapshot["journal_sha256"]
            or audit.get("execution_freezes") != snapshot["execution_freezes"]
            or audit.get("source_projection_sha256") != hashes["snapshot"]
            or audit.get("private_evidence_sha256") != hashes["private"]):
        raise RuntimeError("PhaseII requires a completed source-bound comprehensive audit")
    if (private.get("version") != "resident-cardinality-private-evidence-paths-v1"
            or private.get("journal_sha256") != snapshot["journal_sha256"]
            or private.get("execution_freezes") != snapshot["execution_freezes"]
            or private.get("planner_or_model_calls") != 0
            or private.get("artifact_bodies_exported") is not False
            or private.get("measured_execution_modified") is not False):
        raise RuntimeError("private evidence must come from the verified offline path")
    expected = {r["condition"]["cell_id"] for r, _ in selected}
    reviews = indexed(audit["records"], expected)
    coverage = indexed(private["records"], expected)
    if (set(bindings) != expected or set(reports) != REPORTS
            or audit.get("report_file_sha256") != reports):
        raise RuntimeError("real per-run evidence and all six complete reports required")
    runs = set()
    for row, attempt in selected:
        cell_id = row["condition"]["cell_id"]
        review, support = reviews[cell_id], coverage[cell_id]
        runs.add(attempt["run_id"])
        if (any(review.get(k) is not True for k in CHECKS)
                or not isinstance(review.get("semantic_summary"), str)
                or not review["semantic_summary"].strip()
                or review.get("run_id") != attempt["run_id"]
                or support.get("run_id") != attempt["run_id"]
                or review.get("execution_sha256") != attempt["execution_sha256"]
                or support.get("execution_sha256") != attempt["execution_sha256"]
                or support.get("execution_source_boundary")
                != attempt["execution_source_boundary"]
                or support.get("benchmark_score") != attempt["benchmark_score"]
                or review.get("evidence_file_sha256") != bindings[cell_id]
                or review.get("recipient_contexts_audited")
                != attempt["actual_recipient_contexts_audited"]
                or bindings[cell_id]["trace"] != attempt["trace_file_sha256"]):
            raise RuntimeError("per-run semantic/failure/recipient/adoption review incomplete")
        primary = review.get("primary_cause")
        correct = (attempt["execution_completed"] is True
                   and attempt["format_valid"] is True
                   and attempt["benchmark_score"] == 1)
        if primary not in FAILURES | {"not_applicable"} or (
                primary == "not_applicable" and not correct):
            raise RuntimeError("all nominal failures require an explicit audited primary cause")
        if any(c not in FAILURES for c in review.get("contributing_factors", [])):
            raise RuntimeError("unknown failure taxonomy cannot satisfy the audit gate")
    if (pruning.get("version") != "resident-phase1-method-pruning-v1"
            or pruning.get("comprehensive_audit_sha256") != hashes["audit"]
            or pruning.get("journal_sha256") != snapshot["journal_sha256"]
            or pruning.get("prior_substantive_cells") != PRIOR_SUBSTANTIVE_CELLS
            or pruning.get("frozen") is not True):
        raise RuntimeError("pruning must be frozen after this actual comprehensive audit")
    entries = {r["method"]: r for r in pruning["methods"]}
    if len(pruning["methods"]) != 7 or set(entries) != set(METHODS):
        raise RuntimeError("all seven PhaseI methods require explicit screening decisions")
    survivors: list[Method] = []
    for method in METHODS:
        entry = entries[method]
        status = entry.get("status")
        if (status not in {"retain", "drop", "diagnostic_only"}
                or not isinstance(entry.get("rationale"), str)
                or not entry["rationale"].strip()
                or not entry.get("supporting_run_ids")
                or not set(entry["supporting_run_ids"]).issubset(runs)):
            raise RuntimeError("screening decisions need actual PhaseI evidence and rationale")
        if status == "retain":
            survivors.append(method)
        elif not set(entry.get("bases", [])).intersection(PRUNING_BASES):
            raise RuntimeError("E2E alone is not a permitted pruning basis")
    tasks = tuple(SelectedTask(r["family"], r["source_task_id"], r["position"])
                  for r in selection["tasks"])
    history = tuple((f, s) for f, s in selection["e_history_task_identities"])
    phase1 = phase_one_schedule(tasks, e_history_tasks=history, seed=selection["schedule_seed"])
    if ({c.cell_id for c in phase1} != expected
            or schedule_sha256(phase1) != selection["phase1_schedule_sha256"]):
        raise RuntimeError("audit is not for the original frozen PhaseI task schedule")
    cells = phase_two_schedule(
        tasks, methods=survivors,
        gate=PhaseOneGate(selection["phase1_schedule_sha256"], tuple(sorted(expected)),
                          hashes["audit"]),
        e_history_tasks=history, pruning_manifest_sha256=hashes["pruning"],
        seed=selection["schedule_seed"], prior_substantive_cells=PRIOR_SUBSTANTIVE_CELLS,
    )
    return {
        "version": "resident-phase2-evidence-gate-v1", "methods": survivors,
        "phase1_effective_cells": 168, "phase2_cells": len(cells),
        "prior_substantive_cells": PRIOR_SUBSTANTIVE_CELLS,
        "planned_cumulative_substantive_cells": PRIOR_SUBSTANTIVE_CELLS + 168 + len(cells),
        "journal_sha256": snapshot["journal_sha256"],
        "execution_freezes": snapshot["execution_freezes"],
        "phase2_execution_sha256": snapshot["execution_freezes"]["3"],
        "input_file_sha256": hashes, "report_file_sha256": reports,
        "schedule_seed": selection["schedule_seed"],
        "phase2_schedule_sha256": schedule_sha256(cells),
        "schedule": [{"cell_id": c.cell_id, **asdict(c)} for c in cells],
        "measured_execution_modified": False, "queue_launched": False,
        "planner_or_model_calls": 0,
    }


def freeze_gate(paths: dict[str, Path], output: Path) -> dict[str, Any]:
    private = evidence.private
    root = private.ROOT
    private.assert_inactive(root)
    if (sys.platform != "linux" or output.exists() or output.is_symlink()
            or output.resolve().parent != root / "analysis"
            or set(paths) != {"snapshot", "private", "audit", "pruning"}
            or any(p.is_symlink() or p.resolve().parent != root / "analysis"
                   for p in paths.values()) or len(set(paths.values())) != 4):
        raise RuntimeError("actual evidence gate stays append-only inside4090 analysis")
    hashes = {k: digest(p) for k, p in paths.items()}
    values = {k: json.loads(p.read_text()) for k, p in paths.items()}
    current = evidence.sources.collect()
    # Recollect actual journal/admissions/source proofs; timestamps alone differ.
    if {k: v for k, v in current.items() if k != "captured_utc"} != {
            k: v for k, v in values["snapshot"].items() if k != "captured_utc"}:
        raise RuntimeError("supplied source projection is stale or fabricated")
    selected = evidence.source_bound_membership(current)
    expected_sources = {Path(p).name: digest(Path(p)) for p in (
        evidence.__file__, private.__file__,
        sys.modules[evidence.resolved_membership.__module__].__file__,
        sys.modules[private.scan_store.__module__].__file__,
    )}
    excluded = [a["run_id"] for row in current["rows"] for a in row["attempts"]
                if a["disposition"] != "valid"]
    if (values["private"].get("audit_source_sha256") != expected_sources
            or values["private"].get("excluded_historical_run_ids") != excluded):
        raise RuntimeError("private audit source or excluded historical membership changed")
    bindings = {}
    for row, attempt in selected:
        directory = root / "evidence" / row["condition"]["cell_id"] / (
            "attempt" + str(attempt["attempt_index"]))
        run = directory / "runs" / attempt["run_id"]
        if json.loads((directory / "worker-shutdown.json").read_text())[
                "verified_exited"] is not True:
            raise RuntimeError("effective Worker exit must be verified before PhaseII")
        bindings[row["condition"]["cell_id"]] = {
            "result": digest(run / "result.json"), "trace": digest(run / "trace.jsonl"),
            "admission": digest(directory / "admission.json"),
            "worker_shutdown": digest(directory / "worker-shutdown.json"),
        }
    report_refs = values["audit"]["report_files"]
    reports = {}
    for name, ref in report_refs.items():
        path = root / "analysis" / ref["filename"]
        if (path.is_symlink() or path.resolve().parent != root / "analysis"
                or path.suffix != ".md" or digest(path) != ref["sha256"]):
            raise RuntimeError("missing or changed actual analysis report")
        reports[name] = digest(path)
    manifest = private.PREDECESSOR / "preparation/task-freeze-002/manifest.json"
    if digest(manifest) != evidence.sources.resident.TASK_FREEZE_SHA256:
        raise RuntimeError("original eighteen-task selection changed")
    value = validate_bundle(values["snapshot"], values["private"], values["audit"],
                            values["pruning"], json.loads(manifest.read_text()),
                            hashes, bindings, reports)
    private.assert_inactive(root)
    if (private.sha256(root / "phase1-attempts.jsonl") != current["journal_sha256"]
            or any(digest(p) != hashes[k] for k, p in paths.items())
            or any(digest(root / "analysis" / report_refs[n]["filename"]) != d
                   for n, d in reports.items())):
        raise RuntimeError("audit inputs changed during gate construction")
    value["task_selection_file_sha256"] = digest(manifest)
    value["gate_source_sha256"] = digest(Path(__file__))
    with output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "private", "audit", "pruning", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    inputs = {n: getattr(args, n) for n in ("snapshot", "private", "audit", "pruning")}
    receipt = freeze_gate(inputs, args.output)
    print(json.dumps({k: v for k, v in receipt.items() if k != "schedule"}))
