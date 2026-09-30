"""Run one resource-blind SDK-native MultiHop baseline cell."""

# This experiment intentionally reuses frozen benchmark and control-plane helpers.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

from blind_baseline_6task_v1 import (
    _environment,
    _multihop_bundle,
    _public_bundle_digest,
    _sha256,
    _yaml,
)
from open_ended_mas_preliminary_v1 import _load_key
from resource_blind_live_validation_v1 import (
    MANAGER_INSTRUCTIONS,
    _budget,
    _clients,
    _load_config,
    _operations,
    _placement,
    _sdk_model,
    _write_json,
)

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility, StaticCapabilityContract
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.base import ContractModel
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import WorkerClient

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/sdk-native-blind-multihop-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/sdk-native-blind-multihop-v1"
RUN_ID = "01-multihop-multisource-blind-native"


class FrozenBlindRun(ContractModel):
    experiment_id: str
    code_revision: str
    config_sha256: str
    environment_sha256: str
    corpus_sha256: str
    queries_sha256: str
    corpus_size_bytes: int
    queries_size_bytes: int
    task_label: str
    task_bundle_sha256: str
    task_view: dict[str, Any]
    initial_placement: dict[str, str]
    available_operations: tuple[str, ...]
    static_capabilities: StaticCapabilityContract
    budget: dict[str, int]
    profile_visibility: str
    manager_instructions_sha256: str
    worker_urls: dict[str, str]
    fresh_worker_stores: dict[str, str]
    network: str
    scheduler: str
    repetitions: int
    retry: bool
    replacement: bool


def _revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def _load_bundle(
    config: dict[str, Any],
    base: dict[str, Any],
    corpus_path: Path,
    queries_path: Path,
) -> AdaptationBundle:
    label = str(config["task"])
    if label != "multihop-multisource":
        raise RuntimeError("this runner is frozen to multihop-multisource")
    rows = cast(list[dict[str, Any]], cast(dict[str, Any], base["dataset"])["tasks"])
    matches = [row for row in rows if str(row["label"]) == label]
    if len(matches) != 1:
        raise RuntimeError("frozen MultiHop task row is missing or ambiguous")
    corpus = cast(list[dict[str, Any]], json.loads(corpus_path.read_text("utf-8")))
    queries = cast(list[dict[str, Any]], json.loads(queries_path.read_text("utf-8")))
    if len(corpus) != 609:
        raise RuntimeError(f"expected complete 609-document corpus, got {len(corpus)}")
    revisions = cast(dict[str, str], cast(dict[str, Any], base["dataset"])["revisions"])
    return _multihop_bundle(matches[0], corpus, queries, revisions["multihop_rag"])


def _freeze(
    config_path: Path,
    config: dict[str, Any],
    base: dict[str, Any],
    fresh_path: Path,
    fresh: dict[str, Any],
    bundle: AdaptationBundle,
    corpus_path: Path,
    queries_path: Path,
    static_capabilities: StaticCapabilityContract,
    output: Path,
) -> FrozenBlindRun:
    freeze_path = output / "freeze" / "manifest.json"
    if freeze_path.exists():
        return FrozenBlindRun.model_validate_json(freeze_path.read_text("utf-8"))
    execution = cast(dict[str, Any], config["execution"])
    budget = _budget(config)
    manifest = FrozenBlindRun(
        experiment_id=str(config["experiment_id"]),
        code_revision=_revision(),
        config_sha256=_sha256(config_path),
        environment_sha256=_sha256(fresh_path),
        corpus_sha256=_sha256(corpus_path),
        queries_sha256=_sha256(queries_path),
        corpus_size_bytes=corpus_path.stat().st_size,
        queries_size_bytes=queries_path.stat().st_size,
        task_label=str(config["task"]),
        task_bundle_sha256=_public_bundle_digest(bundle),
        task_view=AgentTaskView.from_contract(bundle.execution.task).model_dump(mode="json"),
        initial_placement=_placement(base, str(config["task"]), bundle),
        available_operations=_operations(base),
        static_capabilities=static_capabilities,
        budget={
            key: int(value)
            for key, value in budget.model_dump(mode="json").items()
        },
        profile_visibility=ProfileVisibility.BLIND.value,
        manager_instructions_sha256=_sha256_text(MANAGER_INSTRUCTIONS),
        worker_urls={
            str(key): str(value)
            for key, value in cast(dict[object, object], fresh["worker_urls"]).items()
        },
        fresh_worker_stores={
            str(key): str(value)
            for key, value in cast(
                dict[object, object], fresh["fresh_worker_stores"]
            ).items()
        },
        network=str(execution["network"]),
        scheduler=str(execution["scheduler"]),
        repetitions=int(execution["repetitions"]),
        retry=bool(execution["retry"]),
        replacement=bool(execution["replacement"]),
    )
    if manifest.repetitions != 1 or manifest.retry or manifest.replacement:
        raise RuntimeError("single-run no-retry/no-replacement contract changed")
    _write_json(freeze_path, manifest)
    _write_json(output / "private" / "task-contract.json", bundle.execution.task)
    _write_json(output / "private" / "private-evaluation.json", bundle.private_evaluation)
    return manifest


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _assert_fresh(clients: dict[str, WorkerClient]) -> None:
    states = await asyncio.gather(*(client.get_state() for client in clients.values()))
    polluted = {
        state.agent_id: [item.artifact_id for item in state.artifacts]
        for state in states
        if state.artifacts
    }
    if polluted:
        raise RuntimeError(f"isolated Worker stores are not empty: {polluted}")


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _trace_summary(path: Path) -> dict[str, Any]:
    events = _events(path)
    reasoning = [
        cast(dict[str, Any], event["payload"])
        for event in events
        if event["event_type"] == "logical.reasoning.completed"
    ]
    snapshots = [
        cast(dict[str, Any], event["payload"])
        for event in events
        if event["event_type"] == "workflow.graph.snapshot"
    ]
    nodes = cast(list[dict[str, Any]], snapshots[-1].get("nodes", [])) if snapshots else []
    observations = [
        cast(dict[str, Any], event["payload"])
        for event in events
        if event["event_type"] == "logical.observation"
    ]
    physical = [
        cast(dict[str, Any], event["payload"])
        for event in events
        if event["event_type"] == "physical.execution"
    ]
    transfer_bytes = 0
    for payload in physical:
        raw_execution = payload.get("execution")
        if isinstance(raw_execution, dict):
            execution = cast(dict[str, Any], raw_execution)
            for transfer in cast(list[dict[str, Any]], execution.get("transfers", [])):
                transfer_bytes += int(transfer["bytes_transferred"])
    failures = [item for item in observations if not bool(item["succeeded"])]
    return {
        "manager_reasoning_turns": sum(
            item.get("logical_agent_id") == "manager" for item in reasoning
        ),
        "specialist_reasoning_turns": sum(
            item.get("logical_agent_id") != "manager" for item in reasoning
        ),
        "tool_calls": sum(item.get("action_type") == "tool" for item in nodes),
        "model_calls": sum(item.get("action_type") == "model" for item in nodes),
        "subagent_calls": sum(
            event["event_type"] == "logical.subagent.start" for event in events
        ),
        "context_failures": [
            item
            for item in failures
            if item.get("failure_code") == "context_limit_exceeded"
        ],
        "all_failed_observations": failures,
        "graph_snapshots": snapshots,
        "final_graph": snapshots[-1] if snapshots else None,
        "action_transfer_bytes": transfer_bytes,
    }


async def run_once(args: argparse.Namespace) -> None:
    if args.api_key_file is not None:
        _load_key(args.api_key_file)
    config = _load_config(args.config)
    base = _yaml(REPO / str(config["source_experiment_config"]))
    fresh_path = REPO / str(config["fresh_environment_config"])
    fresh = _yaml(fresh_path)
    bundle = _load_bundle(config, base, args.multihop_corpus, args.multihop_queries)
    environment = _environment(base, str(config["task"]), bundle)
    registry = build_operator_catalog()
    operations = _operations(base)
    static_capabilities = build_static_capability_contract(
        environment, registry, operations
    )
    manifest = _freeze(
        args.config,
        config,
        base,
        fresh_path,
        fresh,
        bundle,
        args.multihop_corpus,
        args.multihop_queries,
        static_capabilities,
        args.output,
    )
    result_path = args.output / "runs" / RUN_ID / "result.json"
    if result_path.exists():
        raise RuntimeError("single-run result already exists; retry is forbidden")
    budget = _budget(config)
    sdk_model = _sdk_model(config)
    async with AsyncExitStack() as stack:
        clients = await _clients(stack, manifest.worker_urls)
        await _assert_fresh(clients)
        runner_config = RunnerConfig(
            environment=environment,
            worker_urls=manifest.worker_urls,
            planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
            output_root=args.output / "runs",
            max_planning_steps=budget.max_manager_turns,
            http_timeout_seconds=900,
        )
        runtime = OpenAIAgentsNativeRuntime(
            name="resource-blind-manager",
            instructions=MANAGER_INSTRUCTIONS,
            model=sdk_model,
            registry=registry,
            available_operations=operations,
        )
        result = await ControlPlaneBenchmarkRunner(
            runner_config,
            None,
            operations,
            worker_clients=clients,
            profile_visibility=ProfileVisibility.BLIND,
            loop_budget=budget,
            logical_runtime=runtime,
        ).run(bundle, run_id=RUN_ID)
    trace_path = args.output / "runs" / RUN_ID / "trace.jsonl"
    trace = _trace_summary(trace_path)
    summary = {
        "run_id": RUN_ID,
        "execution_completed": result.execution_completed,
        "final_answer": result.final_answer,
        "evaluator_score": (
            None if result.evaluation is None else result.evaluation.benchmark_score
        ),
        "format_valid": (
            None if result.evaluation is None else result.evaluation.format_valid
        ),
        "failure": (
            None if result.failure is None else result.failure.model_dump(mode="json")
        ),
        "loop_usage": (
            None if result.loop is None else result.loop.usage.model_dump(mode="json")
        ),
        "e2e_latency_ms": (
            None if result.telemetry is None else result.telemetry.e2e_latency_ms
        ),
        "initial_transfer_bytes": sum(
            item.bytes_transferred for item in result.initial_transfers
        ),
        "action_transfer_bytes": trace["action_transfer_bytes"],
        "total_transferred_bytes": sum(
            item.bytes_transferred for item in result.initial_transfers
        )
        + int(trace["action_transfer_bytes"]),
        "trace_summary": trace,
    }
    _write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_once(parse_args()))
