"""Isolated 4090-owned A/C exploration; reuse the frozen physical/benchmark substrate."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import yaml
from blind_3family_validation_v1 import (
    REPO,
    _capability_sha256,
    _environment,
    _load_bundle,
    _operations,
    _public_bundle_digest,
    _revision,
    _sha256,
    _task_row,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
    validate_runtime_import_root,
)
from predecision_crossbenchmark_v1 import (
    audit_artifact_persistence,
    load_bundle,
    summarize_run_trace,
)
from prepare_sdk_native_infra_worker_v1_3 import prepare as prepare_worker
from resource_blind_live_validation_v1 import MANAGER_INSTRUCTIONS, _clients, _sdk_model
from run_predecision_matrix_v1 import HOSTS, start_worker, stop_worker, validate_cell, write_new
from run_sdk_native_infra_cell_with_tc_v1_3 import DEFAULT_ENDPOINTS
from run_sdk_native_infra_cell_with_tc_v1_3 import run as run_shaped
from sdk_native_blind_multihop_v1 import _assert_fresh
from sdk_native_infra_preliminary_v1_3 import (
    ModelRequestBodyAdapter,
    _freeze_cell,
    _load_control_plane_key,
)

from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.consequence_profiles import CostHistory
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX, is_ledger_message
from infra_joint.control.method_usage import MeasuredLedgerRuntime
from infra_joint.control.provenance import provenance_sha256
from infra_joint.control.quote_native import QuoteNativeRuntime, _contains_quote
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.state import LinkSpec
from infra_joint.core.task import OutputContract, OutputFormat
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.operators.catalog import build_operator_catalog

CONDITIONS = ("fast-ledger", "fast-quote", "slow-ledger", "slow-quote")
TASKS = ("multihop-multisource", "longbench-multidoc-academic",
         "longbench-multidoc-financial", "video-mme-848-1")
REFERENCE_PROTOCOL = "configs/experiments/predecision-crossbenchmark-v1-isolation-patch1.yaml"
HISTORY_SHA256 = "693f26bc8855f1712e22607e98ca4bc0571027e51d9db247dfe8f0012d3c392b"
HISTORY_MANIFEST_SHA256 = "bd10d6b146c42fe32e0888ca2138584c389d439e7e45aef186563e5bb7e15481"
METHOD_COMPONENTS = (
    "scripts/cost_guidance_exploration_v1.py", "src/infra_joint/control/ledger.py",
    "src/infra_joint/control/ledger_native.py", "src/infra_joint/control/method_usage.py",
    "src/infra_joint/control/quote.py", "src/infra_joint/control/quote_native.py",
    "src/infra_joint/control/consequence.py", "src/infra_joint/control/consequence_profiles.py",
)
REFERENCE_AUDIT = Path("/home/super/xiaoming/predecision-crossbenchmark-v1-3c3bd95"
                       "/audit-final-001.json")
REFERENCE_AUDIT_SHA256 = "d45fb9a1e6500a2c3d7121754e7358ae33c6ec1deff14b844c74a18f1b350e5e"


def protocol() -> dict[str, Any]:
    historical = _yaml(REPO / REFERENCE_PROTOCOL)
    base = _yaml(REPO / historical["source_experiment_config"])
    mh = _task_row(base, TASKS[0]).copy()
    mh["initial_placement"] = base["execution"]["initial_placement"][TASKS[0]]
    by_label = {row["label"]: row for row in historical["tasks"]}
    value = {k: v for k, v in historical.items() if k not in {
        "tasks", "condition_order", "experiment_id",
    }}
    value.update({
        "experiment_id": "cost-guidance-exploration-v1", "condition_order": CONDITIONS,
        "tasks": [mh, *(by_label[label] for label in TASKS[1:])],
        "maximum_substantive_cells": 36, "primary_cells": 16,
        "methods": {"ledger": "ledger-only-v0", "quote": "ledger-quote-v0"},
        "quote": {"ttl_seconds": 120, "max_proposals": 128, "minimum_support": 3},
        "history_sha256": HISTORY_SHA256, "history_manifest_sha256": HISTORY_MANIFEST_SHA256,
    })
    return value


def ensure_remote(root: Path) -> None:
    if (sys.platform != "linux" or root.parent != Path("/home/super/xiaoming")
            or not root.name.startswith("cost-guidance-exploration-v1-")):
        raise RuntimeError("dataset access/execution is allowed only in the 4090-owned namespace")


def base_config(value: dict[str, Any]) -> dict[str, Any]:
    base = _yaml(REPO / value["source_experiment_config"])
    base["dataset"]["tasks"] = value["tasks"]
    base["execution"]["initial_placement"] = {
        row["label"]: row["initial_placement"] for row in value["tasks"]
    }
    return base


def cell_config(value: dict[str, Any], root: Path, row: dict[str, Any],
                condition: str) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError("unknown exploration condition")
    regime, method = condition.split("-")
    run_id = f"{root.name}-{row['label']}-{condition}"
    stores = {
        agent: str((Path("/home/super") if agent == "strong-4090" else Path("/mnt/ssd"))
                   / "heterogeneous-v1/artifacts" / root.name / run_id / agent)
        for agent in HOSTS
    }
    return {"experiment_id": value["experiment_id"], "task": row["label"],
            "run_id": run_id, "method": method, "profile_visibility": "blind",
            "harness_manifest": value["harness_manifest"],
            "harness_manifest_sha256": value["harness_manifest_sha256"],
            "model_service_timeout_seconds": value["model_service_timeout_seconds"],
            "network": value["network_regimes"][regime], "worker_urls": value["worker_urls"],
            "fresh_worker_stores": stores, "execution": value["execution"]}


def task_bundle(row: dict[str, Any], base: dict[str, Any], value: dict[str, Any],
                args: argparse.Namespace) -> tuple[AdaptationBundle, dict[str, Any]]:
    if row["label"] != TASKS[0]:
        return load_bundle(row, base, value["sources"])
    bundle, source = _load_bundle({"task": TASKS[0]}, base, args)
    # Exactly the already-frozen prospective MultiHop terminal serialization contract.
    source["prospective_terminal_contract"] = {
        "original_public_bundle_sha256": _public_bundle_digest(bundle),
        "original_output_contract": bundle.execution.task.output_contract.model_dump(mode="json"),
        "canonical_labels": ["Yes", "No"], "private_evaluator_unchanged": True,
    }
    task = bundle.execution.task.model_copy(update={"output_contract": OutputContract(
        format=OutputFormat.SHORT_TEXT, canonical_labels=("Yes", "No"),
    )})
    return replace(bundle, execution=bundle.execution.model_copy(update={"task": task})), source


def load_history(args: argparse.Namespace) -> CostHistory:
    if (_sha256(args.cost_history) != HISTORY_SHA256
            or _sha256(args.history_manifest) != HISTORY_MANIFEST_SHA256):
        raise RuntimeError("clean empirical history drift")
    return CostHistory.model_validate_json(args.cost_history.read_text(encoding="utf-8"))


def verify_reference_tasks(tasks: list[dict[str, Any]]) -> None:
    """Private admission only: neither source evaluation nor gold reaches cost/Agent context."""
    if _sha256(REFERENCE_AUDIT) != REFERENCE_AUDIT_SHA256:
        raise RuntimeError("historical reference audit drift")
    rows = json.loads(REFERENCE_AUDIT.read_text())["effective_records"]
    for task in tasks:
        if task["label"] == TASKS[0]:
            if task["task_bundle_sha256"] != (
                "059cbc033c1e8610b2322ba4d57d5f49be67fa3ddeb08d9b3495e1c5f3787815"
            ):
                raise RuntimeError("MultiHop frozen representation drift")
            continue
        references = [r for r in rows if r["task_label"] == task["label"]]
        if len(references) != 4 or any(
            r["task_bundle_sha256"] != task["task_bundle_sha256"]
            or r["capability_sha256"] != task["static_capability_sha256"]
            or r["initial_placement"] != task["initial_placement"] for r in references
        ):
            raise RuntimeError("cross-benchmark frozen task/capability/placement drift")


def freeze_protocol(args: argparse.Namespace) -> None:
    value, history = protocol(), load_history(args)
    base = base_config(value)
    harness_path = REPO / value["harness_manifest"]
    _validate_harness_manifest_hash(value, harness_path)
    harness = load_harness(harness_path)
    registry = build_operator_catalog()
    tasks = []
    for row in value["tasks"]:
        bundle, source = task_bundle(row, base, value, args)
        environment = _environment(base, row["label"], bundle)
        capability = build_static_capability_contract(environment, registry, _operations(base))
        validate_harness(harness, environment, capability, _operations(base))
        tasks.append({"label": row["label"], "task_bundle_sha256": _public_bundle_digest(bundle),
                      "source_manifest": source, "static_capability_sha256":
                      _capability_sha256(capability), "initial_placement": {
                          p.artifact_id: p.agent_id for p in environment.initial_placements},
                      "validity": bundle.execution.validity.model_dump(mode="json"),
                      "transformations": [t.model_dump(mode="json")
                                          for t in bundle.execution.transformations]})
    verify_reference_tasks(tasks)
    write_new(args.deployment_root / "protocol-freeze.json", {
        "protocol": value, "protocol_sha256": provenance_sha256(value),
        "code_revision": _revision(), "component_sha256": {
            path: _sha256(REPO / path) for path in METHOD_COMPONENTS},
        "tasks": tasks, "history_file": str(args.cost_history),
        "history_manifest_file": str(args.history_manifest),
        "history_receipts": {"model": len(history.models),
                             "operator": len(history.operators),
                             "transfer": len(history.transfers)},
        "instructions_sha256": provenance_sha256(MANAGER_INSTRUCTIONS),
        "harness_sha256": _sha256(harness_path),
    })
    print(json.dumps({"event": "protocol_frozen", "primary_cells": 16,
                      "maximum_substantive_cells": 36}), flush=True)


async def execute_once(args: argparse.Namespace) -> None:
    validate_runtime_import_root()
    value, history = protocol(), load_history(args)
    config, base = _yaml(args.config), base_config(value)
    frozen = json.loads((args.deployment_root / "protocol-freeze.json").read_text())
    if (_revision() != frozen["code_revision"]
            or provenance_sha256(value) != frozen["protocol_sha256"]
            or any(_sha256(REPO / path) != digest
                   for path, digest in frozen["component_sha256"].items())):
        raise RuntimeError("frozen code/protocol drift")
    row = next(r for r in value["tasks"] if r["label"] == config["task"])
    bundle, source = task_bundle(row, base, value, args)
    task_freeze = next(t for t in frozen["tasks"] if t["label"] == row["label"])
    if (_public_bundle_digest(bundle) != task_freeze["task_bundle_sha256"]
            or source != task_freeze["source_manifest"]):
        raise RuntimeError("task representation/source drift")
    environment = _environment(base, row["label"], bundle)
    network = config["network"]
    environment = environment.model_copy(update={"links": tuple(
        LinkSpec(source_agent_id=a.agent_id, target_agent_id=b.agent_id,
                 bandwidth_mbps=network["bandwidth_mbps"], rtt_ms=network["added_rtt_ms"])
        for a in environment.agents for b in environment.agents if a.agent_id != b.agent_id
    )})
    registry, operations = build_operator_catalog(), _operations(base)
    capability = build_static_capability_contract(environment, registry, operations)
    harness_path = REPO / value["harness_manifest"]
    _validate_harness_manifest_hash(config, harness_path)
    harness = load_harness(harness_path)
    validate_harness(harness, environment, capability, operations)
    if _capability_sha256(capability) != task_freeze["static_capability_sha256"]:
        raise RuntimeError("static capability drift")
    manifest = _freeze_cell(args, config, REPO / value["environment_config"], harness_path,
                            harness, bundle, source, _capability_sha256(capability), base)
    write_new(args.output / "method-freeze.json", {
        "method": value["methods"][config["method"]],
        "protocol_sha256": frozen["protocol_sha256"],
        "component_sha256": frozen["component_sha256"], "history_sha256": HISTORY_SHA256,
        "history_manifest_sha256": HISTORY_MANIFEST_SHA256,
        "quote_settings": value["quote"], "raw_dynamic_profile_injected": False,
        "specialists_and_verifier_blind": True,
    })
    _load_control_plane_key(args.api_key_file, str(harness.manager["api_key_env"]))
    model = ModelRequestBodyAdapter(_sdk_model({"control_plane": {"manager_model": {
        "model": harness.manager["model"], "base_url": harness.manager["base_url"],
        "api_key_env": harness.manager["api_key_env"],
    }}}), dict(harness.manager["request_extra_body"]))
    runtime_options = {"name": "sdk-native-manager", "instructions": MANAGER_INSTRUCTIONS,
                       "model": model, "registry": registry, "available_operations": operations,
                       "enable_blind_verifier": True, "record_input_provenance": True}
    runtime = (MeasuredLedgerRuntime(**runtime_options) if config["method"] == "ledger" else
               QuoteNativeRuntime(environment=environment, cost_history=history,
                                  network_category="fast" if network["regime"] == "fast"
                                  else "constrained", reachable_workers=frozenset(HOSTS),
                                  **runtime_options))
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
            loop_budget=harness.budget, logical_runtime=runtime,
        )
        result = await runner.run(bundle, run_id=manifest.run_id)
    path = args.output / "runs" / manifest.run_id / "trace.jsonl"
    write_new(args.output / "summary.json", {
        "run_id": manifest.run_id, "method": config["method"], "task_label": manifest.task_label,
        "execution_completed": result.execution_completed, "final_answer": result.final_answer,
        "evaluation": (None if result.evaluation is None
                       else result.evaluation.model_dump(mode="json")),
        "failure": None if result.failure is None else result.failure.model_dump(mode="json"),
        "initial_transfer_bytes": sum(t.bytes_transferred for t in result.initial_transfers),
        "initial_transfer_latency_ms": sum(t.duration_ms for t in result.initial_transfers),
        "trace_summary": summarize_run_trace(path),
    })


async def execute_with_workers(args: argparse.Namespace) -> None:
    root, config = args.deployment_root, _yaml(args.config)
    pids: dict[str, int] = {}
    try:
        for agent in HOSTS:
            worker_config = root / "worker-configs" / f"{config['run_id']}-{agent}.yaml"
            prepare_worker(args.config, agent, worker_config)
            pids[agent] = start_worker(root, worker_config, agent,
                                       config["fresh_worker_stores"][agent])
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


def method_trace_audit(events: list[dict[str, Any]], method: str) -> dict[str, Any]:
    problems = []
    inputs = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.input"]
    manager = [p for p in inputs if p["logical_agent_id"] == "manager"]
    for payload in inputs:
        items = payload.get("input_items", [])
        ledgers = [item for item in items if is_ledger_message(item)]
        if provenance_sha256(items) != payload.get("input_sha256"):
            problems.append("effective reasoning input hash mismatch")
        if payload["logical_agent_id"] == "manager":
            if len(ledgers) != 1:
                problems.append("Manager must receive exactly one fresh ledger")
            if method == "ledger" and _contains_quote(items):
                problems.append("Ledger-only Manager received quote")
        elif ledgers or _contains_quote(items):
            problems.append("Blind specialist received ledger/quote")
    for event in events:
        if event["event_type"] == "logical.verification.input":
            context = event["payload"]["context"]
            if (_contains_quote(context) or LEDGER_MESSAGE_PREFIX in json.dumps(context)
                    or provenance_sha256(context) != event["payload"]["context_sha256"]):
                problems.append("Blind Verifier cost isolation/provenance failure")
    usage = [e["payload"] for e in events if e["event_type"] == "logical.method.reasoning_usage"]
    if not manager or not usage:
        problems.append("effective Manager inputs/usage missing")
    created = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.created"]
    observed = [e["payload"] for e in events if e["event_type"] == "logical.cost_quote.observed"]
    if method == "quote":
        if not any(e["event_type"] == "logical.cost_quote.run.end" for e in events):
            problems.append("quote run accounting missing")
        ids = [p["quote"]["quote_id"] for p in created]
        if len(set(ids)) != len(ids):
            problems.append("duplicate quote ID")
    elif created or observed:
        problems.append("Ledger-only route contains quote execution")
    return {"problems": sorted(set(problems)), "manager_inputs": len(manager),
            "specialist_inputs": len(inputs) - len(manager), "metered_reasoning_calls": len(usage),
            "quotes_created": len(created), "quoted_receipts": len(observed)}


def journal(root: Path, value: dict[str, Any]) -> None:
    with (root / "queue.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def run_queue(args: argparse.Namespace) -> None:
    args.deployment_root = args.deployment_root.resolve()
    ensure_remote(args.deployment_root)
    if args.prepare:
        freeze_protocol(args)
        return
    value = protocol()
    journal(args.deployment_root, {"event": "started", "pid": os.getpid()})
    for row in value["tasks"]:
        for condition in CONDITIONS:
            cell = row["label"] + "-" + condition
            if args.only_cell is not None and args.only_cell != cell:
                continue
            args.output = args.deployment_root / "evidence" / cell
            args.output.mkdir(parents=True, exist_ok=False)
            config = cell_config(value, args.deployment_root, row, condition)
            args.config = args.deployment_root / "cell-configs" / f"{cell}.yaml"
            args.config.parent.mkdir(exist_ok=True)
            with args.config.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            journal(args.deployment_root, {"event": "cell_started", "cell": cell,
                                          "run_id": config["run_id"]})
            reserve_cell(config["run_id"])
            try:
                asyncio.run(run_shaped(args, execute_with_workers))
                labels = ("Yes", "No") if row["label"] == TASKS[0] else ("A", "B", "C", "D")
                validation = validate_cell(args.output, config["run_id"], "blind", labels)
                events = JsonlTraceWriter(args.output / "runs" / config["run_id"]
                                          / "trace.jsonl").read_all()
                audit = method_trace_audit(events, config["method"])
                persistence = audit_artifact_persistence(args.output, config["run_id"])
                write_new(args.output / "private/artifact-persistence.json", persistence)
                write_new(args.output / "method-trace-audit.json", audit)
                validation["problems"].extend(audit["problems"])
                if not persistence["pass"]:
                    validation["problems"].append("artifact persistence incident")
                write_new(args.output / "lightweight-validation.json", validation)
                journal(args.deployment_root, {"event": "cell_finished", "cell": cell,
                                               "valid": not validation["problems"],
                                               "completed": validation["completed"]})
                if validation["problems"]:
                    raise RuntimeError("implementation/environment audit required")
            except BaseException as error:
                journal(args.deployment_root, {"event": "audit_required", "cell": cell,
                                               "exception_type": type(error).__name__,
                                               "message": str(error)})
                raise
    journal(args.deployment_root, {"event": "completed", "only_cell": args.only_cell})


def reserve_cell(run_id: str, *, budget_file: Path | None = None) -> None:
    """Conservative global cap across revisions; affected reruns also consume a slot."""
    path = budget_file or Path("/home/super/xiaoming"
                               "/cost-guidance-exploration-v1-cell-budget.jsonl")
    with path.open("a+", encoding="utf-8") as stream:
        stream.seek(0)
        records = [json.loads(line) for line in stream if line.strip()]
        if len(records) >= 36 or any(r["run_id"] == run_id for r in records):
            raise RuntimeError("exploration cap reached or run already reserved; never retry")
        stream.write(json.dumps({"run_id": run_id, "execution_revision": _revision()}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def main(args: argparse.Namespace) -> None:
    ensure_remote(args.deployment_root.resolve())
    import fcntl  # Linux-only controller; no benchmark access on the development PC.

    path = Path("/home/super/xiaoming/cost-guidance-exploration-v1-controller.lock")
    with path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run_queue(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--endpoint-config", type=Path, default=DEFAULT_ENDPOINTS)
    history = Path("/home/super/xiaoming/cost-guidance-history-v0-00ff980/freeze-001")
    parser.add_argument("--cost-history", type=Path, default=history / "cost-history.json")
    parser.add_argument("--history-manifest", type=Path, default=history / "manifest.json")
    data = Path("/home/super/xiaoming/blind_baseline_6task_v1/data")
    parser.add_argument("--multihop-corpus", type=Path, default=data / "corpus.json")
    parser.add_argument("--multihop-queries", type=Path, default=data / "MultiHopRAG.json")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--only-cell", choices=[t + "-" + c for t in TASKS for c in CONDITIONS])
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
