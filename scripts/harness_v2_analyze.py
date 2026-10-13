# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportMissingTypeArgument=false
"""Final-only redacted analysis of Harness v2 requalification attempts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path("/home/super/xiaoming/harness-v2-baseline-requalification/run-001")
STAGES = {
    "stage1": ROOT / "stage1-attempt-002" / "cells",
    "stage1_5": ROOT / "stage1_5" / "cells",
    "stage2": ROOT / "stage2" / "cells",
}
KNOWN_FAILURE_MESSAGES = {
    "manager turn budget exhausted",
    "SDK-native manager returned no textual final answer",
    "Blind verifier did not authorize the terminal synthesis phase",
    "terminal answer has no verifier-bound candidate",
    "terminal answer differs from verifier-bound candidate",
    "terminal answer violates the choice output contract",
    "terminal answer violates the canonical-label output contract",
    "terminal answer violates the short-text output contract",
    "terminal answer is not valid JSON",
    "verifier call budget exhausted",
    "complete verdict lacks a current candidate binding",
    "complete verdict candidate output hash mismatch",
    "complete verdict evidence-state version mismatch",
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def role_usage(out: Path) -> dict[str, dict[str, Any]]:
    roles: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "missing_prompt_usage": 0,
            "missing_completion_usage": 0,
            "provider_latency_ms": 0.0,
        }
    )
    for path in (out / "private" / "api").rglob("*-usage.json"):
        value = read(path)
        role = value.get("recipient", "unknown")
        row = roles[role]
        row["calls"] += 1
        usage = value.get("usage") or {}
        for field, target in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
        ):
            number = usage.get(field)
            if isinstance(number, int):
                row[target] += number
            else:
                row["missing_" + field.split("_")[0] + "_usage"] += 1
    for provider in ("cloud", "local"):
        accounting = out / "api-accounting.json"
        if not accounting.exists():
            continue
        for attempt in read(accounting).get(provider, {}).get("model_attempts", []):
            role = attempt.get("recipient", "unknown")
            latency = attempt.get("latency_ms")
            if isinstance(latency, (int, float)):
                roles[role]["provider_latency_ms"] += latency
    return dict(roles)


def workflow(evs: list[dict[str, Any]]) -> dict[str, Any]:
    actions = [e["payload"]["action"] for e in evs if e["event_type"] == "logical.action.prepared"]
    by_id = {action["action_id"]: index for index, action in enumerate(actions)}
    produced = {
        output["artifact_id"]: index
        for index, action in enumerate(actions)
        for output in action.get("outputs", [])
    }
    signature = []
    for action in actions:
        operator = action.get("operator") if action.get("action_type") == "tool" else "invoke_model"
        signature.append(
            {
                "action_type": action["action_type"],
                "operator": operator,
                "input_flow": [
                    f"produced:{produced[artifact]}" if artifact in produced else f"task:{artifact}"
                    for artifact in action.get("inputs", [])
                ],
                "depends_on": [by_id.get(dep, "unknown") for dep in action.get("depends_on", [])],
                "output_media_types": [out.get("media_type") for out in action.get("outputs", [])],
                "requirements": action.get("requirements")
                if action.get("action_type") == "model"
                else None,
                "owner": action.get("owner_agent_id"),
            }
        )
    physical = [e["payload"] for e in evs if e["event_type"] == "physical.execution"]
    placements = [
        {
            "action_index": by_id.get(item.get("action_id"), "unknown"),
            "agent_ids": (item.get("execution") or {}).get("agent_ids"),
            "deployment_id": (item.get("execution") or {}).get("deployment_id"),
        }
        for item in physical
    ]
    graph = next(
        (e["payload"] for e in reversed(evs) if e["event_type"] == "workflow.graph.snapshot"), None
    )
    terminal = next(
        (
            e["payload"]
            for e in reversed(evs)
            if e["event_type"] == "logical.terminal.candidate_selected"
        ),
        None,
    )
    return {
        "operator_sequence": [item["operator"] for item in signature],
        "logical_signature": signature,
        "graph_node_count": len((graph or {}).get("nodes", [])),
        "graph_edge_count": len((graph or {}).get("edges", [])),
        "synthesis_action_index": None
        if terminal is None
        else by_id.get(terminal.get("source_action_id")),
        "physical_placements": placements,
        "specialist_decisions": sum(
            e["event_type"] == "logical.reasoning.started"
            and e["payload"].get("logical_agent_id") != "manager"
            for e in evs
        ),
    }


def one(stage: str, out: Path) -> dict[str, Any]:
    finished = read(out / "cell-finished.json")
    run_id = finished["run_id"]
    run = out / "runs" / run_id
    result_path = run / "result.json"
    administrative_path = out / "administrative-outcome.json"
    result = (
        read(result_path)
        if result_path.exists()
        else read(administrative_path)
        if administrative_path.exists()
        else None
    )
    trace = events(run / "trace.jsonl")
    physical = [e["payload"] for e in trace if e["event_type"] == "physical.execution"]
    models = [(p.get("execution") or {}).get("model_telemetry") for p in physical]
    successful_models = [m for m in models if isinstance(m, dict)]
    transfers = [t for p in physical for t in (p.get("execution") or {}).get("transfers", [])]
    initial = [] if result is None else result.get("initial_transfers", [])
    telemetry = {} if result is None else result.get("telemetry") or {}
    verification = [e["payload"] for e in trace if e["event_type"] == "logical.verification"]
    schema = [e["payload"] for e in trace if e["event_type"] == "logical.tool.schema_validation"]
    verifier_schema = (
        read(out / "verifier-schema.json") if (out / "verifier-schema.json").exists() else []
    )
    usage = None if result is None or result.get("loop") is None else result["loop"].get("usage")
    accounting = read(out / "api-accounting.json") if (out / "api-accounting.json").exists() else {}
    cloud = accounting.get("cloud", {}).get("roles", {}).get("all", {})
    failure = None if result is None else result.get("failure")
    cleanup = (
        read(out / "worker-shutdown.json") if (out / "worker-shutdown.json").exists() else None
    )
    context = (
        read(out / "context-receipts.json") if (out / "context-receipts.json").exists() else []
    )
    score = (
        None
        if result is None or result.get("evaluation") is None
        else result["evaluation"].get("benchmark_score")
    )
    return {
        "stage": stage,
        "cell": finished["cell"],
        "run_id": run_id,
        "execution_completed": None if result is None else result["execution_completed"],
        "interrupted": None if result is None else result.get("interrupted"),
        "score": score,
        "format_valid": None
        if result is None or result.get("evaluation") is None
        else result["evaluation"].get("format_valid"),
        "failure_code": None if failure is None else failure.get("code"),
        "failure_type": None if failure is None else failure.get("exception_type"),
        "failure_reason": (
            failure.get("message")
            if failure and failure.get("message") in KNOWN_FAILURE_MESSAGES
            else "verifier_schema_validation_failed"
            if failure
            and str(failure.get("message", "")).startswith(
                "Blind verifier failed: ValidationError:"
            )
            else None
        ),
        "system_problems": finished["system_problems"],
        "worker_cleanup": None
        if cleanup is None
        else {
            "drained": cleanup.get("drained"),
            "verified_exited": cleanup.get("verified_exited"),
            "error_count": len(cleanup.get("errors", [])),
        },
        "role_usage": role_usage(out),
        "loop_usage": usage,
        "cloud_api_usd": cloud.get("complete_usd_total"),
        "unknown_cloud_cost_calls": cloud.get("unknown_usd_calls"),
        "e2e_ms": telemetry.get("e2e_latency_ms", finished.get("wall_ms")),
        "cell_wall_ms": finished.get("wall_ms"),
        "initial_bytes": sum(item["bytes_transferred"] for item in initial),
        "action_transfer_bytes": sum(item["bytes_transferred"] for item in transfers),
        "action_transfer_ms": sum(item["duration_ms"] for item in transfers),
        "physical_inference_calls": len(successful_models),
        "physical_service_work_ms": sum(item["service_latency_ms"] for item in successful_models),
        "physical_input_tokens": sum(item.get("input_tokens") or 0 for item in successful_models),
        "physical_output_tokens": sum(item.get("output_tokens") or 0 for item in successful_models),
        "physical_missing_usage_calls": sum(
            item.get("input_tokens") is None or item.get("output_tokens") is None
            for item in successful_models
        ),
        "physical_rejections": Counter(
            e["payload"].get("failure_code") or "unknown"
            for e in trace
            if e["event_type"] == "logical.model.outcome" and not e["payload"].get("succeeded")
        ),
        "schema_calls": len(schema),
        "schema_invalid": sum(not item.get("valid") for item in schema),
        "verifier_schema_calls": len(verifier_schema),
        "verifier_schema_invalid": sum(not item.get("valid") for item in verifier_schema),
        "verification_statuses": dict(Counter(item.get("status") for item in verification)),
        "verification_calls": len(verification),
        "terminal_candidates": sum(
            event["event_type"] == "logical.terminal.candidate_selected" for event in trace
        ),
        "context_rejections": sum(item.get("decision") == "reject" for item in context),
        "context_integrity_failures": sum(
            item.get("error_code") in {"context_integrity_failed", "context_preflight_unavailable"}
            or (
                item.get("decision") == "allow"
                and item.get("http_status") == 200
                and not item.get("integrity_verified")
            )
            for item in context
        ),
        "workflow": workflow(trace),
        "bridge_feasibility": [
            {
                key: value
                if key != "seal_failure_reason" or value is None
                else str(value).split(":", 1)[0]
                for key, value in event["payload"].items()
            }
            for event in trace
            if event["event_type"] == "workflow.v2.feasibility"
        ],
        "ledger_guidance_calls": sum(
            e["event_type"] == "logical.cost_ledger.predecision" for e in trace
        ),
        "raw_profile_guidance_calls": sum(
            e["event_type"] == "logical.profile.predecision" for e in trace
        ),
    }


def differences(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["stage"] != "stage2":
            continue
        cell = row["cell"]
        groups[(cell["source_task_id"], cell["network"], cell["trial"])][cell["method"]] = row
    result = []
    for key, methods in sorted(groups.items()):
        if "BLIND" not in methods:
            continue
        baseline = methods["BLIND"]
        for name in ("AWARE", "LEDGER"):
            if name not in methods:
                continue
            method = methods[name]
            logical_equal = (
                baseline["workflow"]["logical_signature"] == method["workflow"]["logical_signature"]
            )
            placement_equal = (
                baseline["workflow"]["physical_placements"]
                == method["workflow"]["physical_placements"]
            )
            level = "L2" if not logical_equal else "L0" if placement_equal else "L1"
            result.append(
                {
                    "source_task_id": key[0],
                    "network": key[1],
                    "trial": key[2],
                    "method": name,
                    "change_level": level,
                    "blind_score": baseline["score"],
                    "method_score": method["score"],
                    "blind_e2e_ms": baseline["e2e_ms"],
                    "method_e2e_ms": method["e2e_ms"],
                    "blind_transfer_bytes": baseline["initial_bytes"]
                    + baseline["action_transfer_bytes"],
                    "method_transfer_bytes": method["initial_bytes"]
                    + method["action_transfer_bytes"],
                    "blind_physical_service_work_ms": baseline["physical_service_work_ms"],
                    "method_physical_service_work_ms": method["physical_service_work_ms"],
                    "blind_operator_sequence": baseline["workflow"]["operator_sequence"],
                    "method_operator_sequence": method["workflow"]["operator_sequence"],
                }
            )
    return result


def main(output: Path) -> None:
    if output.exists():
        raise FileExistsError("sanitized analysis already exists")
    rows = []
    incomplete = []
    for stage, folder in STAGES.items():
        if not folder.exists():
            continue
        for cell in sorted(folder.iterdir()):
            if not cell.is_dir():
                continue
            if (cell / "cell-finished.json").exists():
                rows.append(one(stage, cell))
            else:
                incomplete.append({"stage": stage, "cell_id": cell.name})
    report = {
        "version": "harness-v2-requalification-sanitized-analysis-001",
        "stage_counts": dict(Counter(row["stage"] for row in rows)),
        "incomplete_claims": incomplete,
        "cells": rows,
        "paired_workflow_differences": differences(rows),
        "local_gpu_usd": None,
        "statistical_significance_claimed": False,
        "raw_trace_exported": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "stage_counts": report["stage_counts"],
                "incomplete_claims": len(incomplete),
                "output": str(output),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
