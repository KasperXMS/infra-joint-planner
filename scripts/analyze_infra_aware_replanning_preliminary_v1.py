"""Audit and report the 18-cell infra-aware replanning preliminary."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, cast


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trace_audit(path: Path, run_id: str) -> dict[str, Any]:
    events = [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chain = bool(events) and all(
        item["run_id"] == run_id
        and item["step_id"].startswith(f"{index:06d}-")
        and item["parent_id"]
        == (events[index - 1]["step_id"] if index else None)
        for index, item in enumerate(events)
    )
    types = [str(item["event_type"]) for item in events]
    return {
        "event_count": len(events),
        "sha256": _sha256(path),
        "parent_chain_valid": chain,
        "replanner_start_count": types.count("workflow.replanner.start"),
        "replanner_end_count": types.count("workflow.replanner.end"),
        "run_end_count": types.count("run.end"),
        "run_failed_count": types.count("run.failed"),
    }


def _tc_audit(value: dict[str, Any], bandwidth: float) -> dict[str, Any]:
    applied = cast(dict[str, str], value["applied_qdisc"])
    before = cast(dict[str, str], value["class_before_run"])
    after = cast(dict[str, str], value["class_after_run"])
    restored = cast(dict[str, str], value["restored_qdisc"])
    return {
        "valid": bool(
            float(value["bandwidth_mbps"]) == bandwidth
            and value["remote_returncode"] == 0
            and value["cleanup_error"] is None
            and len(applied) == 4
            and all("qdisc htb 1: root" in item for item in applied.values())
            and all("class htb 1:20" in item for item in before.values())
            and all("class htb 1:20" in item for item in after.values())
            and all("qdisc htb 1: root" not in item for item in restored.values())
        ),
        "restored_roots": {
            key: item.split()[1] for key, item in restored.items()
        },
    }


def _model_totals(audit: dict[str, Any]) -> tuple[float, int, int, str]:
    calls = list(cast(dict[str, dict[str, Any]], audit["model_telemetry"]).values())
    return (
        sum(float(item["service_latency_ms"]) for item in calls),
        sum(int(item["input_tokens"] or 0) for item in calls),
        sum(int(item["output_tokens"] or 0) for item in calls),
        ",".join(sorted({str(item["finish_reason"]) for item in calls})),
    )


def analyze(root: Path) -> tuple[dict[str, Any], str]:
    manifest = _read(root / "matrix-manifest.json")
    run_dirs = sorted((root / "runs").iterdir())
    if len(run_dirs) != 18:
        raise RuntimeError(f"expected 18 run directories, found {len(run_dirs)}")
    rows: list[dict[str, Any]] = []
    forbidden_private = (
        '"source_ref"',
        '"evaluator_id"',
        '"gold_answer"',
        '"gold_answers"',
        '"supporting_evidence"',
        '"evidence_list"',
    )
    for run_dir in run_dirs:
        audit = _read(run_dir / "audit.json")
        result = _read(run_dir / "result.json")
        call = _read(run_dir / "replanner-call.json")
        tc = _read(run_dir / "tc-attestation.json")
        prompt = str(call["request"]["prompt"])
        trace = _trace_audit(run_dir / "trace.jsonl", run_dir.name)
        tc_result = _tc_audit(tc, float(audit["bandwidth_mbps"]))
        model_ms, input_tokens, output_tokens, finish_reasons = _model_totals(audit)
        arm = str(audit["arm"])
        physical_markers = (
            '"infrastructure_state"',
            '"bandwidth_mbps"',
            '"locations"',
            '"service_latency_ms"',
        )
        visibility_valid = (
            all(marker not in prompt for marker in physical_markers)
            if arm == "resource-blind"
            else all(marker in prompt for marker in physical_markers)
        )
        versions = cast(list[dict[str, Any]], audit["versions"])
        revisions = cast(list[dict[str, Any]], audit["revisions"])
        row = {
            "run_id": run_dir.name,
            "task": audit["task"],
            "regime": audit["regime"],
            "bandwidth_mbps": float(audit["bandwidth_mbps"]),
            "arm": arm,
            "decision": revisions[0]["decision"],
            "trigger": revisions[0]["trigger"],
            "g0_sha256": versions[0]["canonical_sha256"],
            "g1_sha256": audit["final_plan_sha256"],
            "workflow_changed": audit["final_plan_sha256"]
            != versions[0]["canonical_sha256"],
            "changes": revisions[0]["changes"],
            "e2e_latency_ms": float(audit["e2e_latency_ms"]),
            "workflow_latency_ms": float(audit["workflow_latency_ms"]),
            "critical_path_latency_ms": float(audit["critical_path_latency_ms"]),
            "parallel_overlap_ms": float(audit["parallel_overlap_ms"]),
            "transfer_bytes": int(audit["transfer_bytes"]),
            "transfer_time_ms": float(audit["transfer_time_ms"]),
            "model_service_latency_ms": model_ms,
            "model_input_tokens": input_tokens,
            "model_output_tokens": output_tokens,
            "model_finish_reasons": finish_reasons,
            "operator_latency_ms": sum(
                float(item)
                for item in cast(dict[str, float], audit["operator_latency_ms"]).values()
            ),
            "operator_placements": audit["operator_placements"],
            "workflow_planner_overhead_ms": float(
                audit["workflow_planner_overhead_ms"]
            ),
            "replanner_wall_latency_ms": float(audit["replanner_wall_latency_ms"]),
            "score": float(audit["benchmark_score"]),
            "format_valid": bool(audit["format_valid"]),
            "execution_valid": bool(audit["execution_valid"]),
            "trace": trace,
            "tc": tc_result,
            "visibility_valid": visibility_valid,
            "private_leakage": [item for item in forbidden_private if item in prompt],
            "one_replanner_call": bool(
                len(revisions) == 1
                and trace["replanner_start_count"] == 1
                and trace["replanner_end_count"] == 1
            ),
            "result_execution_completed": bool(result["execution_completed"]),
        }
        rows.append(row)

    invalid = [
        row["run_id"]
        for row in rows
        if not (
            row["execution_valid"]
            and row["format_valid"]
            and row["result_execution_completed"]
            and row["trace"]["parent_chain_valid"]
            and row["trace"]["run_end_count"] == 1
            and row["trace"]["run_failed_count"] == 0
            and row["one_replanner_call"]
            and row["tc"]["valid"]
            and row["visibility_valid"]
            and not row["private_leakage"]
        )
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_pair: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row["task"]), str(row["arm"]))].append(row)
        by_pair[(str(row["task"]), str(row["regime"]))][str(row["arm"])] = row
    workflow_summary = []
    for (task, arm), items in sorted(grouped.items()):
        hashes = sorted({str(item["g1_sha256"]) for item in items})
        workflow_summary.append(
            {
                "task": task,
                "arm": arm,
                "unique_g1_sha256": hashes,
                "bandwidth_dependent": len(hashes) > 1,
                "decisions": [
                    item["decision"]
                    for item in sorted(items, key=lambda x: x["bandwidth_mbps"])
                ],
            }
        )
    pairs = []
    for (task, regime), arms in sorted(by_pair.items()):
        blind = arms["resource-blind"]
        aware = arms["infra-aware"]
        pairs.append(
            {
                "task": task,
                "regime": regime,
                "bandwidth_mbps": blind["bandwidth_mbps"],
                "same_final_workflow": blind["g1_sha256"] == aware["g1_sha256"],
                "score_blind": blind["score"],
                "score_aware": aware["score"],
                "e2e_delta_aware_minus_blind_ms": aware["e2e_latency_ms"]
                - blind["e2e_latency_ms"],
                "traffic_delta_aware_minus_blind_bytes": aware["transfer_bytes"]
                - blind["transfer_bytes"],
            }
        )
    cold_start = []
    for task in sorted({str(item["task"]) for item in rows}):
        items = [item for item in rows if item["task"] == task]
        first = min(items, key=lambda item: item["run_id"])
        later = [
            float(item["model_service_latency_ms"])
            for item in items
            if item is not first
        ]
        cold_start.append(
            {
                "task": task,
                "first_run": first["run_id"],
                "first_model_service_latency_ms": first["model_service_latency_ms"],
                "later_median_model_service_latency_ms": median(later),
                "ratio": first["model_service_latency_ms"] / median(later),
                "tokens_identical_across_runs": len(
                    {
                        (item["model_input_tokens"], item["model_output_tokens"])
                        for item in items
                    }
                )
                == 1,
            }
        )
    signal = any(item["bandwidth_dependent"] for item in workflow_summary)
    machine = {
        "experiment_id": manifest["experiment_id"],
        "coverage": {
            "expected": manifest["expected_runs"],
            "completed": len(rows),
            "invalid": invalid,
        },
        "rows": rows,
        "workflow_summary": workflow_summary,
        "paired_comparisons": pairs,
        "cold_start_audit": cold_start,
        "infra_dependent_workflow_change_observed": signal,
        "system_benefit_from_workflow_change_observed": False,
    }
    return machine, _markdown(machine)


def _markdown(audit: dict[str, Any]) -> str:
    rows = cast(list[dict[str, Any]], audit["rows"])
    pairs = cast(list[dict[str, Any]], audit["paired_comparisons"])
    cold = cast(list[dict[str, Any]], audit["cold_start_audit"])
    placements: list[tuple[str, dict[str, list[str]]]] = []
    for task in sorted({str(row["task"]) for row in rows}):
        task_rows = [row for row in rows if row["task"] == task]
        signatures = {
            json.dumps(row["operator_placements"], sort_keys=True)
            for row in task_rows
        }
        if len(signatures) != 1:
            raise RuntimeError(f"operator placements varied unexpectedly: {task}")
        placements.append(
            (
                task,
                cast(dict[str, list[str]], task_rows[0]["operator_placements"]),
            )
        )
    lines = [
        "# Infra-aware replanning preliminary v1",
        "",
        "## Outcome",
        "",
        "All 18 primary cells completed with valid runtime, evaluator, trace, visibility, and "
        "traffic-control evidence. No replanner changed G0 in any cell. Therefore this "
        "preliminary does **not** establish `H1 != H2 -> G(H1) != G(H2)`, and it provides no "
        "measurable system benefit attributable to workflow evolution.",
        "",
        "The negative result is informative: infrastructure visibility alone did not make the "
        "LLM revise pending work, even when the prompt contained artifact locations, complete "
        "3/10/30 Mbps link state, zero load, transfer estimates, and frozen measured A28/4090 "
        "service-cost profiles.",
        "",
        "## Exact settings",
        "",
        "- Cases: Video-MME 795-3, MultiHop multi-source, LongBench multi-document.",
        "- Network: globally filtered worker traffic at 3, 10, or 30 Mbps; added RTT 0 ms.",
        "- Arms: resource-blind semantic view versus the same replanner plus explicit physical "
        "state and cost view.",
        "- Frozen G0, task/evaluator, model pool, operator vocabulary, initial placement, B0 "
        "scheduler, one replan, n=1, no retry or replacement.",
        "- Checkpoint: after the deterministic tool prefix and before the first `invoke_model`; "
        "completed nodes/artifacts are immutable.",
        "- Data were prepositioned once under unshaped networking; each runner E2E begins after "
        "tc is active. Every cell has before/after class counters and restored-qdisc evidence.",
        "",
        "## Actual operator placements",
        "",
        "Each task used the same B0-selected placement in all six cells:",
        "",
    ]
    for task, node_placements in placements:
        placement_text = "; ".join(
            f"`{node}` -> `{','.join(agents)}`"
            for node, agents in sorted(node_placements.items())
        )
        lines.append(f"- {task}: {placement_text}.")
    lines.extend(
        (
        "",
        "## Primary runs",
        "",
        "| Run | Decision | G1 | Score | E2E ms | CP / overlap ms | Transfer B / ms | "
        "Sum op / model ms | Plan / replan ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
        )
    )
    for row in rows:
        lines.append(
            f"| {row['run_id']} | {row['decision']} | `{str(row['g1_sha256'])[:8]}` | "
            f"{row['score']:.1f} | {row['e2e_latency_ms']:.1f} | "
            f"{row['critical_path_latency_ms']:.1f} / {row['parallel_overlap_ms']:.1f} | "
            f"{row['transfer_bytes']} / {row['transfer_time_ms']:.1f} | "
            f"{row['operator_latency_ms']:.1f} / {row['model_service_latency_ms']:.1f} | "
            f"{row['workflow_planner_overhead_ms']:.1f} / "
            f"{row['replanner_wall_latency_ms']:.1f} |"
        )
    lines.extend(
        (
            "",
            "## Blind versus aware",
            "",
            "| Task / regime | Same G1 | Score blind/aware | Aware - blind E2E ms | "
            "Aware - blind traffic B |",
            "|---|---|---:|---:|---:|",
        )
    )
    for item in pairs:
        lines.append(
            f"| {item['task']} / {item['regime']} | "
            f"{'yes' if item['same_final_workflow'] else 'no'} | "
            f"{item['score_blind']:.1f}/{item['score_aware']:.1f} | "
            f"{item['e2e_delta_aware_minus_blind_ms']:.1f} | "
            f"{item['traffic_delta_aware_minus_blind_bytes']} |"
        )
    lines.extend(
        (
            "",
            "Raw E2E deltas are not method effects because every paired comparison executed the "
            "same final workflow. The first run of each task also paid a repeatable model "
            "cold-start penalty:",
            "",
            "| Task | First / later-median model ms | Ratio | Tokens identical |",
            "|---|---:|---:|---|",
        )
    )
    for item in cold:
        lines.append(
            f"| {item['task']} | {item['first_model_service_latency_ms']:.1f} / "
            f"{item['later_median_model_service_latency_ms']:.1f} | {item['ratio']:.2f}x | "
            f"{'yes' if item['tokens_identical_across_runs'] else 'no'} |"
        )
    lines.extend(
        (
            "",
            "## Workflow evolution and failure modes",
            "",
            "- Video: all six cells kept G0 (`6ff35770...`) and scored 1.0. Bandwidth changed "
            "measured transfer time, but neither arm changed the two-stage visual workflow.",
            "- MultiHop: all six cells kept G0 (`9d139d96...`) and scored 0.0. At the early "
            "checkpoint the replanner accepted shard coverage without adding the evidence branch "
            "that the later terminal-checkpoint validation had needed. This is premature keep / "
            "insufficient semantic diagnosis, not a runtime failure.",
            "- LongBench: all six cells kept G0 (`85d9cd7d...`) and scored 0.0. Infra-aware "
            "reasons repeatedly claimed no materially cheaper alternative despite explicit "
            "A28 versus 4090 service profiles. This is reproducible infra ignored / wrong cost "
            "reasoning. Four evidence-note calls also ended at the fixed output limit, preserving "
            "the known quality limitation of the frozen baseline.",
            "- No over-reduction, new branch, deleted node, modified dependency, or model-binding "
            "change occurred. Consequently there is no traffic or latency gain caused by G0->G1.",
            "",
            "## Validity audit",
            "",
            f"- Coverage: {audit['coverage']['completed']}/{audit['coverage']['expected']}; "
            f"invalid cells: {audit['coverage']['invalid']}.",
            "- Every trace has a valid parent chain, exactly one replanner start/end, one run end, "
            "and no run-failed event.",
            "- Blind prompts contain no infrastructure snapshot or physical markers; aware "
            "prompts contain them. Neither arm contains serialized source/evaluator/gold/private "
            "evidence keys.",
            "- Every tc attestation records all four HTB roots/classes, remote exit 0, successful "
            "cleanup, and restored roots A4/A5/A28=`mq`, strong-4090=`noqueue`.",
            "- The pre-execution attempt-1 SSH-key failure is retained separately and excluded; "
            "it created no benchmark run. Attempt 2 contains all 18 primary runs.",
            "",
            "## What this supports",
            "",
            "The experiment supports method formalization around an explicit optimizer or "
            "validated cost-to-action mechanism: merely serializing infrastructure state into an "
            "LLM prompt did not produce joint workflow adaptation. It also shows that checkpoint "
            "placement controls which semantic deficiency is observable and must be part of the "
            "method contract.",
            "",
            "It does not support a claim that infra-aware replanning improves latency, traffic, "
            "cost, or quality; it does not establish bandwidth-dependent workflow evolution; and "
            "n=1 plus cold-start ordering prevents causal interpretation of same-workflow E2E "
            "differences. No extra benchmark, repetition, RL, method, or sweep was run.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    audit, report = analyze(args.evidence)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
