"""Frozen pre-decision cross-benchmark cells; run only on the dataset-owning 4090.

Only dataset admission and experiment orchestration differ from the MultiHop entry.
The original runtime, instructions, Verifier, capability contract and evaluator are reused.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import httpx
import yaml
from blind_3family_validation_v1 import (
    REPO,
    _capability_sha256,
    _environment,
    _load_longbench_samples,
    _load_video_bundles,
    _longbench_multidoc_bundle,
    _operations,
    _public_bundle_digest,
    _revision,
    _sha256,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
    validate_runtime_import_root,
)
from prepare_sdk_native_infra_worker_v1_3 import prepare
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
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.state import LinkSpec
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.evaluation.trace_audit import (
    summarize_concurrency,
    summarize_cost,
    summarize_profiles,
)
from infra_joint.operators.catalog import build_operator_catalog

CONDITIONS = ("fast-blind", "fast-aware", "slow-blind", "slow-aware")
FAMILIES = ("longbench_multidoc", "video_mme")


def validate_protocol(value: Mapping[str, Any]) -> None:
    if tuple(value["condition_order"]) != CONDITIONS:
        raise ValueError("condition order drift")
    if value["execution"] != {
        "scheduler": "auto_physical_locality_aware", "repetitions": 1,
        "retry": False, "replacement": False,
    }:
        raise ValueError("single-run execution drift")
    rows = value["tasks"]
    if len(rows) != 6 or len({r["source_task_id"] + str(r.get("question_id", ""))
                              for r in rows}) != 6:
        raise ValueError("six distinct tasks required")
    if [r["family"] for r in rows] != [FAMILIES[0]] * 3 + [FAMILIES[1]] * 3:
        raise ValueError("three LongBench tasks followed by three Video tasks required")
    if len({r["label"] for r in rows}) != 6:
        raise ValueError("unique labels required")
    for regime, expected in (("fast", (100, 5)), ("slow", (3, 50))):
        network = value["network_regimes"][regime]
        if (network["regime"], network["bandwidth_mbps"], network["added_rtt_ms"]) != (
            regime, *expected,
        ):
            raise ValueError("network drift")


def base_config(protocol: dict[str, Any]) -> dict[str, Any]:
    value = _yaml(REPO / str(protocol["source_experiment_config"]))
    value["dataset"]["tasks"] = protocol["tasks"]
    value["execution"]["initial_placement"] = {
        row["label"]: row["initial_placement"] for row in protocol["tasks"]
    }
    return value


def load_bundle(
    row: dict[str, Any], base: dict[str, Any], sources: dict[str, Any],
) -> tuple[AdaptationBundle, dict[str, Any]]:
    revisions = base["dataset"]["revisions"]
    if row["family"] == "longbench_multidoc":
        path = Path(sources["longbench_samples"])
        sample = _load_longbench_samples(path, {row["source_task_id"]})[row["source_task_id"]]
        bundle = _longbench_multidoc_bundle(
            sample, revisions["longbench_v2"], tuple(row["boundary_lines"]),
        )
        return bundle, {"longbench_samples": {"sha256": _sha256(path),
                                             "size_bytes": path.stat().st_size}}
    if row["family"] != "video_mme":
        raise ValueError("unknown family")
    task_path, answer_path = Path(sources["video_tasks"]), Path(sources["video_answers"])
    path = Path(sources["video_sources"]) / row["source_filename"]
    bundle = _load_video_bundles(
        [row], task_path=task_path, answer_path=answer_path,
        source_root=Path(sources["video_sources"]), source_revision=revisions["video_mme"],
    )[row["label"]]
    return bundle, {"video_tasks": {"sha256": _sha256(task_path)},
                    "video_answers": {"sha256": _sha256(answer_path)},
                    "video_source": {"sha256": _sha256(path), "size_bytes": path.stat().st_size,
                                     "filename": path.name}}


def cell_config(
    protocol: dict[str, Any], row: dict[str, Any], condition: str, attempt: str = "primary",
) -> dict[str, Any]:
    regime, visibility = condition.split("-")
    cell = f"{row['label']}-{condition}-{attempt}"
    stores = {
        agent: str((Path("/home/super") if agent == "strong-4090" else Path("/mnt/ssd"))
                   / "heterogeneous-v1/artifacts/predecision-crossbenchmark-v1" / cell / agent)
        for agent in HOSTS
    }
    return {"experiment_id": "predecision-crossbenchmark-v1", "task": row["label"],
            "run_id": "crossbenchmark-v1-" + cell, "profile_visibility": visibility,
            "harness_manifest": protocol["harness_manifest"],
            "harness_manifest_sha256": protocol["harness_manifest_sha256"],
            "model_service_timeout_seconds": protocol["model_service_timeout_seconds"],
            "network": protocol["network_regimes"][regime],
            "worker_urls": protocol["worker_urls"], "fresh_worker_stores": stores,
            "execution": protocol["execution"]}


def ensure_remote(root: Path) -> None:
    if sys.platform != "linux" or root.parent != Path("/home/super/xiaoming") or not (
        root.name.startswith("predecision-crossbenchmark-v1-")
    ):
        raise RuntimeError("dataset access and execution allowed only on strong-4090")


def prepare_protocol(args: argparse.Namespace) -> None:
    root = args.deployment_root.resolve()
    ensure_remote(root)
    protocol = _yaml(args.protocol)
    validate_protocol(protocol)
    base = base_config(protocol)
    harness_path = REPO / protocol["harness_manifest"]
    _validate_harness_manifest_hash(protocol, harness_path)
    harness = load_harness(harness_path)
    registry = build_operator_catalog()
    frozen: list[dict[str, Any]] = []
    for row in protocol["tasks"]:
        bundle, source = load_bundle(row, base, protocol["sources"])
        environment = _environment(base, row["label"], bundle)
        capabilities = build_static_capability_contract(environment, registry, _operations(base))
        validate_harness(harness, environment, capabilities, _operations(base))
        frozen.append({"label": row["label"], "family": row["family"],
                       "task_bundle_sha256": _public_bundle_digest(bundle),
                       "source_manifest": source,
                       "initial_placement": {p.artifact_id: p.agent_id
                                             for p in environment.initial_placements},
                       "transformations": [t.model_dump(mode="json")
                                           for t in bundle.execution.transformations],
                       "validity": bundle.execution.validity.model_dump(mode="json"),
                       "artifact_metadata": [p.spec.model_dump(mode="json")
                                             for p in bundle.prepared_artifacts],
                       "static_capability_sha256": _capability_sha256(capabilities)})
    write_new(root / "protocol-freeze.json", {
        "code_revision": _revision(), "protocol_sha256": _sha256(args.protocol),
        "runner_sha256": _sha256(Path(__file__)), "tasks": frozen,
        "harness_sha256": _sha256(harness_path), "formal_cells": 24,
    })
    print(json.dumps({"prepared_tasks": len(frozen), "formal_cells": 24,
                      "code_revision": _revision()}), flush=True)


async def execute_once(args: argparse.Namespace) -> None:
    validate_runtime_import_root()
    protocol = _yaml(args.protocol)
    validate_protocol(protocol)
    config = _yaml(args.config)
    base = base_config(protocol)
    row = next(r for r in protocol["tasks"] if r["label"] == config["task"])
    harness_path = REPO / protocol["harness_manifest"]
    _validate_harness_manifest_hash(config, harness_path)
    harness = load_harness(harness_path)
    _load_control_plane_key(args.api_key_file, str(harness.manager["api_key_env"]))
    bundle, source = load_bundle(row, base, protocol["sources"])
    freeze = json.loads((args.deployment_root / "protocol-freeze.json").read_text())
    frozen_task = next(t for t in freeze["tasks"] if t["label"] == row["label"])
    if (_public_bundle_digest(bundle) != frozen_task["task_bundle_sha256"]
            or source != frozen_task["source_manifest"]
            or _sha256(args.protocol) != freeze["protocol_sha256"]
            or _sha256(Path(__file__)) != freeze["runner_sha256"]
            or _revision() != freeze["code_revision"]):
        raise RuntimeError("frozen source/protocol/code drift")
    environment = _environment(base, row["label"], bundle)
    network = config["network"]
    environment = environment.model_copy(update={"links": tuple(
        LinkSpec(source_agent_id=a.agent_id, target_agent_id=b.agent_id,
                 bandwidth_mbps=network["bandwidth_mbps"], rtt_ms=network["added_rtt_ms"])
        for a in environment.agents for b in environment.agents if a.agent_id != b.agent_id
    )})
    registry = build_operator_catalog()
    operations = _operations(base)
    capabilities = build_static_capability_contract(environment, registry, operations)
    validate_harness(harness, environment, capabilities, operations)
    manifest = _freeze_cell(args, config, REPO / protocol["environment_config"], harness_path,
                            harness, bundle, source, _capability_sha256(capabilities), base)
    if (args.output / "runs" / manifest.run_id / "result.json").exists():
        raise FileExistsError("refusing semantic retry/overwrite")
    sdk_model = _sdk_model({"control_plane": {"manager_model": {
        "model": harness.manager["model"], "base_url": harness.manager["base_url"],
        "api_key_env": harness.manager["api_key_env"],
    }}})
    sdk_model = ModelRequestBodyAdapter(sdk_model, dict(harness.manager["request_extra_body"]))
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
            None, operations, worker_clients=clients,
            profile_visibility=manifest.profile_visibility, loop_budget=harness.budget,
            logical_runtime=OpenAIAgentsNativeRuntime(
                name="sdk-native-manager", instructions=MANAGER_INSTRUCTIONS, model=sdk_model,
                registry=registry, available_operations=operations, enable_blind_verifier=True,
                predecision_profiles=True, record_input_provenance=True,
            ),
        )
        result = await runner.run(bundle, run_id=manifest.run_id)
    trace_path = args.output / "runs" / manifest.run_id / "trace.jsonl"
    trace = summarize_run_trace(trace_path)
    write_new(args.output / "summary.json", {
        "run_id": manifest.run_id, "task_label": manifest.task_label,
        "execution_completed": result.execution_completed, "final_answer": result.final_answer,
        "evaluation": (None if result.evaluation is None
                       else result.evaluation.model_dump(mode="json")),
        "failure": None if result.failure is None else result.failure.model_dump(mode="json"),
        "initial_transfer_bytes": sum(t.bytes_transferred for t in result.initial_transfers),
        "initial_transfer_latency_ms": sum(t.duration_ms for t in result.initial_transfers),
        "trace_summary": trace,
    })


def summarize_run_trace(path: Path) -> dict[str, Any]:
    """Generic scalar telemetry, preserving Unicode evidence and unknown cost fields."""
    events = JsonlTraceWriter(path).read_all()
    reasoning = [e["payload"] for e in events if e["event_type"] == "logical.reasoning.completed"]
    observations = [e["payload"] for e in events if e["event_type"] == "logical.observation"]
    snapshots = [e["payload"] for e in events if e["event_type"] == "workflow.graph.snapshot"]
    graph = snapshots[-1] if snapshots else {"nodes": [], "edges": []}
    outcomes = [e["payload"] for e in events if e["event_type"] == "logical.model.outcome"]
    logical_text = json.dumps([e for e in events if e["event_type"].startswith("logical.")])
    findings = [key for key in ("source_ref", "evaluator_id", "gold_answer", "supporting_evidence",
                                "deployment_id", "worker_id", "device_id", "bandwidth", "rtt",
                                "queue", "load") if f'"{key}"' in logical_text]
    if re.search(r'192\.168\.0\.|"(?:A4|A5|A28|strong-4090)"|private://', logical_text):
        findings.append("physical/private identity")
    cost = summarize_cost(events)
    return {
        "manager_reasoning_turns": sum(r.get("logical_agent_id") == "manager" for r in reasoning),
        "specialist_reasoning_turns": sum(
            r.get("logical_agent_id") != "manager" for r in reasoning
        ),
        "tool_calls": sum(n["action_type"] == "tool" for n in graph["nodes"]),
        "model_calls": sum(n["action_type"] == "model" for n in graph["nodes"]),
        "subagent_calls": sum(e["event_type"] == "logical.subagent.start" for e in events),
        "context_failure_count": sum(o.get("failure_code") == "context_limit_exceeded"
                                     for o in observations),
        "graph_nodes": len(graph["nodes"]), "graph_edges": len(graph["edges"]),
        "reached_model_inference": sum(o.get("reached_model_inference") is True for o in outcomes),
        "logical_privacy_pass": not findings, "logical_privacy_findings": findings,
        "cost_decomposition": cost, "trace_e2e_latency_ms": cost["e2e_latency_ms"],
        "trace_action_transfer_bytes": cost["action_transfer_bytes"],
        "trace_action_transfer_latency_ms": cost["action_transfer_latency_ms"],
        **summarize_concurrency(events), **summarize_profiles(events),
    }


async def execute_with_workers(args: argparse.Namespace) -> None:
    root = args.deployment_root
    config = _yaml(args.config)
    pids: dict[str, int] = {}
    try:
        for agent in HOSTS:
            worker_config = root / "worker-configs" / f"{config['run_id']}-{agent}.yaml"
            prepare(args.config, agent, worker_config)
            pids[agent] = start_worker(root, worker_config, agent,
                                       config["fresh_worker_stores"][agent])
        write_new(args.output / "worker-pids.json", pids)
        states: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=10) as client:
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
        shutdown_errors: list[str] = []
        for agent, pid in pids.items():
            try:
                stop_worker(root, agent, pid)
            except Exception as error:
                shutdown_errors.append(f"{agent}: {type(error).__name__}: {error}")
        write_new(args.output / "worker-shutdown.json", {"errors": shutdown_errors})
        if shutdown_errors:
            raise RuntimeError("Worker shutdown incomplete")


def append_journal(root: Path, event: dict[str, Any]) -> None:
    with (root / "queue.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event) + "\n")


def audit_artifact_persistence(output: Path, run_id: str) -> dict[str, Any]:
    """Metadata-only audit, after execution and before shutdown; no logical feedback."""
    states = json.loads((output / "private/worker-state-after.json").read_text())
    available: dict[str, list[dict[str, Any]]] = {}
    for state in states.values():
        for artifact in state["artifacts"]:
            available.setdefault(artifact["artifact_id"], []).append(artifact)
    manifest = json.loads((output / "freeze/manifest.json").read_text())
    expected = {a["artifact_id"]: {"artifact_id": a["artifact_id"],
                                  "size_bytes": a["size_bytes"], "sha256_hex": None}
                for a in manifest["task_view"]["artifacts"]}
    path = output / "runs" / run_id / "trace.jsonl"
    # Physical JSONL boundaries, not Unicode splitlines, which can split valid JSON strings.
    for line in path.open(encoding="utf-8"):
        event = json.loads(line)
        if event["event_type"] == "logical.observation" and event["payload"]["succeeded"]:
            for artifact in event["payload"].get("produced_information", []):
                expected[artifact["artifact_id"]] = artifact
    missing = sorted(set(expected) - set(available))
    mismatches = []
    for artifact_id in sorted(set(expected) & set(available)):
        artifact = expected[artifact_id]
        for actual in available[artifact_id]:
            if (actual["size_bytes"] != artifact["size_bytes"] or (
                artifact.get("sha256_hex") is not None
                and actual["sha256_hex"] != artifact["sha256_hex"]
            )):
                mismatches.append(artifact_id)
    return {"expected_count": len(expected), "present_ids": sorted(available),
            "missing_ids": missing, "metadata_mismatches": sorted(set(mismatches)),
            "pass": not missing and not mismatches}


def main(args: argparse.Namespace) -> None:
    root = args.deployment_root.resolve()
    ensure_remote(root)
    if args.prepare:
        prepare_protocol(args)
        return
    protocol = _yaml(args.protocol)
    validate_protocol(protocol)
    append_journal(root, {"event": "started", "pid": os.getpid()})
    for row in protocol["tasks"]:
        for condition in CONDITIONS:
            cell = f"{row['label']}-{condition}"
            if args.only_cell and cell != args.only_cell:
                continue
            output = root / "evidence" / cell / args.attempt
            if output.exists():
                raise FileExistsError(f"attempt already exists: {output}; inspect, never overwrite")
            output.mkdir(parents=True)
            config = cell_config(protocol, row, condition, args.attempt)
            cell_path = root / "cell-configs" / f"{cell}-{args.attempt}.yaml"
            cell_path.parent.mkdir(exist_ok=True)
            with cell_path.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            args.config, args.output = cell_path, output
            append_journal(root, {"event": "cell_started", "cell": cell,
                                  "attempt": args.attempt, "run_id": config["run_id"]})
            try:
                asyncio.run(run_shaped(args, execute_with_workers))
                validation = validate_cell(output, config["run_id"], config["profile_visibility"],
                                           canonical_labels=("A", "B", "C", "D"))
                persistence = audit_artifact_persistence(output, config["run_id"])
                write_new(output / "private/artifact-persistence.json", persistence)
                if not persistence["pass"]:
                    validation["problems"].append("artifact persistence incident; requires audit")
                write_new(output / "lightweight-validation.json", validation)
                append_journal(root, {"event": "cell_finished", "cell": cell,
                                      "attempt": args.attempt, "validation": validation})
                if validation["problems"]:
                    raise RuntimeError("operational audit required; queue stopped")
            except BaseException as error:
                append_journal(root, {"event": "audit_required", "cell": cell,
                                      "attempt": args.attempt,
                                      "exception_type": type(error).__name__,
                                      "message": str(error)})
                raise
            # Owned Workers finish shutdown before fixed ports are reused.
            time.sleep(3)
    append_journal(root, {"event": "completed", "only_cell": args.only_cell,
                          "attempt": args.attempt})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path,
                        default=REPO / "configs/experiments/predecision-crossbenchmark-v1.yaml")
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--endpoint-config", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--only-cell")
    parser.add_argument("--attempt", choices=("primary", "operational-replacement-1"),
                        default="primary")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
