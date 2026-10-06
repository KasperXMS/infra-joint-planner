"""Exact offline mixed token-rate/policy audit, not a semantic retry waiver.

Only an actual token-rate HTTP429 permits the existing one identical operational
replacement. HTTP400 input-policy refusal alone never qualifies. Original
receipts, prompts, runtime, API concurrency and account quota remain unchanged.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import large_scale_resident_sdk_argument_review_v1 as previous

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.attempt_ledger import Attempt

DIRECTORY = previous.DIRECTORY
RATE_DIRECTORY = "mixed-token-rate-policy-adjudications"
GATE = "unclassified_API_failure_requires_audit"
REASON = "audited_external_token_rate_with_input_policy_failure"
RATE_MESSAGE = (
    "Allocated quota exceeded, please increase your quota limit. For details, see: "
    "https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit"
)
POLICY_MESSAGE = "Input text data may contain inappropriate content."
SOURCE_PATHS = (
    "src/infra_joint/experiments/sdk_api_meter.py",
    "src/infra_joint/control/native_agents.py",
    "scripts/large_scale_execution_v1.py",
)
methods, sha256 = previous.methods, previous.sha256


def review(original: dict[str, Any], api: Path,
           events: list[dict[str, Any]]) -> dict[str, Any]:
    terminal: dict[str, Any] = original.get("terminal_failure") or {}
    if (original.get("disposition") != "confounder" or original.get("reason") != GATE
            or original.get("problems") != [GATE]
            or original.get("operational_incidents") != ["provider_outage"]
            or original.get("api_audit", {}).get("problems") != [GATE]
            or original.get("api_audit", {}).get("operational_incidents") != ["provider_outage"]
            or original.get("execution_completed") is not False
            or original.get("original_evaluation") is not None
            or terminal.get("code") != "logical_loop_failed"
            or terminal.get("exception_type") != "AgentLoopError"
            or not str(terminal.get("message", "")).startswith(
                "Blind verifier failed: BadRequestError: Error code: 400")
            or POLICY_MESSAGE not in str(terminal.get("message", ""))
            or "data_inspection_failed" not in str(terminal.get("message", ""))
            or not events or events[-1]["event_type"] != "run.failed"
            or [e["payload"].get("failure") for e in events
                if e["event_type"] == "run.failed"] != [terminal]):
        raise RuntimeError("mixed provider review cannot waive other findings or evaluated results")
    usages = [(p, json.loads(p.read_text())) for p in sorted(api.glob("*-usage.json"))]
    ids = [row.get("call_id") for _, row in usages]
    contexts = original["api_audit"].get("contexts", [])
    if (not ids or any(not isinstance(c, str) or not c or Path(c).name != c for c in ids)
            or len(set(ids)) != len(ids) or len(contexts) != len(ids)
            or {c.get("call_id") for c in contexts} != set(ids)
            or any(c.get("findings") != [] for c in contexts)
            or original["api_audit"].get("HTTP_calls") != len(ids)):
        raise RuntimeError("unique original API identities and clean recipient audits required")
    expected = {call + suffix for call in ids for suffix in (
        "-usage.json", "-request.json", "-response.json")}
    scopes = [row.get("scope_id") for _, row in usages]
    if (any(not isinstance(s, str) or not s or Path(s).name != s for s in scopes)
            or len(set(scopes)) != len(scopes)):
        raise RuntimeError("unique SDK invocation scope identities required")
    expected.update(scope + "-model-attempt.json" for scope in scopes)
    actual = {p.name for p in api.glob("*.json")}
    if actual != expected:
        raise RuntimeError("all original HTTP request/response/usage files must be present")
    failures: list[dict[str, Any]] = []
    for usage_path, row in usages:
        call = row["call_id"]
        request_path = api / (call + "-request.json")
        response_path = api / (call + "-response.json")
        if (usage_path.name != call + "-usage.json" or any(
                p.is_symlink() or not p.is_file() for p in (
                    usage_path, request_path, response_path))):
            raise RuntimeError("owned unmodified API files required")
        request = json.loads(request_path.read_text())
        if row.get("requested_model") != request.get("model"):
            raise RuntimeError("actual request/model provenance mismatch")
        invocation_path = api / (row["scope_id"] + "-model-attempt.json")
        if invocation_path.is_symlink() or not invocation_path.is_file():
            raise RuntimeError("original SDK invocation metadata required")
        invocation = json.loads(invocation_path.read_text())
        expected_exception = ("RateLimitError" if row.get("status") == 429 else
                              "BadRequestError" if row.get("status") == 400 else None)
        if (invocation.get("scope_id") != row["scope_id"] or invocation.get("http_calls") != 1
                or any(invocation.get(k) != row.get(k)
                       for k in ("recipient", "agent_name", "requested_model"))
                or invocation.get("error_type") != expected_exception):
            raise RuntimeError("original single-attempt SDK invocation/provenance mismatch")
        if row.get("status") == 200:
            continue
        response = json.loads(response_path.read_text())
        error: dict[str, Any] = response.get("error") or {}
        status, role = row.get("status"), row.get("recipient")
        expected_error = "insufficient_quota" if status == 429 else "data_inspection_failed"
        expected_message = RATE_MESSAGE if status == 429 else POLICY_MESSAGE
        model = "qwen3.8-max" if role == "verifier" else "deepseek-v4-pro"
        agent = "blind_evidence_verifier" if role == "verifier" else "bounded_specialist"
        if (status not in {400, 429} or role not in {"specialist", "verifier"}
                or (status == 429 and role != "specialist")
                or row.get("agent_name") != agent
                or row.get("intended_model") != model or row.get("requested_model") != model
                or row.get("usage") is not None or row.get("error_type") is not None
                or error.get("code") != expected_error or error.get("type") != expected_error
                or error.get("message") != expected_message):
            raise RuntimeError("not the exact token-rate and input-policy responses")
        if role == "verifier" and [t.get("function", {}).get("name")
                for t in request.get("tools", [])] != ["submit_verification"]:
            raise RuntimeError("terminal refusal must target the fixed Blind Verifier")
        try:
            started = datetime.fromisoformat(row["started_utc"])
            finished = datetime.fromisoformat(row["finished_utc"])
        except (KeyError, TypeError, ValueError) as interval_error:
            raise RuntimeError("provider failure interval is not evidenced") from interval_error
        latency = row.get("latency_ms")
        if (started.tzinfo is None or finished.tzinfo is None or finished < started
                or isinstance(latency, bool) or not isinstance(latency, (int, float))
                or abs((finished - started).total_seconds() * 1000 - latency) > 1000):
            raise RuntimeError("provider failure timing drift")
        failures.append({"call_id": call, "recipient": role, "agent_name": agent,
            "requested_model": model, "http_status": status, "provider_error_code": expected_error,
            "started_utc": row["started_utc"], "finished_utc": row["finished_utc"],
            "request_sha256": sha256(request_path), "response_sha256": sha256(response_path),
            "usage_sha256": sha256(usage_path),
            "model_attempt_sha256": sha256(invocation_path), "failed_call_usage": None})
    if sorted((f["http_status"], f["recipient"]) for f in failures) != [
            (400, "specialist"), (400, "verifier"), (429, "specialist")]:
        raise RuntimeError("exactly one rate429 and two policy400 failures required")
    verifier = next(f for f in failures if f["recipient"] == "verifier")
    if any(datetime.fromisoformat(row["finished_utc"]) > datetime.fromisoformat(
            verifier["finished_utc"]) for _, row in usages):
        raise RuntimeError("fixed Verifier policy failure must be the last API response")
    inputs = sum(e["event_type"] == "logical.verification.input" for e in events)
    if (sum(row.get("recipient") == "verifier" for _, row in usages) != inputs
            or inputs != sum(e["event_type"] == "logical.verification" for e in events) + 1
            or sum(e["event_type"] == "logical.verification.failed" for e in events) != 1):
        raise RuntimeError("terminal Verifier receipt must match the actual loop trace")
    ends = [e["payload"] for e in events if e["event_type"] == "logical.subagent.end"]
    summaries: list[dict[str, Any]] = []
    for code in ("insufficient_quota", "data_inspection_failed"):
        matching = [p for p in ends if code in str(p.get("answer", ""))]
        if len(matching) != 1:
            raise RuntimeError("each failed specialist result must be observed in the trace")
        p = matching[0]
        summaries.append({"logical_agent_id": p["logical_agent_id"], "call_id": p["call_id"],
                          "provider_error_code": code,
                          "answer_sha256": provenance_sha256(p["answer"])})
    return {"mixed_provider_proof": failures, "specialist_failure_proof": summaries,
        "reviewed_admission": {**original, "disposition": "operational_excluded", "reason": REASON,
            "problems": [], "operational_incidents": ["external_provider_token_rate_limit"],
            "failure_class": "mixed_provider_token_rate_and_input_policy",
            "primary_failure": "external_provider_token_rate_comparison_confounder",
            "immediate_terminal_failure": "provider_input_policy",
            "original_operational_incidents": original["operational_incidents"],
            "replacement_basis": "independently_proven_HTTP429_token_rate_limit",
            "replacement_authorized": True, "identical_execution_required": True,
            "max_operational_replacements": 1, "policy_only_replacement_authorized": False,
            "counterfactual_without_throttling": None, "billing_failure_proven": False,
            "provider_wide_outage_proven": False, "evaluation_imputed": False}}


def verify_sidecar(path: Path, attempt: Attempt) -> dict[str, Any]:
    root = path.parent.parent
    directory = root / "evidence" / attempt.cell_id / f"attempt{attempt.attempt_index}"
    value = json.loads(path.read_text())
    original = json.loads((directory / "admission.json").read_text())
    if (path.is_symlink() or path.parent.name != RATE_DIRECTORY
            or path.name != attempt.run_id + ".json" or value["run_id"] != attempt.run_id
            or attempt.disposition != "confounder" or attempt.reason != GATE
            or provenance_sha256(original) != attempt.receipt_sha256
            or value["original_admission_sha256"] != attempt.receipt_sha256
            or value["original_execution_sha256"] != attempt.execution_sha256
            or value["reviewer_source_sha256"] != sha256(Path(__file__))
            or value["previous_reviewer_source_sha256"] != sha256(Path(previous.__file__))
            or value["execution_sources_sha256"] != methods.frozen_sources(
                root, attempt, SOURCE_PATHS)
            or value["original_evidence_file_sha256"] != methods.evidence_files(directory)):
        raise RuntimeError("mixed provider proof identity/source/evidence drift")
    events = [json.loads(line) for line in (
        directory / "runs" / attempt.run_id / "trace.jsonl").open(encoding="utf-8")]
    actual = review(original, directory / "private/api", events)
    if (actual != {k: value[k] for k in actual}
            or provenance_sha256(actual["reviewed_admission"])
            != value["reviewed_admission_sha256"]):
        raise RuntimeError("mixed provider proof cannot be reproduced")
    return value


class ProjectionAttemptLedger(previous.ProjectionAttemptLedger):
    @property
    def attempts(self) -> tuple[Attempt, ...]:
        result: list[Attempt] = []
        for attempt in super().attempts:
            path = self.path.parent / RATE_DIRECTORY / (attempt.run_id + ".json")
            if path.exists():
                value = verify_sidecar(path, attempt)
                attempt = replace(attempt, disposition="operational_excluded", reason=REASON,
                                  receipt_sha256=value["reviewed_admission_sha256"])
            result.append(attempt)
        return tuple(result)


def effective_admission(root: Path, attempt: Attempt) -> dict[str, Any]:
    if attempt.reason != REASON:
        return previous.effective_admission(root, attempt)
    value = json.loads((root / RATE_DIRECTORY / (attempt.run_id + ".json")).read_text())
    if value["reviewed_admission_sha256"] != attempt.receipt_sha256:
        raise RuntimeError("effective mixed provider admission drift")
    return value["reviewed_admission"]
