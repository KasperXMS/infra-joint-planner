"""Read-only final matrix admission/parity audit, run on4090 after queue exit.

No inference, artifact fetch, process launch, shaping, repair or quality-based
selection. Only append-only metadata is persisted; raw results remain remote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from cost_guidance_cell_analysis_v1 import analyze
from cost_guidance_private_multihop_audit_v1 import assert_queue_inactive

from infra_joint.evaluation.trace import JsonlTraceWriter

CONDITIONS = ("fast-ledger", "fast-quote", "slow-ledger", "slow-quote")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def trace_findings(events: list[dict[str, Any]], run_id: str) -> list[str]:
    """Check the whole serialized chain, not just a favorable terminal slice."""
    problems: list[str] = []
    previous: str | None = None
    seen: set[str] = set()
    for event in events:
        identifier = event.get("step_id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            problems.append("missing/duplicate trace event identifier")
        else:
            seen.add(identifier)
        if event.get("run_id") != run_id:
            problems.append("trace event run identity mismatch")
        if event.get("parent_id") != previous:
            problems.append("trace parent chain broken")
        if not event.get("timestamp"):
            problems.append("trace event timestamp missing")
        previous = identifier if isinstance(identifier, str) else None
    if not events or events[0]["event_type"] != "task.start":
        problems.append("trace task start missing")
    if not events or events[-1]["event_type"] != "run.end":
        problems.append("trace terminal run end missing")
    return sorted(set(problems))


def admission(directory: Path, result: Path, trace: Path) -> tuple[str, list[str]]:
    validation = read(directory / "lightweight-validation.json")
    if not validation["problems"]:
        return "original_operational_checks_pass", []
    path = directory / "postrun-eligibility-audit-001.json"
    if not path.is_file():
        return "audit_required", ["original gate findings lack independent adjudication"]
    audit = read(path)
    proven = (
        audit.get("effective_cell_retained") is True
        and audit.get("rerun") is False
        and audit.get("remaining_operational_gates_pass") is True
        and audit.get("runtime_or_semantic_behavior_changed") is False
        and audit.get("result_sha256") == digest(result)
        and audit.get("trace_sha256") == digest(trace)
    )
    return ("independently_adjudicated_retained", []) if proven else (
        "audit_required", ["independent adjudication fails exact retained-evidence check"])


def freeze_findings(
    manifest: dict[str, Any], method: dict[str, Any], task: dict[str, Any],
    protocol: dict[str, Any], condition: str,
) -> list[str]:
    """Do not relax any freeze in response to a semantic failure or low score."""
    problems: list[str] = []
    expected = {
        "code_revision": protocol["code_revision"],
        "task_bundle_sha256": task["task_bundle_sha256"],
        "static_capability_contract_sha256": task["static_capability_sha256"],
        "initial_placement": task["initial_placement"],
        "source_manifest": task["source_manifest"],
        "harness_manifest_sha256": protocol["harness_sha256"],
        "profile_visibility": "blind", "repetitions": 1,
        "retry": False, "replacement": False,
        "scheduler": "auto_physical_locality_aware", "model_service_timeout_seconds": 1200.0,
        "network_regime": condition.split("-")[0],
        "bandwidth_mbps": 100 if condition.startswith("fast-") else 3,
        "added_rtt_ms": 5 if condition.startswith("fast-") else 50,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            problems.append("cell freeze mismatch: " + key)
    for key in ("protocol_sha256", "component_sha256"):
        if method.get(key) != protocol[key]:
            problems.append("method freeze mismatch: " + key)
    for key, source in (("history_sha256", "history_file"),
                        ("history_manifest_sha256", "history_manifest_file")):
        if method.get(key) != digest(Path(protocol[source])):
            problems.append("historical estimator freeze mismatch: " + key)
    expected_method = "ledger-quote-v0" if condition.endswith("quote") else "ledger-only-v0"
    if method.get("method") != expected_method:
        problems.append("method identity differs from scheduled condition")
    if (method.get("raw_dynamic_profile_injected") is not False
            or method.get("specialists_and_verifier_blind") is not True):
        problems.append("method exposure contract mismatch")
    return problems


def audit_matrix(root: Path) -> dict[str, Any]:
    assert_queue_inactive(root)
    protocol_path = root / "protocol-freeze.json"
    protocol = read(protocol_path)
    problems: list[str] = []
    if digest(protocol_path) != (
        "f18bfff202a0314c29bdd673158ddcd875a08b084118df6a2b9df109bf1eec66"
    ):
        problems.append("initial protocol file freeze drift")
    harness_path = root / "app" / protocol["protocol"]["harness_manifest"]
    if digest(harness_path) != protocol["harness_sha256"]:
        problems.append("frozen semantic harness file drift")
    components = dict(protocol["component_sha256"])
    components["src/infra_joint/control/native_agents.py"] = (
        "b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985")
    for name, expected in components.items():
        if digest(root / "app" / name) != expected:
            problems.append("execution source drift: " + name)
    cells: list[dict[str, Any]] = []
    store_roots: set[str] = set()
    environments: set[str] = set()
    harnesses: list[dict[str, Any]] = []
    for task in protocol["tasks"]:
        for condition in CONDITIONS:
            cell = task["label"] + "-" + condition
            directory = root / "evidence" / cell
            results = list(directory.glob("runs/*/result.json"))
            if len(results) != 1 or not (results[0].parent / "trace.jsonl").is_file():
                raise RuntimeError("incomplete/ambiguous cell; never restart: " + cell)
            result_path = results[0]
            trace = result_path.parent / "trace.jsonl"
            status, findings = admission(directory, result_path, trace)
            manifest_path = directory / "freeze/manifest.json"
            manifest = read(manifest_path)
            findings += freeze_findings(manifest, read(directory / "method-freeze.json"),
                                       task, protocol, condition)
            if digest(root / "cell-configs" / (cell + ".yaml")) != manifest["config_sha256"]:
                findings.append("persisted cell config drift")
            environments.add(manifest["environment_sha256"])
            harnesses.append(manifest["harness"])
            roots = list(manifest["fresh_worker_stores"].values())
            if len(roots) != 4 or len(set(roots)) != 4 or set(roots) & store_roots:
                findings.append("Worker store count/reuse confounder")
            if any(root.name not in Path(path).parts for path in roots):
                findings.append("Worker stores outside owned experimental namespace")
            store_roots.update(roots)
            before = read(directory / "private/worker-state-before.json")
            if len(before) != 4 or any(state["artifacts"] for state in before.values()):
                findings.append("Worker stores were not initially empty")
            if read(directory / "worker-shutdown.json")["errors"]:
                findings.append("owned Worker shutdown errors")
            tc = read(directory / "tc-attestation.json")
            if tc.get("cleanup_error") is not None or tc["restored_qdisc"] != tc["original_qdisc"]:
                findings.append("network restoration not proven")
            method_audit = read(directory / "method-trace-audit.json")
            if method_audit["problems"]:
                findings.append("method trace isolation/accounting gate failed")
            events = JsonlTraceWriter(trace).read_all()
            result = read(result_path)
            findings += trace_findings(events, result["run_id"])
            analysis = analyze(events)
            if condition.endswith("quote") and any(
                not q["exact_card_visible_before_decision"] for q in analysis["quote_decisions"]
            ):
                # Audit flag, not a semantic-quality admission gate or retry instruction.
                findings.append("created quote lacks exact pre-decision Manager exposure receipt")
            evaluation = result.get("evaluation")
            if result["execution_completed"] and (
                not evaluation or not evaluation.get("format_valid")
            ):
                findings.append("completed cell missing valid terminal/evaluation contract")
            for finding in findings:
                problems.append(cell + ": " + finding)
            cells.append({
                "cell": cell, "run_id": result["run_id"], "admission": status,
                "problems": findings, "execution_completed": result["execution_completed"],
                "benchmark_score": evaluation.get("benchmark_score") if evaluation else None,
                "format_valid": evaluation.get("format_valid") if evaluation else None,
                "result_sha256": digest(result_path), "trace_sha256": digest(trace),
                "freeze_sha256": digest(manifest_path),
                "method_audit_sha256": digest(directory / "method-trace-audit.json"),
                "analysis": analysis,
            })
    if len(environments) != 1:
        problems.append("EnvironmentSpec changed across cells")
    if harnesses and any(h != harnesses[0] for h in harnesses):
        problems.append("semantic harness changed across cells")
    return {
        "audit_is_read_only": True, "audit_is_quality_selection": False,
        "protocol_file_sha256": digest(protocol_path),
        "protocol_content_sha256": protocol["protocol_sha256"],
        "execution_revision": protocol["code_revision"],
        "cell_count": len(cells), "distinct_worker_store_roots": len(store_roots),
        "problems": problems, "cells": cells,
        "does_not_establish_causality_or_statistical_significance": True,
    }


def main(args: argparse.Namespace) -> None:
    root = args.deployment_root.resolve()
    if not str(root).startswith("/home/super/xiaoming/cost-guidance-exploration-v1-"):
        raise RuntimeError("matrix audit must run on4090-owned evidence, not development PC")
    if args.output.exists():
        raise FileExistsError("choose a new append-only audit path")
    value = audit_matrix(root)
    value["audit_source_sha256"] = digest(Path(__file__))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"cells": value["cell_count"], "problems": value["problems"],
                      "audit_sha256": digest(args.output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
