"""Read-only post-block audit. Execute on 4090; never copy datasets to development PC."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, cast

from infra_joint.evaluation.trace_audit import summarize_concurrency, summarize_cost

CONDITIONS = ("fast-blind", "fast-aware", "slow-blind", "slow-aware")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution(event: dict[str, Any]) -> dict[str, Any]:
    value: Any = event["payload"].get("execution")
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def operator(action: dict[str, Any]) -> str:
    if action["action_type"] == "model":
        return "invoke_model"
    return str(action["operator"])


def known_sum(values: list[Any]) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(int(value) for value in values)


def audit_run(directory: Path) -> dict[str, Any]:
    results = list(directory.glob("runs/*/result.json"))
    if len(results) != 1:
        raise ValueError("expected exactly one preserved result per primary cell")
    path = results[0]
    result = json.loads(path.read_text())
    trace = path.with_name("trace.jsonl")
    events: list[dict[str, Any]] = [json.loads(line) for line in trace.read_text().splitlines()]
    prepared = [e for e in events if e["event_type"] == "logical.action.prepared"]
    operations = Counter(operator(e["payload"]["action"]) for e in prepared)
    batches = [e for e in events if e["event_type"] == "logical.batch.started"]
    first_decision = batches[0]["payload"]["decision_id"] if batches else None
    first_ids = {aid for e in batches if e["payload"]["decision_id"] == first_decision
                 for aid in e["payload"]["action_ids"]}
    physical = [e for e in events if e["event_type"] == "physical.execution"]
    first_bytes = sum(t["bytes_transferred"] for e in physical
                      if e["payload"]["action_id"] in first_ids
                      for t in execution(e).get("transfers", []))
    profiles = [e for e in events if e["event_type"] == "logical.profile.predecision"]
    manager_inputs = [e for e in events if e["event_type"] == "logical.reasoning.input"
                      and e["payload"]["logical_agent_id"] == "manager"]
    by_decision = {e["payload"]["decision_id"]: e for e in profiles}
    timing_checks: list[bool] = []
    for event in manager_inputs:
        profile = by_decision.get(event["payload"]["decision_id"])
        actual = event["payload"]["current_anonymous_profile"]
        timing_checks.append(actual is None if not profiles else (
            profile is not None and events.index(profile) < events.index(event)
            and actual == profile["payload"]["profile"]
        ))
    observations = [e for e in events if e["event_type"] == "logical.observation"]
    failures = [e for e in observations if not e["payload"].get("succeeded")]
    action_operators = {e["payload"]["action"]["action_id"]: operator(e["payload"]["action"])
                        for e in prepared}
    selected = [e for e in events if e["event_type"] == "logical.action.selected"]
    empty_graph: dict[str, Any] = {"nodes": [], "edges": []}
    graph: dict[str, Any] = next((e["payload"] for e in reversed(events)
                  if e["event_type"] == "workflow.graph.snapshot"), empty_graph)
    verifier = [e for e in events if e["event_type"] == "logical.verification"]
    diagnostics_path = path.parent / "private/observer-diagnostics.jsonl"
    diagnostics = [json.loads(line) for line in diagnostics_path.read_text().splitlines()]
    probe_errors = [p for d in diagnostics for p in d["probes"] if not p["probe_success"]]
    outcome_events = [e for e in events if e["event_type"] == "logical.model.outcome"]
    return {
        "run_id": result["run_id"], "completion": result["execution_completed"],
        "answer": result.get("final_answer"), "evaluation": result.get("evaluation"),
        "failure": result.get("failure"), "usage": result["loop"]["usage"]
        if result.get("loop") else None,
        "cost": summarize_cost(events), "concurrency": summarize_concurrency(events),
        "operations": dict(operations), "first_actions": [e for e in prepared
            if e["payload"]["action"]["action_id"] in first_ids],
        "selected_operator_counts": dict(Counter(e["payload"]["operator"] for e in selected)),
        "selected_actions": selected,
        "successful_tool_executions": sum(e["payload"].get("succeeded") is True
            and action_operators.get(e["payload"]["action_id"]) not in {None, "invoke_model"}
            for e in observations),
        "successful_model_executions": sum(e["payload"].get("succeeded") is True
            and action_operators.get(e["payload"]["action_id"]) == "invoke_model"
            for e in observations),
        "first_transfer_bytes": first_bytes,
        "profile_count": len(profiles), "manager_input_count": len(manager_inputs),
        "predecision_timing_all_pass": bool(timing_checks) and all(timing_checks),
        "profiles": profiles, "prepared_actions": prepared,
        "typed_failures": failures, "failure_counts": dict(Counter(
            e["payload"].get("failure_code") for e in failures)),
        "model_outcomes": outcome_events,
        "reported_reached_inference": sum(e["payload"].get("reached_model_inference") is True
                                          for e in outcome_events),
        "cloud_tokens": {
            "reasoning_input": known_sum([e["payload"]["telemetry"].get("input_tokens")
                for e in events if e["event_type"] == "logical.reasoning.completed"]),
            "reasoning_output": known_sum([e["payload"]["telemetry"].get("output_tokens")
                for e in events if e["event_type"] == "logical.reasoning.completed"]),
            "verifier_input": known_sum([e["payload"].get("input_tokens") for e in verifier]),
            "verifier_output": known_sum([e["payload"].get("output_tokens") for e in verifier]),
        },
        "model_service": [e for e in physical
            if execution(e).get("model_telemetry") is not None],
        "verifier_inputs": [e for e in events if e["event_type"] == "logical.verification.input"],
        "verifier_verdicts": verifier,
        "first_ready": next((e for e in verifier
            if e["payload"].get("status") == "ready_for_synthesis"), None),
        "graph_nodes": len(graph["nodes"]), "graph_edges": len(graph["edges"]),
        "graph_snapshots": sum(e["event_type"] == "workflow.graph.snapshot" for e in events),
        "final_graph": graph,
        "subagent_calls": sum(e["event_type"] == "logical.subagent.start" for e in events),
        "handoffs": sum(e["event_type"] == "logical.information.handoff" for e in events),
        "physical_selections": [e["payload"].get("selection") for e in physical],
        "physical_events": physical,  # Preserve failed-action metadata even without selection.
        "probe_error_count": len(probe_errors), "probe_errors": probe_errors,
        "validation": json.loads((directory / "lightweight-validation.json").read_text()),
        "evidence_hashes": {str(p.relative_to(directory)): sha256(p) for p in (
            path, trace, diagnostics_path, directory / "summary.json",
            directory / "tc-attestation.json", directory / "freeze/manifest.json",
        )},
    }


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Only independent run-level scalars; never pool historical runs or impute unknown."""
    groups: dict[str, Any] = {}
    for condition in CONDITIONS:
        rows = [r for r in records if r["condition"] == condition]
        quality = [r["evaluation"]["benchmark_score"] for r in rows if r["evaluation"]]
        entry: dict[str, Any] = {
            "n": len(rows), "completed": sum(r["completion"] for r in rows),
            "evaluated": len(quality),
            "mean_score_evaluated_only": mean(quality) if quality else None,
            "missing_evaluation_count": len(rows) - len(quality),
            "first_operator_signatures": [
                [operator(e["payload"]["action"]) for e in r["first_actions"]] for r in rows],
        }
        for key in ("e2e_latency_ms", "action_transfer_bytes", "action_transfer_latency_ms",
                    "model_service_latency_ms", "completed_physical_model_inferences",
                    "manager_latency_ms", "specialist_latency_ms", "verifier_latency_ms",
                    "tool_operator_latency_ms"):
            values = [r["cost"][key] for r in rows]
            known = [v for v in values if v is not None]
            entry[key] = {"individual": values, "unknown": len(values) - len(known),
                          "mean_known": mean(known) if known else None,
                          "median_known": median(known) if known else None}
        groups[condition] = entry
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    journal = [json.loads(line) for line in (args.root / "queue.jsonl").read_text().splitlines()]
    if not any(e.get("event") == "completed" and e.get("cells") == 12 for e in journal):
        raise RuntimeError("post-block audit requires completed twelve-cell queue")
    rows: list[dict[str, Any]] = []
    for repetition in (1, 2, 3):
        for condition in CONDITIONS:
            row = audit_run(args.root / "evidence" / f"matrix-r{repetition}" / condition)
            row.update(condition=condition, repetition=repetition)
            rows.append(row)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"audit_version": "predecision-raw-trace-v1", "runs": rows,
                   "conditions": aggregate(rows)}, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
