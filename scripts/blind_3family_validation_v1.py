"""Run one Stage-2 family with the frozen Blind harness v1.

The script deliberately separates the immutable semantic harness from per-run dataset
and Worker-store configuration. It refuses to start when any frozen harness component
has drifted.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, cast

from blind_baseline_6task_v1 import (
    _environment,
    _load_longbench_samples,
    _load_video_bundles,
    _longbench_multidoc_bundle,
    _multihop_bundle,
    _placement_map,
    _public_bundle_digest,
    _sha256,
    _yaml,
)
from open_ended_mas_preliminary_v1 import _load_key
from resource_blind_live_validation_v1 import (
    MANAGER_INSTRUCTIONS,
    _clients,
    _sdk_model,
    _write_json,
)
from sdk_native_blind_multihop_v1 import _assert_fresh, _trace_summary

from infra_joint.agents.context import AgentTaskView
from infra_joint.benchmarks.base import AdaptationBundle
from infra_joint.config import EnvironmentSpec, PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control import native_agents as native_agents_module
from infra_joint.control import verification as verification_module
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility, StaticCapabilityContract
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.base import ContractModel
from infra_joint.operators.catalog import build_operator_catalog

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/blind-3family-longbench-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/blind-3family-validation-v1-longbench"
ALLOWED_TASKS = {
    "longbench-multidoc",
    "multihop-multisource",
    "video-long-payload",
}


class BlindHarnessFreeze(ContractModel):
    harness_id: str
    frozen_from_revision: str
    positive_baseline_run_id: str
    profile_visibility: str
    runtime: dict[str, Any]
    manager: dict[str, Any]
    verifier: dict[str, Any]
    budget: AgentLoopBudget
    available_operations: tuple[str, ...]
    anonymous_model_contract: dict[str, Any]
    static_capability_contract_sha256: str


class Stage2RunFreeze(ContractModel):
    experiment_id: str
    code_revision: str
    config_sha256: str
    environment_sha256: str
    harness_manifest_sha256: str
    harness: BlindHarnessFreeze
    task_label: str
    run_id: str
    task_bundle_sha256: str
    task_view: dict[str, Any]
    source_manifest: dict[str, Any]
    initial_placement: dict[str, str]
    static_capability_contract_sha256: str
    worker_urls: dict[str, str]
    fresh_worker_stores: dict[str, str]
    network: str
    scheduler: str
    repetitions: int
    retry: bool
    replacement: bool


def _revision() -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        revision = os.environ.get("INFRA_JOINT_CODE_REVISION", "")
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise RuntimeError(
            "code revision is unavailable; set INFRA_JOINT_CODE_REVISION for archive deploys"
        )
    return revision


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _capability_sha256(capabilities: StaticCapabilityContract) -> str:
    value = capabilities.model_dump(mode="json")
    operators = cast(list[dict[str, Any]], value["operators"])
    for operator in operators:
        operator["required_capabilities"] = sorted(operator["required_capabilities"])
    value["operators"] = sorted(operators, key=lambda item: str(item["operator"]))
    model_classes = cast(list[dict[str, Any]], value["model_classes"])
    for model_class in model_classes:
        for key in ("capabilities", "modalities", "quality_classes"):
            model_class[key] = sorted(model_class[key])
    value["model_classes"] = sorted(
        model_classes, key=lambda item: str(item["capability_class"])
    )
    return _canonical_sha256(value)


def load_harness(path: Path) -> BlindHarnessFreeze:
    return BlindHarnessFreeze.model_validate(_yaml(path))


def validate_runtime_import_root() -> None:
    expected = {
        "native runtime": (REPO / "src/infra_joint/control/native_agents.py").resolve(),
        "Verifier": (REPO / "src/infra_joint/control/verification.py").resolve(),
    }
    actual = {
        "native runtime": Path(str(native_agents_module.__file__)).resolve(),
        "Verifier": Path(str(verification_module.__file__)).resolve(),
    }
    drift = [
        f"{name}: expected={expected[name]}, imported={path}"
        for name, path in actual.items()
        if path != expected[name]
    ]
    if drift:
        raise RuntimeError(
            "archive deployment imported infra_joint from a different checkout: "
            + "; ".join(drift)
        )


def _operations(base: dict[str, Any]) -> tuple[str, ...]:
    planner = cast(dict[str, Any], base["planner"])
    return tuple(str(item) for item in cast(list[object], planner["available_operations"]))


def validate_harness(
    harness: BlindHarnessFreeze,
    environment: EnvironmentSpec,
    capabilities: StaticCapabilityContract,
    operations: tuple[str, ...],
) -> None:
    errors: list[str] = []
    if harness.harness_id not in {"blind-harness-v1", "blind-harness-v1.1"}:
        errors.append("unexpected harness_id")
    if harness.profile_visibility != ProfileVisibility.BLIND.value:
        errors.append("profile visibility is not Blind")
    if harness.runtime.get("implementation") != "OpenAIAgentsNativeRuntime":
        errors.append("runtime implementation drift")
    if harness.runtime.get("source_sha256") != _sha256(
        REPO / "src/infra_joint/control/native_agents.py"
    ):
        errors.append("native runtime source drift")
    if harness.verifier.get("source_sha256") != _sha256(
        REPO / "src/infra_joint/control/verification.py"
    ):
        errors.append("Verifier source drift")
    if harness.manager.get("instructions_sha256") != _sha256_text(MANAGER_INSTRUCTIONS):
        errors.append("Manager instructions drift")
    if harness.manager.get("model") != harness.verifier.get("model"):
        errors.append("Manager/Verifier model mismatch")
    if not bool(harness.verifier.get("enabled")):
        errors.append("Verifier is disabled")
    if float(harness.verifier.get("temperature", -1)) != 0:
        errors.append("Verifier temperature drift")
    if harness.verifier.get("result_transport") != "required_function_tool":
        errors.append("Verifier transport drift")
    if operations != harness.available_operations:
        errors.append("operator vocabulary drift")
    capability_hash = _capability_sha256(capabilities)
    if capability_hash != harness.static_capability_contract_sha256:
        errors.append("static capability contract drift")
    expected_model = harness.anonymous_model_contract
    for deployment in environment.deployments:
        if deployment.context_window != int(expected_model["context_window"]):
            errors.append(f"context window drift: {deployment.deployment_id}")
        if deployment.reserved_output_tokens != int(
            expected_model["reserved_output_tokens"]
        ):
            errors.append(f"reserved-output drift: {deployment.deployment_id}")
        if set(deployment.modalities) != set(expected_model["modalities"]):
            errors.append(f"modality drift: {deployment.deployment_id}")
        if deployment.image_token_cost != int(expected_model["image_token_cost"]):
            errors.append(f"image-token-cost drift: {deployment.deployment_id}")
    if errors:
        raise RuntimeError("frozen Blind harness validation failed: " + "; ".join(errors))


def _task_row(base: dict[str, Any], label: str) -> dict[str, Any]:
    dataset = cast(dict[str, Any], base["dataset"])
    rows = cast(list[dict[str, Any]], dataset["tasks"])
    matches = [row for row in rows if str(row["label"]) == label]
    if len(matches) != 1:
        raise RuntimeError(f"frozen task row missing or ambiguous: {label}")
    return matches[0]


def _load_bundle(
    config: dict[str, Any], base: dict[str, Any], args: argparse.Namespace
) -> tuple[AdaptationBundle, dict[str, Any]]:
    label = str(config["task"])
    if label not in ALLOWED_TASKS:
        raise RuntimeError(f"Stage-2 runner does not admit task: {label}")
    row = _task_row(base, label)
    revisions = cast(dict[str, str], cast(dict[str, Any], base["dataset"])["revisions"])
    if label == "longbench-multidoc":
        if args.longbench_samples is None:
            raise RuntimeError("--longbench-samples is required for longbench-multidoc")
        sample_id = str(row["source_task_id"])
        samples = _load_longbench_samples(args.longbench_samples, {sample_id})
        bundle = _longbench_multidoc_bundle(
            samples[sample_id],
            revisions["longbench_v2"],
            tuple(int(item) for item in cast(list[object], row["boundary_lines"])),
        )
        source = {
            "longbench_samples": {
                "size_bytes": args.longbench_samples.stat().st_size,
                "sha256": _sha256(args.longbench_samples),
            }
        }
        return bundle, source
    if label == "multihop-multisource":
        if args.multihop_corpus is None or args.multihop_queries is None:
            raise RuntimeError(
                "--multihop-corpus and --multihop-queries are required for "
                "multihop-multisource"
            )
        corpus = cast(
            list[dict[str, Any]],
            json.loads(args.multihop_corpus.read_text(encoding="utf-8")),
        )
        queries = cast(
            list[dict[str, Any]],
            json.loads(args.multihop_queries.read_text(encoding="utf-8")),
        )
        if len(corpus) != 609:
            raise RuntimeError(f"expected complete 609-document corpus, got {len(corpus)}")
        bundle = _multihop_bundle(
            row,
            corpus,
            queries,
            revisions["multihop_rag"],
        )
        source = {
            "multihop_corpus": {
                "size_bytes": args.multihop_corpus.stat().st_size,
                "sha256": _sha256(args.multihop_corpus),
            },
            "multihop_queries": {
                "size_bytes": args.multihop_queries.stat().st_size,
                "sha256": _sha256(args.multihop_queries),
            },
        }
        return bundle, source
    if args.video_tasks is None or args.video_answers is None or args.video_sources is None:
        raise RuntimeError(
            "--video-tasks, --video-answers, and --video-sources are required for video"
        )
    bundles = _load_video_bundles(
        [row],
        task_path=args.video_tasks,
        answer_path=args.video_answers,
        source_root=args.video_sources,
        source_revision=revisions["video_mme"],
    )
    source_path = args.video_sources / str(row["source_filename"])
    source = {
        "video_tasks": {"sha256": _sha256(args.video_tasks)},
        "video_answers": {"sha256": _sha256(args.video_answers)},
        "video_source": {
            "filename": source_path.name,
            "size_bytes": source_path.stat().st_size,
            "sha256": _sha256(source_path),
        },
    }
    return bundles[label], source


def _validate_run_config(config: dict[str, Any]) -> None:
    execution = cast(dict[str, Any], config["execution"])
    if str(config["task"]) not in ALLOWED_TASKS:
        raise RuntimeError("only the frozen Stage-2 representative tasks are admitted")
    if execution != {
        "network": "native_unshaped",
        "scheduler": "auto_physical_locality_aware",
        "repetitions": 1,
        "retry": False,
        "replacement": False,
    }:
        raise RuntimeError("Stage-2 single-run execution contract drift")


def _validate_harness_manifest_hash(config: dict[str, Any], path: Path) -> None:
    expected = str(config["harness_manifest_sha256"])
    actual = _sha256(path)
    if actual != expected:
        raise RuntimeError(
            f"frozen Blind harness manifest drift: expected={expected}, actual={actual}"
        )


def _freeze(
    args: argparse.Namespace,
    config: dict[str, Any],
    fresh_path: Path,
    fresh: dict[str, Any],
    harness_path: Path,
    harness: BlindHarnessFreeze,
    bundle: AdaptationBundle,
    source_manifest: dict[str, Any],
    capability_hash: str,
    base: dict[str, Any],
) -> Stage2RunFreeze:
    freeze_path = args.output / "freeze" / "manifest.json"
    if freeze_path.exists():
        return Stage2RunFreeze.model_validate_json(freeze_path.read_text("utf-8"))
    execution = cast(dict[str, Any], config["execution"])
    manifest = Stage2RunFreeze(
        experiment_id=str(config["experiment_id"]),
        code_revision=_revision(),
        config_sha256=_sha256(args.config),
        environment_sha256=_sha256(fresh_path),
        harness_manifest_sha256=_sha256(harness_path),
        harness=harness,
        task_label=str(config["task"]),
        run_id=str(config["run_id"]),
        task_bundle_sha256=_public_bundle_digest(bundle),
        task_view=AgentTaskView.from_contract(bundle.execution.task).model_dump(mode="json"),
        source_manifest=source_manifest,
        initial_placement=_placement_map(base, str(config["task"]), bundle),
        static_capability_contract_sha256=capability_hash,
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
    _write_json(freeze_path, manifest)
    _write_json(args.output / "private" / "task-contract.json", bundle.execution.task)
    _write_json(
        args.output / "private" / "private-evaluation.json", bundle.private_evaluation
    )
    return manifest


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _extra_trace_summary(path: Path) -> dict[str, Any]:
    events = _events(path)
    model_outcomes = [
        cast(dict[str, Any], event["payload"])
        for event in events
        if event["event_type"] == "logical.model.outcome"
    ]
    logical = json.dumps(
        [event for event in events if str(event["event_type"]).startswith("logical.")],
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden = {
        "source_ref": r'"source_ref"',
        "evaluator_id": r'"evaluator_id"',
        "gold_answer": r'"gold_answer"',
        "supporting_evidence": r'"supporting_evidence"',
        "private_uri": r"private://",
        "node_ip": r"192\.168\.0\.",
        "worker_identity": r'"(?:A4|A5|A28|strong-4090)"',
        "deployment_identity": r'"deployment_id"',
        "bandwidth": r'"bandwidth"',
        "rtt": r'"rtt"',
        "queue": r'"queue"',
        "load": r'"load"',
    }
    findings = [name for name, pattern in forbidden.items() if re.search(pattern, logical)]
    return {
        "model_outcomes": model_outcomes,
        "reached_model_inference": sum(
            bool(item.get("reached_model_inference")) for item in model_outcomes
        ),
        "logical_privacy_findings": findings,
        "logical_privacy_pass": not findings,
    }


async def run_once(args: argparse.Namespace) -> None:
    validate_runtime_import_root()
    if args.api_key_file is not None:
        _load_key(args.api_key_file)
    config = _yaml(args.config)
    _validate_run_config(config)
    base = _yaml(REPO / str(config["source_experiment_config"]))
    fresh_path = REPO / str(config["fresh_environment_config"])
    fresh = _yaml(fresh_path)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    harness = load_harness(harness_path)
    bundle, source_manifest = _load_bundle(config, base, args)
    environment = _environment(base, str(config["task"]), bundle)
    fresh_environment = EnvironmentSpec.model_validate(fresh["environment"])
    if (
        environment.agents != fresh_environment.agents
        or environment.deployments != fresh_environment.deployments
    ):
        raise RuntimeError("fresh Worker environment does not match the benchmark environment")
    registry = build_operator_catalog()
    operations = _operations(base)
    capabilities = build_static_capability_contract(environment, registry, operations)
    validate_harness(harness, environment, capabilities, operations)
    capability_hash = _capability_sha256(capabilities)
    manifest = _freeze(
        args,
        config,
        fresh_path,
        fresh,
        harness_path,
        harness,
        bundle,
        source_manifest,
        capability_hash,
        base,
    )
    result_path = args.output / "runs" / manifest.run_id / "result.json"
    if result_path.exists():
        raise RuntimeError("single-run result already exists; retry is forbidden")
    sdk_model = _sdk_model(
        {
            "control_plane": {
                "manager_model": {
                    "model": str(harness.manager["model"]),
                    "base_url": str(harness.manager["base_url"]),
                    "api_key_env": str(harness.manager["api_key_env"]),
                }
            }
        }
    )
    async with AsyncExitStack() as stack:
        clients = await _clients(stack, manifest.worker_urls)
        await _assert_fresh(clients)
        runner_config = RunnerConfig(
            environment=environment,
            worker_urls=manifest.worker_urls,
            planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
            output_root=args.output / "runs",
            max_planning_steps=harness.budget.max_manager_turns,
            http_timeout_seconds=900,
        )
        runtime = OpenAIAgentsNativeRuntime(
            name="resource-blind-manager",
            instructions=MANAGER_INSTRUCTIONS,
            model=sdk_model,
            registry=registry,
            available_operations=operations,
            enable_blind_verifier=True,
        )
        result = await ControlPlaneBenchmarkRunner(
            runner_config,
            None,
            operations,
            worker_clients=clients,
            profile_visibility=ProfileVisibility.BLIND,
            loop_budget=harness.budget,
            logical_runtime=runtime,
        ).run(bundle, run_id=manifest.run_id)
    trace_path = args.output / "runs" / manifest.run_id / "trace.jsonl"
    trace = _trace_summary(trace_path)
    trace.update(_extra_trace_summary(trace_path))
    initial_bytes = sum(item.bytes_transferred for item in result.initial_transfers)
    summary = {
        "harness_id": harness.harness_id,
        "task_label": manifest.task_label,
        "run_id": manifest.run_id,
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
        "initial_transfer_bytes": initial_bytes,
        "action_transfer_bytes": trace["action_transfer_bytes"],
        "total_transferred_bytes": initial_bytes + int(trace["action_transfer_bytes"]),
        "trace_summary": trace,
    }
    _write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--longbench-samples", type=Path)
    parser.add_argument("--multihop-corpus", type=Path)
    parser.add_argument("--multihop-queries", type=Path)
    parser.add_argument("--video-tasks", type=Path)
    parser.add_argument("--video-answers", type=Path)
    parser.add_argument("--video-sources", type=Path)
    parser.add_argument("--api-key-file", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_once(parse_args()))
