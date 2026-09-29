"""Run the clean resource-blind 18/24/32 action-budget diagnostic."""

# This experiment intentionally reuses the already-frozen benchmark adapter helpers.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import math
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

from blind_baseline_6task_v1 import (
    _environment,
    _public_bundle_digest,
    _sha256,
    _source_manifest,
    _yaml,
)
from open_ended_mas_preliminary_v1 import _load_key
from resource_blind_live_validation_v1 import (
    MANAGER_INSTRUCTIONS,
    _clients,
    _load_config,
    _operations,
    _placement,
    _sdk_model,
    _selected_bundles,
    _write_json,
)

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility, StaticCapabilityContract
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner, PersistedControlPlaneResult
from infra_joint.core.base import ContractModel
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import WorkerClient

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/blind-budget-diagnostic-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/blind-budget-diagnostic-v1"

SEMANTIC_OR_READINESS_CODES = frozenset(
    {
        "artifact_not_accessible",
        "artifact_not_materialized",
        "duplicate_logical_agent",
        "semantic_validation_failed",
        "validation_failed",
    }
)
PHYSICAL_PREFLIGHT_CODES = frozenset(
    {
        "capability_mismatch",
        "context_limit_exceeded",
        "deployment_unavailable",
        "infeasible_binding",
        "physical_feasibility_failed",
        "unsupported_modality",
    }
)


class FrozenBudgetDiagnostic(ContractModel):
    experiment_id: str
    code_revision: str
    implementation_manifest: dict[str, str]
    config_sha256: str
    environment_sha256: str
    source_manifest: dict[str, Any]
    task_order: tuple[str, ...]
    bundle_sha256: dict[str, str]
    task_views: dict[str, dict[str, Any]]
    initial_placement: dict[str, dict[str, str]]
    available_operations: tuple[str, ...]
    static_capabilities: StaticCapabilityContract
    action_call_budgets: tuple[int, ...]
    manager_turn_limits: dict[int, int]
    max_subagent_turns: int
    max_created_subagents: int
    max_active_subagents: int
    profile_visibility: str
    worker_urls: dict[str, str]
    fresh_worker_stores: dict[str, str]


class BudgetRunTelemetry(ContractModel):
    manager_reasoning_turns: int
    specialist_reasoning_turns: int
    successful_tool_executions: int
    successful_model_executions: int
    failed_semantic_or_readiness_calls: int
    failed_physical_preflight_calls: int
    other_failed_calls: int
    reached_model_inference_calls: int
    static_impossible_model_requests: int
    static_feasible_failed_model_requests: int
    created_specialists: int
    e2e_latency_ms: float
    transfer_bytes: int
    transfer_latency_ms: float
    model_service_latency_ms: float


class BudgetRunSummary(ContractModel):
    label: str
    run_id: str
    action_call_budget: int
    manager_turn_limit: int
    execution_completed: bool
    failure_code: str | None = None
    failure_message: str | None = None
    score: float | None = None
    format_valid: bool | None = None
    telemetry: BudgetRunTelemetry


class HarnessAmendment(ContractModel):
    amendment_id: str
    reason: str
    original_runner_sha256: str
    revised_runner_sha256: str
    completed_runs_preserved: tuple[str, ...]
    behavior_scope: str


def _persist_summaries(path: Path, summaries: list[BudgetRunSummary]) -> None:
    _write_json(path, [item.model_dump(mode="json") for item in summaries])


def _revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def _implementation_manifest(config_path: Path, environment_path: Path) -> dict[str, str]:
    paths = [
        *sorted((REPO / "src").rglob("*.py")),
        Path(__file__).resolve(),
        config_path.resolve(),
        environment_path.resolve(),
        *sorted(
            (REPO / "configs/experiments/workers/blind-budget-diagnostic-v1").glob(
                "*.yaml"
            )
        ),
    ]
    return {
        path.relative_to(REPO).as_posix(): _sha256(path)
        for path in paths
    }


def _budgets(validation: dict[str, Any]) -> tuple[int, ...]:
    control = cast(dict[str, Any], validation["control_plane"])
    raw_budgets = cast(list[object], control["action_call_budgets"])
    if not all(isinstance(item, (int, str)) for item in raw_budgets):
        raise TypeError("action_call_budgets must contain integers")
    result = tuple(int(cast(int | str, item)) for item in raw_budgets)
    if result != (18, 24, 32):
        raise ValueError("diagnostic action budgets must be exactly 18, 24, 32")
    return result


def _manager_turns(action_budget: int) -> int:
    return math.ceil(action_budget * 2 / 3)


def _config_int(values: dict[str, Any], key: str) -> int:
    value = values[key]
    if not isinstance(value, (int, str)):
        raise TypeError(f"{key} must be an integer")
    return int(value)


def _loop_budget(validation: dict[str, Any], action_budget: int) -> AgentLoopBudget:
    control = cast(dict[str, Any], validation["control_plane"])
    if control["manager_turn_rule"] != "ceil_two_thirds_action_budget":
        raise ValueError("unexpected Manager-turn scaling rule")
    return AgentLoopBudget(
        max_manager_turns=_manager_turns(action_budget),
        max_subagent_turns=_config_int(control, "max_subagent_turns"),
        max_tool_model_calls=action_budget,
        max_created_subagents=_config_int(control, "max_created_subagents"),
        max_active_subagents=_config_int(control, "max_active_subagents"),
    )


def _freeze(
    config_path: Path,
    validation: dict[str, Any],
    base: dict[str, Any],
    fresh: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    static_capabilities: StaticCapabilityContract,
    args: argparse.Namespace,
) -> FrozenBudgetDiagnostic:
    freeze_path = args.output / "freeze" / "manifest.json"
    if freeze_path.exists():
        return FrozenBudgetDiagnostic.model_validate_json(freeze_path.read_text("utf-8"))
    labels = tuple(bundles)
    budgets = _budgets(validation)
    manifest = FrozenBudgetDiagnostic(
        experiment_id=str(validation["experiment_id"]),
        code_revision=_revision(),
        implementation_manifest=_implementation_manifest(
            config_path,
            REPO / str(validation["fresh_environment_config"]),
        ),
        config_sha256=_sha256(config_path),
        environment_sha256=_sha256(REPO / str(validation["fresh_environment_config"])),
        source_manifest=_source_manifest(args, base),
        task_order=labels,
        bundle_sha256={
            label: _public_bundle_digest(bundle) for label, bundle in bundles.items()
        },
        task_views={
            label: AgentTaskView.from_contract(bundle.execution.task).model_dump(mode="json")
            for label, bundle in bundles.items()
        },
        initial_placement={
            label: _placement(base, label, bundle)
            for label, bundle in bundles.items()
        },
        available_operations=_operations(base),
        static_capabilities=static_capabilities,
        action_call_budgets=budgets,
        manager_turn_limits={item: _manager_turns(item) for item in budgets},
        max_subagent_turns=_config_int(
            cast(dict[str, Any], validation["control_plane"]), "max_subagent_turns"
        ),
        max_created_subagents=_config_int(
            cast(dict[str, Any], validation["control_plane"]),
            "max_created_subagents",
        ),
        max_active_subagents=_config_int(
            cast(dict[str, Any], validation["control_plane"]), "max_active_subagents"
        ),
        profile_visibility=ProfileVisibility.BLIND.value,
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
    )
    _write_json(freeze_path, manifest)
    return manifest


async def _assert_fresh(clients: dict[str, WorkerClient]) -> None:
    states = await asyncio.gather(*(client.get_state() for client in clients.values()))
    polluted = {
        state.agent_id: tuple(item.artifact_id for item in state.artifacts)
        for state in states
        if state.artifacts
    }
    if polluted:
        raise RuntimeError(f"fresh Worker artifact stores are not empty: {polluted}")


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _trace_telemetry(
    result: PersistedControlPlaneResult,
    trace_path: Path,
) -> BudgetRunTelemetry:
    events = _events(trace_path)
    reasoning = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "logical.reasoning.completed"
    ]
    manager_turns = sum(item.get("logical_agent_id") == "manager" for item in reasoning)
    specialist_turns = len(reasoning) - manager_turns
    snapshots = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "workflow.graph.snapshot"
    ]
    nodes = cast(list[dict[str, Any]], snapshots[-1]["nodes"]) if snapshots else []
    successful_tools = sum(
        item["action_type"] == "tool" and item["status"] == "succeeded"
        for item in nodes
    )
    successful_models = sum(
        item["action_type"] == "model" and item["status"] == "succeeded"
        for item in nodes
    )
    failed_observations = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "logical.observation"
        and not cast(dict[str, Any], item["payload"])["succeeded"]
    ]
    failure_codes = [str(item.get("failure_code")) for item in failed_observations]
    semantic_failures = sum(item in SEMANTIC_OR_READINESS_CODES for item in failure_codes)
    physical_failures = sum(item in PHYSICAL_PREFLIGHT_CODES for item in failure_codes)
    other_failures = len(failure_codes) - semantic_failures - physical_failures
    model_requirements = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "logical.model.requirements"
    ]
    model_outcomes = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "logical.model.outcome"
    ]
    reached_inference = sum(bool(item["reached_model_inference"]) for item in model_outcomes)
    static_impossible = sum(not bool(item["static_feasible"]) for item in model_requirements)
    static_feasible_failed = sum(
        bool(item["static_feasible"]) and not bool(item["succeeded"])
        for item in model_outcomes
    )
    physical_events = [
        cast(dict[str, Any], item["payload"])
        for item in events
        if item["event_type"] == "physical.execution"
    ]
    action_transfers: list[dict[str, Any]] = []
    model_service_latency = 0.0
    for payload in physical_events:
        execution_value = payload.get("execution")
        if not isinstance(execution_value, dict):
            continue
        execution = cast(dict[str, Any], execution_value)
        action_transfers.extend(
            cast(list[dict[str, Any]], execution.get("transfers", []))
        )
        model_value = execution.get("model_telemetry")
        if isinstance(model_value, dict):
            model = cast(dict[str, Any], model_value)
            model_service_latency += float(model.get("service_latency_ms", 0.0))
    initial = [item.model_dump(mode="json") for item in result.initial_transfers]
    transfers = [*initial, *action_transfers]
    run_failed = next(
        (
            cast(dict[str, Any], item["payload"])
            for item in reversed(events)
            if item["event_type"] == "run.failed"
        ),
        None,
    )
    e2e = (
        result.telemetry.e2e_latency_ms
        if result.telemetry is not None
        else float(cast(dict[str, Any], run_failed)["e2e_latency_ms"])
    )
    return BudgetRunTelemetry(
        manager_reasoning_turns=manager_turns,
        specialist_reasoning_turns=specialist_turns,
        successful_tool_executions=successful_tools,
        successful_model_executions=successful_models,
        failed_semantic_or_readiness_calls=semantic_failures,
        failed_physical_preflight_calls=physical_failures,
        other_failed_calls=other_failures,
        reached_model_inference_calls=reached_inference,
        static_impossible_model_requests=static_impossible,
        static_feasible_failed_model_requests=static_feasible_failed,
        created_specialists=sum(
            item["event_type"] == "logical.subagent.start" for item in events
        ),
        e2e_latency_ms=e2e,
        transfer_bytes=sum(int(item["bytes_transferred"]) for item in transfers),
        transfer_latency_ms=sum(float(item["duration_ms"]) for item in transfers),
        model_service_latency_ms=model_service_latency,
    )


def _completed_summary(
    output: Path,
    label: str,
    run_id: str,
    action_budget: int,
) -> BudgetRunSummary | None:
    run_dir = output / "runs" / run_id
    result_path = run_dir / "result.json"
    trace_path = run_dir / "trace.jsonl"
    present = (result_path.exists(), trace_path.exists())
    if not any(present):
        return None
    if not all(present):
        raise RuntimeError(
            f"incomplete prior cell must not be retried or overwritten: {run_id}"
        )
    result = PersistedControlPlaneResult.model_validate_json(
        result_path.read_text(encoding="utf-8")
    )
    return BudgetRunSummary(
        label=label,
        run_id=run_id,
        action_call_budget=action_budget,
        manager_turn_limit=_manager_turns(action_budget),
        execution_completed=result.execution_completed,
        failure_code=None if result.failure is None else result.failure.code,
        failure_message=None if result.failure is None else result.failure.message,
        score=None if result.evaluation is None else result.evaluation.benchmark_score,
        format_valid=None if result.evaluation is None else result.evaluation.format_valid,
        telemetry=_trace_telemetry(result, trace_path),
    )


def _record_harness_amendment(
    output: Path,
    manifest: FrozenBudgetDiagnostic,
) -> None:
    relative = Path(__file__).resolve().relative_to(REPO).as_posix()
    original = manifest.implementation_manifest[relative]
    revised = _sha256(Path(__file__).resolve())
    if original == revised:
        return
    completed = tuple(
        sorted(
            path.parent.name
            for path in (output / "runs").glob("*/result.json")
        )
    )
    if not completed:
        raise RuntimeError("frozen implementation changed before any completed run")
    amendment = HarnessAmendment(
        amendment_id="harness-amendment-001",
        reason=(
            "Serialize BudgetRunSummary models before writing progress/summary JSON and "
            "resume without retrying or overwriting completed cells."
        ),
        original_runner_sha256=original,
        revised_runner_sha256=revised,
        completed_runs_preserved=completed,
        behavior_scope=(
            "Evidence aggregation and fail-closed resume only; logical prompts, tool space, "
            "budgets, benchmark adapters, physical scheduling, and runtime execution unchanged."
        ),
    )
    path = output / "freeze" / "harness-amendment-001.json"
    if path.exists():
        existing = HarnessAmendment.model_validate_json(path.read_text(encoding="utf-8"))
        if existing != amendment:
            raise RuntimeError("existing harness amendment does not match current runner")
        return
    _write_json(path, amendment)


async def run_all(
    validation: dict[str, Any],
    base: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    manifest: FrozenBudgetDiagnostic,
    args: argparse.Namespace,
) -> None:
    registry = build_operator_catalog()
    sdk_model = _sdk_model(validation)
    urls = manifest.worker_urls
    summaries: list[BudgetRunSummary] = []
    completed: set[str] = set()
    for action_budget in manifest.action_call_budgets:
        for index, label in enumerate(bundles, start=1):
            run_id = f"b{action_budget:02d}-{index:02d}-{label}-blind-native"
            summary = _completed_summary(
                args.output,
                label,
                run_id,
                action_budget,
            )
            if summary is not None:
                summaries.append(summary)
                completed.add(run_id)
    _persist_summaries(args.output / "progress.json", summaries)
    async with AsyncExitStack() as stack:
        clients = await _clients(stack, urls)
        if not completed:
            await _assert_fresh(clients)
        for action_budget in manifest.action_call_budgets:
            budget = _loop_budget(validation, action_budget)
            for index, (label, bundle) in enumerate(bundles.items(), start=1):
                run_id = f"b{action_budget:02d}-{index:02d}-{label}-blind-native"
                if run_id in completed:
                    continue
                environment = _environment(base, label, bundle)
                config = RunnerConfig(
                    environment=environment,
                    worker_urls=urls,
                    planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                    output_root=args.output / "runs",
                    max_planning_steps=budget.max_manager_turns,
                    http_timeout_seconds=900,
                )
                logical_runtime = OpenAIAgentsNativeRuntime(
                    name="resource-blind-manager",
                    instructions=MANAGER_INSTRUCTIONS,
                    model=sdk_model,
                    registry=registry,
                    available_operations=manifest.available_operations,
                )
                result = await ControlPlaneBenchmarkRunner(
                    config,
                    None,
                    manifest.available_operations,
                    worker_clients=clients,
                    profile_visibility=ProfileVisibility.BLIND,
                    loop_budget=budget,
                    logical_runtime=logical_runtime,
                ).run(bundle, run_id=run_id)
                trace_path = args.output / "runs" / run_id / "trace.jsonl"
                summary = BudgetRunSummary(
                    label=label,
                    run_id=run_id,
                    action_call_budget=action_budget,
                    manager_turn_limit=budget.max_manager_turns,
                    execution_completed=result.execution_completed,
                    failure_code=None if result.failure is None else result.failure.code,
                    failure_message=None if result.failure is None else result.failure.message,
                    score=(
                        None
                        if result.evaluation is None
                        else result.evaluation.benchmark_score
                    ),
                    format_valid=(
                        None if result.evaluation is None else result.evaluation.format_valid
                    ),
                    telemetry=_trace_telemetry(result, trace_path),
                )
                summaries.append(summary)
                _persist_summaries(args.output / "progress.json", summaries)
                print(summary.model_dump_json(), flush=True)
                if not result.execution_completed and (
                    result.failure is None
                    or result.failure.code != "logical_loop_failed"
                ):
                    raise RuntimeError(
                        f"system/harness failure stops diagnostic at {run_id}: "
                        f"{result.failure}"
                    )
    _persist_summaries(args.output / "summary.json", summaries)


async def main_async(args: argparse.Namespace) -> None:
    if args.api_key_file is not None:
        _load_key(args.api_key_file)
    validation = _load_config(args.config)
    base = _yaml(REPO / str(validation["source_experiment_config"]))
    fresh_path = REPO / str(validation["fresh_environment_config"])
    fresh = _yaml(fresh_path)
    bundles = _selected_bundles(validation, base, args)
    registry = build_operator_catalog()
    static_capabilities = build_static_capability_contract(
        _environment(base, next(iter(bundles)), next(iter(bundles.values()))),
        registry,
        _operations(base),
    )
    manifest = _freeze(
        args.config,
        validation,
        base,
        fresh,
        bundles,
        static_capabilities,
        args,
    )
    if args.freeze_only:
        return
    _record_harness_amendment(args.output, manifest)
    await run_all(validation, base, bundles, manifest, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--video-tasks", type=Path, required=True)
    parser.add_argument("--video-answers", type=Path, required=True)
    parser.add_argument("--video-sources", type=Path, required=True)
    parser.add_argument("--longbench-samples", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--freeze-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
