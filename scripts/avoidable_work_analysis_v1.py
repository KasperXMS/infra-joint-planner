"""Offline, metadata-only characterization of already-exported resident traces.

No runtime execution, provider access, admission writes or private-body exports.
Run with the repository environment: python -m scripts.avoidable_work_analysis_v1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

# Existing scripts use sibling imports. Importing these helpers does not run CLIs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from large_scale_graph_audit_v1 import graph_audit  # noqa: E402
from large_scale_snapshot_v1 import event_metrics, trace_cost_receipts  # noqa: E402

EXACT = "Exact Candidate"
CF = "Counterfactual-required Candidate"
UNSAFE = "Unsafe / Semantically Non-equivalent"
UNKNOWN = "Unknown"
DETERMINISTIC = {
    "bm25_retrieve",
    "filter_records",
    "select_fields",
    "derive_fields",
    "aggregate_records",
    "aggregate_artifacts",
    "top_k_records",
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def distribution(values: list[Any]) -> dict[str, Any]:
    known = [v for v in values if number(v)]
    return {
        "n": len(values),
        "known_n": len(known),
        "unknown_n": len(values) - len(known),
        "median": median(known) if known else None,
        "min": min(known) if known else None,
        "max": max(known) if known else None,
        "known_sum": sum(known) if known else None,
        "complete_sum": sum(known) if len(known) == len(values) else None,
    }


def total(values: list[Any]) -> int | float | None:
    return sum(values) if all(number(v) for v in values) else None


def fingerprint(
    action: dict[str, Any], identities: dict[str, Any], contract: dict[str, Any] | None = None
) -> tuple[str, bool]:
    """An observational key unless the caller supplies a complete bound contract.

    Ordered input identities include media type/hash/version, not just IDs.
    A contract must bind historical implementation/config, effective defaults,
    deterministic behavior and safe output rebinding. Historical exports here
    do not supply this proof. Output names are ignored only as a mining signal.
    """
    arguments = dict((contract or {}).get("effective_defaults", {}))
    arguments.update(action.get("arguments", {}))
    arguments.pop("output_artifact_id", None)
    inputs = [identities.get(i, {"opaque_id_sha256": digest(i)}) for i in action.get("inputs", [])]
    proved = bool(
        contract
        and contract.get("deterministic") is True
        and contract.get("output_rebinding_safe") is True
        and contract.get("defaults_complete") is True
        and contract.get("implementation_sha256")
        and contract.get("config_sha256")
        and contract.get("proof_sha256")
        and all(i.get("sha256") and i.get("media_type") for i in inputs)
        and action.get("operator") in DETERMINISTIC
    )
    return digest(
        {
            "operator": action.get("operator"),
            "arguments": arguments,
            "inputs": inputs,
            "contract": contract,
        }
    ), proved


def load_archives(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: dict[str, dict[str, Any]] = {}
    archives = []
    cells: dict[str, str] = {}
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            body = archive.read("manifest.json")
            manifest = json.loads(body)
            entries = manifest["entries"]
            valid = 0
            for entry in entries:
                member = entry.get("trace_archive_path", entry.get("archive_path"))
                raw = archive.read(member)
                sha = hashlib.sha256(raw).hexdigest()
                expected = entry.get("trace_sha256", entry.get("sha256"))
                if sha != expected:
                    raise ValueError("trace hash differs from export manifest")
                if len(raw) != entry.get("trace_bytes", entry.get("bytes")):
                    raise ValueError("trace size differs from export manifest")
                events = [
                    json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()
                ]
                if len(events) != entry["event_count"]:
                    raise ValueError("trace event count differs from export manifest")
                eligible = entry.get(
                    "comparative_sample_eligible", entry.get("effective_disposition") == "valid"
                )
                if eligible != (entry.get("effective_disposition") == "valid"):
                    raise ValueError("inconsistent effective export membership")
                if not eligible:
                    continue
                valid += 1
                run_id, cell_id = entry["run_id"], entry["cell_id"]
                if run_id in runs:
                    if runs[run_id]["source"]["trace_sha256"] != sha:
                        raise ValueError("conflicting duplicate run")
                    continue
                if cell_id in cells:
                    raise ValueError("multiple effective attempts for one cell")
                cells[cell_id] = run_id
                match = re.fullmatch(
                    r"(phase[12])-(longbench_v2|multihop_rag|video_mme)-(\d+)-"
                    r"[0-9a-f]+-(p[12])-(fast|slow)-(B0|B1|A|B|C|D|E)",
                    cell_id,
                )
                if not match:
                    raise ValueError("unrecognized resident cell identity")
                phase, benchmark, position, planner, network, method = match.groups()
                starts = [e["payload"] for e in events if e["event_type"] == "task.start"]
                if len(starts) != 1:
                    raise ValueError("ambiguous task identity")
                source = {
                    "experiment": "resident-" + phase,
                    "cell_index": entry["cell_index"],
                    "cell_sha256": digest(cell_id),
                    "run_sha256": digest(run_id),
                    "task_sha256": digest(starts[0]["task_id"]),
                    "trace_sha256": sha,
                    "manifest_sha256": hashlib.sha256(body).hexdigest(),
                    "journal_sha256": manifest.get("journal_sha256"),
                    "admission_sha256": entry.get(
                        "effective_admission_sha256", entry.get("raw_admission_sha256")
                    ),
                    "execution_sha256": entry.get("execution_sha256"),
                    "execution_epoch": entry.get("execution_source_epoch"),
                    "attempt_index": entry["attempt_index"],
                    "membership_evidence": "exported effective view; sidecars not replayed",
                    "benchmark": benchmark,
                    "task_position": int(position),
                    "planner": planner,
                    "method": method,
                    "network": network,
                }
                runs[run_id] = {"source": source, "events": events}
            archives.append(
                {
                    "name": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "manifest_sha256": hashlib.sha256(body).hexdigest(),
                    "journal_sha256": manifest.get("journal_sha256"),
                    "attempts": len(entries),
                    "eligible_entries": valid,
                    "dispositions": dict(Counter(e["effective_disposition"] for e in entries)),
                }
            )
    return sorted(
        runs.values(), key=lambda r: (r["source"]["experiment"], r["source"]["cell_index"])
    ), archives


def project(run: dict[str, Any]) -> dict[str, Any]:
    events, source = run["events"], run["source"]
    metrics, receipts, graph = (
        event_metrics(events),
        trace_cost_receipts(events),
        graph_audit(events),
    )
    evaluations = [e["payload"] for e in events if e["event_type"] == "evaluation.result"]
    if len(evaluations) > 1:
        raise ValueError("multiple evaluations")
    score = evaluations[0].get("benchmark_score") if evaluations else None
    outcome = (
        "score1"
        if score == 1
        else "score0"
        if score == 0
        else "unevaluated"
        if score is None
        else "other_score"
    )
    components = {}
    for role in ["manager", "specialist", "verifier"]:
        if role == "verifier":
            starts = [e for e in events if e["event_type"] == "logical.verification.started"]
            done = [e["payload"] for e in events if e["event_type"] == "logical.verification"]
            latencies = [p.get("latency_ms") for p in done]
        else:

            def selected(e: dict[str, Any], suffix: str, role: str = role) -> bool:
                return e["event_type"] == "logical.reasoning." + suffix and (
                    e["payload"].get("logical_agent_id") == "manager"
                ) == (role == "manager")

            starts = [e for e in events if selected(e, "started")]
            done = [e["payload"] for e in events if selected(e, "completed")]
            latencies = [p.get("telemetry", {}).get("latency_ms") for p in done]
        components[role] = {
            "turns_started": len(starts),
            "turns_completed": len(done),
            "latency_receipt_subtotal_ms": total(latencies),
            "latency_complete_work_ms": total(latencies) if len(starts) == len(done) else None,
            "provider_requests": None,
            "provider_successful_requests": None,
            "provider_input_tokens": None,
            "provider_output_tokens": None,
            "api_usd": None,
            "sdk_input_token_receipt_subtotal": total([p.get("input_tokens") for p in done])
            if role == "verifier" and all(p.get("input_tokens", 0) > 0 for p in done)
            else None,
            "sdk_output_token_receipt_subtotal": total([p.get("output_tokens") for p in done])
            if role == "verifier" and all(p.get("output_tokens", 0) > 0 for p in done)
            else None,
        }
    components["inference"] = {
        "prepared_actions": metrics["prepared_model_actions"],
        "context_limit_failures": metrics["failure_codes"].get("context_limit_exceeded", 0),
        "reported_reached_inference": metrics["reported_reached_model_inference"],
        "successful_receipts": metrics["successful_inference_telemetry_count"],
        "service_receipt_subtotal_ms": metrics["model_service_work_ms"],
        "service_complete_work_ms": metrics["model_service_work_complete_total_ms"],
        "input_token_receipt_subtotal": metrics["physical_model_input_tokens"],
        "output_token_receipt_subtotal": metrics["physical_model_output_tokens"],
        "unmeasured_failed_outcomes": metrics["unmeasured_failed_model_outcomes"],
        "missing_physical_receipts": metrics["unmeasured_model_actions_missing_physical_receipt"],
        "gpu_seconds": None,
    }
    outcomes = [e["payload"] for e in events if e["event_type"] == "logical.model.outcome"]
    components["inference"]["preflight_rejected_actions"] = sum(
        p.get("failure_code")
        in {"context_limit_exceeded", "unsupported_modality", "deployment_required"}
        for p in outcomes
    )
    components["inference"]["selected_deployment_sha256s"] = sorted(
        {
            digest(e["payload"]["selection"]["selected_deployment_id"])
            for e in events
            if e["event_type"] == "physical.execution"
            and e["payload"].get("selection", {}).get("selected_deployment_id")
        }
    )
    components["network"] = {
        k: v for k, v in receipts.items() if k.startswith(("initial_", "action_transfer_"))
    }
    components["operator"] = {
        "prepared_calls": metrics["prepared_tool_actions"],
        "successful_calls": metrics["successful_tool_executions"],
        "complete_work_ms": receipts["complete_tool_execution_work_ms"],
        "receipt_subtotal_ms": receipts["successful_tool_execution_work_ms"],
        "calls_by_operator": dict(Counter(metrics["operator_sequence"])),
    }
    return {
        "source": source,
        "outcome": outcome,
        "original_score": score,
        "resource_vector": components,
        "e2e_ms": receipts["recorded_e2e_latency_ms"],
        "failure_codes": metrics["failure_codes"],
        "sdk_failures_lower_bound": metrics["sdk_function_failure_receipts_lower_bound"],
        "method_interface": metrics["method_interface"],
        "structure": {
            k: graph.get(k)
            for k in [
                "graph_available",
                "node_count",
                "edge_count",
                "max_concurrent_actions",
                "overlap_wall_ms",
                "dependency_critical_path_ms",
                "ordinal_structure_sha256",
                "dependency_order_violations",
            ]
        },
        "manager_budget_exhausted": any(
            "manager turn budget exhausted" in str(e["payload"].get("failure", "")).lower()
            for e in events
            if e["event_type"] == "run.failed"
        ),
    }


def mine(run: dict[str, Any], projection: dict[str, Any]) -> list[dict[str, Any]]:
    events, source = run["events"], run["source"]
    actions = {
        e["payload"]["action"]["action_id"]: (i, e["payload"]["action"])
        for i, e in enumerate(events)
        if e["event_type"] == "logical.action.prepared"
    }
    physical = {
        e["payload"]["action_id"]: e["payload"]
        for e in events
        if e["event_type"] == "physical.execution"
    }
    final = next(
        (e["payload"] for e in reversed(events) if e["event_type"] == "workflow.graph.snapshot"), {}
    )
    terminal = next(
        (
            e["payload"].get("terminal_action_id")
            for e in reversed(events)
            if e["event_type"] == "logical.loop.end"
        ),
        None,
    )
    consumers: dict[str, list[str]] = defaultdict(list)
    for edge in final.get("edges", []):
        consumers[edge["producer_action_id"]].append(edge["consumer_action_id"])
    selected_decisions = {
        e["payload"]["action_id"]: e["payload"].get("decision_id")
        for e in events
        if e["event_type"] == "logical.action.selected"
    }
    decision_inputs = {
        e["payload"]["decision_id"]: i
        for i, e in enumerate(events)
        if e["event_type"] == "logical.reasoning.input"
    }
    decision_work = {
        e["payload"]["decision_id"]: e["payload"].get("telemetry", {}).get("latency_ms")
        for e in events
        if e["event_type"] == "logical.reasoning.completed"
    }
    latest_manager_decision = None
    result = []

    def candidate(
        pattern: str,
        index: int,
        action_id: str | None,
        signals: list[str],
        classification: str,
        transform: str,
        prior: str | None = None,
    ) -> None:
        action = actions.get(action_id, (None, {}))[1]
        execution = physical.get(action_id, {}).get("execution") or {}
        model = execution.get("model_telemetry") or {}
        decision = selected_decisions.get(action_id) if action_id else latest_manager_decision
        observed = {
            "operator_work_ms": execution.get("operator_latency_ms")
            if action.get("action_type") == "tool"
            else None,
            "model_service_ms": model.get("service_latency_ms"),
            "model_input_tokens": model.get("input_tokens"),
            "model_output_tokens": model.get("output_tokens"),
            "enclosing_reasoning_work_ms": decision_work.get(decision),
            "action_transfer_bytes": total(
                [t.get("bytes_transferred") for t in execution.get("transfers", [])]
            )
            if execution
            else None,
        }
        output_text = execution.get("output", {}).get("text")
        later_inputs = [
            e
            for e in events[index + 1 :]
            if e["event_type"] in {"logical.reasoning.input", "logical.verification.input"}
        ]
        # Exact text containment is an observable exposure signal only. Negative
        # results do not exclude paraphrase, truncation or implicit context use.
        text_exposures = (
            sum(output_text in json.dumps(e["payload"], ensure_ascii=False) for e in later_inputs)
            if output_text
            else None
        )
        result.append(
            {
                "opportunity_id": "aw-" + digest([source["trace_sha256"], pattern, index])[:20],
                "source": source,
                "outcome": projection["outcome"],
                "pattern": pattern,
                "intervention_point": {
                    "event_index": index,
                    "action_sha256": digest(action_id) if action_id else None,
                    "decision_input_event_index": decision_inputs.get(decision),
                    "decision_sha256": digest(decision) if decision else None,
                },
                "operation_type": action.get("operator", "control_protocol"),
                "original_dependencies_sha256": [digest(x) for x in action.get("depends_on", [])],
                "input_artifact_ids_sha256": [digest(x) for x in action.get("inputs", [])],
                "explicit_consumers_sha256": sorted(
                    {digest(x) for x in consumers.get(action_id, [])}
                ),
                "later_control_input_count": len(later_inputs),
                "later_control_inputs_containing_exact_output_text": text_exposures,
                "prior_action_sha256": digest(prior) if prior else None,
                "proposed_transformation": transform,
                "signals": signals,
                "observed_cost": observed,
                "potential_saved_cost": {
                    "gross_local_upper_bound": {
                        k: v for k, v in observed.items() if k != "enclosing_reasoning_work_ms"
                    }
                    if classification != UNSAFE
                    else None,
                    "evidence_level": "hypothetical avoided observed work; not measured benefit",
                    "verified_positive_lower_bound": None,
                    "net_saving": None,
                },
                "additional_required_work": "cache lookup/rebinding or intervention execution, "
                "state restoration, natural continuation and fallback; unmeasured",
                "semantic_validity_evidence": "signal only; historical exact contract absent",
                "information_preservation_risk": "prompt-carried evidence and Manager/Verifier "
                "influence remain possible; explicit DAG is incomplete",
                "counterfactual_replay_requirements": "same pre-action state, independent stores, "
                "frozen runtime and natural fresh suffix; see protocol",
                "infrastructure_dependence": "Unknown",
                "classification": classification,
                "uncertainty": "candidate costs overlap; no causal effect established",
            }
        )

    identities: dict[str, Any] = {}
    seen: dict[str, str] = {}
    model_seen: dict[str, str] = {}
    repeated_rejects: dict[str, str] = {}
    for index, event in enumerate(events):
        kind, p = event["event_type"], event["payload"]
        if kind == "logical.reasoning.input" and p.get("logical_agent_id") == "manager":
            latest_manager_decision = p["decision_id"]
        elif kind == "logical.action.prepared":
            action = p["action"]
            aid, operator = action["action_id"], action.get("operator", "invoke_model")
            if operator in DETERMINISTIC:
                key, _ = fingerprint(action, identities)
                if key in seen:
                    previous = physical.get(seen[key], {}).get("execution")
                    candidate(
                        "A",
                        index,
                        aid,
                        [
                            "same_normalized_arguments_and_observed_input_identity",
                            "prior_successful_receipt" if previous else "prior_failure_or_missing",
                        ],
                        UNKNOWN,
                        "reuse prior deterministic result with output rebinding",
                        seen[key],
                    )
                # Only an already observed successful result may be a reuse source.
            if action.get("action_type") == "model":
                inputs = [
                    identities.get(x, {"opaque_id_sha256": digest(x)})
                    for x in action.get("inputs", [])
                ]
                key = digest(inputs)
                signals = []
                prior = model_seen.get(key) if inputs else None
                if prior:
                    signals.append("repeated_ordered_evidence_identity_not_prompt_equivalence")
                if (
                    aid != terminal
                    and not consumers.get(aid)
                    and physical.get(aid, {}).get("execution")
                ):
                    signals.append("no_explicit_graph_consumer_nonterminal")
                if signals:
                    candidate(
                        "B",
                        index,
                        aid,
                        signals,
                        CF,
                        "skip/merge one model operation; preserve all observations under test",
                        prior,
                    )
                if inputs:
                    model_seen[key] = aid
        elif kind == "physical.execution" and p.get("execution"):
            aid = p["action_id"]
            action = actions[aid][1]
            if action.get("operator") in DETERMINISTIC:
                key, _ = fingerprint(action, identities)
                seen.setdefault(key, aid)
            output = p["execution"].get("output", {})
            artifacts = output.get("artifacts", []) if isinstance(output, dict) else []
            if isinstance(output, dict) and "artifact_id" in output:
                artifacts = [*artifacts, output]
            for artifact in artifacts:
                if isinstance(artifact, dict) and artifact.get("artifact_id"):
                    identities[artifact["artifact_id"]] = {
                        "sha256": artifact.get("sha256_hex"),
                        "media_type": artifact.get("media_type"),
                        "size_bytes": artifact.get("size_bytes"),
                    }
            transfers = p["execution"].get("transfers", [])
            if (
                action.get("operator") in {"select_fields", "filter_records", "top_k_records"}
                and transfers
            ):
                candidate(
                    "D",
                    index,
                    aid,
                    ["transfer_into_reduction_operator"],
                    UNKNOWN,
                    "evaluate lossless pushdown before transfer; compare with existing scheduler",
                )
            elif (
                action.get("operator") == "aggregate_artifacts"
                and transfers
                and any(
                    actions.get(c, (None, {}))[1].get("operator") == "bm25_retrieve"
                    for c in consumers.get(aid, [])
                )
            ):
                candidate(
                    "D",
                    index,
                    aid,
                    ["transferred_full_aggregation_before_retrieval"],
                    UNKNOWN,
                    "test distributed global-statistics BM25 with stable global "
                    "ranking; shard-local top-k concatenation is not equivalent",
                )
        elif kind == "logical.model.outcome" and p.get("failure_code") == "context_limit_exceeded":
            aid = p["action_id"]
            if aid in actions:
                action = actions[aid][1]
                # Include prompt, requirements and exact input IDs: a changed recovery
                # attempt is not counted as repeating an already known failure.
                key = digest(
                    {
                        k: v
                        for k, v in action.items()
                        if k not in {"action_id", "owner_agent_id", "outputs", "depends_on"}
                    }
                )
                if key in repeated_rejects:
                    candidate(
                        "C",
                        index,
                        aid,
                        ["repeated_identical_context_reject"],
                        CF,
                        "return cached static refusal within unchanged capability/config state",
                        repeated_rejects[key],
                    )
                repeated_rejects[key] = aid
        elif kind == "logical.cost_quote.control_only_batch":
            candidate(
                "C",
                index,
                None,
                ["quote_protocol_control_only_batch"],
                CF,
                "collapse one quote/commit exchange; preserve decision-time feedback",
            )
    return result


METRICS = {
    "manager_turns": ("manager", "turns_started"),
    "verifier_calls": ("verifier", "turns_started"),
    "specialist_turns": ("specialist", "turns_started"),
    "manager_work_ms": ("manager", "latency_complete_work_ms"),
    "verifier_work_ms": ("verifier", "latency_complete_work_ms"),
    "specialist_work_ms": ("specialist", "latency_complete_work_ms"),
    "api_usd": ("manager", "api_usd"),
    "model_requests": ("inference", "prepared_actions"),
    "inference_receipts": ("inference", "successful_receipts"),
    "model_service_ms": ("inference", "service_complete_work_ms"),
    "artifact_bytes": ("network", "action_transfer_complete_bytes"),
    "artifact_transfer_ms": ("network", "action_transfer_complete_work_ms"),
    "operator_work_ms": ("operator", "complete_work_ms"),
}


def summarize(rows: list[dict[str, Any]], opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        source = row["source"]
        grouped[
            tuple(source[k] for k in ["experiment", "benchmark", "planner", "method"])
            + (row["outcome"],)
        ].append(row)
    groups = []
    for key, members in sorted(grouped.items()):
        groups.append(
            {
                "group": dict(
                    zip(
                        ["experiment", "benchmark", "planner", "method", "outcome"],
                        key,
                        strict=True,
                    )
                ),
                "n": len(members),
                "metrics": {
                    name: distribution([r["resource_vector"][part][field] for r in members])
                    for name, (part, field) in METRICS.items()
                },
            }
        )
    matched = []
    by_condition: dict[tuple[Any, ...], dict[str, Any]] = defaultdict(dict)
    for row in rows:
        s = row["source"]
        key = tuple(s[k] for k in ["experiment", "benchmark", "task_sha256", "planner", "network"])
        by_condition[key][s["method"]] = row
    for key, methods in sorted(by_condition.items()):
        blind = methods.get("B0")
        if blind is None:
            continue
        for method, row in sorted(methods.items()):
            if method == "B0":
                continue
            deltas = {}
            for name, (part, field) in METRICS.items():
                before, after = (x["resource_vector"][part][field] for x in [blind, row])
                deltas[name] = before - after if number(before) and number(after) else None
            matched.append(
                {
                    "experiment": key[0],
                    "benchmark": key[1],
                    "task_sha256": key[2],
                    "planner": key[3],
                    "network": key[4],
                    "method": method,
                    "B0_outcome": blind["outcome"],
                    "method_outcome": row["outcome"],
                    "both_score1": blind["outcome"] == row["outcome"] == "score1",
                    "B0_minus_method": deltas,
                }
            )
    population = []
    for experiment in sorted({r["source"]["experiment"] for r in rows}):
        for benchmark in sorted({r["source"]["benchmark"] for r in rows}):
            members = [
                r
                for r in rows
                if r["source"]["experiment"] == experiment and r["source"]["benchmark"] == benchmark
            ]
            population.append(
                {
                    "experiment": experiment,
                    "benchmark": benchmark,
                    "admitted_in_export": len(members),
                    "distinct_tasks": len({r["source"]["task_sha256"] for r in members}),
                    "outcomes": dict(Counter(r["outcome"] for r in members)),
                }
            )
    patterns = []
    for pattern in ["A", "B", "C", "D"]:
        candidates = [o for o in opportunities if o["pattern"] == pattern]
        patterns.append(
            {
                "pattern": pattern,
                "candidate_count": len(candidates),
                "affected_runs": len({o["source"]["trace_sha256"] for o in candidates}),
                "classifications": dict(Counter(o["classification"] for o in candidates)),
                "outcomes": dict(Counter(o["outcome"] for o in candidates)),
                "gross_local_model_service_ms": distribution(
                    [o["observed_cost"]["model_service_ms"] for o in candidates]
                ),
                "gross_local_operator_work_ms": distribution(
                    [o["observed_cost"]["operator_work_ms"] for o in candidates]
                ),
            }
        )
    return {
        "schema": "avoidable-work-v1",
        "population": population,
        "groups": groups,
        "patterns": patterns,
        "matched_to_B0": matched,
        "candidate_count": len(opportunities),
        "classifications": dict(Counter(o["classification"] for o in opportunities)),
        "unique_candidate_runs": len({o["source"]["trace_sha256"] for o in opportunities}),
        "proven_positive_saving": None,
        "interpretation": "descriptive export subsets; no pooled accuracy, causal effect, "
        "net benefit or independent-task replication; pattern sums can overlap",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, action="append", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New, separate directory; existing directories are rejected",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError("output directory must be new; historical outputs are immutable")
    runs, archives = load_archives(args.archive)
    rows = [project(run) for run in runs]  # Cost decomposition precedes mining.
    opportunities = [o for run, row in zip(runs, rows, strict=True) for o in mine(run, row)]
    summary = summarize(rows, opportunities)
    summary["archives"] = archives
    summary["analysis_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary["helper_source_sha256s"] = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in ["large_scale_snapshot_v1.py", "large_scale_graph_audit_v1.py"]
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, records in [
        ("avoidable-work-resources-v1.jsonl", rows),
        ("avoidable-work-opportunities-v1.jsonl", opportunities),
    ]:
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(
                    json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
                )
    with (output / "avoidable-work-summary-v1.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "runs": len(rows),
                "opportunities": len(opportunities),
                "classifications": summary["classifications"],
            }
        )
    )


if __name__ == "__main__":
    main()
