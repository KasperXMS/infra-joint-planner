"""Read-only cross-benchmark audit. Dataset bodies and traces stay on the 4090."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from blind_3family_validation_v1 import _sha256, _yaml
from predecision_crossbenchmark_v1 import CONDITIONS, summarize_run_trace
from run_predecision_matrix_v1 import write_new

from infra_joint.control.native_agents import _deterministic_terminal_answer
from infra_joint.control.provenance import provenance_sha256
from infra_joint.core.task import OutputContract
from infra_joint.evaluation.trace import JsonlTraceWriter


def action_operator(action: dict[str, Any]) -> str:
    return "invoke_model" if action["action_type"] == "model" else action["operator"]


def effective_attempt(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Quality is not an eligibility gate; operationally confounded attempts are retained."""
    clean = [r for r in records if not r["validation"]["problems"]
             and not r["probe_errors"] and r["persistence"]["pass"]
             and r["provenance"]["pass"] and r["summary"]["logical_privacy_pass"]
             and r["terminal_answer_provenance_pass"] is not False]
    if len(clean) > 1:
        raise ValueError("multiple clean attempts for one n=1 cell require protocol audit")
    return clean[0] if clean else None


def provenance_checks(events: list[dict[str, Any]], visibility: str) -> dict[str, Any]:
    profiles = {e["payload"]["decision_id"]: (i, e["payload"]["profile"])
                for i, e in enumerate(events) if e["event_type"] == "logical.profile.predecision"}
    failures = []
    manager_count = verifier_count = 0
    for i, event in enumerate(events):
        payload = event["payload"]
        if event["event_type"] == "logical.reasoning.input":
            if provenance_sha256(payload["input_items"]) != payload["input_sha256"]:
                failures.append("reasoning input hash mismatch")
            if payload["logical_agent_id"] == "manager":
                manager_count += 1
                before = profiles.get(payload["decision_id"])
                actual = payload["current_anonymous_profile"]
                if visibility == "aware":
                    if before is None or before[0] >= i or before[1] != actual:
                        failures.append("Aware profile timing/input mismatch")
                elif before is not None or actual is not None:
                    failures.append("Blind dynamic profile leakage")
        if event["event_type"] == "logical.verification.input":
            verifier_count += 1
            if provenance_sha256(payload["context"]) != payload["context_sha256"]:
                failures.append("Verifier context hash mismatch")
            context = json.dumps(payload["context"])
            if '"physical_profile": {' in context or "network_class" in context:
                failures.append("Verifier profile leakage")
    if not manager_count:
        failures.append("no actual Manager input provenance")
    return {"manager_inputs": manager_count, "verifier_inputs": verifier_count,
            "profiles": len(profiles), "failures": sorted(set(failures)), "pass": not failures}


def audit_cell(directory: Path) -> dict[str, Any]:
    paths = list(directory.glob("runs/*/result.json"))
    if len(paths) != 1:
        raise ValueError("one result required for an auditable attempt")
    path = paths[0]
    result = json.loads(path.read_text())
    trace = path.with_name("trace.jsonl")
    events = JsonlTraceWriter(trace).read_all()
    freeze = json.loads((directory / "freeze/manifest.json").read_text())
    summary = summarize_run_trace(trace)
    actions = [e["payload"]["action"] for e in events
               if e["event_type"] == "logical.action.prepared"]
    batches = [e["payload"] for e in events if e["event_type"] == "logical.batch.started"]
    first_decision = batches[0]["decision_id"] if batches else None
    first_ids = {a for b in batches if b["decision_id"] == first_decision for a in b["action_ids"]}
    failures = [e["payload"] for e in events
                if e["event_type"] == "logical.observation" and not e["payload"]["succeeded"]]
    physical = [e["payload"] for e in events if e["event_type"] == "physical.execution"]
    selections = [p["selection"] for p in physical if p.get("selection") is not None]
    model_service = [p for p in physical if p.get("execution") is not None
                     and p["execution"].get("model_telemetry") is not None]
    produced = {a["artifact_id"]: a for e in events if e["event_type"] == "logical.observation"
                for a in e["payload"].get("produced_information", [])}
    initial = {a["artifact_id"]: a for a in freeze["task_view"]["artifacts"]}
    sizes = {a: v["size_bytes"] for a, v in {**initial, **produced}.items()}
    model_actions = [a for a in actions if a["action_type"] == "model"]
    terminal_id = result.get("loop", {}).get("terminal_action_id") if result.get("loop") else None
    final = (next((a for a in model_actions if a["action_id"] == terminal_id), None)
             if terminal_id else (model_actions[-1] if model_actions else None))
    final_inputs = final["inputs"] if final else []
    input_size = (sum(sizes[a] for a in final_inputs)
                  if all(a in sizes for a in final_inputs) else None)
    diagnostics_path = path.parent / "private/observer-diagnostics.jsonl"
    diagnostics = JsonlTraceWriter(diagnostics_path).read_all()
    probes = [p for d in diagnostics for p in d["probes"]]
    snapshots = [e["payload"] for e in events if e["event_type"] == "workflow.graph.snapshot"]
    verification = [e["payload"] for e in events if e["event_type"] == "logical.verification"]
    observation_by_id = {e["payload"]["action_id"]: e["payload"] for e in events
                         if e["event_type"] == "logical.observation"}
    terminal = observation_by_id.get(terminal_id)
    terminal_matches = (None if not result["execution_completed"] else
                        terminal is not None and terminal["succeeded"]
                        and terminal["owner_agent_id"] == "manager"
                        and _deterministic_terminal_answer(
                            OutputContract.model_validate(
                                freeze["task_view"]["output_contract"], by_name=True,
                            ),
                            terminal["output"].get("text", ""),
                        ) == result["final_answer"])
    sampling_actions = [a for a in actions if action_operator(a) == "sample_frames"]
    sampled_outputs = [a for action in sampling_actions
                       for a in observation_by_id.get(action["action_id"], {}).get(
                           "produced_information", [])]
    sheet_actions = [a for a in actions if action_operator(a) == "make_contact_sheet"]
    metadata = [a.get("content_schema") or {} for a in initial.values()]
    workload = {
        "raw_input_bytes": sum(a["size_bytes"] for a in initial.values()),
        "source_context_bytes": None,
        "distributed_sources": len(set(freeze["initial_placement"].values())),
        "initial_artifacts": len(initial), "input_modalities": sorted({
            a["media_type"] for a in initial.values()}),
        "document_count": len(initial) if freeze["task_label"].startswith("longbench") else None,
        "video_durations_seconds": [m["duration_seconds"] for m in metadata
                                    if m.get("duration_seconds") is not None],
        "codecs": sorted({m["codec"] for m in metadata if m.get("codec")}),
        "sampled_frames": len(sampled_outputs),
        "contact_sheet_input_frame_count": sum(len(a["inputs"]) for a in sheet_actions),
        "final_model_artifact_input_bytes": input_size,
        "final_model_prompt_bytes": len(final["prompt"].encode()) if final else None,
        "final_model_is_successful_terminal": terminal_id is not None,
        "final_input_to_raw_byte_ratio": (
            input_size / sum(a["size_bytes"] for a in initial.values())
            if input_size is not None else None
        ),
    }
    return {
        "attempt": directory.name,
        "attempt_evidence_directory": str(directory),
        "run_id": result["run_id"], "task_label": freeze["task_label"],
        "task_id": result["task_id"], "benchmark": result["benchmark_id"],
        "condition": freeze["network_regime"] + "-" + freeze["profile_visibility"],
        "completed": result["execution_completed"], "answer": result["final_answer"],
        "evaluation": result["evaluation"], "failure": result["failure"],
        "code_revision": freeze["code_revision"],
        "harness_sha256": freeze["harness_manifest_sha256"],
        "task_bundle_sha256": freeze["task_bundle_sha256"],
        "capability_sha256": freeze["static_capability_contract_sha256"],
        "initial_placement": freeze["initial_placement"], "workload": workload,
        "summary": summary, "operation_counts": dict(Counter(action_operator(a) for a in actions)),
        "first_actions": [action_operator(a) for a in actions if a["action_id"] in first_ids],
        "failure_counts": dict(Counter(f["failure_code"] for f in failures)),
        "typed_failures": failures, "physical_selections": selections,
        "model_service": model_service, "graph_snapshots": snapshots,
        "verifier_statuses": [v["status"] for v in verification],
        "first_ready": next(
            (v for v in verification if v["status"] == "ready_for_synthesis"), None
        ),
        "terminal_answer_provenance_pass": terminal_matches,
        "provenance": provenance_checks(events, freeze["profile_visibility"]),
        "probe_count": len(probes), "probe_errors": [p for p in probes if not p["probe_success"]],
        "validation": json.loads((directory / "lightweight-validation.json").read_text()),
        "persistence": json.loads((directory / "private/artifact-persistence.json").read_text()),
        "evidence_hashes": {str(p.relative_to(directory)): _sha256(p) for p in (
            path, trace, diagnostics_path, directory / "tc-attestation.json",
            directory / "freeze/manifest.json", directory / "summary.json",
        )},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--previous-root", type=Path, action="append", default=[])
    parser.add_argument("--protocol", type=Path)
    args = parser.parse_args()
    protocol = _yaml(args.protocol or (
        args.root / "app/configs/experiments/predecision-crossbenchmark-v1.yaml"
    ))
    roots = [*args.previous_root, args.root]
    if len(set(roots)) != len(roots):
        raise ValueError("duplicate audit roots")
    records = []
    attempts = []
    effective = []
    missing = []
    unresolved = []
    for row in protocol["tasks"]:
        for condition in CONDITIONS:
            cell = f"{row['label']}-{condition}"
            cell_attempts = [audit_cell(root / "evidence" / cell / attempt)
                             for root in roots for attempt in (
                                 "primary", "operational-replacement-1", "transport-patch-1",
                             ) if (root / "evidence" / cell / attempt
                                   / "lightweight-validation.json").exists()]
            attempts.extend(cell_attempts)
            primary = next((r for r in cell_attempts if r["attempt"] == "primary"), None)
            if primary is None:
                missing.append(cell)
            else:
                records.append(primary)
            selected = effective_attempt(cell_attempts)
            if selected is None:
                unresolved.append(cell)
            else:
                effective.append(selected)
    if args.require_complete and (missing or unresolved):
        raise RuntimeError(f"matrix incomplete or confounded: {unresolved}")
    write_new(args.output, {"audit_source_sha256": _sha256(Path(__file__)),
                            "scope_roots": [str(root) for root in roots],
                            "records": records, "attempt_records": attempts,
                            "effective_records": effective,
                            "missing_primary_cells": missing, "unresolved_cells": unresolved})
    print(json.dumps({"audited_primary_cells": len(records), "audited_attempts": len(attempts),
                      "clean_cells": len(effective), "unresolved": len(unresolved)}))


if __name__ == "__main__":
    main()
