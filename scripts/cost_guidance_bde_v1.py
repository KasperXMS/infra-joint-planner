"""4090-only B/D/E follow-up: 18 prospective cells, same global 36-cell cap."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any

import cost_guidance_exploration_v1 as frozen
import httpx
import yaml
from build_cost_guidance_history_v1 import verified_trace
from openai import AsyncOpenAI
from predecision_crossbenchmark_v1 import audit_artifact_persistence, summarize_run_trace
from prepare_sdk_native_infra_worker_v1_3 import prepare as prepare_worker
from resource_blind_live_validation_v1 import MANAGER_INSTRUCTIONS, _clients, _sdk_model
from run_predecision_matrix_v1 import HOSTS, start_worker, stop_worker, validate_cell, write_new
from run_sdk_native_infra_cell_with_tc_v1_3 import run as run_shaped
from sdk_native_blind_multihop_v1 import _assert_fresh
from sdk_native_infra_preliminary_v1_3 import (
    ModelRequestBodyAdapter,
    _freeze_cell,
    _load_control_plane_key,
)

from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.bde_native import BDENativeRuntime, contains_bde_feedback
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.cost_rules import (
    DISTILLATION_INSTRUCTIONS,
    anonymized_cost_trace,
    parse_rules,
    validate_rule_set,
)
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX, is_ledger_message
from infra_joint.control.provenance import provenance_sha256
from infra_joint.control.quote_native import _contains_quote
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.state import LinkSpec
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.operators.catalog import build_operator_catalog

TASKS = (frozen.TASKS[0], frozen.TASKS[1], frozen.TASKS[3])
CONDITIONS = tuple(f"{regime}-{route}" for regime in ("fast", "slow")
                   for route in ("B", "D", "E"))
COMPONENTS = (*frozen.METHOD_COMPONENTS, "scripts/cost_guidance_bde_v1.py",
              "src/infra_joint/control/bde_native.py", "src/infra_joint/control/cost_rules.py")
TRAIN_TASKS = ("longbench-multidoc-financial", "longbench-multidoc-news", "video-mme-795-3")


def protocol() -> dict[str, Any]:
    value = frozen.protocol()
    value.update({"experiment_id": "cost-guidance-bde-v1", "primary_cells": 18,
                  "tasks": [r for r in value["tasks"] if r["label"] in TASKS],
                  "condition_order": CONDITIONS, "methods": {
                      "B": "optional-ready-action-cards-v0",
                      "D": "bounded-agent-candidate-comparison-v0",
                      "E": "optional-cards-trace-distilled-rules-v0"},
                  "distillation_source_tasks": TRAIN_TASKS,
                  "maximum_candidates": 3, "automatic_candidate_selection": False,
                  "query_execution_is_optional_for_B_E": True,
                  "prior_A_C_cells": 16, "global_primary_total": 34})
    return value


def distillation_examples(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    # Select solely by predeclared task holdout, NOT completion/evaluator score.
    selected = [r for r in manifest["runs"]
                if any(label in r["run_id"] for label in TRAIN_TASKS)]
    if any(any(label in r["run_id"] for label in TASKS) for r in selected) or not selected:
        raise ValueError("distillation/test task overlap or empty independent history")
    return [anonymized_cost_trace(verified_trace(
        Path(r["evidence_directory"]), {**r, "evidence_hashes": r["source_hashes"]}), r["run_id"])
            for r in selected]


async def distill(args: argparse.Namespace) -> None:
    frozen.load_history(args)  # Same source audit SHA guard as the numeric profiles.
    examples = distillation_examples(json.loads(args.history_manifest.read_text()))
    path = args.deployment_root / "rules"
    path.mkdir(exist_ok=False)
    harness = frozen.load_harness(frozen.REPO / protocol()["harness_manifest"])
    _load_control_plane_key(args.api_key_file, str(harness.manager["api_key_env"]))
    request = {"instructions": DISTILLATION_INSTRUCTIONS, "examples": examples}
    write_new(path / "request.json", request)
    write_new(path / "attempt.json", {"calls": 1, "retry": False,
              "model": harness.manager["model"], "source_manifest_sha256":
              frozen.HISTORY_MANIFEST_SHA256, "code_revision": frozen._revision(),
              "request_sha256": provenance_sha256(request), "test_tasks_excluded": TASKS})
    started = perf_counter()
    try:
        async with AsyncOpenAI(base_url=harness.manager["base_url"],
                               api_key=os.environ[harness.manager["api_key_env"]],
                               max_retries=0, timeout=1200) as client:
            response = await client.chat.completions.create(
                model=harness.manager["model"], messages=[
                    {"role": "system", "content": DISTILLATION_INSTRUCTIONS},
                    {"role": "user", "content": json.dumps({"examples": examples})}],
                extra_body=dict(harness.manager["request_extra_body"]),
            )
        write_new(path / "response.json", response.model_dump(mode="json"))
        rules = parse_rules(response.choices[0].message.content or "")
        validate_rule_set(rules, examples)
        payload = rules.model_dump(mode="json")
        write_new(args.rules_manifest, {
            "version": "trace-distilled-cost-rules-v0", "rules": payload,
            "rules_sha256": provenance_sha256(payload),
            "examples_sha256": provenance_sha256(examples),
            "source_manifest_sha256": frozen.HISTORY_MANIFEST_SHA256,
            "distillation_model": harness.manager["model"],
            "distillation_latency_ms": (perf_counter() - started) * 1000,
            "distillation_usage": None if response.usage is None
            else response.usage.model_dump(mode="json"),
            "source_tasks": TRAIN_TASKS, "excluded_test_tasks": TASKS,
            "quality_used": False, "new_A_C_results_used": False,
            "prompt_sha256": provenance_sha256(DISTILLATION_INSTRUCTIONS),
            "request_file_sha256": frozen._sha256(path / "request.json"),
            "response_file_sha256": frozen._sha256(path / "response.json"),
            "lineage": "in-context trace heuristics; Enum/GRPO-related idea, no RL/weight update",
        })
    except BaseException as error:
        write_new(path / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


def freeze(args: argparse.Namespace) -> None:
    value = protocol()
    history = frozen.load_history(args)
    base = frozen.base_config(value)
    harness_path = frozen.REPO / value["harness_manifest"]
    harness = frozen.load_harness(harness_path)
    frozen._validate_harness_manifest_hash(value, harness_path)
    registry = build_operator_catalog()
    tasks = []
    for row in value["tasks"]:
        bundle, source = frozen.task_bundle(row, base, value, args)
        environment = frozen._environment(base, row["label"], bundle)
        capability = build_static_capability_contract(
            environment, registry, frozen._operations(base))
        frozen.validate_harness(harness, environment, capability, frozen._operations(base))
        tasks.append({"label": row["label"], "task_bundle_sha256":
                      frozen._public_bundle_digest(bundle), "source_manifest": source,
                      "static_capability_sha256": frozen._capability_sha256(capability),
                      "initial_placement": {p.artifact_id: p.agent_id
                                            for p in environment.initial_placements}})
    frozen.verify_reference_tasks(tasks)
    rules = json.loads(args.rules_manifest.read_text())
    if (rules["source_manifest_sha256"] != frozen.HISTORY_MANIFEST_SHA256
            or tuple(rules["excluded_test_tasks"]) != TASKS
            or provenance_sha256(rules["rules"]) != rules["rules_sha256"]):
        raise RuntimeError("distillation holdout/provenance mismatch")
    write_new(args.deployment_root / "protocol-freeze.json", {
        "protocol": value, "protocol_sha256": provenance_sha256(value),
        "code_revision": frozen._revision(), "component_sha256": {
            p: frozen._sha256(frozen.REPO / p) for p in COMPONENTS},
        "tasks": tasks, "rules_manifest_sha256": frozen._sha256(args.rules_manifest),
        "history_receipts": {"model": len(history.models), "operator": len(history.operators),
                             "transfer": len(history.transfers)},
        "harness_sha256": frozen._sha256(harness_path),
        "instructions_sha256": provenance_sha256(MANAGER_INSTRUCTIONS),
    })


def cell_config(root: Path, row: dict[str, Any], condition: str) -> dict[str, Any]:
    regime, route = condition.split("-")
    value = protocol()
    cfg = frozen.cell_config(value, root, row, regime + "-ledger")
    old_id = cfg["run_id"]
    cfg["run_id"] = old_id.removesuffix("ledger") + route
    cfg["method"] = route
    cfg["fresh_worker_stores"] = {k: v.replace(old_id, cfg["run_id"])
                                  for k, v in cfg["fresh_worker_stores"].items()}
    return cfg


async def execute_once(args: argparse.Namespace) -> None:
    frozen.validate_runtime_import_root()
    value, history = protocol(), frozen.load_history(args)
    config, base = frozen._yaml(args.config), frozen.base_config(value)
    saved = json.loads((args.deployment_root / "protocol-freeze.json").read_text())
    if (frozen._revision() != saved["code_revision"]
            or provenance_sha256(value) != saved["protocol_sha256"]
            or any(frozen._sha256(frozen.REPO / p) != sha
                   for p, sha in saved["component_sha256"].items())
            or frozen._sha256(args.rules_manifest) != saved["rules_manifest_sha256"]):
        raise RuntimeError("frozen BDE code/config/rules drift")
    row = next(r for r in value["tasks"] if r["label"] == config["task"])
    bundle, source = frozen.task_bundle(row, base, value, args)
    task_freeze = next(t for t in saved["tasks"] if t["label"] == row["label"])
    if (frozen._public_bundle_digest(bundle) != task_freeze["task_bundle_sha256"]
            or source != task_freeze["source_manifest"]):
        raise RuntimeError("task representation/source drift")
    environment = frozen._environment(base, row["label"], bundle)
    network = config["network"]
    environment = environment.model_copy(update={"links": tuple(
        LinkSpec(source_agent_id=a.agent_id, target_agent_id=b.agent_id,
                 bandwidth_mbps=network["bandwidth_mbps"], rtt_ms=network["added_rtt_ms"])
        for a in environment.agents for b in environment.agents if a.agent_id != b.agent_id)})
    registry, operations = build_operator_catalog(), frozen._operations(base)
    capability = build_static_capability_contract(environment, registry, operations)
    harness_path = frozen.REPO / value["harness_manifest"]
    harness = frozen.load_harness(harness_path)
    frozen.validate_harness(harness, environment, capability, operations)
    if frozen._capability_sha256(capability) != task_freeze["static_capability_sha256"]:
        raise RuntimeError("static capability drift")
    manifest = _freeze_cell(args, config, frozen.REPO / value["environment_config"], harness_path,
                            harness, bundle, source, frozen._capability_sha256(capability), base)
    write_new(args.output / "method-freeze.json", {
        "method": value["methods"][config["method"]], "protocol_sha256": saved["protocol_sha256"],
        "component_sha256": saved["component_sha256"], "history_sha256": frozen.HISTORY_SHA256,
        "rules_manifest_sha256": saved["rules_manifest_sha256"],
        "raw_dynamic_profile_injected": False, "specialists_and_verifier_blind": True})
    _load_control_plane_key(args.api_key_file, str(harness.manager["api_key_env"]))
    model = ModelRequestBodyAdapter(_sdk_model({"control_plane": {"manager_model": {
        "model": harness.manager["model"], "base_url": harness.manager["base_url"],
        "api_key_env": harness.manager["api_key_env"]}}}),
        dict(harness.manager["request_extra_body"]))
    runtime = BDENativeRuntime(
        route=config["method"], rules=json.loads(args.rules_manifest.read_text())["rules"]
        if config["method"] == "E" else None,
        environment=environment, cost_history=history,
        network_category="fast" if network["regime"] == "fast" else "constrained",
        reachable_workers=frozenset(HOSTS), name="sdk-native-manager",
        instructions=MANAGER_INSTRUCTIONS, model=model, registry=registry,
        available_operations=operations, enable_blind_verifier=True, record_input_provenance=True,
    )
    async with AsyncExitStack() as stack:
        clients = await _clients(stack, manifest.worker_urls,
                                 timeout_seconds=manifest.model_service_timeout_seconds)
        await _assert_fresh(clients)
        runner = ControlPlaneBenchmarkRunner(
            RunnerConfig(environment=environment, worker_urls=manifest.worker_urls,
                         planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                         output_root=args.output / "runs",
                         max_planning_steps=harness.budget.max_manager_turns,
                         http_timeout_seconds=manifest.model_service_timeout_seconds),
            None, operations, worker_clients=clients, profile_visibility=ProfileVisibility.BLIND,
            loop_budget=harness.budget, logical_runtime=runtime)
        result = await runner.run(bundle, run_id=manifest.run_id)
    trace = args.output / "runs" / manifest.run_id / "trace.jsonl"
    write_new(args.output / "summary.json", {
        "run_id": manifest.run_id, "method": config["method"], "task_label": manifest.task_label,
        "execution_completed": result.execution_completed, "final_answer": result.final_answer,
        "evaluation": None if result.evaluation is None
        else result.evaluation.model_dump(mode="json"),
        "failure": None if result.failure is None else result.failure.model_dump(mode="json"),
        "initial_transfer_bytes": sum(t.bytes_transferred for t in result.initial_transfers),
        "initial_transfer_latency_ms": sum(t.duration_ms for t in result.initial_transfers),
        "trace_summary": summarize_run_trace(trace)})


async def execute_with_workers(args: argparse.Namespace) -> None:
    root, config = args.deployment_root, frozen._yaml(args.config)
    pids: dict[str, int] = {}
    try:
        for agent in HOSTS:
            worker_cfg = root / "worker-configs" / f"{config['run_id']}-{agent}.yaml"
            prepare_worker(args.config, agent, worker_cfg)
            pids[agent] = start_worker(
                root, worker_cfg, agent, config["fresh_worker_stores"][agent])
        write_new(args.output / "worker-pids.json", pids)
        async with httpx.AsyncClient(timeout=10) as client:
            states = {}
            for agent, url in config["worker_urls"].items():
                for attempt in range(60):
                    try:
                        response = await client.get(url + "/state")
                        response.raise_for_status()
                        state = response.json()
                        if state["agent_id"] != agent or state["artifacts"]:
                            raise RuntimeError("fresh Worker identity/store invalid")
                        states[agent] = state
                        break
                    except httpx.HTTPError:
                        if attempt == 59:
                            raise
                        await asyncio.sleep(1)
            write_new(args.output / "private/worker-state-before.json", states)
            await execute_once(args)
            after = {}
            for agent, url in config["worker_urls"].items():
                response = await client.get(url + "/state")
                response.raise_for_status()
                after[agent] = response.json()
            write_new(args.output / "private/worker-state-after.json", after)
    finally:
        errors = []
        for agent, pid in pids.items():
            try:
                stop_worker(root, agent, pid)
            except Exception as error:
                errors.append(f"{agent}: {type(error).__name__}: {error}")
        write_new(args.output / "worker-shutdown.json", {"errors": errors})
        if errors:
            raise RuntimeError("owned Worker shutdown incomplete")


def method_audit(events: list[dict[str, Any]], route: str) -> dict[str, Any]:
    issues = []
    manager_inputs = 0
    for event in events:
        p = event["payload"]
        if event["event_type"] == "logical.reasoning.input":
            items = p.get("input_items", [])
            if provenance_sha256(items) != p.get("input_sha256"):
                issues.append("reasoning input provenance mismatch")
            ledgers = [i for i in items if is_ledger_message(i)]
            if p["logical_agent_id"] == "manager":
                manager_inputs += 1
                if len(ledgers) != 1:
                    issues.append("Manager missing exact fresh ledger")
            elif ledgers or _contains_quote(items) or contains_bde_feedback(items):
                issues.append("specialist cost leakage")
        if event["event_type"] == "logical.verification.input":
            context = p["context"]
            if (_contains_quote(context) or contains_bde_feedback(context)
                    or LEDGER_MESSAGE_PREFIX in json.dumps(context)
                    or provenance_sha256(context) != p["context_sha256"]):
                issues.append("Verifier cost isolation/provenance failure")
    if not manager_inputs:
        issues.append("missing effective Manager inputs")
    counts = {k: sum(e["event_type"] == k for e in events) for k in (
        "logical.cost_card.returned", "logical.cost_card.matched",
        "logical.cost_candidates.returned", "logical.cost_candidates.selected",
        "logical.cost_rules.predecision", "logical.method.reasoning_usage")}
    if route == "E" and counts["logical.cost_rules.predecision"] != manager_inputs:
        issues.append("E missing rule feedback")
    return {"problems": sorted(set(issues)), "manager_inputs": manager_inputs, "counts": counts}


def queue(args: argparse.Namespace) -> None:
    value = protocol()
    frozen.journal(args.deployment_root, {"event": "started", "pid": os.getpid()})
    for row in value["tasks"]:
        for condition in CONDITIONS:
            cell = row["label"] + "-" + condition
            if args.only_cell and args.only_cell != cell:
                continue
            args.output = args.deployment_root / "evidence" / cell
            args.output.mkdir(parents=True, exist_ok=False)
            config = cell_config(args.deployment_root, row, condition)
            args.config = args.deployment_root / "cell-configs" / f"{cell}.yaml"
            args.config.parent.mkdir(exist_ok=True)
            with args.config.open("x") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            frozen.reserve_cell(config["run_id"])
            frozen.journal(args.deployment_root, {"event": "cell_started", "cell": cell,
                                                  "run_id": config["run_id"]})
            try:
                asyncio.run(run_shaped(args, execute_with_workers))
                labels = ("Yes", "No") if row["label"] == TASKS[0] else ("A", "B", "C", "D")
                validation = validate_cell(args.output, config["run_id"], "blind", labels)
                events = JsonlTraceWriter(args.output / "runs" / config["run_id"]
                                          / "trace.jsonl").read_all()
                audit = method_audit(events, config["method"])
                persistence = audit_artifact_persistence(args.output, config["run_id"])
                write_new(args.output / "private/artifact-persistence.json", persistence)
                write_new(args.output / "method-trace-audit.json", audit)
                validation["problems"].extend(audit["problems"])
                if not persistence["pass"]:
                    validation["problems"].append("artifact persistence incident")
                write_new(args.output / "lightweight-validation.json", validation)
                frozen.journal(args.deployment_root, {"event": "cell_finished", "cell": cell,
                    "valid": not validation["problems"], "completed": validation["completed"]})
                if validation["problems"]:
                    raise RuntimeError("implementation/environment audit required")
            except BaseException as error:
                frozen.journal(args.deployment_root, {"event": "audit_required", "cell": cell,
                    "exception_type": type(error).__name__, "message": str(error)})
                raise
    frozen.journal(args.deployment_root, {"event": "completed", "only_cell": args.only_cell})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--endpoint-config", type=Path, default=frozen.DEFAULT_ENDPOINTS)
    history = Path("/home/super/xiaoming/cost-guidance-history-v0-00ff980/freeze-001")
    parser.add_argument("--cost-history", type=Path, default=history / "cost-history.json")
    parser.add_argument("--history-manifest", type=Path, default=history / "manifest.json")
    data = Path("/home/super/xiaoming/blind_baseline_6task_v1/data")
    parser.add_argument("--multihop-corpus", type=Path, default=data / "corpus.json")
    parser.add_argument("--multihop-queries", type=Path, default=data / "MultiHopRAG.json")
    parser.add_argument("--rules-manifest", type=Path)
    parser.add_argument("--distill", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--only-cell", choices=[t + "-" + c for t in TASKS for c in CONDITIONS])
    args = parser.parse_args()
    args.deployment_root = args.deployment_root.resolve()
    frozen.ensure_remote(args.deployment_root)
    if args.rules_manifest is None:
        args.rules_manifest = args.deployment_root / "rules/rules-freeze.json"
    import fcntl

    lock_path = Path("/home/super/xiaoming/cost-guidance-exploration-v1-controller.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.distill:
            asyncio.run(distill(args))
        elif args.prepare:
            freeze(args)
        else:
            queue(args)


if __name__ == "__main__":
    main()
