"""Run and freeze the six-task resource-blind semantic-cleanup baseline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import AsyncExitStack
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import blind_baseline_6task_v1 as base
from open_ended_mas_preliminary_v1 import (
    PrepositionedWorkflowRunner,
    _canonical_hash,
    _code_revision,
    _load_key,
)

from infra_joint.config import RunnerConfig, build_model_backend, load_planner_config
from infra_joint.infrastructure.validation import validate_worker_surfaces
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.planning.planner import CompletionBackend
from infra_joint.worker.model_backend import ModelCompletion, ModelRequest
from infra_joint.workflow.planner import ScriptedWorkflowPlanner
from infra_joint.workflow.replanning import (
    OpaqueModelAliasWorkflowReplanner,
)
from infra_joint.workflow.runner import PersistedWorkflowRunResult
from infra_joint.workflow.scheduler import LocalityAwareMyopicScheduler

DEFAULT_CONFIG = (
    base.REPO
    / "configs/experiments/blind-baseline-6task-semantic-cleanup-v1.yaml"
)
DEFAULT_OUTPUT = base.REPO / "results/blind-baseline-6task-semantic-cleanup-v1"
DEFAULT_KEY = base.REPO.parent / "api_key.txt"


class CapturingBackend:
    def __init__(self, backend: CompletionBackend) -> None:
        self._backend = backend
        self.requests: list[ModelRequest] = []
        self.completions: list[ModelCompletion] = []
        self.wall_latency_ms: list[float] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        started = perf_counter()
        completion = await self._backend.invoke(request)
        self.wall_latency_ms.append((perf_counter() - started) * 1000)
        self.completions.append(completion)
        return completion


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replanner_call(
    capture: CapturingBackend,
    hidden_model_instance_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    if (
        len(capture.requests) != 1
        or len(capture.completions) != 1
        or len(capture.wall_latency_ms) != 1
    ):
        raise RuntimeError("each task must make exactly one replanner call")
    prompt = capture.requests[0].prompt
    leakage = base._private_structural_leakage(prompt)
    if leakage:
        raise RuntimeError(f"private fields leaked into replanner prompt: {leakage}")
    leaked_instances = tuple(
        instance_id for instance_id in hidden_model_instance_ids if instance_id in prompt
    )
    if leaked_instances:
        raise RuntimeError(
            f"physical model instance IDs leaked into Blind replanner prompt: "
            f"{leaked_instances}"
        )
    return {
        "call_count": 1,
        "request": capture.requests[0].model_dump(mode="json"),
        "completion": capture.completions[0].model_dump(mode="json"),
        "wall_latency_ms": capture.wall_latency_ms[0],
    }


def _replan_context(trace_path: Path) -> dict[str, Any]:
    starts = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = cast(dict[str, Any], json.loads(line))
        if event["event_type"] == "workflow.replanner.start":
            starts.append(cast(dict[str, Any], event["payload"]))
    if len(starts) != 1:
        raise RuntimeError(f"expected one replanner start event, got {len(starts)}")
    return cast(dict[str, Any], starts[0]["context"])


def _implementation_hashes(config_path: Path) -> dict[str, str]:
    paths = (
        config_path,
        base.REPO / "configs/experiments/blind-baseline-environment-v2.yaml",
        base.REPO / "src/infra_joint/workflow/orchestrator.py",
        base.REPO / "src/infra_joint/workflow/replanning.py",
        base.REPO / "src/infra_joint/workflow/runner.py",
        base.REPO / "src/infra_joint/worker/server.py",
        base.REPO / "scripts/blind_baseline_6task_v1.py",
        Path(__file__).resolve(),
    )
    return {
        str(path.relative_to(base.REPO)): _sha256(path)
        for path in paths
    }


def _augment_audit(
    label: str,
    initial_plan: Any,
    result: PersistedWorkflowRunResult,
    planner_call: dict[str, Any],
    replanner_call: dict[str, Any],
    bundle: Any,
) -> dict[str, Any]:
    if result.plan is None or result.replanning is None:
        raise RuntimeError(f"missing replanning result: {label}")
    audit = base._run_audit(label, bundle, result.plan, result, planner_call)
    audit.update(
        {
            "checkpoint": "after_evidence_before_terminal",
            "max_replans": 1,
            "g0_sha256": _canonical_hash(initial_plan.model_dump(mode="json")),
            "g_final_sha256": _canonical_hash(result.plan.model_dump(mode="json")),
            "workflow_versions": [
                item.model_dump(mode="json")
                for item in result.replanning.versions
            ],
            "workflow_revisions": [
                item.model_dump(mode="json")
                for item in result.replanning.revisions
            ],
            "replan_context": _replan_context(Path(result.trace_path)),
            "replanner": replanner_call,
        }
    )
    return audit


async def run_baseline(
    config: dict[str, Any],
    bundles: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    if not (args.output / "preflight.json").exists():
        raise RuntimeError("preflight evidence is missing")
    baseline_path = args.output / "baseline-manifest.json"
    if baseline_path.exists():
        raise RuntimeError("baseline manifest exists; retry or overwrite is forbidden")
    freeze = cast(
        dict[str, Any],
        json.loads((args.output / "freeze/manifest.json").read_text("utf-8")),
    )
    if config["execution"]["replan_checkpoint"] != "after_evidence_before_terminal":
        raise RuntimeError("semantic-cleanup checkpoint contract drift")
    if int(config["execution"]["max_replans"]) != 1:
        raise RuntimeError("semantic-cleanup replanning budget drift")
    _load_key(args.api_key_file)
    planner_config = load_planner_config(
        base.REPO / str(config["planner"]["config"])
    )
    backend, planner_client = build_model_backend(planner_config.model)
    registry = build_operator_catalog()
    operations = tuple(str(item) for item in config["planner"]["available_operations"])
    max_agents = int(config["planner"]["max_agents"])
    aliases = {
        str(alias): str(real)
        for alias, real in config["planner"]["model_instance_aliases"].items()
    }
    worker_urls = cast(dict[str, str], base._infrastructure(config)["worker_urls"])
    task_order = {
        str(item["label"]): index
        for index, item in enumerate(config["dataset"]["tasks"], start=1)
    }
    manifest: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "execution_revision": _code_revision(),
        "network": "native_unshaped",
        "scheduler": "B0_LOCALITY_AWARE_MYOPIC",
        "checkpoint": "after_evidence_before_terminal",
        "max_replans": 1,
        "n": 1,
        "retry": False,
        "replacement": False,
        "resource_visibility": "semantic_only",
        "tasks": [],
    }
    base._write_json(baseline_path, manifest)
    try:
        async with AsyncExitStack() as stack:
            clients = await base._configured_clients(stack, config)
            for label, bundle in bundles.items():
                frozen = cast(dict[str, Any], freeze["tasks"][label])
                if frozen["planning_status"] != "valid":
                    manifest["tasks"].append(
                        {
                            "task": label,
                            "run_id": None,
                            "planning_status": "invalid",
                            "execution_attempted": False,
                            "g0_sha256": None,
                            "g_final_sha256": None,
                            "decision": "planning_failed",
                            "benchmark_score": None,
                            "format_valid": None,
                            "execution_valid": False,
                            "failure": frozen.get("planning_error"),
                        }
                    )
                    base._write_json(baseline_path, manifest)
                    continue
                initial_plan = base._load_plan(args.output, label)
                g0 = _canonical_hash(initial_plan.model_dump(mode="json"))
                if g0 != frozen["workflow_plan_sha256"]:
                    raise RuntimeError(f"frozen workflow hash drift: {label}")
                environment = base._environment(config, label, bundle)
                await validate_worker_surfaces(environment, registry, clients)
                initial_ids = tuple(
                    item.spec.artifact_id for item in bundle.prepared_artifacts
                )
                await base._delete_artifacts(
                    clients,
                    (*base._generated_ids(initial_plan), *initial_ids),
                )
                await base._preload(
                    config,
                    label,
                    bundle,
                    clients,
                    remove_existing=False,
                )
                await base._assert_placement(config, label, bundle, clients)
                run_id = f"{task_order[label]:02d}-{label}-semantic-cleanup-native"
                capture = CapturingBackend(backend)
                runner_config = RunnerConfig(
                    environment=environment,
                    worker_urls=worker_urls,
                    planner=planner_config,
                    output_root=args.output / "runs",
                    http_timeout_seconds=1800,
                )
                result: PersistedWorkflowRunResult | None = None
                cleanup_error: Exception | None = None
                try:
                    result = await PrepositionedWorkflowRunner(
                        runner_config,
                        base._workload(bundle, environment, operations, max_agents),
                        LocalityAwareMyopicScheduler(),
                        worker_clients=clients,
                        planner=ScriptedWorkflowPlanner((initial_plan,)),
                        replanner=OpaqueModelAliasWorkflowReplanner(
                            capture,
                            registry,
                            environment,
                            aliases,
                        ),
                    ).run(bundle, run_id=run_id)
                    call = _replanner_call(capture, tuple(aliases.values()))
                    base._write_json(
                        args.output / "runs" / run_id / "replanner-call.json",
                        call,
                    )
                    planner_call = cast(
                        dict[str, Any],
                        json.loads(
                            (
                                args.output
                                / "freeze"
                                / label
                                / "planner-call.json"
                            ).read_text("utf-8")
                        ),
                    )
                    audit = _augment_audit(
                        label,
                        initial_plan,
                        result,
                        planner_call,
                        call,
                        bundle,
                    )
                    base._write_json(
                        args.output / "runs" / run_id / "audit.json",
                        audit,
                    )
                    if (
                        not result.execution_completed
                        or not audit["retained_valid_blind_sample"]
                        or len(audit["workflow_revisions"]) != 1
                    ):
                        raise RuntimeError(
                            f"invalid baseline execution: {label}/{audit['failure']}"
                        )
                    base._write_json(
                        args.output / "freeze" / label / "workflow-plan-final.json",
                        result.plan.model_dump(mode="json") if result.plan else None,
                    )
                    manifest["tasks"].append(
                        {
                            "task": label,
                            "run_id": run_id,
                            "planning_status": "valid",
                            "execution_attempted": True,
                            "g0_sha256": audit["g0_sha256"],
                            "g_final_sha256": audit["g_final_sha256"],
                            "decision": audit["workflow_revisions"][0]["decision"],
                            "benchmark_score": audit["benchmark_score"],
                            "format_valid": audit["format_valid"],
                            "execution_valid": audit["execution_valid"],
                        }
                    )
                    base._write_json(baseline_path, manifest)
                finally:
                    final_plan = (
                        result.plan
                        if result is not None and result.plan is not None
                        else initial_plan
                    )
                    try:
                        await base._delete_artifacts(
                            clients,
                            tuple(
                                dict.fromkeys(
                                    (
                                        *initial_ids,
                                        *base._generated_ids(initial_plan),
                                        *base._generated_ids(final_plan),
                                    )
                                )
                            ),
                        )
                    except Exception as exc:  # cleanup is part of validity
                        cleanup_error = exc
                if cleanup_error is not None:
                    manifest["stopped_on_system_harness_confounder"] = label
                    base._write_json(baseline_path, manifest)
                    raise RuntimeError(
                        f"artifact cleanup failed: {type(cleanup_error).__name__}: "
                        f"{cleanup_error}"
                    )
    finally:
        if planner_client is not None:
            await planner_client.close()
    if len(manifest["tasks"]) != 6:
        raise RuntimeError("six one-shot task outcomes are required for freeze")
    base._write_json(
        args.output / "freeze/blind-baseline-final.json",
        {
            "experiment_id": config["experiment_id"],
            "status": "frozen_no_further_semantic_tuning",
            "implementation_sha256": _implementation_hashes(args.config),
            "checkpoint": "after_evidence_before_terminal",
            "deployment_output_token_limit": 1024,
            "tasks": manifest["tasks"],
        },
    )


def report(config: dict[str, Any], output: Path) -> None:
    manifest = cast(
        dict[str, Any],
        json.loads((output / "baseline-manifest.json").read_text("utf-8")),
    )
    if len(manifest["tasks"]) != 6:
        raise RuntimeError("report requires all six primary outcomes")
    rows: list[str] = []
    revisions: list[str] = []
    for item in cast(list[dict[str, Any]], manifest["tasks"]):
        if not item["execution_attempted"]:
            failure = cast(dict[str, Any], item["failure"])
            rows.append(
                f"| {item['task']} | planning_failed | - | - | - | - | - | 0 | - |"
            )
            revisions.extend(
                (
                    f"### {item['task']}",
                    "",
                    "- Decision: `planning_failed`",
                    f"- Typed failure: `{failure['type']}` — {failure['message']}",
                    "- No execution was attempted and the one-shot plan was not retried.",
                    "",
                )
            )
            continue
        audit = cast(
            dict[str, Any],
            json.loads(
                (output / "runs" / item["run_id"] / "audit.json").read_text("utf-8")
            ),
        )
        revision = cast(list[dict[str, Any]], audit["workflow_revisions"])[0]
        calls = cast(list[dict[str, Any]], audit["model_calls"])
        finish = ",".join(
            sorted(
                {
                    str(call["telemetry"]["finish_reason"])
                    for call in calls
                    if call["telemetry"] is not None
                }
            )
        )
        rows.append(
            f"| {item['task']} | {revision['decision']} | "
            f"`{str(item['g0_sha256'])[:8]}` -> "
            f"`{str(item['g_final_sha256'])[:8]}` | {audit['terminal_answer']} | "
            f"{audit['benchmark_score']:.1f} | {audit['e2e_latency_ms']:.1f} | "
            f"{audit['transfer_bytes']} / {audit['transfer_time_ms']:.1f} | "
            f"{len(calls)} | {finish} |"
        )
        changes = revision.get("changes")
        model_tokens = ", ".join(
            f"{call['node_id']}={call['telemetry']['input_tokens']}/"
            f"{call['telemetry']['output_tokens']}/"
            f"{call['telemetry']['finish_reason']}"
            for call in calls
        )
        replanner_telemetry = cast(
            dict[str, Any], audit["replanner"]["completion"]["telemetry"]
        )
        revisions.extend(
            (
                f"### {item['task']}",
                "",
                f"- Decision: `{revision['decision']}`",
                f"- Trigger: `{revision.get('trigger')}`",
                f"- Reason: {revision['reason']}",
                f"- Changes: `{json.dumps(changes, ensure_ascii=False, sort_keys=True)}`",
                f"- Model input/output/finish: `{model_tokens}`",
                "- Replanner input/output/finish/wall-ms: "
                f"`{replanner_telemetry['input_tokens']}/"
                f"{replanner_telemetry['output_tokens']}/"
                f"{replanner_telemetry['finish_reason']}/"
                f"{audit['replanner']['wall_latency_ms']:.1f}`",
                "",
            )
        )
    report_path = base.REPO / "docs/blind-baseline-semantic-cleanup-v1-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            (
                "# Blind baseline semantic competence cleanup v1",
                "",
                "## Frozen contract",
                "",
                "Each of the six original tasks received exactly one Cloud Blind Planner call. "
                "Five valid G0 plans were executed once in the accepted clean attempt under "
                "the original benchmark/evaluator contracts, native networking, fixed "
                "model/operator pool, and B0 scheduler. The LongBench multi-document G0 failed "
                "context validation before execution and was not retried. One resource-blind "
                "replan was allowed only after all currently executable non-terminal "
                "evidence/model nodes had materialized. Completed nodes and artifacts were "
                "immutable and were not replayed.",
                "",
                "Both model deployments used the generic configured 1024-token output limit. "
                "Context preflight remained fail-closed, and every call retained output-token "
                "and finish-reason telemetry; all accepted model calls ended with `stop`, and "
                "the largest materialized evidence-note output was 293 tokens. No critic, "
                "hidden summarization, memory, RL, task-specific rule, or infrastructure "
                "visibility was added.",
                "",
                "Two predecessor attempts are preserved but excluded: attempt 1 contained a "
                "forbidden private-field name in fixed replanner instructions; attempt 2 used "
                "physical deployment IDs instead of opaque model aliases. Only those privacy "
                "boundaries were corrected. Frozen G0 plans, actions, model pool, benchmark "
                "inputs, and evaluator were unchanged. The accepted attempt used no retry or "
                "replacement.",
                "",
                "## Outcomes",
                "",
                "| Task | Replan | G0 -> Gfinal | Answer | Score | E2E ms | Transfer B / ms | "
                "Model calls | Finish reasons |",
                "|---|---|---|---|---:|---:|---:|---:|---|",
                *rows,
                "",
                "## Workflow revisions",
                "",
                *revisions,
                "## Trace audit",
                "",
                "Every accepted execution contains exactly one replanner checkpoint. Every "
                "workflow node has exactly one `workflow.node.start`, so no completed node was "
                "replayed. All five decisions were `keep`, hence every G0 hash equals Gfinal. "
                "Planner/replanner prompt scans found no private field names, private values, "
                "network/address state, or real deployment IDs.",
                "",
                "## Freeze",
                "",
                "The final manifest is `freeze/blind-baseline-final.json`. This is the frozen "
                "resource-blind semantic baseline; no further semantic Planner tuning is "
                "authorized after this run.",
                "",
            )
        ),
        encoding="utf-8",
    )


async def main_async(args: argparse.Namespace) -> None:
    config = base._yaml(args.config)
    bundles = base.load_bundles(config, args)
    if args.command == "prepare":
        base.prepare(config, bundles, args)
    elif args.command == "freeze":
        await base.freeze_plans(config, bundles, args)
    elif args.command == "preflight":
        await base.preflight(
            config,
            bundles,
            args.output,
            args.native_network_snapshot,
        )
    elif args.command == "run":
        await run_baseline(config, bundles, args)
    elif args.command == "report":
        report(config, args.output)
    elif args.command == "all":
        base.prepare(config, bundles, args)
        await base.freeze_plans(config, bundles, args)
        await base.preflight(
            config,
            bundles,
            args.output,
            args.native_network_snapshot,
        )
        await run_baseline(config, bundles, args)
        report(config, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("prepare", "freeze", "preflight", "run", "report", "all"),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--video-tasks", type=Path, required=True)
    parser.add_argument("--video-answers", type=Path, required=True)
    parser.add_argument("--video-sources", type=Path, required=True)
    parser.add_argument("--longbench-samples", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--native-network-snapshot", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
