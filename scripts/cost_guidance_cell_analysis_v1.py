"""Read-only exploratory cost/decision audit. Raw inputs stay on the owning controller."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

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


def _action_metadata(action: dict[str, Any]) -> dict[str, Any]:
    """Do not export prompts, queries, artifact contents or arbitrary arguments."""
    prompt = action.get("prompt")
    arguments = action.get("arguments", {})
    return {
        "action_id": action.get("action_id"),
        "operator": action.get("operator", "invoke_model"),
        "input_artifact_ids": action.get("inputs", []),
        "output_artifact_ids": [o["artifact_id"] for o in action.get("outputs", [])],
        "prompt_bytes": len(prompt.encode("utf-8")) if isinstance(prompt, str) else None,
        "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest()
        if isinstance(prompt, str) else None,
        "retrieval_top_k": arguments.get("top_k")
        if isinstance(arguments.get("top_k"), int) else None,
        "requirements": action.get("requirements"),
    }


def quote_decision_audit(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prove available feedback, not that the Agent used it or its causal effect.

    Only an exact structured function-tool result in an actual Manager input
    counts as quote visibility. A text mention, planned input or child input does
    not. Exposure after consumption/discard is not pre-decision exposure.
    """
    created: dict[str, dict[str, Any]] = {}
    input_receipts: dict[str, list[dict[str, Any]]] = {}
    lifecycle: dict[str, list[dict[str, Any]]] = {}
    observed: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        kind, payload = event["event_type"], event["payload"]
        if kind == "logical.cost_quote.created":
            identifier = payload["quote"]["quote_id"]
            if identifier in created:
                raise ValueError("duplicate created quote identifier")
            created[identifier] = {"index": index, "payload": payload}
            input_receipts[identifier] = []
            lifecycle[identifier] = []
        elif kind == "logical.reasoning.input" and payload.get("logical_agent_id") == "manager":
            seen: set[str] = set()
            for item in payload.get("input_items", []):
                if item.get("type") != "function_call_output":
                    continue
                output = item.get("output")
                if not isinstance(output, str):
                    continue
                try:
                    value = json.loads(output)
                except json.JSONDecodeError:
                    continue
                if not isinstance(value, dict):
                    continue
                identifier = cast(dict[str, Any], value).get("quote_id")
                if (not isinstance(identifier, str) or identifier not in created
                        or identifier in seen):
                    continue
                original = created[identifier]["payload"]["quote"]
                # Verifiable complete card equality, not an opaque-ID substring.
                if value != original:
                    continue
                seen.add(identifier)
                input_receipts[identifier].append({
                    "event_index": index, "decision_id": payload.get("decision_id"),
                    "input_sha256": payload.get("input_sha256"),
                })
        elif kind in {"logical.cost_quote.commit_authorized", "logical.cost_quote.discarded"}:
            identifier = payload["quote_id"]
            if identifier not in created:
                raise ValueError("quote lifecycle has no creation receipt")
            lifecycle[identifier].append({
                "event_index": index,
                "operation": ("authorize_commit" if kind.endswith("commit_authorized")
                              else "discard"),
                "age_ms": payload.get("age_ms"),
            })
        elif kind == "logical.cost_quote.observed":
            identifier = payload["quote_id"]
            if identifier not in created or identifier in observed:
                raise ValueError("quote execution lacks a unique creation receipt")
            observed[identifier] = {"event_index": index, "payload": payload}

    rows: list[dict[str, Any]] = []
    for identifier, record in created.items():
        transitions = lifecycle[identifier]
        execution = observed.get(identifier)
        first_decision = transitions[0]["event_index"] if transitions else len(events)
        before = [r for r in input_receipts[identifier]
                  if record["index"] < r["event_index"] < first_decision]
        quote = record["payload"]["quote"]
        consequence = quote.get("consequence")
        if execution is not None:
            state = "consumed"
        elif any(t["operation"] == "discard" for t in transitions):
            state = "discarded"
        elif transitions:
            state = "authorized_without_execution_receipt"
        else:
            state = "pending"
        observed_payload = execution["payload"] if execution is not None else None
        rows.append({
            "quote_id": identifier, "action_sha256": quote["action_sha256"],
            "creation_event_index": record["index"], "state": state,
            "action": _action_metadata(record["payload"]["action"]),
            "consequence": consequence,
            "manager_inputs_before_first_commit_or_discard": before,
            "exact_card_visible_before_decision": bool(before),
            "transitions": transitions,
            "execution_succeeded": (None if observed_payload is None
                                    else observed_payload["succeeded"]),
            "execution_failure_code": None if observed_payload is None
            else observed_payload.get("failure_code"),
            "committed_despite_known_selection_failure": bool(
                transitions and transitions[0]["operation"] == "authorize_commit"
                and consequence is not None
                and consequence.get("physical_selection_succeeded") is False),
            "visibility_proves_causal_use": False,
            "provider_private_reasoning_available": False,
        })
    return rows


def model_evidence_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Separate artifact-backed inference from prompt-only completion.

    No claim about semantic evidence adequacy or where prompt knowledge came
    from follows from artifact counts. This is a trace-path diagnostic only.
    """
    actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"]
               for e in events if e["event_type"] == "logical.action.prepared"}
    successes = {e["payload"]["action_id"] for e in events
                 if e["event_type"] == "logical.observation" and e["payload"]["succeeded"]}
    outcomes = {e["payload"]["action_id"]: e["payload"] for e in events
                if e["event_type"] == "logical.model.outcome"}
    reached = {identifier for identifier, value in outcomes.items()
               if value.get("reached_model_inference") is True}
    missing = [identifier for identifier, action in actions.items()
               if action.get("action_type") == "model" and identifier in successes
               and outcomes.get(identifier, {}).get("reached_model_inference") is None]
    inference_actions = [_action_metadata(actions[identifier]) for identifier in sorted(reached)
                         if identifier in actions and identifier in successes]
    terminals = [e["payload"]["source_action_id"] for e in events
                 if e["event_type"] == "logical.terminal.candidate_selected"]
    terminal = actions.get(terminals[-1]) if terminals else None
    terminal_model = (terminal if terminal is not None
                      and terminal.get("action_type") == "model" else None)
    reads = [identifier for identifier, action in actions.items()
             if action.get("operator") == "read_artifact" and identifier in successes]
    return {
        "successful_inferences": inference_actions,
        "successful_read_artifact_action_ids": reads,
        "terminal_model_action": None if terminal_model is None
        else _action_metadata(terminal_model),
        "terminal_model_has_artifact_inputs": None if terminal_model is None
        else bool(terminal_model.get("inputs")),
        "successful_inferences_missing_outcome_receipts": missing,
        "successful_inference_artifact_input_count": None if missing else sum(
            len(a["input_artifact_ids"]) for a in inference_actions),
        "counts_establish_semantic_adequacy": False,
        "prompt_knowledge_provenance_inferred": False,
    }


def analyze(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Scalar/structural output only; no source bodies, prompts, gold or answers."""
    reasoning = [e["payload"] for e in events
                 if e["event_type"] == "logical.method.reasoning_usage"]
    observations = [e["payload"] for e in events if e["event_type"] == "logical.observation"]
    prepared = [e["payload"] for e in events if e["event_type"] == "logical.action.prepared"]
    graphs = [e["payload"] for e in events if e["event_type"] == "workflow.graph.snapshot"]
    graph: dict[str, Any] = graphs[-1] if graphs else {"nodes": [], "edges": []}
    quotes = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.created"]
    actuals = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.observed"]
    executions = {e["payload"]["action_id"]: e["payload"].get("execution") for e in events
                  if e["event_type"] == "physical.execution"}
    quote_ids = {p["quote"]["quote_id"]: p for p in quotes}
    rejected = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.rejected"]
    estimates: list[dict[str, Any]] = []
    for receipt in actuals:
        original = quote_ids[receipt["quote_id"]]
        cost = receipt["predicted_consequence"]
        movement = cost.get("movement")
        profiles: list[dict[str, Any]] = (
            [] if movement is None else movement["empirical_transfer_receipts"])
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
    operations: list[str] = []
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
        "quote_decisions": quote_decision_audit(events),
        "model_evidence_path": model_evidence_audit(events),
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
