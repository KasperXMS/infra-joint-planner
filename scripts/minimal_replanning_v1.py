"""Run the two-case minimal resource-blind workflow-replanning validation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

from blind_baseline_6task_v1 import (
    REPO,
    _configured_clients,
    _delete_artifacts,
    _environment,
    _generated_ids,
    _load_plan,
    _multihop_bundle,
    _preload,
    _workload,
    _write_json,
    _yaml,
)
from open_ended_mas_preliminary_v1 import (
    PrepositionedWorkflowRunner,
    _canonical_hash,
    _load_key,
)

from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import CompletionBackend
from infra_joint.worker.model_backend import ModelCompletion, ModelRequest
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.replanning import LLMWorkflowReplanner
from infra_joint.workflow.runner import PersistedWorkflowRunResult
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler

DEFAULT_CONFIG = REPO / "configs/experiments/blind-baseline-6task-competent-v2.yaml"
DEFAULT_KEY = REPO.parent / "api_key.txt"
DEFAULT_OUTPUT = REPO / "results/minimal-replanning-v1"
TASKS = ("multihop-multisource", "multihop-reasoning")


class CapturingBackend:
    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend
        self.requests: list[ModelRequest] = []
        self.completions: list[ModelCompletion] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        completion = await self._backend.invoke(request)
        self.completions.append(completion)
        return completion


def _load_source_plan(source: Path, label: str) -> WorkflowPlan:
    return _load_plan(source, label)


def _load_bundles(
    config: dict[str, Any],
    corpus_path: Path,
    query_path: Path,
) -> dict[str, AdaptationBundle]:
    corpus_rows = cast(
        list[dict[str, Any]], json.loads(corpus_path.read_text(encoding="utf-8"))
    )
    query_rows = cast(
        list[dict[str, Any]], json.loads(query_path.read_text(encoding="utf-8"))
    )
    if len(corpus_rows) != 609:
        raise RuntimeError(
            f"expected complete 609-document MultiHop corpus, got {len(corpus_rows)}"
        )
    revisions = cast(dict[str, str], config["dataset"]["revisions"])
    rows = {
        str(row["label"]): cast(dict[str, Any], row)
        for row in cast(list[dict[str, Any]], config["dataset"]["tasks"])
        if str(row["label"]) in TASKS
    }
    if set(rows) != set(TASKS):
        raise RuntimeError("experiment config is missing a required validation task")
    return {
        label: _multihop_bundle(
            rows[label], corpus_rows, query_rows, revisions["multihop_rag"]
        )
        for label in TASKS
    }


def _replan_call(backend: CapturingBackend) -> dict[str, Any]:
    if len(backend.requests) != 1 or len(backend.completions) != 1:
        raise RuntimeError("each validation task must make exactly one replanner call")
    return {
        "request": backend.requests[0].model_dump(mode="json"),
        "completion": backend.completions[0].model_dump(mode="json"),
    }


def _implementation_hashes() -> dict[str, str]:
    paths = (
        REPO / "src/infra_joint/core/task.py",
        REPO / "src/infra_joint/agents/manager.py",
        REPO / "src/infra_joint/workflow/orchestrator.py",
        REPO / "src/infra_joint/workflow/replanning.py",
        REPO / "src/infra_joint/workflow/runner.py",
        Path(__file__).resolve(),
    )
    return {
        str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _audit(
    label: str,
    initial_plan: WorkflowPlan,
    result: PersistedWorkflowRunResult,
) -> dict[str, Any]:
    replanning = result.replanning
    workflow = result.workflow
    if replanning is None or workflow is None:
        return {
            "task": label,
            "execution_valid": False,
            "failure": result.failure.model_dump(mode="json") if result.failure else None,
        }
    model_calls = [
        record
        for record in workflow.records
        if record.action.semantic.operator == "invoke_model"
    ]
    transfers = [
        transfer
        for record in workflow.records
        if record.execution is not None
        for transfer in record.execution.transfers
    ]
    return {
        "task": label,
        "execution_valid": bool(result.execution_completed and workflow.completed),
        "g0_sha256": _canonical_hash(initial_plan.model_dump(mode="json")),
        "versions": [item.model_dump(mode="json") for item in replanning.versions],
        "revisions": [item.model_dump(mode="json") for item in replanning.revisions],
        "node_final_states": workflow.state.node_status,
        "agent_final_states": {
            state.agent_id: state.status for state in workflow.agent_states
        },
        "quality": (
            result.evaluation.model_dump(mode="json") if result.evaluation else None
        ),
        "terminal_answer": result.final_answer,
        "e2e_latency_ms": result.runner_e2e_latency_ms,
        "workflow_latency_ms": workflow.telemetry.e2e_latency_ms,
        "transfer_bytes": sum(item.bytes_transferred for item in transfers),
        "transfer_time_ms": sum(item.duration_ms for item in transfers),
        "model_calls": len(model_calls),
        "model_service_latency_ms": workflow.telemetry.total_model_service_latency_ms,
        "operator_latency_ms": workflow.telemetry.total_operator_latency_ms,
        "failure": result.failure.model_dump(mode="json") if result.failure else None,
        "trace_path": result.trace_path,
    }


def _report(rows: list[dict[str, Any]], output: Path) -> None:
    lines = [
        "# Minimal workflow replanning v1 audit",
        "",
        "This validation replays the two previously frozen MultiHop plans. It uses one "
        "resource-blind semantic replanner call per task, the fixed operator/model pool, native "
        "networking, and the original private evaluator.",
        "",
        "| Task | Decision | G versions | Answer | Score | E2E ms | Transfer bytes | Model calls |",
        "|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        revisions = row.get("revisions", [])
        decision = revisions[0]["decision"] if revisions else "failed"
        quality = row.get("quality") or {}
        lines.append(
            f"| {row['task']} | {decision} | {len(row.get('versions', []))} | "
            f"{row.get('terminal_answer', '—')} | {quality.get('benchmark_score', '—')} | "
            f"{row.get('e2e_latency_ms', 0):.1f} | {row.get('transfer_bytes', 0)} | "
            f"{row.get('model_calls', 0)} |"
        )
    lines.extend(
        (
            "",
            "## Revision records",
            "",
        )
    )
    for row in rows:
        lines.append(f"### {row['task']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(row.get("revisions", []), ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    (output / "minimal-replanning-v1-audit.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


async def run(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise RuntimeError("output directory exists; refusing retry or overwrite")
    args.output.mkdir(parents=True)
    config = _yaml(args.config)
    bundles = _load_bundles(config, args.multihop_corpus, args.multihop_queries)
    source_manifest = json.loads(
        (args.source_evidence / "freeze/manifest.json").read_text(encoding="utf-8")
    )
    _load_key(args.api_key_file)
    planner_config = load_planner_config(REPO / str(config["planner"]["config"]))
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    backend, planner_client = build_model_backend(planner_config.model)
    registry = build_operator_catalog()
    rows: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "experiment": "minimal-replanning-v1",
        "source_evidence": str(args.source_evidence),
        "prior_invalid_attempt": (
            str(args.prior_attempt) if args.prior_attempt is not None else None
        ),
        "implementation_sha256": _implementation_hashes(),
        "tasks": [],
        "retries": False,
        "resource_visibility": "semantic_only",
    }
    try:
        async with AsyncExitStack() as stack:
            clients = await _configured_clients(stack, config)
            for index, label in enumerate(TASKS, start=1):
                bundle = bundles[label]
                initial_plan = _load_source_plan(args.source_evidence, label)
                expected_hash = str(
                    source_manifest["tasks"][label]["workflow_plan_sha256"]
                )
                actual_hash = _canonical_hash(initial_plan.model_dump(mode="json"))
                if actual_hash != expected_hash:
                    raise RuntimeError(f"source frozen-plan hash drift: {label}")
                current_environment = _environment(config, label, bundle)
                await validate_worker_surfaces(current_environment, registry, clients)
                await _delete_artifacts(
                    clients,
                    (
                        *_generated_ids(initial_plan),
                        *(item.spec.artifact_id for item in bundle.prepared_artifacts),
                    ),
                )
                await _preload(config, label, bundle, clients, remove_existing=False)
                run_id = f"{index:02d}-{label}-replanning-native"
                runner_config = RunnerConfig(
                    environment=current_environment,
                    worker_urls=cast(
                        dict[str, str],
                        _yaml(REPO / str(config["environment_config"]))["worker_urls"],
                    ),
                    planner=planner_config,
                    output_root=args.output / "runs",
                    http_timeout_seconds=1800,
                )
                capture = CapturingBackend(backend)
                result = await PrepositionedWorkflowRunner(
                    runner_config,
                    _workload(bundle, current_environment, operations, max_agents),
                    LocalityAwareMyopicScheduler(),
                    worker_clients=clients,
                    planner=ScriptedWorkflowPlanner((initial_plan,)),
                    replanner=LLMWorkflowReplanner(
                        capture,
                        registry,
                        current_environment,
                    ),
                ).run(bundle, run_id=run_id)
                _write_json(
                    args.output / "runs" / run_id / "replanner-call.json",
                    _replan_call(capture),
                )
                row = _audit(label, initial_plan, result)
                _write_json(args.output / "runs" / run_id / "audit.json", row)
                rows.append(row)
                manifest["tasks"].append(
                    {
                        "task": label,
                        "run_id": run_id,
                        "execution_valid": row["execution_valid"],
                        "quality": row.get("quality"),
                        "failure": row.get("failure"),
                    }
                )
                final_plan = result.plan or initial_plan
                await _delete_artifacts(
                    clients,
                    (
                        *_generated_ids(initial_plan),
                        *_generated_ids(final_plan),
                        *(item.spec.artifact_id for item in bundle.prepared_artifacts),
                    ),
                )
                if not row["execution_valid"]:
                    manifest["stopped_on_invalid_execution"] = label
                    break
    finally:
        if planner_client is not None:
            await planner_client.close()
    _write_json(args.output / "manifest.json", manifest)
    _report(rows, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--prior-attempt", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
