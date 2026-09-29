"""Run the three-case resource-blind persistent-manager live validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from blind_baseline_6task_v1 import (
    _environment,
    _public_bundle_digest,
    _sha256,
    _source_manifest,
    _yaml,
    load_bundles,
)
from openai import AsyncOpenAI

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.openai_agents import (
    OpenAIAgentsManagerPolicy,
    OpenAIAgentsSubagentFactory,
)
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.base import ContractModel
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient, WorkerClient

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/resource-blind-live-validation-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/resource-blind-live-validation-v1"
MANAGER_INSTRUCTIONS = """Solve the benchmark task faithfully through an observation-driven loop.
Use only the finite operator contracts and logical actions supplied by the system. You may create
bounded specialists as tools when independent evidence acquisition or analysis is useful. After
every observation, assess whether the evidence is sufficient, relevant, and mutually consistent.
If it is insufficient, irrelevant, or conflicting, continue with another legal semantic action or
specialist. Do not invent evidence, physical routing, or unavailable operators. Preserve the task's
output contract exactly. Finish only from your own successful terminal model action."""


class FrozenValidation(ContractModel):
    experiment_id: str
    code_revision: str
    config_sha256: str
    source_manifest: dict[str, Any]
    task_order: tuple[str, ...]
    bundle_sha256: dict[str, str]
    task_views: dict[str, dict[str, Any]]
    initial_placement: dict[str, dict[str, str]]
    available_operations: tuple[str, ...]
    budget: AgentLoopBudget
    profile_visibility: str
    sdk_runtime: str


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = value.model_dump(mode="json") if isinstance(value, ContractModel) else value
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def _load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("validation config root must be a mapping")
    return cast(dict[str, Any], raw)


def _selected_bundles(
    validation: dict[str, Any],
    base: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, AdaptationBundle]:
    all_bundles = load_bundles(base, args)
    labels = tuple(str(item) for item in validation["tasks"])
    if len(labels) != 3 or len(set(labels)) != 3:
        raise RuntimeError("validation must freeze exactly three unique tasks")
    return {label: all_bundles[label] for label in labels}


def _budget(validation: dict[str, Any]) -> AgentLoopBudget:
    control = cast(dict[str, Any], validation["control_plane"])
    return AgentLoopBudget.model_validate(control["budget"])


def _operations(base: dict[str, Any]) -> tuple[str, ...]:
    planner = cast(dict[str, Any], base["planner"])
    return tuple(str(item) for item in planner["available_operations"])


def _placement(
    base: dict[str, Any], label: str, bundle: AdaptationBundle
) -> dict[str, str]:
    execution = cast(dict[str, Any], base["execution"])
    placements = cast(dict[str, list[str]], execution["initial_placement"])
    agents = placements[label]
    artifacts = [item.spec.artifact_id for item in bundle.prepared_artifacts]
    return dict(zip(artifacts, agents, strict=True))


def freeze(
    validation_path: Path,
    validation: dict[str, Any],
    base: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    args: argparse.Namespace,
) -> FrozenValidation:
    freeze_path = args.output / "freeze" / "manifest.json"
    if freeze_path.exists():
        return FrozenValidation.model_validate_json(freeze_path.read_text("utf-8"))
    labels = tuple(bundles)
    manifest = FrozenValidation(
        experiment_id=str(validation["experiment_id"]),
        code_revision=_revision(),
        config_sha256=_sha256(validation_path),
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
        budget=_budget(validation),
        profile_visibility=ProfileVisibility.BLIND.value,
        sdk_runtime="OpenAI Agents SDK Manager + bounded specialists-as-tools",
    )
    _write_json(freeze_path, manifest)
    for label, bundle in bundles.items():
        private_root = args.output / "private" / label
        _write_json(private_root / "task-contract.json", bundle.execution.task)
        _write_json(private_root / "private-evaluation.json", bundle.private_evaluation)
    return manifest


def _sdk_model(validation: dict[str, Any]) -> object:
    try:
        import agents
    except ImportError as exc:
        raise RuntimeError("OpenAI Agents SDK is required for this validation") from exc
    model_config = cast(
        dict[str, str],
        cast(dict[str, Any], validation["control_plane"])["manager_model"],
    )
    key_name = model_config["api_key_env"]
    try:
        api_key = os.environ[key_name]
    except KeyError as exc:
        raise RuntimeError(f"required manager API key is missing: {key_name}") from exc
    agents.set_tracing_disabled(True)
    return agents.OpenAIChatCompletionsModel(
        model=model_config["model"],
        openai_client=AsyncOpenAI(
            api_key=api_key,
            base_url=model_config["base_url"],
            timeout=180,
            max_retries=0,
        ),
    )


async def _clients(
    stack: AsyncExitStack,
    urls: dict[str, str],
) -> dict[str, WorkerClient]:
    result: dict[str, WorkerClient] = {}
    for agent_id, url in urls.items():
        http = await stack.enter_async_context(
            httpx.AsyncClient(base_url=url, timeout=900, trust_env=False)
        )
        result[agent_id] = HttpWorkerClient(agent_id, http)
    return result


async def run_all(
    validation: dict[str, Any],
    base: dict[str, Any],
    bundles: dict[str, AdaptationBundle],
    manifest: FrozenValidation,
    args: argparse.Namespace,
) -> None:
    registry = build_operator_catalog()
    operations = manifest.available_operations
    sdk_model = _sdk_model(validation)
    infrastructure = _yaml(REPO / str(base["environment_config"]))
    urls = cast(dict[str, str], infrastructure["worker_urls"])
    summaries: list[dict[str, Any]] = []
    async with AsyncExitStack() as stack:
        clients = await _clients(stack, urls)
        for index, (label, bundle) in enumerate(bundles.items(), start=1):
            run_id = f"{index:02d}-{label}-blind-live-v1"
            environment = _environment(base, label, bundle)
            config = RunnerConfig(
                environment=environment,
                worker_urls=urls,
                planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                output_root=args.output / "runs",
                max_planning_steps=manifest.budget.max_manager_turns,
                http_timeout_seconds=900,
            )
            manager = OpenAIAgentsManagerPolicy(
                name="resource-blind-manager",
                instructions=MANAGER_INSTRUCTIONS,
                model=sdk_model,
                registry=registry,
                available_operations=operations,
            )
            subagents = OpenAIAgentsSubagentFactory(
                model=sdk_model,
                registry=registry,
                available_operations=operations,
            )
            result = await ControlPlaneBenchmarkRunner(
                config,
                manager,
                operations,
                worker_clients=clients,
                subagent_factory=subagents,
                profile_visibility=ProfileVisibility.BLIND,
                loop_budget=manifest.budget,
            ).run(bundle, run_id=run_id)
            summary = {
                "label": label,
                "run_id": run_id,
                "execution_completed": result.execution_completed,
                "failure": (
                    None if result.failure is None else result.failure.model_dump(mode="json")
                ),
                "score": (
                    None
                    if result.evaluation is None
                    else result.evaluation.benchmark_score
                ),
                "format_valid": (
                    None if result.evaluation is None else result.evaluation.format_valid
                ),
                "usage": (
                    None if result.loop is None else result.loop.usage.model_dump(mode="json")
                ),
                "telemetry": (
                    None
                    if result.telemetry is None
                    else result.telemetry.model_dump(mode="json")
                ),
            }
            summaries.append(summary)
            _write_json(args.output / "progress.json", summaries)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            if not result.execution_completed and (
                result.failure is None or result.failure.code != "logical_loop_failed"
            ):
                raise RuntimeError(
                    f"system/harness failure stops validation at {label}: {result.failure}"
                )
    _write_json(args.output / "summary.json", summaries)


async def main_async(args: argparse.Namespace) -> None:
    validation = _load_config(args.config)
    base_path = REPO / str(validation["source_experiment_config"])
    base = _yaml(base_path)
    bundles = _selected_bundles(validation, base, args)
    manifest = freeze(args.config, validation, base, bundles, args)
    if args.freeze_only:
        return
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
    parser.add_argument("--freeze-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
