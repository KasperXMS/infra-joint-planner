"""Read-only settled-evidence collector, never an Agent input or queue controller.

Exports bounded telemetry/structure, not prompts, corpus, gold, evaluator details,
tool outputs or raw recipient context. Does not rank/prune methods or pool scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from large_scale_provider_policy_review_v1 import (
    ClassifiedAttemptLedger,
    effective_admission,
)

from infra_joint.control.provenance import provenance_sha256

ROOT = Path("/home/super/xiaoming/large-scale-cost-guidance-v1")


class SnapshotAttemptLedger(ClassifiedAttemptLedger):
    """Check effective evidence once per membership calculation, not per cell.

    Journal replay still uses the independently verified admission view. This
    only removes the base property's repeated proof checks inside its cell loop;
    no cached/unverified admission is introduced.
    """

    @property
    def completed_cells(self) -> tuple[str, ...]:
        admitted = {item.cell_id for item in self.attempts if item.disposition == "valid"}
        return tuple(cell for cell in self.cells if cell in admitted)


def measured_total(values: list[Any]) -> int | float | None:
    """Empty executed populations are zero; any missing measurement stays unknown."""
    if any(not isinstance(value, int | float) or isinstance(value, bool) for value in values):
        return None
    return sum(values)


def trace_cost_receipts(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Project actual persisted receipts, never infer missing work from elapsed time.

    Keep this separate from the original result telemetry. Failed execution can
    have unmeasured movement/service; successful receipt sums are then incomplete.
    """
    endings = [e["payload"] for e in events if e["event_type"] in {"run.end", "run.failed"}]
    if len(endings) > 1:
        raise RuntimeError("multiple run endings cannot yield unambiguous recorded E2E")

    def total(values: list[Any]) -> int | float | None:
        if any(not isinstance(v, int | float) or isinstance(v, bool)
               or not math.isfinite(v) or v < 0 for v in values):
            return None
        return sum(values)

    initial = [e["payload"] for e in events if e["event_type"] == "artifact.materialize.end"]
    prepared_actions = {e["payload"]["action"]["action_id"]: e["payload"]["action"] for e in events
                        if e["event_type"] == "logical.action.prepared"}
    prepared = set(prepared_actions)
    physical = [e["payload"] for e in events if e["event_type"] == "physical.execution"]
    if len(physical) != len({p["action_id"] for p in physical}):
        raise RuntimeError("duplicate physical receipt cannot be summed as independent work")
    missing = prepared - {p["action_id"] for p in physical}
    executions = [p["execution"] for p in physical if p.get("execution")]
    tool_executions = [p["execution"] for p in physical if p.get("execution")
                       and prepared_actions.get(p["action_id"], {}).get("action_type") == "tool"]
    model_executions = [p["execution"] for p in physical if p.get("execution")
                        and prepared_actions.get(p["action_id"], {}).get("action_type") == "model"]
    unknown_execution_kind = len(executions) - len(tool_executions) - len(model_executions)
    uncertain_tool_work = any(
        prepared_actions.get(p["action_id"], {}).get("action_type") == "tool"
        and not p.get("execution")
        and (not p.get("failure") or p["failure"].get("stage") != "selection") for p in physical)
    uncertain_tool_work |= any(
        prepared_actions[aid].get("action_type") == "tool" for aid in missing)
    tool_work = total([p.get("operator_latency_ms") for p in tool_executions])
    transfers = [t for execution in executions for t in execution.get("transfers", [])]
    uncertain = sum(bool(p.get("failure")) and p["failure"].get("stage") != "selection"
                    for p in physical)
    uncertain += sum(not p.get("execution") and not p.get("failure") for p in physical)
    bytes_subtotal = total([t.get("bytes_transferred") for t in transfers])
    time_subtotal = total([t.get("duration_ms") for t in transfers])
    end_value = endings[0].get("e2e_latency_ms") if endings else None
    return {
        "recorded_e2e_latency_ms": total([end_value]) if endings else None,
        "e2e_source": "explicit run.end/run.failed receipt" if endings else "unknown",
        "initial_completed_receipt_count": len(initial),
        "initial_completed_bytes": total([p.get("bytes_transferred") for p in initial]),
        "initial_completed_transfer_work_ms": total([p.get("duration_ms") for p in initial]),
        "initial_scope": "completed materialization receipts, not inferred requested totals",
        "action_transfer_receipt_count": len(transfers),
        "action_transfer_successful_receipts_bytes": bytes_subtotal,
        "action_transfer_successful_receipts_work_ms": time_subtotal,
        "action_transfer_complete_bytes": None if uncertain or missing else bytes_subtotal,
        "action_transfer_complete_work_ms": None if uncertain or missing else time_subtotal,
        "unmeasured_execution_failures": uncertain,
        "prepared_without_physical_receipt": len(missing),
        "operator_successful_receipts_work_ms": total([
            p.get("operator_latency_ms") for p in executions]),
        "operator_receipt_scope": "all successful Worker action receipts, including invoke_model",
        "successful_tool_execution_work_ms": tool_work,
        "complete_tool_execution_work_ms": None
        if unknown_execution_kind or uncertain_tool_work else tool_work,
        "successful_model_action_execution_work_ms": total([
            p.get("operator_latency_ms") for p in model_executions]),
        "execution_kind_unknown_receipts": unknown_execution_kind,
        "exclusive_work_scope": "logical action type; model-action execution is not additional "
        "backend service work and must not be double-counted",
        "original_result_modified": False,
        "timing_scope": "persisted receipt work; overlapping work is not an E2E decomposition",
    }


def root_function_receipts(api_root: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Actual response calls include the final turn absent from accumulated SDK input.

    Correlate on the controller's event/request UTC timestamps,
    not UUID order. Only counts/names leave this function; argument/body text never
    does. Responses from specialists/Verifier are deliberately separate.
    """
    starts = sorted((datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")),
                     e["payload"]["decision_id"]) for e in events
                    if e["event_type"] == "logical.reasoning.started"
                    and e["payload"]["logical_agent_id"] == "manager" and "timestamp" in e)
    names: Counter[str] = Counter()
    query_decisions = set()
    malformed = unknown_responses = unmapped_queries = optional_interface_requests = 0
    for path in api_root.glob("*-usage.json"):
        usage = json.loads(path.read_text())
        if usage["recipient"] != "manager":
            continue
        request_path = api_root / f"{usage['call_id']}-request.json"
        if request_path.exists():
            request = json.loads(request_path.read_text())
            if any(tool.get("function", {}).get("name", "").startswith("estimate_")
                   for tool in request.get("tools", [])):
                optional_interface_requests += 1
        response_path = api_root / f"{usage['call_id']}-response.json"
        if not response_path.exists() or usage["status"] != 200:
            unknown_responses += 1
            continue
        response = json.loads(response_path.read_text())
        choices = response.get("choices") if isinstance(response, dict) else None
        if not isinstance(choices, list) or len(choices) != 1:
            unknown_responses += 1
            continue
        started = datetime.fromisoformat(usage["started_utc"].replace("Z", "+00:00"))
        candidates = [decision for timestamp, decision in starts if timestamp <= started]
        decision_id = candidates[-1] if candidates else None
        message = choices[0].get("message", {})
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            name = function.get("name")
            if not isinstance(name, str):
                malformed += 1
                continue
            names[name] += 1
            if name.startswith("estimate_"):
                if decision_id is None:
                    unmapped_queries += 1
                else:
                    query_decisions.add(decision_id)
    return {"function_calls": dict(names),
            "optional_query_attempts": sum(n for name, n in names.items()
                                           if name.startswith("estimate_")),
            "optional_query_decision_ids": sorted(query_decisions),
            "unknown_manager_responses": unknown_responses,
            "manager_requests_with_optional_query_interface": optional_interface_requests,
            "unmapped_optional_queries": unmapped_queries, "malformed_function_calls": malformed,
            "count_source": "actual raw provider response, not replayed SDK history"}


def event_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [e["payload"] for e in events if e["event_type"] == "logical.observation"]
    prepared = [e["payload"]["action"] for e in events
                if e["event_type"] == "logical.action.prepared"]
    executions = [e["payload"]["execution"] for e in events
                  if e["event_type"] == "physical.execution" and "execution" in e["payload"]]
    model = [x["model_telemetry"] for x in executions if x.get("model_telemetry") is not None]
    outcomes = [e["payload"] for e in events if e["event_type"] == "logical.model.outcome"]
    model_action_ids = {x["action_id"] for x in prepared if x["action_type"] == "model"}
    physical_by_id = {e["payload"]["action_id"]: e["payload"] for e in events
                      if e["event_type"] == "physical.execution"
                      and "action_id" in e["payload"]}
    preflight_codes = {"context_limit_exceeded", "unsupported_modality", "deployment_required"}
    no_inference_ids = {x["action_id"] for x in observations + outcomes
                        if "action_id" in x and x.get("succeeded") is False
                        and (x.get("failure_code") in preflight_codes
                             or x.get("physical_selection_succeeded") is False)}
    no_inference_ids.update(action_id for action_id, p in physical_by_id.items()
                            if (p.get("failure") or {}).get("stage") == "selection")
    # Transport exceptions can close a logical action without emitting either a
    # physical receipt or model.outcome. Do not turn their absence into zero work.
    uncertain_model_ids = set()
    anonymous_uncertain_outcomes = 0
    for x in outcomes:
        if (x.get("succeeded") is False and x.get("physical_selection_succeeded") is True
                and not x.get("reached_model_inference")
                and x.get("failure_code") not in preflight_codes):
            if "action_id" in x:
                uncertain_model_ids.add(x["action_id"])
            else:
                anonymous_uncertain_outcomes += 1
    for x in observations:
        action_id = x.get("action_id")
        if (x.get("succeeded") is False and action_id in model_action_ids
                and action_id not in no_inference_ids
                and not (physical_by_id.get(action_id, {}).get("execution") or {}).get(
                    "model_telemetry")):
            uncertain_model_ids.add(action_id)
    missing_model_receipts = model_action_ids - physical_by_id.keys() - no_inference_ids
    uncertain_model_work = len(uncertain_model_ids) + anonymous_uncertain_outcomes
    unknown_model_work = bool(uncertain_model_work or missing_model_receipts)
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
    sdk_failures: dict[tuple[str, str], str] = {}
    for event in events:
        if event["event_type"] != "logical.reasoning.input":
            continue
        p = event["payload"]
        for item in p.get("input_items", []):
            if (item.get("type") != "function_call_output"
                    or not isinstance(item.get("call_id"), str)):
                continue
            try:
                value = json.loads(item.get("output", ""))
            except (ValueError, TypeError):
                continue
            if (isinstance(value, dict) and value.get("succeeded") is False
                    and isinstance(value.get("failure_code"), str)):
                sdk_failures[p["logical_agent_id"], item["call_id"]] = value["failure_code"]
    failed = [x for x in observations if not x["succeeded"]]
    # Denominator is observable selected-ready opportunities, not unobserved
    # counterfactual actions or every thought/finish turn. Readiness is established
    # by the frozen gateway; no measured-cost cutoff or task-specific threshold.
    eligible_decisions = set()
    query_eligible_decisions = set()
    active_root_decision = None
    quoted_ids = set()
    for e in events:
        kind, p = e["event_type"], e["payload"]
        if kind == "logical.reasoning.started" and p["logical_agent_id"] == "manager":
            active_root_decision = p["decision_id"]
        elif (kind == "logical.batch.validation" and p["logical_agent_id"] == "manager"
              and p["status"] == "accepted" and p.get("all_inputs_materialized") is True):
            eligible_decisions.add(p["decision_id"])
        elif (kind == "logical.cost_quote.created"
              and p["action"]["owner_agent_id"] == "manager"
              and active_root_decision is not None):
            quoted_ids.add(p["quote"]["quote_id"])
            eligible_decisions.add(active_root_decision)
        elif (kind == "logical.cost_card.returned" and p["card_id"] in quoted_ids
              and active_root_decision is not None):
            query_eligible_decisions.add(active_root_decision)
    final_quote = next((e["payload"] for e in reversed(events)
                        if e["event_type"] == "logical.cost_quote.run.end"), None)
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
        "inference_flag_is_complete_measurement": False,
        "inference_flag_note": "frozen flag confirms returned model telemetry; a failed "
        "post-inference output parse can lack telemetry. "
        "False is not universal proof of no inference",
        "successful_inference_telemetry_count": len(model),
        "model_service_work_ms": measured_total([x.get("service_latency_ms") for x in model]),
        "model_service_work_scope": "returned inference telemetry only; "
        "excludes unmeasured failures",
        "unmeasured_failed_model_outcomes": uncertain_model_work,
        "unmeasured_model_actions_missing_physical_receipt": len(missing_model_receipts),
        "model_service_work_complete_total_ms": None if unknown_model_work else measured_total(
            [x.get("service_latency_ms") for x in model]),
        "failed_physical_execution_work_ms": measured_total([
            e["payload"]["failure"].get("duration_ms") for e in events
            if e["event_type"] == "physical.execution" and e["payload"].get("failure")
            and e["payload"]["failure"].get("stage") == "execution"]),
        "physical_model_input_tokens": measured_total([x.get("input_tokens") for x in model]),
        "physical_model_output_tokens": measured_total([x.get("output_tokens") for x in model]),
        "finish_reasons": dict(Counter(x.get("finish_reason", "unknown") for x in model)),
        "failure_codes": dict(Counter(x.get("failure_code", "unknown") for x in failed)),
        "sdk_function_failure_receipts_lower_bound": dict(Counter(sdk_failures.values())),
        "sdk_failure_source_note": "deduplicated effective SDK tool outputs; may overlap logical "
        "observations/quote rejects; final-turn outputs without later input remain unobserved",
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
            "commits_authorized": types["logical.cost_quote.commit_authorized"],
            "discarded_quotes": types["logical.cost_quote.discarded"],
            "stale_quotes": types["logical.cost_quote.stale"],
            "quote_final_states": final_quote.get("quote_states") if final_quote else None,
            "quote_proposal_attempts": final_quote.get("proposal_attempts")
            if final_quote else None,
            "quote_induced_revision_rate": None,
            "revision_note": "discard/staleness observable; causal semantic revision needs audit",
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
            "eligible_selected_ready_decisions": len(eligible_decisions),
            "eligible_high_impact_decisions": len(eligible_decisions),
            "valid_optional_query_decisions": len(query_eligible_decisions),
            "valid_query_adoption_rate": len(query_eligible_decisions) / len(eligible_decisions)
            if eligible_decisions else None,
            "eligibility_note": "observed schema-valid ready root-action opportunities; all native "
            "physical operators/models, no scalar cost threshold; excludes pure reasoning/finish "
            "and rejected readiness. Not a count of unobserved counterfactual decisions",
        },
    }


def settled_attempt(root: Path, cell_id: str, attempt: Any, *,
                    admission_reader: Callable[..., dict[str, Any]] | None = None,
                    ) -> dict[str, Any]:
    directory = root / "evidence" / cell_id / f"attempt{attempt.attempt_index}"
    admission = (admission_reader or effective_admission)(root, attempt)
    if (provenance_sha256(admission) != attempt.receipt_sha256
            or admission["disposition"] != attempt.disposition):
        raise RuntimeError("settled admission/ledger drift")
    result_path = directory / "runs" / attempt.run_id / "result.json"
    result = json.loads(result_path.read_text())
    if (admission.get("result_sha256") is not None
            and provenance_sha256(result) != admission["result_sha256"]):
        raise RuntimeError("settled result/admission drift")
    # JSONL boundaries are physical newlines. Unicode U+2028/U+0085 inside a
    # valid JSON string must not split one persisted event into fragments.
    events = [json.loads(line) for line in result_path.with_name("trace.jsonl").open(
        encoding="utf-8")]
    evaluation = result.get("evaluation")
    terminal = result.get("final_answer")
    account_path = directory / "api-accounting.json"
    usage = [json.loads(path.read_text())["cost_receipt"] for path in
             (directory / "private/api").glob("*-usage.json")]
    adjudication_path = root / "adjudications" / (attempt.run_id + ".json")
    adjudication = json.loads(adjudication_path.read_text()) if adjudication_path.exists() else None
    record_path = root / "record-field-adjudications" / (attempt.run_id + ".json")
    record_review = json.loads(record_path.read_text()) if record_path.exists() else None
    policy_path = root / "resident-provider-policy-adjudications" / (attempt.run_id + ".json")
    policy_review = json.loads(policy_path.read_text()) if policy_path.exists() else None
    legacy_policy_path = root / "provider-policy-adjudications" / (attempt.run_id + ".json")
    legacy_policy = (json.loads(legacy_policy_path.read_text())
                     if legacy_policy_path.exists() else None)
    return {
        "run_id": attempt.run_id, "attempt_index": attempt.attempt_index,
        "execution_sha256": attempt.execution_sha256,
        "disposition": attempt.disposition, "admission_reason": attempt.reason,
        "admission_problems": admission.get("problems", []),
        "original_rejection_preserved": any(v is not None for v in (
            adjudication, record_review, policy_review, legacy_policy)),
        "provider_policy_adjudication_sha256": provenance_sha256(legacy_policy)
        if legacy_policy is not None else None,
        "resident_provider_policy_adjudication_sha256": provenance_sha256(policy_review)
        if policy_review is not None else None,
        "record_field_adjudication_sha256": provenance_sha256(record_review)
        if record_review is not None else None,
        "confirmed_absent_record_field_failures": len(record_review["record_field_proof"])
        if record_review is not None else 0,
        "provider_policy_failure": admission.get("failure_class") == "provider_input_policy",
        "adjudication_sha256": provenance_sha256(adjudication) if adjudication else None,
        "confirmed_post_inference_json_failures": len(adjudication["proof"])
        if adjudication else 0,
        "post_inference_failed_service_tokens": None if adjudication else 0,
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
        "trace_cost_receipts": trace_cost_receipts(events),
        "actual_manager_function_receipts": root_function_receipts(
            directory / "private/api", events),
    }


def snapshot(root: Path, *, selection_root: Path | None = None,
             ledger_class: type[SnapshotAttemptLedger] | None = None,
             admission_reader: Callable[..., dict[str, Any]] | None = None,
             ) -> dict[str, Any]:
    selection = selection_root or root / "preparation/task-freeze-002"
    manifest = json.loads((selection / "manifest.json").read_text())
    schedule = json.loads((selection / "phase1-schedule.json").read_text())
    cell_ids = tuple(row["cell_id"] for row in schedule)
    if not (root / "phase1-attempts.jsonl").is_file():
        raise RuntimeError("read-only collector cannot initialize a missing attempt ledger")
    ledger = (ledger_class or SnapshotAttemptLedger)(root / "phase1-attempts.jsonl", cell_ids,
                                                    manifest["phase1_schedule_sha256"])
    attempts = ledger.attempts
    admitted = {item.cell_id for item in attempts if item.disposition == "valid"}
    original_attempts = ledger.original_attempts
    rows = []

    def read_attempt(cell_id: str, attempt: Any) -> dict[str, Any]:
        if admission_reader is None:
            return settled_attempt(root, cell_id, attempt)
        return settled_attempt(root, cell_id, attempt, admission_reader=admission_reader)

    for cell in schedule:
        matched = [x for x in attempts if x.cell_id == cell["cell_id"]]
        rows.append({"condition": cell,
                     "attempts": [read_attempt(cell["cell_id"], x)
                                  for x in matched
                                  if x.disposition is not None],
                     "pending_run_ids": [x.run_id for x in matched if x.disposition is None]})
    return {"version": "large-scale-settled-telemetry-v1", "scheduled_cells": len(cell_ids),
            "admitted_cells": len(admitted), "attempt_count": len(attempts),
            "pending_count": sum(x.disposition is None for x in attempts),
            "confounded_attempts": sum(x.disposition == "confounder" for x in attempts),
            "original_confounded_attempts": sum(x.disposition == "confounder"
                                                for x in original_attempts),
            "adjudicated_attempts": sum(x.reason == "audited_post_inference_model_json_failure"
                                         for x in attempts),
            "provider_policy_adjudicated_attempts": sum(
                x.reason == "audited_provider_input_policy_failure" for x in attempts),
            "record_field_adjudicated_attempts": sum(
                x.reason == "audited_materialized_record_absent_field_misuse" for x in attempts),
            "operational_excluded_attempts": sum(x.disposition == "operational_excluded"
                                                 for x in attempts),
            "phase1_complete": len(admitted) == len(cell_ids),
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
