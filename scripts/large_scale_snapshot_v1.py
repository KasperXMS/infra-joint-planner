"""Read-only settled-evidence collector, never an Agent input or queue controller.

Exports bounded telemetry/structure, not prompts, corpus, gold, evaluator details,
tool outputs or raw recipient context. Does not rank/prune methods or pool scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import AttemptLedger

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")


def measured_total(values: list[Any]) -> int | float | None:
    """Empty executed populations are zero; any missing measurement stays unknown."""
    if any(not isinstance(value, int | float) or isinstance(value, bool) for value in values):
        return None
    return sum(values)


def event_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [e["payload"] for e in events if e["event_type"] == "logical.observation"]
    prepared = [e["payload"]["action"] for e in events
                if e["event_type"] == "logical.action.prepared"]
    executions = [e["payload"]["execution"] for e in events
                  if e["event_type"] == "physical.execution" and "execution" in e["payload"]]
    model = [x["model_telemetry"] for x in executions if x.get("model_telemetry") is not None]
    outcomes = [e["payload"] for e in events if e["event_type"] == "logical.model.outcome"]
    reasoning = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.completed"]
    graph = next((e["payload"] for e in reversed(events)
                  if e["event_type"] == "workflow.graph.snapshot"), None)
    comparisons = [e["payload"] for e in events
                   if e["event_type"] == "logical.cost_candidates.returned"]
    selected = [e["payload"] for e in events if e["event_type"] == "logical.action.selected"]
    quotes = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.created"]
    types = Counter(e["event_type"] for e in events)
    # SDK history receipts are deduplicated. A final-turn call lacking a subsequent
    # effective input is not invented: these are explicit lower-bound counts.
    calls: dict[tuple[str, str], str] = {}
    for event in events:
        if event["event_type"] != "logical.reasoning.input":
            continue
        p = event["payload"]
        for item in p.get("input_items", []):
            if (item.get("type") == "function_call" and isinstance(item.get("call_id"), str)
                    and isinstance(item.get("name"), str)):
                calls[p["logical_agent_id"], item["call_id"]] = item["name"]
    root_calls = Counter(name for (owner, _), name in calls.items() if owner == "manager")
    model_action_ids = {x["action_id"] for x in prepared if x["action_type"] == "model"}
    failed = [x for x in observations if not x["succeeded"]]
    return {
        "reasoning_started": {
            "manager": sum(e["event_type"] == "logical.reasoning.started"
                           and e["payload"]["logical_agent_id"] == "manager" for e in events),
            "specialist": sum(e["event_type"] == "logical.reasoning.started"
                              and e["payload"]["logical_agent_id"] != "manager" for e in events),
        },
        "reasoning_work_ms": {role: measured_total([
            p["telemetry"].get("latency_ms") for p in reasoning
            if (p["logical_agent_id"] == "manager") == (role == "manager")])
            for role in ("manager", "specialist")},
        "verifier_calls": types["logical.verification.input"],
        "verifier_work_ms": measured_total([e["payload"].get("latency_ms") for e in events
                                             if e["event_type"] == "logical.verification"]),
        "created_specialists": types["logical.subagent.start"],
        "prepared_physical_actions": len(prepared),
        "prepared_model_actions": len(model_action_ids),
        "prepared_tool_actions": sum(x["action_type"] == "tool" for x in prepared),
        "successful_model_actions": sum(x["succeeded"] and x["action_id"] in model_action_ids
                                        for x in observations),
        "successful_tool_executions": sum(x.get("operator") != "invoke_model"
                                           for x in executions),
        "reported_reached_model_inference": sum(x["reached_model_inference"] for x in outcomes),
        "successful_inference_telemetry_count": len(model),
        "model_service_work_ms": measured_total([x.get("service_latency_ms") for x in model]),
        "physical_model_input_tokens": measured_total([x.get("input_tokens") for x in model]),
        "physical_model_output_tokens": measured_total([x.get("output_tokens") for x in model]),
        "finish_reasons": dict(Counter(x.get("finish_reason", "unknown") for x in model)),
        "failure_codes": dict(Counter(x.get("failure_code", "unknown") for x in failed)),
        "operator_sequence": [x.get("operator", "invoke_model") for x in prepared],
        "selected_operator_sequence": [x["operator"] for x in selected],
        "model_requirements_classifications": dict(Counter(e["payload"]["classification"]
            for e in events if e["event_type"] == "logical.model.requirements")),
        "graph_versions": types["workflow.graph.snapshot"],
        "graph_nodes": len(graph["nodes"]) if graph is not None else None,
        "graph_edges": len(graph["edges"]) if graph is not None else None,
        "information_handoffs": types["logical.information.handoff"],
        "physical_selections": [{"action_id": e["payload"]["action_id"],
                                 "worker": e["payload"]["selection"]["selected_agent_id"],
                                 "deployment": e["payload"]["selection"].get(
                                     "selected_deployment_id")}
                                for e in events if e["event_type"] == "physical.execution"
                                and "selection" in e["payload"]],
        "method_interface": {
            "manager_function_call_receipts_lower_bound": dict(root_calls),
            "optional_query_attempts_lower_bound": sum(n for name, n in root_calls.items()
                                                        if name.startswith("estimate_")),
            "valid_optional_cards": types["logical.cost_card.returned"],
            "matched_optional_cards": types["logical.cost_card.matched"],
            "quotes": len(quotes),
            "quotes_observed": types["logical.cost_quote.observed"],
            "quote_rejection_codes": dict(Counter(e["payload"]["failure_code"] for e in events
                if e["event_type"] == "logical.cost_quote.rejected")),
            "candidate_counts": [len(p["candidates"]) for p in comparisons],
            "real_multi_candidate_comparisons": sum(len(p["candidates"]) >= 2
                                                     for p in comparisons),
            "post_comparison_choices": types["logical.cost_candidates.selected"],
            "rules_visible_inputs": types["logical.cost_rules.predecision"],
            "quote_control_work_ms": measured_total([e["payload"].get("control_work_ms")
                for e in events if e["event_type"] == "logical.cost_quote.control_timing"]),
            "rules_internal_use": "not observable",
            "eligible_high_impact_decisions": None,
            "eligibility_note": "requires readiness/owner/frontier audit, not every reasoning turn",
        },
    }


def settled_attempt(root: Path, cell_id: str, attempt: Any) -> dict[str, Any]:
    directory = root / "evidence" / cell_id / f"attempt{attempt.attempt_index}"
    admission_path = directory / "admission.json"
    admission = json.loads(admission_path.read_text())
    if (provenance_sha256(admission) != attempt.receipt_sha256
            or admission["disposition"] != attempt.disposition):
        raise RuntimeError("settled admission/ledger drift")
    result_path = directory / "runs" / attempt.run_id / "result.json"
    result = json.loads(result_path.read_text())
    if admission.get("result_sha256") is not None and hashlib.sha256(
        result_path.read_bytes()).hexdigest() != admission["result_sha256"]:
        raise RuntimeError("settled result/admission drift")
    events = [json.loads(line) for line in result_path.with_name("trace.jsonl").read_text(
        encoding="utf-8").splitlines()]
    evaluation = result.get("evaluation")
    terminal = result.get("final_answer")
    account_path = directory / "api-accounting.json"
    usage = [json.loads(path.read_text())["cost_receipt"] for path in
             (directory / "private/api").glob("*-usage.json")]
    return {
        "run_id": attempt.run_id, "attempt_index": attempt.attempt_index,
        "execution_sha256": attempt.execution_sha256,
        "disposition": attempt.disposition, "admission_reason": attempt.reason,
        "admission_problems": admission.get("problems", []),
        "execution_completed": result["execution_completed"],
        "benchmark_score": evaluation.get("benchmark_score") if evaluation else None,
        "format_valid": evaluation.get("format_valid") if evaluation else None,
        "terminal_answer_sha256": hashlib.sha256(terminal.encode()).hexdigest()
        if terminal is not None else None,
        "terminal_answer_bytes": len(terminal.encode()) if terminal is not None else None,
        "terminal_failure_code": (result.get("failure") or {}).get("code"),
        "terminal_exception_type": (result.get("failure") or {}).get("exception_type"),
        "telemetry": result.get("telemetry"),
        "loop_usage": result["loop"].get("usage") if result.get("loop") else None,
        "api_accounting": json.loads(account_path.read_text()) if account_path.exists() else None,
        "api_tokens_by_recipient": {
            role: {key: measured_total([row["cost"]["usage"].get(key) for row in usage
                                       if role == "all" or row["recipient"] == role])
                   for key in ("input_tokens", "output_tokens", "cached_input_tokens",
                               "reasoning_output_tokens")}
            for role in ("manager", "specialist", "verifier", "all")},
        "trace_metrics": event_metrics(events),
    }


def snapshot(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / "preparation/task-freeze-002/manifest.json").read_text())
    schedule = json.loads((root / "preparation/task-freeze-002/phase1-schedule.json").read_text())
    cell_ids = tuple(row["cell_id"] for row in schedule)
    if not (root / "phase1-attempts.jsonl").is_file():
        raise RuntimeError("read-only collector cannot initialize a missing attempt ledger")
    ledger = AttemptLedger(root / "phase1-attempts.jsonl", cell_ids,
                           manifest["phase1_schedule_sha256"])
    attempts = ledger.attempts
    rows = []
    for cell in schedule:
        matched = [x for x in attempts if x.cell_id == cell["cell_id"]]
        rows.append({"condition": cell,
                     "attempts": [settled_attempt(root, cell["cell_id"], x) for x in matched
                                  if x.disposition is not None],
                     "pending_run_ids": [x.run_id for x in matched if x.disposition is None]})
    return {"version": "large-scale-settled-telemetry-v1", "scheduled_cells": len(cell_ids),
            "admitted_cells": len(ledger.completed_cells), "attempt_count": len(attempts),
            "pending_count": len(ledger.pending),
            "confounded_attempts": sum(x.disposition == "confounder" for x in attempts),
            "operational_excluded_attempts": sum(x.disposition == "operational_excluded"
                                                 for x in attempts),
            "phase1_complete": len(ledger.completed_cells) == len(cell_ids),
            "method_pruning_authorized": False, "score_aggregation": "not performed",
            "source_payload_exported": False, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if (sys.platform != "linux" or arguments.root.resolve() != ROOT
            or arguments.output.resolve().parent != ROOT / "analysis"):
        raise RuntimeError("analysis and evidence remain remote in the isolated namespace")
    value = snapshot(arguments.root)
    arguments.output.parent.mkdir(exist_ok=True)
    with arguments.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
    print(json.dumps({key: item for key, item in value.items() if key != "rows"}))
