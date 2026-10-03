"""Read-only exploratory cost/decision audit. Raw inputs stay on the owning controller."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.evaluation.trace_audit import summarize_concurrency, summarize_cost


def measured_sum(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [r[key] for r in rows if isinstance(r.get(key), int | float)]
    return {"observed_sum": sum(values), "measured_receipts": len(values),
            "unknown_receipts": len(rows) - len(values),
            "complete_total": sum(values) if len(values) == len(rows) else None}


def profile_error(profile: dict[str, Any] | None, actual: float | None) -> dict[str, Any]:
    if profile is None or profile.get("source") != "empirical" or actual is None:
        return {"observed_ms": actual, "prediction_source": "unknown",
                "p50_error_ms": None, "p90_error_ms": None}
    return {"observed_ms": actual, "prediction_source": "empirical",
            "sample_count": profile["sample_count"],
            "p50_error_ms": actual - profile["p50_ms"],
            "p90_error_ms": actual - profile["p90_ms"]}


def analyze(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Scalar/structural output only; no source bodies, prompts, gold or answers."""
    reasoning = [e["payload"] for e in events
                 if e["event_type"] == "logical.method.reasoning_usage"]
    observations = [e["payload"] for e in events if e["event_type"] == "logical.observation"]
    prepared = [e["payload"] for e in events if e["event_type"] == "logical.action.prepared"]
    graphs = [e["payload"] for e in events if e["event_type"] == "workflow.graph.snapshot"]
    graph = graphs[-1] if graphs else {"nodes": [], "edges": []}
    quotes = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.created"]
    actuals = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.observed"]
    executions = {e["payload"]["action_id"]: e["payload"].get("execution") for e in events
                  if e["event_type"] == "physical.execution"}
    quote_ids = {p["quote"]["quote_id"]: p for p in quotes}
    rejected = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.rejected"]
    estimates = []
    for receipt in actuals:
        original = quote_ids[receipt["quote_id"]]
        cost = receipt["predicted_consequence"]
        movement = cost.get("movement")
        profiles = [] if movement is None else movement["empirical_transfer_receipts"]
        execution = executions.get(receipt["action_id"])
        transfers = None if execution is None else execution.get("transfers")
        supported = (transfers is not None and len(profiles) == len(transfers)
                     and all(p["source"] == "empirical" for p in profiles)
                     and receipt["actual_transfer_work_ms"] is not None)
        transfer_p50 = sum(p["p50_ms"] for p in profiles) if supported else None
        transfer_p90 = sum(p["p90_ms"] for p in profiles) if supported else None
        context = cost.get("context")
        fits = None if context is None else context["envelope_fits"]
        context_match = (None if fits is None else
                         fits if receipt["succeeded"] else
                         not fits if receipt.get("failure_code") == "context_limit_exceeded"
                         else None)
        estimates.append({
            "quote_id": receipt["quote_id"], "action_id": receipt["action_id"],
            "operator": cost["operator"], "succeeded": receipt["succeeded"],
            "failure_code": receipt.get("failure_code"),
            "effective_action_sha256": original["quote"]["action_sha256"],
            "predicted_transfer_bytes": receipt["predicted_transfer_bytes"],
            "actual_transfer_bytes": receipt["actual_transfer_bytes"],
            "transfer_bytes_error": receipt["transfer_bytes_error"],
            "configured_serialization_ms": (None if movement is None
                                             else movement["configured_serialization_ms"]),
            "actual_transfer_work_ms": receipt["actual_transfer_work_ms"],
            "empirical_transfer_profiles": profiles,
            "transfer_p50_work_estimate_ms": transfer_p50,
            "transfer_p90_work_estimate_ms": transfer_p90,
            "transfer_estimate_is_joint_quantile_or_wall_time": False,
            "transfer_p50_work_error_ms": (None if transfer_p50 is None else
                                          receipt["actual_transfer_work_ms"] - transfer_p50),
            "transfer_p90_work_error_ms": (None if transfer_p90 is None else
                                          receipt["actual_transfer_work_ms"] - transfer_p90),
            "transfer_prediction_error_unknown_reason": (
                None if supported else "unsupported profile or actual receipt count mismatch"),
            "model_service_error": profile_error(cost.get("model_service"),
                                                  receipt["actual_model_service_ms"]),
            "context_prediction": context, "context_preflight_prediction_match": context_match,
            "context_preflight_refused": receipt.get("failure_code") == "context_limit_exceeded",
        })
    managers = [p for p in reasoning if p["recipient"] == "manager"]
    specialists = [p for p in reasoning if p["recipient"] == "specialist"]
    operations = []
    for payload in prepared:
        action = payload.get("action", payload.get("logical_action", {}))
        name = action.get("operator") or ("invoke_model" if action.get("action_type") == "model"
                                           else None)
        if name:
            operations.append(name)
    return {
        "work_sums_are_nonadditive_not_e2e": True,
        "cost": summarize_cost(events), "concurrency": summarize_concurrency(events),
        "manager_calls": len(managers), "specialist_calls": len(specialists),
        "manager_input_tokens": measured_sum(managers, "input_tokens"),
        "manager_output_tokens": measured_sum(managers, "output_tokens"),
        "specialist_input_tokens": measured_sum(specialists, "input_tokens"),
        "specialist_output_tokens": measured_sum(specialists, "output_tokens"),
        "manager_work_ms": measured_sum(managers, "latency_ms"),
        "specialist_work_ms": measured_sum(specialists, "latency_ms"),
        "physical_observations": len(observations), "operator_sequence": operations,
        "failed_physical_calls": dict(Counter(p.get("failure_code") for p in observations
                                               if not p["succeeded"])),
        "graph_nodes": len(graph["nodes"]), "graph_edges": len(graph["edges"]),
        "quotes_created": len(quotes), "quoted_actions_executed": len(actuals),
        "quote_protocol_rejections": rejected,
        "quote_control_timing": [e["payload"] for e in events
                                 if e["event_type"] == "logical.cost_quote.control_timing"],
        "quote_final_accounting": [e["payload"] for e in events
                                   if e["event_type"] == "logical.cost_quote.run.end"],
        "estimated_vs_observed": estimates,
    }


def main(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise FileExistsError("append-only analysis: choose a new output file")
    events = JsonlTraceWriter(args.trace).read_all()
    value = analyze(events)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"analyzed_events": len(events),
                      "quotes_created": value["quotes_created"],
                      "quoted_actions_executed": value["quoted_actions_executed"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
