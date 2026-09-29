"""Run the frozen-prior workflow-centric 2x2 preliminary experiment."""

# The benchmark construction helpers are frozen by the preceding baseline.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from blind_baseline_6task_v1 import _multihop_bundle
from open_ended_infra_aware_preliminary_v1 import _observed_operator_profiles
from open_ended_mas_preliminary_v1 import _load_key

from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import (
    OpenAIBackendConfig,
    PlannerConfig,
    RunnerConfig,
    StaticBackendConfig,
    build_model_backend,
)
from infra_joint.control.adaptation import (
    KeepWorkflowPolicy,
    LLMInfraAwareWorkflowAdapter,
    WorkflowAdaptationContext,
    WorkflowAdaptationOutcome,
    WorkflowAdaptationPolicy,
)
from infra_joint.control.adaptive_runner import (
    AdaptiveWorkflowBenchmarkRunner,
    PersistedAdaptiveWorkflowResult,
)
from infra_joint.control.prior import (
    LLMPriorWorkflowGenerator,
    PriorAttemptStore,
    PriorWorkflowStore,
)
from infra_joint.control.workflow import canonical_sha256
from infra_joint.core.state import ArtifactPlacement, EnvironmentSpec, LinkSpec
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.worker.model_backend import ModelCompletion, ModelRequest

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/workflow-formal-preliminary-2x2-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/workflow-formal-preliminary-2x2-v1"


class CapturingBackend:
    def __init__(self, backend: Any) -> None:
        self._backend = backend
        self.requests: list[ModelRequest] = []
        self.completions: list[ModelCompletion] = []

    async def invoke(self, request: ModelRequest) -> ModelCompletion:
        self.requests.append(request)
        completion = await self._backend.invoke(request)
        self.completions.append(completion)
        return completion


class CapturingPolicy:
    def __init__(self, policy: WorkflowAdaptationPolicy) -> None:
        self._policy = policy
        self.calls: list[dict[str, Any]] = []

    async def adapt(self, context: WorkflowAdaptationContext) -> WorkflowAdaptationOutcome:
        outcome = await self._policy.adapt(context)
        self.calls.append(
            {
                "plan_sha256": context.plan.canonical_sha256(),
                "plan_version": context.plan.version,
                "runtime": context.runtime.model_dump(mode="json"),
                "physical": context.physical.model_dump(mode="json"),
                "decision": outcome.decision.model_dump(mode="json"),
                "telemetry": outcome.telemetry.model_dump(mode="json"),
            }
        )
        return outcome


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"configuration must be a mapping: {path}")
    return cast(dict[str, Any], value)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_bundle(config: dict[str, Any], args: argparse.Namespace) -> AdaptationBundle:
    base = _yaml(REPO / str(config["source_benchmark_config"]))
    task_config = cast(dict[str, Any], config["task"])
    source_rows = cast(list[dict[str, Any]], cast(dict[str, Any], base["dataset"])["tasks"])
    row = next(item for item in source_rows if str(item["label"]) == str(task_config["label"]))
    if str(row["source_task_id"]) != str(task_config["source_task_id"]):
        raise RuntimeError("selected task identity differs from the frozen benchmark config")
    corpus_rows = cast(list[dict[str, Any]], json.loads(args.multihop_corpus.read_text("utf-8")))
    query_rows = cast(list[dict[str, Any]], json.loads(args.multihop_queries.read_text("utf-8")))
    revisions = cast(dict[str, str], cast(dict[str, Any], base["dataset"])["revisions"])
    bundle = _multihop_bundle(row, corpus_rows, query_rows, revisions["multihop_rag"])
    validity = bundle.execution.validity
    if not (
        validity.information_equivalent
        and validity.query_equivalent
        and validity.evaluator_equivalent
    ):
        raise RuntimeError(
            "selected benchmark adaptation is not information/query/evaluator equivalent"
        )
    return bundle


def _operations(config: dict[str, Any]) -> tuple[str, ...]:
    execution = cast(dict[str, Any], config["execution"])
    return tuple(str(item) for item in cast(list[object], execution["available_operations"]))


def _environment(
    config: dict[str, Any],
    bundle: AdaptationBundle,
    regime: str,
) -> EnvironmentSpec:
    base = _yaml(REPO / str(config["source_benchmark_config"]))
    environment_path = REPO / str(base["environment_config"])
    environment = EnvironmentSpec.model_validate(_yaml(environment_path)["environment"])
    execution = cast(dict[str, Any], base["execution"])
    placement_lists = cast(dict[str, list[str]], execution["initial_placement"])
    placement_agents = placement_lists[str(cast(dict[str, Any], config["task"])["label"])]
    artifact_ids = [item.spec.artifact_id for item in bundle.prepared_artifacts]
    placements = tuple(
        ArtifactPlacement(artifact_id=artifact_id, agent_id=agent_id)
        for artifact_id, agent_id in zip(artifact_ids, placement_agents, strict=True)
    )
    regime_values = cast(dict[str, Any], cast(dict[str, Any], config["network"])["regimes"])[regime]
    network = cast(dict[str, Any], regime_values)
    links = tuple(
        LinkSpec(
            source_agent_id=source.agent_id,
            target_agent_id=target.agent_id,
            bandwidth_mbps=float(network["bandwidth_mbps"]),
            rtt_ms=float(network["added_rtt_ms"]),
        )
        for source in environment.agents
        for target in environment.agents
        if source.agent_id != target.agent_id
    )
    return environment.model_copy(update={"initial_placements": placements, "links": links})


def _runner_config(
    environment: EnvironmentSpec,
    worker_urls: dict[str, str],
    output: Path,
) -> RunnerConfig:
    return RunnerConfig(
        environment=environment,
        worker_urls=worker_urls,
        planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
        output_root=output / "runs",
        max_planning_steps=128,
        http_timeout_seconds=900,
    )


def _model_config(config: dict[str, Any], section: str) -> OpenAIBackendConfig:
    values = cast(dict[str, Any], cast(dict[str, Any], config[section])["model"])
    return OpenAIBackendConfig.model_validate(values)


def _prior_generator(
    config: dict[str, Any],
    backend: Any,
    *,
    attempt_store: PriorAttemptStore | None = None,
) -> LLMPriorWorkflowGenerator:
    model = _model_config(config, "prior")
    from infra_joint.operators.catalog import build_operator_catalog

    return LLMPriorWorkflowGenerator(
        backend,
        build_operator_catalog(),
        model_id=model.model,
        generator_id="workflow-formal-preliminary-2x2-v1-prior",
        attempt_store=attempt_store,
    )


def _worker_urls(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        agent_id, separator, url = value.partition("=")
        if not separator or not agent_id or not url:
            raise ValueError("--worker-url must have AGENT_ID=URL form")
        parsed[agent_id] = url
    expected = {"A4", "A5", "A28", "strong-4090"}
    if set(parsed) != expected:
        raise ValueError(f"worker URLs must cover exactly {sorted(expected)}")
    return parsed


async def _assert_empty_workers(worker_urls: dict[str, str]) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    async with AsyncExitStack() as stack:
        for agent_id, url in sorted(worker_urls.items()):
            http = await stack.enter_async_context(
                httpx.AsyncClient(base_url=url, timeout=30, trust_env=False)
            )
            state = await HttpWorkerClient(agent_id, http).get_state()
            if state.in_flight != 0 or not state.available:
                raise RuntimeError(f"fresh Worker is not idle and available: {agent_id}")
            if state.artifacts:
                raise RuntimeError(f"fresh Worker artifact store is not empty: {agent_id}")
            observed[agent_id] = state.model_dump(mode="json")
    return observed


def _backend_evidence(capture: CapturingBackend) -> list[dict[str, Any]]:
    return [
        {
            "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
            "prompt_bytes": len(request.prompt.encode("utf-8")),
            "completion_sha256": hashlib.sha256(completion.text.encode("utf-8")).hexdigest(),
            "completion": completion.text,
            "telemetry": completion.telemetry.model_dump(mode="json"),
        }
        for request, completion in zip(capture.requests, capture.completions, strict=True)
    ]


async def prepare(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    bundle = _load_bundle(config, args)
    output = args.output
    attempt_root = output / "prior_attempts" / bundle.execution.task.task_id
    attempts_before = (
        {path for path in attempt_root.iterdir() if path.is_dir()}
        if attempt_root.exists()
        else set()
    )
    store = PriorWorkflowStore(output / "frozen-prior")
    model_config = _model_config(config, "prior")
    backend, client = build_model_backend(model_config)
    capture = CapturingBackend(backend)
    try:
        runner = AdaptiveWorkflowBenchmarkRunner(
            _runner_config(
                _environment(config, bundle, "fast"),
                {
                    "A4": "http://127.0.0.1:1",
                    "A5": "http://127.0.0.1:2",
                    "A28": "http://127.0.0.1:3",
                    "strong-4090": "http://127.0.0.1:4",
                },
                output,
            ),
            _prior_generator(
                config,
                capture,
                attempt_store=PriorAttemptStore(output / "prior_attempts"),
            ),
            KeepWorkflowPolicy(),
            _operations(config),
            prior_store=store,
            require_frozen_prior=True,
        )
        frozen = await runner.prepare_prior_workflow(bundle)
    finally:
        if client is not None:
            await client.close()
    if len(capture.requests) != 1 or len(capture.completions) != 1:
        raise RuntimeError("prior preparation must make exactly one model call")
    attempts_after = {path for path in attempt_root.iterdir() if path.is_dir()}
    new_attempts = tuple(sorted(attempts_after - attempts_before))
    if len(new_attempts) != 1:
        raise RuntimeError("formal prior preparation must create exactly one durable attempt")
    attempt_directory = new_attempts[0]
    validation_result = json.loads(
        (attempt_directory / "validation_result.json").read_text("utf-8")
    )
    if validation_result.get("attempt_status") != "frozen_success":
        raise RuntimeError("successful prior preparation lacks frozen-success evidence")
    _write_json(
        output / "freeze" / "preparation.json",
        {
            "experiment_id": config["experiment_id"],
            "task_label": cast(dict[str, Any], config["task"])["label"],
            "task_id": bundle.execution.task.task_id,
            "task_contract_sha256": canonical_sha256(bundle.execution.task.model_dump(mode="json")),
            "public_artifact_sha256": {
                item.spec.artifact_id: item.sha256_hex for item in bundle.prepared_artifacts
            },
            "prior_plan_sha256": frozen.plan_sha256,
            "task_view_sha256": frozen.task_view_sha256,
            "capability_sha256": frozen.capability_sha256,
            "prompt_sha256": frozen.prompt_sha256,
            "prior_model": frozen.prior_model,
            "generator_id": frozen.generator_id,
            "generator_version": frozen.generator_version,
            "prior_call_count": 1,
            "attempt_id": attempt_directory.name,
            "attempt_path": str(attempt_directory),
            "raw_completion_persisted": (attempt_directory / "raw_completion.txt").exists(),
            "draft_parse": "passed",
            "constructed_g0_version": frozen.plan.version,
            "semantic_validation": validation_result["semantic_validation"],
            "static_feasibility": validation_result["static_feasibility"],
            "frozen_prior_path": validation_result["frozen_prior_path"],
            "prior_call": _backend_evidence(capture)[0],
            "plan": frozen.plan.model_dump(mode="json"),
        },
    )
    print(frozen.plan_sha256, flush=True)


def _matrix_cell(config: dict[str, Any], run_id: str) -> dict[str, Any]:
    matrix = cast(list[dict[str, Any]], config["matrix"])
    matches = [item for item in matrix if str(item["run_id"]) == run_id]
    if len(matches) != 1:
        raise ValueError(f"run ID is not one frozen 2x2 cell: {run_id}")
    return matches[0]


async def run_cell(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    cell = _matrix_cell(config, args.run_id)
    regime = str(cell["regime"])
    method = str(cell["method"])
    bundle = _load_bundle(config, args)
    worker_urls = _worker_urls(args.worker_url)
    worker_states = await _assert_empty_workers(worker_urls)
    output = args.output
    run_directory = output / "runs" / args.run_id
    if run_directory.exists():
        raise FileExistsError("refusing retry or overwrite of an existing formal cell")
    model_config = _model_config(config, "adaptation")
    backend, client = build_model_backend(model_config)
    capture = CapturingBackend(backend)
    inner_policy: WorkflowAdaptationPolicy
    if method == "keep":
        inner_policy = KeepWorkflowPolicy("frozen baseline policy preserves the pending workflow")
    elif method == "aware":
        inner_policy = LLMInfraAwareWorkflowAdapter(capture)
    else:
        raise ValueError(f"unknown method: {method}")
    policy = CapturingPolicy(inner_policy)
    profiles_config = cast(dict[str, Any], config["profiles"])
    profiles = _observed_operator_profiles(Path(str(profiles_config["operator_source_evidence"])))
    runner = AdaptiveWorkflowBenchmarkRunner(
        _runner_config(_environment(config, bundle, regime), worker_urls, output),
        _prior_generator(config, capture),
        policy,
        _operations(config),
        prior_store=PriorWorkflowStore(output / "frozen-prior"),
        require_frozen_prior=True,
        cost_profiles=profiles,
    )
    try:
        result = await runner.run(bundle, run_id=args.run_id)
    finally:
        if client is not None:
            await client.close()
    evidence = {
        "run_id": args.run_id,
        "regime": regime,
        "method": method,
        "prior_plan_sha256": result.prior_plan_sha256,
        "fresh_worker_states": worker_states,
        "adaptation_calls": policy.calls,
        "adapter_backend_calls": _backend_evidence(capture),
        "result": result.model_dump(mode="json"),
    }
    _write_json(run_directory / "cell-audit.json", evidence)
    print(json.dumps(_cell_summary(result, policy.calls), ensure_ascii=False), flush=True)


def _trace_events(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _duration_ms(start: str, end: str) -> float:
    return (
        datetime.fromisoformat(end).timestamp() - datetime.fromisoformat(start).timestamp()
    ) * 1000


def _cell_summary(
    result: PersistedAdaptiveWorkflowResult,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    events = _trace_events(Path(result.trace_path))
    physical = [item for item in events if item["event_type"] == "physical.execution"]
    executions = [
        cast(dict[str, Any], cast(dict[str, Any], item["payload"])["execution"])
        for item in physical
        if cast(dict[str, Any], item["payload"]).get("execution") is not None
    ]
    transfers = [
        transfer
        for execution in executions
        for transfer in cast(list[dict[str, Any]], execution.get("transfers", []))
    ]
    model_telemetry = [
        cast(dict[str, Any], execution["model_telemetry"])
        for execution in executions
        if execution.get("model_telemetry") is not None
    ]
    workflow_events = [item for item in events if item["event_type"] == "workflow.plan.version"]
    workflow_e2e = None
    if workflow_events and events:
        workflow_e2e = _duration_ms(
            str(workflow_events[0]["timestamp"]), str(events[-1]["timestamp"])
        )
    execution = result.execution
    return {
        "run_id": result.run_id,
        "execution_completed": result.execution_completed,
        "prior_plan_sha256": result.prior_plan_sha256,
        "adaptation_decisions": [item["decision"] for item in calls],
        "workflow_versions": (
            [item.model_dump(mode="json") for item in execution.versions]
            if execution is not None
            else []
        ),
        "benchmark_score": (
            result.evaluation.benchmark_score if result.evaluation is not None else None
        ),
        "format_valid": (result.evaluation.format_valid if result.evaluation is not None else None),
        "terminal_output_contract_valid": result.terminal_output_contract_valid,
        "runner_e2e_latency_ms": result.e2e_latency_ms,
        "workflow_e2e_latency_ms": workflow_e2e,
        "transfer_bytes": sum(int(item["bytes_transferred"]) for item in transfers),
        "transfer_latency_ms": sum(float(item["duration_ms"]) for item in transfers),
        "model_service_latency_ms": sum(
            float(item["service_latency_ms"]) for item in model_telemetry
        ),
        "operator_latency_ms": sum(
            float(item.get("operator_latency_ms", 0.0)) for item in executions
        ),
        "adaptation_latency_ms": sum(
            float(cast(dict[str, Any], item["telemetry"])["adaptation_latency_ms"])
            for item in calls
        ),
        "adaptation_input_tokens": sum(
            int(value)
            for item in calls
            if (value := cast(dict[str, Any], item["telemetry"]).get("input_tokens")) is not None
        ),
        "adaptation_output_tokens": sum(
            int(value)
            for item in calls
            if (value := cast(dict[str, Any], item["telemetry"]).get("output_tokens")) is not None
        ),
        "physical_selections": [
            cast(dict[str, Any], item["payload"]).get("selection") for item in physical
        ],
        "predictions": [item["physical"] for item in calls],
        "failure": result.failure.model_dump(mode="json") if result.failure else None,
    }


def report(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    preparation = cast(
        dict[str, Any],
        json.loads((args.output / "freeze" / "preparation.json").read_text("utf-8")),
    )
    rows: list[dict[str, Any]] = []
    for cell in cast(list[dict[str, Any]], config["matrix"]):
        run_id = str(cell["run_id"])
        audit = cast(
            dict[str, Any],
            json.loads((args.output / "runs" / run_id / "cell-audit.json").read_text("utf-8")),
        )
        result = PersistedAdaptiveWorkflowResult.model_validate(audit["result"])
        rows.append(
            {
                "regime": cell["regime"],
                "method": cell["method"],
                **_cell_summary(
                    result,
                    cast(list[dict[str, Any]], audit["adaptation_calls"]),
                ),
            }
        )
    hashes = {item["prior_plan_sha256"] for item in rows}
    if hashes != {preparation["prior_plan_sha256"]}:
        raise RuntimeError("the 2x2 cells did not use exactly the same frozen G0")
    _write_json(args.output / "summary.json", rows)
    network = cast(dict[str, Any], config["network"])["regimes"]
    lines = [
        "# Workflow-Centric Formal Preliminary 2x2 v1",
        "",
        f"- Task: `{preparation['task_label']}` / `{preparation['task_id']}`",
        f"- Frozen G0 SHA-256: `{preparation['prior_plan_sha256']}`",
        f"- Task SHA-256: `{preparation['task_contract_sha256']}`",
        f"- Capability SHA-256: `{preparation['capability_sha256']}`",
        f"- Prior prompt SHA-256: `{preparation['prompt_sha256']}`",
        f"- Prior model: `{preparation['prior_model']}`; calls: 1",
        f"- Fast: `{network['fast']}`",
        f"- Slow: `{network['slow']}`",
        "",
        "| Regime | Method | Decisions | Complete | Score | Format | Workflow E2E ms | "
        "Bytes | Transfer ms | Model ms | Adapt ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        decisions = ", ".join(
            str(item["decision_type"])
            for item in cast(list[dict[str, Any]], row["adaptation_decisions"])
        )
        lines.append(
            "| {regime} | {method} | {decisions} | {complete} | {score} | {fmt} | "
            "{e2e} | {bytes} | {transfer} | {model} | {adapt} |".format(
                regime=row["regime"],
                method=row["method"],
                decisions=decisions,
                complete=row["execution_completed"],
                score=row["benchmark_score"],
                fmt=row["format_valid"],
                e2e=row["workflow_e2e_latency_ms"],
                bytes=row["transfer_bytes"],
                transfer=row["transfer_latency_ms"],
                model=row["model_service_latency_ms"],
                adapt=row["adaptation_latency_ms"],
            )
        )
    lines.extend(
        (
            "",
            "## Frozen G0",
            "",
            "```json",
            json.dumps(preparation["plan"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Predicted versus actual and patch evidence",
            "",
            "The machine-readable `summary.json` and per-cell `cell-audit.json` files retain every "
            "pre-adaptation workflow profile, KEEP/PATCH edit, workflow version, physical "
            "selection, and actual execution telemetry. Unknown predictions remain JSON null "
            "with their original "
            "reason codes.",
            "",
            "## Decision",
            "",
            "Interpretation must be filled only from the four frozen primary cells; no additional "
            "task, retry, replacement, repetition, bandwidth, or tuned rerun is permitted.",
        )
    )
    report_path = args.output / "preliminary-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run-cell", "report"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--worker-url", action="append", default=[])
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.api_key_file is not None:
        _load_key(args.api_key_file)
    if args.command == "prepare":
        await prepare(args)
    elif args.command == "run-cell":
        if args.run_id is None:
            raise ValueError("run-cell requires --run-id")
        await run_cell(args)
    else:
        report(args)


if __name__ == "__main__":
    asyncio.run(main())
