"""Export scalar-only fixed-workflow evidence from the isolated controller."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infra_joint.evaluation.trace_audit import summarize_cost


def _json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _qdisc_kind(value: str) -> str | None:
    for line in value.splitlines():
        words = line.split()
        if len(words) > 2 and words[0] == "qdisc" and "root" in words:
            return words[1]
    return None


def analyze(root: Path, attempt: str, cells: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        directory = root / "evidence" / attempt / cell
        summary = _json(directory / "summary.json")
        tc = _json(directory / "tc-attestation.json")
        cleanup = _json(directory / "worker-cleanup.json")
        traces = (
            list((directory / "runs").glob("*/trace.jsonl"))
            if (directory / "runs").is_dir()
            else []
        )
        events = (
            [json.loads(line) for line in traces[0].open(encoding="utf-8") if line.strip()]
            if len(traces) == 1
            else []
        )
        cost = summarize_cost(events) if events else None
        actions = []
        for event in events:
            if event["event_type"] != "physical.execution":
                continue
            payload = event["payload"]
            execution = payload.get("execution") or {}
            transfer = execution.get("transfers", [])
            model = execution.get("model_telemetry") or {}
            actions.append(
                {
                    "action_id": payload.get("action_id"),
                    "operator": execution.get("operator"),
                    "selected_agent": None
                    if payload.get("selection") is None
                    else payload["selection"].get("selected_agent_id"),
                    "completed": bool(execution),
                    "operator_latency_ms": execution.get("operator_latency_ms"),
                    "transfer_bytes": sum(t.get("bytes_transferred", 0) for t in transfer),
                    "transfer_latency_ms": sum(t.get("duration_ms", 0) for t in transfer),
                    "model_service_ms": model.get("service_latency_ms"),
                    "model_input_tokens": model.get("input_tokens"),
                    "model_output_tokens": model.get("output_tokens"),
                }
            )
        evaluation = None if summary is None else summary.get("original_evaluation")
        restored = None
        if tc is not None and tc.get("restored_qdisc") is not None:
            restored = tc.get("cleanup_error") is None and all(
                _qdisc_kind(tc["original_qdisc"][key]) == _qdisc_kind(value)
                for key, value in tc["restored_qdisc"].items()
            )
        rows.append(
            {
                "cell": cell,
                "status": "completed" if summary is not None else "missing_or_interrupted",
                "execution_completed": None if summary is None else summary["execution_completed"],
                "valid_output": None if summary is None else summary["valid_output"],
                "original_task_score": None
                if evaluation is None
                else evaluation["benchmark_score"],
                "task_success": None
                if evaluation is None
                else bool(evaluation["benchmark_score"] >= 1),
                "failure_code": None if summary is None else summary["failure_code"],
                "failure_type": None if summary is None else summary["failure_type"],
                "cost": cost,
                "actions": actions,
                "configured_network": None if tc is None else tc["network"],
                "tc_restored": restored,
                "own_workers_cleaned": None if cleanup is None else not cleanup["errors"],
                "trace_sha256": (
                    hashlib.sha256(traces[0].read_bytes()).hexdigest() if len(traces) == 1 else None
                ),
            }
        )
    return {
        "condition_id": "infra-workflow-opportunity-v1-fixed-transport-fix-1",
        "attempt": attempt,
        "raw_task_or_trace_content_exported": False,
        "rows": rows,
        "gpu_monetary_cost": "unknown",
        "cloud_api_usd_for_fixed_policy": 0,
        "method_note": "fixed deterministic Manager policy; no cloud Manager/Specialist/Verifier",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--attempt", default="transport-fix-1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.root, args.attempt, ["fast-frames", "fast-sheet", "slow-frames", "slow-sheet"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
