"""Remote offline admission: retain semantic failures, stop unresolved confounders."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.api_cost import (
    APICostReceipt,
    APIPriceCard,
    FXReference,
    estimate_api_cost,
    summarize_api_costs,
)
from infra_joint.experiments.recipient_audit import audit_effective_inputs, scan_recipient_context

SEMANTIC_ACTION_FAILURES = frozenset({
    "phase_restricted", "artifact_not_materialized", "context_limit_exceeded",
    "semantic_validation_failed", "artifact_too_large", "unsupported_modality",
    "model_binding_failed", "no_matching_deployment", "physical_feasibility_failed",
    "action_cancelled", "model_output_too_large", "infeasible_binding",
})


def raw_api_audit(
    api_root: Path, *, method: str, planner: str, prices: dict[str, APIPriceCard],
    fx: FXReference, physical_identifiers: tuple[str, ...],
) -> dict[str, Any]:
    """Read every actual HTTP request, not only selected provenance events."""
    issues, incidents, receipts, contexts = [], [], [], []
    usage_files = sorted(api_root.glob("*-usage.json"))
    requests = {path.name.removesuffix("-request.json"): path
                for path in api_root.glob("*-request.json")}
    seen = set()
    for path in usage_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        identifier = row["call_id"]
        if identifier in seen:
            issues.append("duplicate_raw_API_call")
        seen.add(identifier)
        role = row["recipient"]
        if role not in {"manager", "specialist", "verifier"}:
            issues.append("unknown_API_recipient")
            continue
        expected = "qwen3.8-max" if role == "verifier" else planner
        if row["intended_model"] != expected or row["requested_model"] != expected:
            issues.append("API_request_model_drift")
        response_path = api_root / f"{identifier}-response.json"
        request_path = requests.get(identifier)
        if request_path is None or not response_path.exists():
            issues.append("missing_raw_API_request_or_response")
            continue
        request = json.loads(request_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if request.get("model") != expected:
            issues.append("raw_request_model_drift")
        messages = request.get("messages")
        if not isinstance(messages, list):
            issues.append("actual_recipient_context_missing")
        else:
            findings = scan_recipient_context(messages, recipient=role, method=method,
                                              physical_identifiers=physical_identifiers)
            contexts.append({"call_id": identifier, "recipient": role,
                             "context_sha256": provenance_sha256(messages),
                             "findings": [asdict(item) for item in findings]})
            if findings:
                issues.append("actual_recipient_privacy_or_method_leakage")
        raw_usage = response.get("usage") if isinstance(response, dict) else None
        raw_model = response.get("model") if isinstance(response, dict) else None
        if raw_usage != row["usage"] or raw_model != row["response_model"]:
            issues.append("raw_usage_receipt_mismatch")
        if row["status"] == 200 and raw_model != expected:
            issues.append("API_response_model_drift")
        if row["status"] != 200:
            # 4xx schema/config faults are not presumed provider outages.
            status, error = row["status"], row.get("error_type")
            if status in {429, 500, 502, 503, 504}:
                incidents.append("provider_outage")
            elif status is None and error in {
                "ReadTimeout", "ConnectTimeout", "ConnectError", "ReadError", "RemoteProtocolError",
            }:
                incidents.append("connection_reset")
            else:
                issues.append("unclassified_API_failure_requires_audit")
        cost = estimate_api_cost(
            raw_usage, prices.get(expected), fx, provider="aliyun-model-studio",
            region="cn-beijing", requested_model=row["requested_model"], response_model=raw_model,
        )
        receipt = APICostReceipt(call_id=identifier, recipient=role, cost=cost)
        if receipt.model_dump(mode="json") != row["cost_receipt"]:
            issues.append("API_cost_receipt_drift")
        receipts.append(receipt)
    if set(requests) != seen:
        issues.append("unclosed_raw_API_requests")
    summaries = {role: summary.model_dump(mode="json")
                 for role, summary in summarize_api_costs(receipts).items()}
    return {"problems": sorted(set(issues)), "operational_incidents": sorted(set(incidents)),
            "contexts": contexts, "roles": summaries, "HTTP_calls": len(seen)}


def trace_audit(events: list[dict[str, Any]], run_id: str) -> list[str]:
    issues = []
    previous = None
    seen = set()
    for index, event in enumerate(events):
        if (event["run_id"] != run_id or event["parent_id"] != previous
                or event["step_id"] in seen
                or not event["step_id"].startswith(f"{index:06d}-")):
            issues.append("trace_chain_invalid")
        seen.add(event["step_id"])
        previous = event["step_id"]
    terminal = [event for event in events if event["event_type"] in {"run.end", "run.failed"}]
    if len(terminal) != 1 or not events or events[-1] != terminal[0]:
        issues.append("terminal_trace_event_missing_or_duplicated")
    return sorted(set(issues))


def classify_terminal(result: dict[str, Any]) -> tuple[list[str], list[str]]:
    """No quality gate and no forced Yes/No labels for original MultiHop free text."""
    problems, operational = [], []
    if result["execution_completed"]:
        if not result.get("final_answer") or result.get("evaluation") is None:
            problems.append("completed_run_missing_terminal_or_original_evaluation")
    elif result.get("failure") is None:
        problems.append("failed_run_without_typed_reason")
    failure = result.get("failure") or {}
    exception = failure.get("exception_type")
    message = failure.get("message", "").lower()
    if exception in {"ReadTimeout", "ConnectTimeout", "ConnectError", "ReadError"}:
        operational.append("external_model_service_failure")
    elif exception not in {None, "AgentLoopError", "MaxTurnsExceeded", "ModelBehaviorError"}:
        problems.append("terminal_failure_requires_system_audit")
    elif "unrecoverable physical" in message or "observer" in message:
        problems.append("terminal_physical_or_observer_failure")
    return problems, operational


def admit(directory: Path, config: dict[str, Any], prices_path: Path) -> dict[str, Any]:
    """Offline gate after attempt cleanup. Private evidence never enters logical feedback."""
    result_path = directory / "runs" / config["run_id"] / "result.json"
    trace_path = result_path.with_name("trace.jsonl")
    if not result_path.exists() or not trace_path.exists():
        return {"disposition": "confounder", "reason": "missing_attempt_result_or_trace",
                "problems": ["missing_attempt_result_or_trace"]}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    events = JsonlTraceWriter(trace_path).read_all()
    issues, operational = classify_terminal(result)
    issues += trace_audit(events, config["run_id"])
    if result["run_id"] != config["run_id"]:
        issues.append("result_run_identity_mismatch")
    method = audit_effective_inputs(events, config["method"])
    issues += method["problems"]
    if not method["recipient_inputs"]["manager"]:
        issues.append("agent_loop_never_entered_requires_audit")
    prices = json.loads(prices_path.read_text(encoding="utf-8"))
    before = json.loads((directory / "private/worker-state-before.json").read_text())
    identities = tuple(url.split("://", 1)[-1].split(":", 1)[0]
                       for url in config["worker_urls"].values())
    deployments = tuple(deployment["deployment_id"] for state in before.values()
                        for deployment in state.get("deployments", []))
    api = raw_api_audit(
        directory / "private/api", method=config["method"], planner=config["planner"],
        prices={key: APIPriceCard.model_validate(value) for key, value in prices["prices"].items()},
        fx=FXReference.model_validate(prices["fx"]),
        physical_identifiers=identities + deployments,
    )
    issues += api["problems"]
    operational += api["operational_incidents"]
    accounting = json.loads((directory / "api-accounting.json").read_text())
    if accounting["roles"] != api["roles"] or accounting["logical_feedback"] is not False:
        issues.append("API_accounting_summary_mismatch")
    tc = json.loads((directory / "tc-attestation.json").read_text())
    if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
        issues.append("tc_cleanup_failure")
    if not tc.get("applied_qdisc"):
        issues.append("tc_application_not_attested")
    shutdown = json.loads((directory / "worker-shutdown.json").read_text())
    if shutdown["errors"] or not shutdown.get("verified_exited"):
        issues.append("worker_cleanup_not_verified")
    persistence = json.loads((directory / "private/artifact-persistence.json").read_text())
    if not persistence["pass"]:
        issues.append("artifact_persistence_failure")
    diagnostics_path = result_path.parent / "private/observer-diagnostics.jsonl"
    if not diagnostics_path.exists():
        issues.append("observer_diagnostics_missing")
    else:
        diagnostics = [json.loads(line) for line in diagnostics_path.open(encoding="utf-8")
                       if line.strip()]
        if not diagnostics or any(not probe["probe_success"] for item in diagnostics
                                  for probe in item["probes"]):
            issues.append("observer_probe_incident")
    for event in events:
        if event["event_type"] == "logical.observation" and not event["payload"]["succeeded"]:
            code = event["payload"]["failure_code"]
            if code == "model_service_error":
                operational.append("external_model_service_failure")
            elif code not in SEMANTIC_ACTION_FAILURES:
                # validation_failed can be ordinary Agent field misuse. Preserve
                # and audit the exact action; never silently exclude or repeat it.
                issues.append(f"typed_action_failure_requires_audit:{code}")
    disposition = "confounder" if issues else "operational_excluded" if operational else "valid"
    return {"disposition": disposition, "reason": sorted(set(issues or operational))[0]
            if issues or operational else "completed_or_valid_semantic_failure",
            "problems": sorted(set(issues)), "operational_incidents": sorted(set(operational)),
            "execution_completed": result["execution_completed"],
            "original_evaluation": result.get("evaluation"),
            "terminal_failure": result.get("failure"),
            "method_audit": method, "api_audit": api,
            "result_sha256": provenance_sha256(result), "event_count": len(events)}
