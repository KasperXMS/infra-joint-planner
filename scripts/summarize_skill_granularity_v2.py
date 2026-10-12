"""Summarize the completed v2 pilot against v1 using sanitized results only."""

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def number(value):
    return value if type(value) in (int, float) else 0


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
        + ["| " + " | ".join(str(item) for item in row) + " |" for row in rows]
    )


def snapshot(data):
    cells = data["cells"]
    role = {}
    for name in ("manager", "specialist", "verifier"):
        parts = [cell["roles"][name] for cell in cells]
        role[name] = {
            "turns": sum(number(part.get("turns")) for part in parts),
            "requests": sum(number(part.get("requests")) for part in parts),
            "known_input_tokens": sum(number(part.get("known_input_tokens_subtotal")) for part in parts),
            "known_output_tokens": sum(number(part.get("known_output_tokens_subtotal")) for part in parts),
            "unknown_token_usage_requests": sum(number(part.get("unknown_token_usage_requests")) for part in parts),
        }
    cloud = [cell["cost_accounting"]["cloud"]["roles"]["all"] for cell in cells]
    usd = sum((Decimal(part["known_usd_subtotal"]) for part in cloud), Decimal(0))
    return {
        "cells": len(cells),
        "completed": sum(bool(cell["completed"]) for cell in cells),
        "successful": sum(bool(cell["successful"]) for cell in cells),
        "provider_timeout_cells": sum(cell["outcome_type"] == "provider_timeout_error" for cell in cells),
        "outcomes": dict(Counter(cell["outcome_type"] for cell in cells)),
        "schema_failures": sum(number(cell["schema_failures"]) for cell in cells),
        "roles": role,
        "known_cloud_api_usd": str(usd),
        "unknown_cloud_usd_calls": sum(number(part["unknown_usd_calls"]) for part in cloud),
        "physical_successful_inference_calls": sum(number(cell["physical"]["successful_inference_calls"]) for cell in cells),
        "physical_known_model_service_ms": sum(number(cell["physical"]["known_model_service_ms"]) for cell in cells),
        "transfer_bytes": sum(number(cell["physical"]["initial_transfer_bytes"]) + number(cell["physical"]["action_transfer_bytes"]) for cell in cells),
        "batch_wall_hours": data["matrix_wall_ms"] / 3600000,
        "full_gpu_monetary_cost": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1", type=Path, required=True)
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--request-timing", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old, new, timing = read(args.v1), read(args.v2), read(args.request_timing)
    if old["analyzed_cells"] != 30 or new["analyzed_cells"] != 30:
        raise RuntimeError("incomplete compared matrix")
    old_plan = old["execution_freeze"]["frozen_configuration"]["plan"]
    new_plan = new["execution_freeze"]["frozen_configuration"]["plan"]
    for field in ("tasks", "skills", "models", "order", "fixed_specialist", "fixed_verifier"):
        if old_plan[field] != new_plan[field]:
            raise RuntimeError("v1/v2 frozen condition drift: " + field)
    if {cell["cell"]["cell_id"] for cell in old["cells"]} != {cell["cell"]["cell_id"] for cell in new["cells"]}:
        raise RuntimeError("v1/v2 cell identity mismatch")
    if new["final_integrity"]["numeric_evidence"].get("system_problems"):
        raise RuntimeError("v2 final integrity contains a system problem")
    v1, v2 = snapshot(old), snapshot(new)
    keys = [f"{model}__{skill}" for model in ("qwen35-4b", "qwen35-9b", "qwen35-27b") for skill in (("S0", "S3") if model == "qwen35-27b" else ("S0", "S1", "S2", "S3"))]
    conditions = []
    for key in keys:
        a, b = old["conditions"][key], new["conditions"][key]
        conditions.append(
            {
                "condition": key,
                "v1_completion": f"{a['completed']}/3",
                "v2_completion": f"{b['completed']}/3",
                "v1_tsr": f"{a['successful']}/3",
                "v2_tsr": f"{b['successful']}/3",
                "v1_timeouts": a["outcome_types"].get("provider_timeout_error", 0),
                "v2_timeouts": b["outcome_types"].get("provider_timeout_error", 0),
                "v2_schema_failures": b["schema_failures"],
                "v2_cloud_api_usd": b["cloud_api_cost"]["complete_usd_total"],
            }
        )
    by_id = {cell["cell"]["cell_id"]: cell for cell in new["cells"]}
    trajectories = []
    for model in ("qwen35-4b", "qwen35-9b", "qwen35-27b"):
        for task in (1, 2, 3):
            row = {"model": model, "task": task}
            for skill in (("S0", "S3") if model == "qwen35-27b" else ("S0", "S1", "S2", "S3")):
                cell = by_id[f"{model}-t{task}-{skill}"]
                row[skill] = cell["outcome_type"]
            trajectories.append(row)
    latencies = defaultdict(lambda: {"queue": [], "provider": [], "timeouts": 0})
    request_count = 0
    for cell in timing["cells"]:
        for request in cell["transport_requests"]:
            request_count += 1
            bucket = latencies[request["endpoint_slot"]]
            if request["queue_wait_ms"] is not None:
                bucket["queue"].append(request["queue_wait_ms"])
            if request["provider_latency_ms"] is not None:
                bucket["provider"].append(request["provider_latency_ms"])
            bucket["timeouts"] += "Timeout" in str(request["error_type"])
    latency = {
        name: {
            "requests": len(bucket["provider"]),
            "queue_p50_ms": percentile(bucket["queue"], 0.5),
            "queue_p95_ms": percentile(bucket["queue"], 0.95),
            "provider_p50_ms": percentile(bucket["provider"], 0.5),
            "provider_p95_ms": percentile(bucket["provider"], 0.95),
            "transport_timeouts": bucket["timeouts"],
        }
        for name, bucket in latencies.items()
    }
    summary = {
        "version": "skill-granularity-v2-vs-v1-descriptive-summary",
        "same_frozen_tasks_skills_models_order": True,
        "v2_is_not_independent_held_out_validation": True,
        "v1": v1,
        "v2": v2,
        "conditions": conditions,
        "v2_task_trajectories": trajectories,
        "v2_request_timing": latency,
        "v2_transport_request_count": request_count,
        "gpu_price": None,
        "exploratory_only_three_tasks_per_condition": True,
    }
    lines = [
        "# Skill Granularity Pilot v2: comparison with v1",
        "",
        "The same frozen 30 cells were each executed once in a separate v2 namespace. "
        "V2 is a serving rerun of the same three tasks, not independent held-out validation. "
        "Ollama 0.34.0 cannot use multiple runner slots for the qwen35 architecture; "
        "A28 used two independent one-slot replicas after a three-replica load left only "
        "4.8 GiB MemAvailable, below the 8 GiB reserve. Three workflows were dispatched "
        "concurrently, with client-side Manager slot admission and 300-second HTTP timeout.",
        "",
        f"V1 completed {v1['completed']}/30 with {v1['successful']}/30 task successes and {v1['provider_timeout_cells']} provider-timeout cells. "
        f"V2 completed {v2['completed']}/30 with {v2['successful']}/30 task successes and {v2['provider_timeout_cells']} provider-timeout cells. "
        f"Batch wall time was {v1['batch_wall_hours']:.2f} h in v1 and {v2['batch_wall_hours']:.2f} h in v2.",
        "",
        "## Completion, TSR and failure changes",
        "",
        table(
            ["Model × Skill", "v1 Completion", "v2 Completion", "v1 TSR", "v2 TSR", "v1 timeouts", "v2 timeouts", "v2 schema failures"],
            [[row[k] for k in ("condition", "v1_completion", "v2_completion", "v1_tsr", "v2_tsr", "v1_timeouts", "v2_timeouts", "v2_schema_failures")] for row in conditions],
        ),
        "",
        "## Resources and cost",
        "",
        table(
            ["Metric", "v1", "v2"],
            [
                ["Known cloud API USD", v1["known_cloud_api_usd"], v2["known_cloud_api_usd"]],
                ["Physical successful inference calls", v1["physical_successful_inference_calls"], v2["physical_successful_inference_calls"]],
                ["Known physical model-service ms", round(v1["physical_known_model_service_ms"]), round(v2["physical_known_model_service_ms"])],
                ["Data transfer bytes", v1["transfer_bytes"], v2["transfer_bytes"]],
                ["GPU monetary cost", "unknown", "unknown"],
            ]
            + [[f"{role} {metric}", v1["roles"][role][metric], v2["roles"][role][metric]] for role in ("manager", "specialist", "verifier") for metric in ("turns", "known_input_tokens", "known_output_tokens")],
        ),
        "",
        "Known cloud USD excludes unknown local GPU cost. Model-service times and E2E are "
        "diagnostic under overlapping workflows and may include shared work. Early failure "
        "can reduce usage without improving efficiency.",
        "",
        "## Manager request timing",
        "",
        table(
            ["Endpoint", "Requests", "Queue p50 ms", "Queue p95 ms", "Provider p50 ms", "Provider p95 ms", "Transport timeouts"],
            [[name, value["requests"], round(value["queue_p50_ms"] or 0), round(value["queue_p95_ms"] or 0), round(value["provider_p50_ms"] or 0), round(value["provider_p95_ms"] or 0), value["transport_timeouts"]] for name, value in sorted(latency.items())],
        ),
        "",
        "Queue wait is measured before HTTP dispatch; provider latency includes Ollama "
        "response time and is not exclusive GPU inference time. Per-request UTC start, "
        "finish, status and tokens are in the sanitized timing export.",
        "",
        "## Per-task v2 outcomes",
        "",
        table(["Model", "Task", "S0", "S1", "S2", "S3"], [[row.get(key, "—") for key in ("model", "task", "S0", "S1", "S2", "S3")] for row in trajectories]),
        "",
        "Skill granularity effects are exploratory: three tasks per condition cannot establish "
        "statistical significance. The fixed slot assignment sometimes gave one replica two "
        "workflows while the other had one, so queue exposure differs by condition; read "
        "completion, TSR and provider failures together. See the full v2 report for schema, "
        "Verifier amplification, recovery and workflow structure.",
        "",
    ]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (args.output / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"cells": len(new["cells"]), "v2_timeouts": v2["provider_timeout_cells"], "requests": request_count}))


if __name__ == "__main__":
    main()
