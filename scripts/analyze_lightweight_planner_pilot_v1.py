"""Offline aggregation on the experiment host; export numeric, content-free evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def total(values):
    values = list(values)
    return sum(values) if all(v is not None for v in values) else None


def usd(rows, role="all"):
    records = [r["cost_accounting"]["cloud"]["roles"][role] for r in rows]
    return {
        "known_usd_subtotal": str(sum(Decimal(r["known_usd_subtotal"]) for r in records)),
        "complete_usd_total": str(sum(Decimal(r["complete_usd_total"]) for r in records))
        if all(r["complete_usd_total"] is not None for r in records)
        else None,
        "unknown_usd_calls": sum(r["unknown_usd_calls"] for r in records),
    }


def enrich(root, row):
    cell = root / "cells" / row["cell"]["cell_id"]
    traces = list((cell / "runs").glob("*/trace.jsonl"))
    events = [
        read_line for p in traces for read_line in map(json.loads, p.read_text().splitlines())
    ]
    run_paths = list((cell / "runs").glob("*/result.json"))
    raw = read(run_paths[0]) if run_paths else read(cell / "administrative-outcome.json")
    message = (raw.get("failure") or {}).get("message", "").lower()
    failure_type = (raw.get("failure") or {}).get("exception_type", "")
    provider_errors = Counter()
    for path in (cell / "private/api").rglob("*-response.json"):
        error = read(path).get("error")
        if error:
            text = str(error).lower()
            category = (
                "invalid_generated_json"
                if "json" in text and "unexpected" in text
                else "provider_error_other"
            )
            provider_errors[category] += 1
    if row["successful"]:
        outcome = "success"
    elif row["completed"]:
        outcome = "incorrect_answer"
    elif row["context_rejections"] or "context_limit_exceeded" in message:
        outcome = "context_budget_exceeded"
    elif provider_errors["invalid_generated_json"]:
        outcome = "provider_generated_json_invalid"
    elif "maxturns" in failure_type.lower() or "max turns" in message or "turn budget" in message:
        outcome = "turn_budget_exhausted"
    elif "budget" in failure_type.lower() or any(
        s in message for s in ("quota", "budget exhausted", "deadline")
    ):
        outcome = "resource_budget_exhausted"
    elif "terminal" in message or "final answer" in message:
        outcome = "terminal_contract_failed"
    elif any(s in message for s in ("verification", "verifier", "submit_verification")):
        outcome = "verification_failed"
    else:
        outcome = (row.get("failure") or {}).get("code", "unclassified_failure")
    row["outcome_type"] = outcome
    row["provider_error_types"] = dict(provider_errors)
    failed_run = [e["payload"] for e in events if e["event_type"] == "run.failed"]
    row["task_e2e_ms"] = (row.get("telemetry") or {}).get("e2e_latency_ms")
    if row["task_e2e_ms"] is None and failed_run:
        row["task_e2e_ms"] = failed_run[-1].get("e2e_latency_ms")
    schema = [e["payload"] for e in events if e["event_type"] == "logical.tool.schema_validation"]
    failed_owners = {e["owner_agent_id"] for e in schema if not e["valid"]}
    recovered = set()
    seen_failed = set()
    for e in schema:
        owner = e["owner_agent_id"]
        if not e["valid"]:
            seen_failed.add(owner)
        elif owner in seen_failed:
            recovered.add(owner)
    verifier_schema = read(cell / "verifier-schema.json")
    row["schema_detail"] = {
        "operator_or_delegation_invalid": row["schema_failures"],
        "owners_with_invalid_call": len(failed_owners),
        "owners_with_later_valid_call": len(recovered),
        "verifier_invalid": sum(not v["valid"] for v in verifier_schema),
        "missing_arguments": sum(
            any("'arguments' is a required property" in error for error in e["errors"])
            for e in schema
            if not e["valid"]
        ),
    }
    statuses = Counter()
    signatures = Counter()
    for e in events:
        if e["event_type"] == "logical.verification":
            statuses[e["payload"]["status"]] += 1
        if e["event_type"] == "logical.action.selected":
            p = e["payload"]
            # Count repeated semantic calls without exporting arguments or artifact identities.
            signature = json.dumps(
                {"operator": p["operator"], "arguments": p["selected_tool_arguments"]},
                sort_keys=True,
            )
            signatures[hashlib.sha256(signature.encode()).hexdigest()] += 1
    row["workflow_detail"] = {
        "operators": dict(Counter(n["operator"] for n in row["workflow"]["nodes"])),
        "owners": dict(Counter(n["owner"] for n in row["workflow"]["nodes"])),
        "node_count": len(row["workflow"]["nodes"]),
        "edge_count": len(row["workflow"]["edges"]),
        "verifier_statuses": dict(statuses),
        "repeated_identical_selected_calls": sum(n - 1 for n in signatures.values()),
        "specialist_invocations": row["created_specialists"],
    }
    context = read(cell / "context-receipts.json")
    row["context_detail"] = {
        "allowed": sum(r.get("decision") == "allow" for r in context),
        "integrity_verified": sum(bool(r.get("integrity_verified")) for r in context),
        "rejected": row["context_rejections"],
        "maximum_rendered_tokens": max(
            (r.get("rendered_tokens", r.get("prompt_tokens", 0)) for r in context), default=0
        ),
    }
    per_node = {}
    for p in sorted((cell / "private/residency-log-intervals").glob("*.json")):
        intervals = read(p)["intervals"]
        text = "\n".join(v["text"] for v in intervals.values())
        per_node[p.stem] = {
            "runner_task_starts": len(re.findall(r"processing task, is_child = 0", text)),
            "reported_total_times_ms": [
                float(v) for v in re.findall(r"total time\s*=\s*([\d.]+)\s*ms", text)
            ],
        }
    row["resident_runner_work"] = {
        "nodes": per_node,
        "observed_task_starts": sum(v["runner_task_starts"] for v in per_node.values()),
        "reported_total_time_ms_sum": sum(
            sum(v["reported_total_times_ms"]) for v in per_node.values()
        ),
        "scope": (
            "all five resident runners, including local Planner and physical execution; "
            "partial service proxy, not GPU compute"
        ),
    }
    api_bytes = Counter()
    for p in (cell / "private/api").rglob("*.json"):
        if p.name.endswith("-request.json"):
            api_bytes["persisted_request_json_bytes"] += p.stat().st_size
        elif p.name.endswith("-response.json"):
            api_bytes["persisted_response_json_bytes"] += p.stat().st_size
    row["api_payload_storage_bytes"] = dict(api_bytes)
    return row


def aggregate(rows):
    roles = {}
    for role in ("manager", "specialist", "verifier"):
        roles[role] = {
            field: total(r["roles"][role][field] for r in rows)
            for field in (
                "requests",
                "turns",
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "provider_latency_ms",
            )
        }
        roles[role]["cloud_api_cost"] = usd(rows, role)
    return {
        "executed": len(rows),
        "completed": sum(r["completed"] for r in rows),
        "successful": sum(r["successful"] for r in rows),
        "completion": sum(r["completed"] for r in rows) / len(rows) if rows else None,
        "tsr": sum(r["successful"] for r in rows) / len(rows) if rows else None,
        "outcome_types": dict(Counter(r["outcome_type"] for r in rows)),
        "tool_failure_counts": dict(sum((Counter(r["failure_counts"]) for r in rows), Counter())),
        "schema_failures": sum(r["schema_failures"] for r in rows),
        "missing_arguments_failures": sum(r["schema_detail"]["missing_arguments"] for r in rows),
        "verifier_schema_failures": sum(r["schema_detail"]["verifier_invalid"] for r in rows),
        "roles": roles,
        "cloud_api_cost": usd(rows),
        "full_resource_monetary_cost": None,
        "physical": {
            field: total(r["physical"][field] for r in rows)
            for field in (
                "admitted_requests",
                "successful_inference_calls",
                "failed_actions",
                "input_tokens",
                "output_tokens",
                "known_model_service_ms",
                "operator_ms",
                "initial_transfer_bytes",
                "action_transfer_bytes",
            )
        },
        "task_e2e_ms": total(r["task_e2e_ms"] for r in rows),
        "controller_execution_wall_ms": total(r["timing"]["wall_ms"] for r in rows),
        "runner_task_starts": sum(r["resident_runner_work"]["observed_task_starts"] for r in rows),
        "runner_reported_total_time_ms": sum(
            r["resident_runner_work"]["reported_total_time_ms_sum"] for r in rows
        ),
    }


def report(data):
    groups = data["groups"]
    lines = [
        "# Lightweight Planner Competence Pilot — formal results",
        "",
        f"Completed matrix: {len(data['cells'])}/18 cells. Base `41d034d`; no selective "
        "model reruns or additional capability gates. "
        "Prior No-Go reports remain historical evidence.",
        "",
        "| Group | Completion | TSR | Raw schema failures | Cloud API USD (known) | Full cost |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for group, r in groups.items():
        lines.append(
            f"| {group} | {r['completed']}/{r['executed']} | "
            f"{r['successful']}/{r['executed']} | {r['schema_failures']} | "
            f"{r['cloud_api_cost']['known_usd_subtotal']} | unknown |"
        )
    lines += [
        "",
        (
            "B0 = strong Manager without Skills; B1 = local 8B without Skills; B2 = same"
            " local 8B with frozen Skills. Specialist and Verifier remain strong. All "
            "groups use identical raw-call validation."
        ),
        "",
        "## Cells and workflow",
        "",
        (
            "| Cell | Task | Group | Completion | Score | Outcome | M/S/V turns | Schema"
            " failures | Physical successes/admissions | E2E s |"
        ),
        "|---|---|---|---|---|---|---|---:|---|---:|",
    ]
    for r in data["cells"]:
        c = r["cell"]
        score = (r["original_evaluation"] or {}).get("score", "unknown")
        turns = "/".join(
            str(r["roles"][role]["turns"]) for role in ("manager", "specialist", "verifier")
        )
        e2e = round(r["task_e2e_ms"] / 1000, 3) if r["task_e2e_ms"] is not None else "unknown"
        p = r["physical"]
        lines.append(
            f"| {c['cell_id']} | {c['family']}/{c['position']} | {c['group']} | "
            f"{r['completed']} | {score} | {r['outcome_type']} | {turns} | "
            f"{r['schema_failures']} | {p['successful_inference_calls']}/"
            f"{p['admitted_requests']} | {e2e} |"
        )
    lines += [
        "",
        "## Control and physical resources",
        "",
        (
            "| Group/role | Turns | Input tokens | Output tokens | Cached input | API "
            "USD known subtotal |"
        ),
        "|---|---:|---:|---:|---:|---:|",
    ]
    for group, r in groups.items():
        for role, v in r["roles"].items():
            lines.append(
                f"| {group}/{role} | {v['turns']} | {v['input_tokens']} | "
                f"{v['output_tokens']} | {v['cached_input_tokens']} | "
                f"{v['cloud_api_cost']['known_usd_subtotal']} |"
            )
    lines += [
        "",
        (
            "Missing usage remains unknown (JSON null); zero recorded requests yields "
            "zero measured usage. Cloud API estimates use the frozen provider price card"
            " and FX reference, not billing statements. Local Planner "
            "GPU/energy/monetary cost and physical GPU cost remain unknown. Known cloud "
            "subtotals cannot establish a total-cost advantage."
        ),
        "",
        (
            "| Group | Physical successes/admissions | Physical service s (known) | "
            "Runner starts | Runner reported service s | E2E s | Initial/action bytes |"
        ),
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for group, r in groups.items():
        p = r["physical"]
        e2e = round(r["task_e2e_ms"] / 1000, 3) if r["task_e2e_ms"] is not None else "unknown"
        lines.append(
            f"| {group} | {p['successful_inference_calls']}/{p['admitted_requests']} | "
            f"{p['known_model_service_ms'] / 1000:.3f} | {r['runner_task_starts']} | "
            f"{r['runner_reported_total_time_ms'] / 1000:.3f} | {e2e} | "
            f"{p['initial_transfer_bytes']}/{p['action_transfer_bytes']} |"
        )
    lines += [
        "",
        (
            "Successful physical calls have backend telemetry. Admissions may fail "
            "before inference and are not all actual model calls. Failed/cancelled calls"
            " can have unmeasured work. Runner log starts include both the local Planner"
            " and Executor; runner timing sums are partial service proxies, never GPU "
            "busy time. Service sums can overlap and must not be added to E2E. Transfer "
            "counts are application artifact bytes, not wire traffic. Per-cell worker "
            "setup, tc, SSH and cleanup sit outside task E2E."
        ),
        "",
        "## Paired behavior and Skills effect",
        "",
        "| Task | B0 workflow | B1 workflow | B2 workflow |",
        "|---|---|---|---|",
    ]
    for task in range(1, 7):
        paired = {r["cell"]["group"]: r for r in data["cells"] if r["cell"]["task_index"] == task}
        entries = []
        for group in ("B0", "B1", "B2"):
            r = paired.get(group)
            if r is None:
                entries.append("not run")
                continue
            ops = (
                " → ".join(n["operator"] for n in r["workflow"]["nodes"])
                or "no executed graph nodes"
            )
            d = r["workflow_detail"]
            entries.append(
                f"{ops}; specialists={d['specialist_invocations']}; "
                f"edges={d['edge_count']}; {r['outcome_type']}"
            )
        lines.append(f"| {task} | " + " | ".join(entries) + " |")
    if all(groups[g]["executed"] == 6 for g in ("B0", "B1", "B2")):
        b0, b1, b2 = (groups[g] for g in ("B0", "B1", "B2"))
        lines += [
            "",
            "B1→B2 paired Skills difference: completion "
            f"{b2['completed'] - b1['completed']:+d}/6; TSR "
            f"{b2['successful'] - b1['successful']:+d}/6; schema failures "
            f"{b2['schema_failures'] - b1['schema_failures']:+d}. B0→B2 quality difference: "
            f"TSR {b2['successful'] - b0['successful']:+d}/6. The machine-readable artifact "
            "provides the full turns, tokens, calls, service work, E2E and transfer vector "
            "for both comparisons. GPU prices remain unknown, so no complete monetary "
            "cost ratio is identified.",
        ]
    lines += [
        "",
        (
            "These are six previously examined tasks with one execution per group, a "
            "descriptive feasibility pilot. No significance, non-inferiority, held-out "
            "generalization or causal adapter-effect claim is supported. Execution order"
            " is frozen and balanced across tasks; cache and sequential residency "
            "effects remain possible."
        ),
        "",
        "## Infra-aware Workflow Adapter decision",
        "",
        data["adapter_decision"]["reason"],
        "",
        "## Evidence and execution safety",
        "",
        (
            "The adjacent `pilot-results.json` contains each sanitized cell, numeric "
            "resources, workflow structure, schema recovery counters and SHA-256 links "
            "to remote raw evidence. Raw API payloads, traces, artifact bodies, "
            "evaluator details and logs stay on experiment machines. "
            "`execution-freeze.json` preserves deployed source hashes; append-only "
            "journal preserves order. Zero-model initialization corrections are separate"
            " from the competence matrix. The final integrity receipt records "
            "source/history/Skills consistency, tc restoration, Worker termination and "
            "context checks. Benchmark, evaluator, frozen Skills, semantic instructions,"
            " Physical Scheduler and Executor were not modified."
        ),
    ]
    return "\n".join(lines).replace("| None |", "| unknown |") + "\n"


def main(root, output):
    if not (root / "matrix-complete.json").exists():
        raise RuntimeError("refusing to publish an incomplete matrix as completed")
    freeze = read(root / "execution-freeze.json")
    rows = [
        enrich(root, read(root / "cells" / c["cell_id"] / "sanitized-result.json"))
        for c in freeze["ordered_cells"]
    ]
    assert len(rows) == 18 and not any(r["system_problems"] for r in rows)
    groups = {
        g: aggregate([r for r in rows if r["cell"]["group"] == g]) for g in ("B0", "B1", "B2")
    }
    b2 = groups["B2"]
    # A transparent feasibility heuristic, not an additional model admission gate.
    go = b2["successful"] >= 4 and b2["completed"] >= 5
    decision = {
        "decision": "GO_bounded_followup" if go else "NO_GO_adapter_now",
        "posthoc_descriptive_heuristic": True,
        "reason": (
            "GO for a bounded adapter follow-up: B2 completes at least five and succeeds"
            " on at least four of these six tasks. Use paired workflow/resource evidence"
            " to select one infrastructure hypothesis; this pilot does not validate an "
            "adapter or establish total-cost savings."
        )
        if go
        else (
            "NO-GO for adding the Infra-aware Workflow Adapter now: B2 does not meet the"
            " descriptive feasibility threshold of five completions and four successes "
            "out of six. Address the observed context/protocol/semantic competence "
            "limitations first. Infrastructure adaptation has no demonstrated ability to"
            " repair those failures; do not launch a further experiment automatically."
        ),
    }
    data = {
        "version": "lightweight-planner-formal-results-v1",
        "base_commit": "41d034d",
        "remote_namespace": root.name,
        "matrix": read(root / "matrix-complete.json"),
        "groups": groups,
        "families": {
            family: {
                g: aggregate(
                    [r for r in rows if r["cell"]["family"] == family and r["cell"]["group"] == g]
                )
                for g in groups
            }
            for family in {r["cell"]["family"] for r in rows}
        },
        "adapter_decision": decision,
        "cells": rows,
    }
    output.mkdir(parents=True, exist_ok=False)
    write(output / "pilot-results.json", data)
    (output / "report.md").write_text(report(data), encoding="utf-8", newline="\n")
    for name in (
        "execution-freeze.json",
        "matrix-complete.json",
        "first-task-audit.json",
        "deployment.json",
        "initialization-correction-001.json",
        "initialization-correction-002.json",
    ):
        write(output / name, read(root / name))
    for name in ("reporting-repair.json", "continuation-source-freeze.json"):
        if (root / name).exists():
            write(output / name, read(root / name))
    (output / "journal.jsonl").write_bytes((root / "journal.jsonl").read_bytes())
    active_sources = (
        read(root / "continuation-source-freeze.json")
        if (root / "continuation-source-freeze.json").exists()
        else freeze["source_sha256"]
    )
    source_ok = all(
        hashlib.sha256((root / "app" / p).read_bytes()).hexdigest() == h
        for p, h in active_sources.items()
    )
    protected_ok = all(
        hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
        for p, h in freeze["protected_sha256"].items()
    )
    write(
        output / "final-integrity.json",
        {
            "source_unchanged": source_ok,
            "protected_history_and_skills_unchanged": protected_ok,
            "all_workers_drained_and_exited": all(
                r["cleanup"]["drained"] and r["cleanup"]["verified_exited"] for r in rows
            ),
            "system_problems": [p for r in rows for p in r["system_problems"]],
            "semantic_retries": 0,
            "private_raw_evidence_exported": False,
        },
    )
    assert source_ok and protected_ok
    print(
        json.dumps(
            {
                "groups": {
                    g: {
                        k: r[k]
                        for k in (
                            "executed",
                            "completed",
                            "successful",
                            "schema_failures",
                            "outcome_types",
                        )
                    }
                    for g, r in groups.items()
                },
                "adapter_decision": decision,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.root, args.output)
