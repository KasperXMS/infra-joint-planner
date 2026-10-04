"""Read-only remote B/D/E evidence audit; exports bounded cost/structure metadata only."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from audit_cost_guidance_matrix_v1 import admission, digest, trace_findings
from cost_guidance_bde_v1 import CONDITIONS, TASKS, method_audit
from cost_guidance_cell_analysis_v1 import _action_metadata, measured_sum, profile_error
from cost_guidance_private_multihop_audit_v1 import assert_queue_inactive
from run_predecision_matrix_v1 import write_new

from infra_joint.control.bde_native import RULE_PREFIX
from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.evaluation.trace_audit import summarize_concurrency, summarize_cost


def returned_cards(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    if "consequence" in value and ("quote_id" in value or "card_id" in value):
        return [value]
    return [c for item in value.get("candidates", []) for c in returned_cards(item)]


def feedback_visibility(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    created: dict[str, tuple[int, dict[str, Any]]] = {}
    visible: dict[str, list[int]] = {}
    actual: dict[str, tuple[int, dict[str, Any]]] = {}
    matched_actions: dict[str, str] = {}
    optional: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        kind, p = event["event_type"], event["payload"]
        if kind == "logical.cost_quote.created":
            identifier = p["quote"]["quote_id"]
            created[identifier] = (index, p)
            visible[identifier] = []
        elif kind == "logical.cost_card.returned":
            optional[p["card_id"]] = p
        elif kind == "logical.reasoning.input" and p["logical_agent_id"] == "manager":
            for item in p["input_items"]:
                if item.get("type") != "function_call_output":
                    continue
                try:
                    output = json.loads(item.get("output", ""))
                except (ValueError, TypeError):
                    continue
                for card in returned_cards(output):
                    identifier = card.get("quote_id", card.get("card_id"))
                    if identifier not in created:
                        continue
                    expected = optional.get(identifier, created[identifier][1]["quote"])
                    if card == expected:
                        visible[identifier].append(index)
        elif kind == "logical.cost_card.matched":
            matched_actions[p["card_id"]] = p["action_id"]
        elif kind == "logical.cost_quote.observed":
            actual[p["quote_id"]] = (index, p)
    result = []
    selected_events = {e["payload"]["action_id"]: i for i, e in enumerate(events)
                       if e["event_type"] == "logical.action.selected"}
    for identifier, (index, p) in created.items():
        observation = actual.get(identifier)
        action_id = matched_actions.get(identifier, p["action"]["action_id"])
        selected = selected_events.get(action_id)
        receipt = observation[1] if observation else None
        consequence = p["quote"]["consequence"]
        result.append({
            "card_id": identifier, "optional": identifier in optional,
            "action": _action_metadata(p["action"]), "consequence": consequence,
            "exact_manager_input_receipts": visible[identifier],
            "exact_visible_after_creation": any(i > index for i in visible[identifier]),
            "exact_visible_before_action_selection": selected is not None
            and any(index < i < selected for i in visible[identifier]),
            "matched_actual_action_id": action_id if receipt else None,
            "actual": receipt,
            "model_profile_error": profile_error(consequence.get("model_service"),
                receipt.get("actual_model_service_ms") if receipt else None),
        })
    return result


def analyze(events: list[dict[str, Any]]) -> dict[str, Any]:
    usage = [e["payload"] for e in events if e["event_type"] == "logical.method.reasoning_usage"]
    starts = [e["payload"] for e in events if e["event_type"] == "logical.action.prepared"]
    last_graph = next((e["payload"] for e in reversed(events)
                       if e["event_type"] == "workflow.graph.snapshot"), {})
    failures = Counter(e["payload"].get("failure_code") for e in events
                       if e["event_type"] == "logical.observation"
                       and not e["payload"].get("succeeded", True))
    comparisons = [e["payload"] for e in events if e["event_type"]
                   == "logical.cost_candidates.returned"]
    selected = [e["payload"] for e in events if e["event_type"]
                == "logical.cost_candidates.selected"]
    return {
        "cost": summarize_cost(events), "concurrency": summarize_concurrency(events),
        "manager": {k: measured_sum([u for u in usage if u["recipient"] == "manager"], k)
                    for k in ("latency_ms", "input_tokens", "output_tokens")},
        "specialist": {k: measured_sum([u for u in usage if u["recipient"] == "specialist"], k)
                       for k in ("latency_ms", "input_tokens", "output_tokens")},
        "manager_calls": sum(u["recipient"] == "manager" for u in usage),
        "specialist_calls": sum(u["recipient"] == "specialist" for u in usage),
        "created_specialists": sum(e["event_type"] == "logical.subagent.start" for e in events),
        "verifier_calls": sum(e["event_type"] == "logical.verification.input" for e in events),
        "physical_calls": len(starts),
        "model_calls": sum(p["action"]["action_type"] == "model" for p in starts),
        "operator_sequence": [p["action"].get("operator", "invoke_model") for p in starts],
        "action_structure": [_action_metadata(p["action"]) for p in starts],
        "graph_nodes": len(last_graph.get("nodes", [])),
        "graph_edges": len(last_graph.get("edges", [])),
        "failure_codes": dict(failures),
        "comparison_sizes": [len(p["candidates"]) for p in comparisons],
        "comparisons_selected": len(selected),
        "system_chose_candidates": any(p["system_selected"] for p in selected),
        "query_control_work_ms": sum(e["payload"]["control_work_ms"] for e in events
                                     if e["event_type"] == "logical.cost_quote.control_timing"),
        "query_rejections": dict(Counter(e["payload"]["failure_code"] for e in events
                                         if e["event_type"] == "logical.cost_quote.rejected")),
        "feedback": feedback_visibility(events),
    }


def audit(root: Path, *, partial: bool = False) -> dict[str, Any]:
    if not partial:
        assert_queue_inactive(root)
    freeze = json.loads((root / "protocol-freeze.json").read_text())
    rules = json.loads((root / "rules/rules-freeze.json").read_text())
    findings = []
    if digest(root / "rules/rules-freeze.json") != freeze["rules_manifest_sha256"]:
        findings.append("rule manifest changed")
    if any(digest(root / "app" / p) != expected
           for p, expected in freeze["component_sha256"].items()):
        findings.append("frozen execution component changed")
    stores: set[str] = set()
    cells = []
    for task in freeze["tasks"]:
        for condition in CONDITIONS:
            cell = task["label"] + "-" + condition
            directory = root / "evidence" / cell
            paths = list(directory.glob("runs/*/result.json"))
            if len(paths) != 1 or not (directory / "lightweight-validation.json").is_file():
                if partial:
                    continue
                findings.append("missing/incomplete primary cell " + cell)
                continue
            result_path = paths[0]
            trace = result_path.parent / "trace.jsonl"
            result = json.loads(result_path.read_text())
            admitted, issues = admission(directory, result_path, trace)
            events = JsonlTraceWriter(trace).read_all()
            chain = trace_findings(events, result["run_id"])
            # Failed runs terminate with run.failed; retain them without requiring completion.
            if events and events[-1]["event_type"] == "run.failed":
                chain = [x for x in chain if x != "trace terminal run end missing"]
            issues.extend(chain)
            route = condition.split("-")[1]
            issues.extend(method_audit(events, route)["problems"])
            manifest = json.loads((directory / "freeze/manifest.json").read_text())
            for key, expected in {
                "code_revision": freeze["code_revision"],
                "task_bundle_sha256": task["task_bundle_sha256"],
                "static_capability_contract_sha256": task["static_capability_sha256"],
                "initial_placement": task["initial_placement"], "source_manifest":
                task["source_manifest"], "harness_manifest_sha256": freeze["harness_sha256"],
                "retry": False, "replacement": False, "repetitions": 1,
                "profile_visibility": "blind", "model_service_timeout_seconds": 1200.0,
                "config_sha256": digest(root / "cell-configs" / (cell + ".yaml")),
            }.items():
                if manifest.get(key) != expected:
                    issues.append("manifest mismatch " + key)
            roots = list(manifest["fresh_worker_stores"].values())
            if len(roots) != 4 or set(roots) & stores:
                issues.append("store reuse or missing Worker stores")
            stores.update(roots)
            before = json.loads((directory / "private/worker-state-before.json").read_text())
            if len(before) != 4 or any(s["artifacts"] for s in before.values()):
                issues.append("nonempty initial Worker store")
            if json.loads((directory / "worker-shutdown.json").read_text())["errors"]:
                issues.append("Worker shutdown error")
            tc = json.loads((directory / "tc-attestation.json").read_text())
            if tc["cleanup_error"] is not None or tc["original_qdisc"] != tc["restored_qdisc"]:
                issues.append("tc restore failed")
            if tc["applied_qdisc"] is None:
                issues.append("no tc shaping receipt")
            if route == "E":
                for event in events:
                    if (event["event_type"] == "logical.reasoning.input"
                            and event["payload"]["logical_agent_id"] == "manager"):
                        supplied = [json.loads(i["content"][len(RULE_PREFIX):])
                                    for i in event["payload"]["input_items"]
                                    if isinstance(i.get("content"), str)
                                    and i["content"].startswith(RULE_PREFIX)]
                        if supplied != [rules["rules"]]:
                            issues.append("effective E rule content mismatch")
            analysis = analyze(events)
            cells.append({"cell": cell, "method": route, "task": task["label"],
                "admission": admitted, "issues": sorted(set(issues)),
                "completed": result["execution_completed"], "final_answer": result["final_answer"],
                "evaluation": result.get("evaluation"), "failure": result.get("failure"),
                "analysis": analysis, "result_sha256": digest(result_path),
                "trace_sha256": digest(trace), "manifest_sha256": digest(directory / "freeze"
                                                                          / "manifest.json")})
            findings.extend(cell + ": " + i for i in issues)
    return {"version": "bde-audit-v1", "execution_revision": freeze["code_revision"],
            "protocol_sha256": digest(root / "protocol-freeze.json"),
            "rules_manifest_sha256": freeze["rules_manifest_sha256"],
            "rules_content_sha256": provenance_sha256(rules["rules"]),
            "expected_cells": len(TASKS) * len(CONDITIONS), "audited_cells": len(cells),
            "worker_store_count": len(stores), "findings": sorted(set(findings)), "cells": cells,
            "is_partial": partial, "no_inference_or_evaluator_call_performed": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    if args.root.resolve().parent != Path("/home/super/xiaoming"):
        raise RuntimeError("raw trace audit must run on 4090")
    write_new(args.output, audit(args.root, partial=args.partial))
