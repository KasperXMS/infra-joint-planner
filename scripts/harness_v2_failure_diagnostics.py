"""Analyze frozen private Stage 2 failures in place; export only protocol metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from infra_joint.control.verification import VerificationResult

VERDICT_FIELDS = frozenset(
    {
        "status",
        "failure_stage",
        "reason",
        "missing_requirements",
        "candidate_action_id",
        "candidate_output_sha256",
        "evidence_state_version",
    }
)


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verifier_responses(cell: Path) -> list[dict[str, Any]]:
    folder = cell / "private" / "api" / "cloud"
    result = []
    for usage_path in folder.glob("*-usage.json"):
        if read(usage_path).get("recipient") != "verifier":
            continue
        response_path = usage_path.with_name(
            usage_path.name.replace("-usage.json", "-response.json")
        )
        request_path = usage_path.with_name(usage_path.name.replace("-usage.json", "-request.json"))
        if not response_path.exists():
            result.append({"response_saved": False, "usage_file": usage_path.name})
            continue
        raw_response = response_path.read_bytes()
        response = json.loads(raw_response)
        request = read(request_path)
        choices = response.get("choices") or []
        choice = choices[0] if choices else {}
        message = choice.get("message") or {}
        declared_tools = {
            tool.get("function", {}).get("name"): tool.get("function", {}).get("parameters")
            for tool in request.get("tools", [])
        }
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            raw_name = function.get("name")
            name = raw_name if raw_name == "submit_verification" else "other_tool_name"
            raw_arguments = function.get("arguments")
            parsed: Any = None
            parse_error = None
            try:
                if isinstance(raw_arguments, str):
                    parsed = json.loads(raw_arguments)
                else:
                    parse_error = "arguments_not_string"
            except json.JSONDecodeError:
                parse_error = "arguments_invalid_json"
            schema = declared_tools.get(raw_name)
            validation_errors = []
            if parse_error is None and isinstance(schema, dict):
                validation_errors = [
                    {
                        "validator": error.validator,
                        "path": "/".join(map(str, error.absolute_path)),
                        "observed_type": type(error.instance).__name__,
                    }
                    for error in Draft202012Validator(schema).iter_errors(parsed)
                ]
            semantic_errors = []
            if isinstance(raw_arguments, str) and parse_error is None:
                try:
                    VerificationResult.model_validate_json(raw_arguments)
                except ValidationError as exc:
                    semantic_errors = [
                        {
                            "type": item["type"],
                            "path": "/".join(map(str, item["loc"])),
                        }
                        for item in exc.errors()
                    ]
            calls.append(
                {
                    "name": name,
                    "arguments_sha256": hashlib.sha256(str(raw_arguments).encode()).hexdigest(),
                    "argument_parse_error": parse_error,
                    "argument_json_type": type(parsed).__name__,
                    "argument_key_types": {
                        key: type(value).__name__
                        for key, value in parsed.items()
                        if key in VERDICT_FIELDS
                    }
                    if isinstance(parsed, dict)
                    else None,
                    "unknown_argument_key_count": len(set(parsed) - VERDICT_FIELDS)
                    if isinstance(parsed, dict)
                    else None,
                    "status": parsed.get("status")
                    if isinstance(parsed, dict)
                    and parsed.get("status") in {"continue", "ready_for_synthesis", "complete"}
                    else "missing_or_invalid",
                    "failure_stage": parsed.get("failure_stage")
                    if isinstance(parsed, dict)
                    and parsed.get("failure_stage")
                    in {"evidence_collection", "execution", "synthesis", "none"}
                    else "missing_or_invalid",
                    "schema_errors": validation_errors,
                    "semantic_errors": semantic_errors,
                }
            )
        result.append(
            {
                "response_saved": True,
                "response_file": f"private/api/cloud/{response_path.name}",
                "response_sha256": hashlib.sha256(raw_response).hexdigest(),
                "finish_reason": choice.get("finish_reason"),
                "message_content_length": len(message.get("content") or ""),
                "tool_calls": calls,
            }
        )
    return sorted(result, key=lambda item: item.get("response_file", ""))


def one(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    cell_id = row["cell"]["cell_id"]
    cell = root / "stage2" / "cells" / cell_id
    run = cell / "runs" / row["run_id"]
    trace = events(run / "trace.jsonl")
    action_type = {
        event["payload"]["action"]["action_id"]: event["payload"]["action"]["action_type"]
        for event in trace
        if event["event_type"] == "logical.action.prepared"
    }
    observations = [
        event["payload"] for event in trace if event["event_type"] == "logical.observation"
    ]
    model_outputs = [
        observation
        for observation in observations
        if observation.get("owner_agent_id") == "manager"
        and action_type.get(observation.get("action_id")) == "model"
        and observation.get("succeeded")
        and str((observation.get("output") or {}).get("text") or "").strip()
    ]
    started = [
        event["payload"] for event in trace if event["event_type"] == "logical.verification.started"
    ]
    failures = [
        event["payload"] for event in trace if event["event_type"] == "logical.verification.failed"
    ]
    candidate = [
        event for event in trace if event["event_type"] == "logical.terminal.candidate_selected"
    ]
    context_inputs = [
        event["payload"] for event in trace if event["event_type"] == "logical.verification.input"
    ]
    remaining = (
        (context_inputs[-1].get("context") or {}).get("remaining_budget")
        if context_inputs
        else None
    )
    calls = verifier_responses(cell)
    invalid = [
        {
            "response_file": item.get("response_file"),
            "response_sha256": item.get("response_sha256"),
            **call,
        }
        for item in calls
        for call in item.get("tool_calls", [])
        if call["schema_errors"] or call["argument_parse_error"]
    ]
    return {
        "cell_id": cell_id,
        "family": row["cell"]["family"],
        "network": row["cell"]["network"],
        "method": row["cell"]["method"],
        "trial": row["cell"]["trial"],
        "failure_reason": row["failure_reason"],
        "failure_code": row["failure_code"],
        "manager_turns": row["manager_turns_observed"],
        "logical_actions": len(row["workflow"]["logical_signature"]),
        "settled_semantic_actions": len(observations),
        "successful_semantic_actions": sum(item.get("succeeded") is True for item in observations),
        "failed_semantic_actions": sum(item.get("succeeded") is False for item in observations),
        "operator_counts": dict(Counter(row["workflow"]["operator_sequence"])),
        "nonempty_manager_model_outputs": len(model_outputs),
        "terminal_candidates_selected": len(candidate),
        "verification_attempts": len(started),
        "verification_failure_events": len(failures),
        "phase_at_failure": started[-1]["phase"] if started else None,
        "remaining_budget_at_failure": remaining,
        "verifier_response_count": len(calls),
        "invalid_raw_calls": invalid,
        "all_verifier_responses": calls,
        "verifier_schema_invalid_count": sum(
            not item["valid"] for item in read(cell / "verifier-schema.json")
        ),
        "physical_inference_calls": row["physical_inference_calls"],
        "physical_context_rejections": row["physical_rejections"].get("context_limit_exceeded", 0),
        "physical_service_work_ms": row["physical_service_work_ms"],
        "transfer_bytes": row["initial_bytes"] + row["action_transfer_bytes"],
        "e2e_ms": row["e2e_ms"],
        "cloud_api_usd": row["cloud_api_usd"],
        "role_usage": row["role_usage"],
        "raw_trace_relative_path": f"stage2/cells/{cell_id}/runs/{row['run_id']}/trace.jsonl",
    }


def main(root: Path, output: Path) -> None:
    analysis = read(root / "final-sanitized-analysis.json")
    failed = [
        row
        for row in analysis["cells"]
        if row["stage"] == "stage2" and not row["execution_completed"]
    ]
    rows = [one(root, row) for row in failed]
    report = {
        "version": "harness-v2-stage2-failure-diagnostics-001",
        "failed_cell_count": len(rows),
        "rows": rows,
        "raw_content_exported": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"failed_cell_count": len(rows), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    main(arguments.root, arguments.output)
