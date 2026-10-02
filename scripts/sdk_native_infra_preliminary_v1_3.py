"""Run one frozen SDK-native Blind/Aware MultiHop preliminary cell."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from agents import Model
from blind_3family_validation_v1 import (
    REPO,
    BlindHarnessFreeze,
    _capability_sha256,
    _environment,
    _extra_trace_summary,
    _load_bundle,
    _model_service_timeout_seconds,
    _operations,
    _placement_map,
    _public_bundle_digest,
    _revision,
    _sha256,
    _validate_harness_manifest_hash,
    _yaml,
    load_harness,
    validate_harness,
    validate_runtime_import_root,
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
from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ProfileVisibility
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.runner import ControlPlaneBenchmarkRunner
from infra_joint.core.base import ContractModel
from infra_joint.core.state import LinkSpec
from infra_joint.core.task import OutputContract, OutputFormat
from infra_joint.evaluation.trace_audit import (
    summarize_concurrency,
    summarize_cost,
    summarize_profiles,
)
from infra_joint.operators.catalog import build_operator_catalog


class InfraPreliminaryCellFreeze(ContractModel):
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
    profile_visibility: ProfileVisibility
    network_regime: str
    bandwidth_mbps: float
    added_rtt_ms: float
    scheduler: str
    model_service_timeout_seconds: float
    repetitions: int
    retry: bool
    replacement: bool


_SUPPORTED_HARNESS_IDS = frozenset(
    {
        "blind-harness-v1.3",
        "blind-harness-v1.3.1",
        "qwen-infra-sanity-v1",
        "qwen-infra-sanity-v2",
        "qwen-infra-preliminary-v1",
        "infra-aware-predecision-v1",
    }
)


class ModelRequestBodyAdapter(Model):
    """Inject frozen provider request fields without changing agent semantics."""

    def __init__(self, delegate: object, extra_body: dict[str, object]) -> None:
        self._delegate = delegate
        self._extra_body = dict(extra_body)

    def _settings(self, model_settings: Any) -> Any:
        existing = dict(model_settings.extra_body or {})
        conflicts = {
            key
            for key, value in self._extra_body.items()
            if key in existing and existing[key] != value
        }
        if conflicts:
            raise RuntimeError(
                "provider request options conflict with agent settings: "
                + ", ".join(sorted(conflicts))
            )
        return replace(
            model_settings,
            extra_body={**existing, **self._extra_body},
        )

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        values = list(args)
        if "model_settings" in kwargs:
            kwargs["model_settings"] = self._settings(kwargs["model_settings"])
        elif len(values) >= 3:
            values[2] = self._settings(values[2])
        else:
            raise RuntimeError("model request is missing ModelSettings")
        method = cast(Any, self._delegate).get_response
        return await method(*values, **kwargs)

    async def stream_response(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[Any]:
        values = list(args)
        if "model_settings" in kwargs:
            kwargs["model_settings"] = self._settings(kwargs["model_settings"])
        elif len(values) >= 3:
            values[2] = self._settings(values[2])
        else:
            raise RuntimeError("model request is missing ModelSettings")
        method = cast(Any, self._delegate).stream_response
        async for event in method(*values, **kwargs):
            yield event


def _load_control_plane_key(path: Path, environment_variable: str) -> None:
    """Load the configured provider key without assuming a DeepSeek control plane."""
    if os.environ.get(environment_variable):
        return
    assignments: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{environment_variable}="):
            assignments.append(stripped.split("=", 1)[1].strip().strip("\"'"))
    if len(assignments) == 1 and assignments[0]:
        os.environ[environment_variable] = assignments[0]
        return
    if environment_variable == "DEEPSEEK_API_KEY":
        _load_key(path)
        return
    raise RuntimeError(
        f"API key file must contain exactly one {environment_variable} assignment"
    )


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("task") != "multihop-multisource":
        raise RuntimeError("v1.3 preliminary admits only multihop-multisource")
    visibility = ProfileVisibility(str(config["profile_visibility"]))
    if visibility not in {ProfileVisibility.BLIND, ProfileVisibility.AWARE}:
        raise RuntimeError("unsupported profile visibility")
    network = cast(dict[str, Any], config["network"])
    regime = str(network["regime"])
    expected = {
        "fast": (100.0, 5.0),
        "slow": (3.0, 50.0),
    }
    if regime not in expected or (
        float(network["bandwidth_mbps"]),
        float(network["added_rtt_ms"]),
    ) != expected[regime]:
        raise RuntimeError("network regime drift")
    execution = cast(dict[str, Any], config["execution"])
    if execution != {
        "scheduler": "auto_physical_locality_aware",
        "repetitions": 1,
        "retry": False,
        "replacement": False,
    }:
        raise RuntimeError("preliminary single-run execution contract drift")


def _freeze_cell(
    args: argparse.Namespace,
    config: dict[str, Any],
    base_environment_path: Path,
    harness_path: Path,
    harness: BlindHarnessFreeze,
    bundle: AdaptationBundle,
    source_manifest: dict[str, Any],
    capability_hash: str,
    base: dict[str, Any],
) -> InfraPreliminaryCellFreeze:
    freeze_path = args.output / "freeze" / "manifest.json"
    if freeze_path.exists():
        return InfraPreliminaryCellFreeze.model_validate_json(
            freeze_path.read_text(encoding="utf-8")
        )
    network = cast(dict[str, Any], config["network"])
    execution = cast(dict[str, Any], config["execution"])
    manifest = InfraPreliminaryCellFreeze(
        experiment_id=str(config["experiment_id"]),
        code_revision=_revision(),
        config_sha256=_sha256(args.config),
        environment_sha256=_sha256(base_environment_path),
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
            for key, value in cast(
                dict[object, object], config["worker_urls"]
            ).items()
        },
        fresh_worker_stores={
            str(key): str(value)
            for key, value in cast(
                dict[object, object], config["fresh_worker_stores"]
            ).items()
        },
        profile_visibility=ProfileVisibility(str(config["profile_visibility"])),
        network_regime=str(network["regime"]),
        bandwidth_mbps=float(network["bandwidth_mbps"]),
        added_rtt_ms=float(network["added_rtt_ms"]),
        scheduler=str(execution["scheduler"]),
        model_service_timeout_seconds=_model_service_timeout_seconds(config),
        repetitions=int(execution["repetitions"]),
        retry=bool(execution["retry"]),
        replacement=bool(execution["replacement"]),
    )
    _write_json(freeze_path, manifest)
    _write_json(args.output / "private" / "task-contract.json", bundle.execution.task)
    _write_json(
        args.output / "private" / "private-evaluation.json",
        bundle.private_evaluation,
    )
    return manifest


def _compact_trace(
    path: Path,
    result: dict[str, Any] | None = None,
) -> dict[str, object]:
    detail = _trace_summary(path)
    extra = _extra_trace_summary(path)
    graph = detail["final_graph"]
    events = [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    action_transfer_bytes = 0
    action_transfer_latency_ms = 0.0
    trace_e2e_latency_ms: float | None = None
    for event in events:
        event_type = event.get("event_type")
        payload = cast(dict[str, Any], event.get("payload", {}))
        if event_type in {"run.end", "run.failed"}:
            raw_e2e = payload.get("e2e_latency_ms")
            if isinstance(raw_e2e, int | float):
                trace_e2e_latency_ms = float(raw_e2e)
        if event_type != "physical.execution":
            continue
        execution = cast(dict[str, Any], payload.get("execution", {}))
        transfers = execution.get("transfers", [])
        if isinstance(transfers, list):
            for raw_transfer in transfers:
                if not isinstance(raw_transfer, dict):
                    continue
                transfer = cast(dict[str, Any], raw_transfer)
                raw_bytes = transfer.get("bytes_transferred")
                raw_duration = transfer.get("duration_ms")
                if isinstance(raw_bytes, int):
                    action_transfer_bytes += raw_bytes
                if isinstance(raw_duration, int | float):
                    action_transfer_latency_ms += float(raw_duration)
    profile_events = events
    # Compatibility for old, incomplete traces; never override an actual JSONL observation.
    if not any(e.get("event_type") == "logical.observation" for e in events):
        loop = None if result is None else result.get("loop")
        if isinstance(loop, dict):
            profile_events = [
                {"event_type": "logical.observation", "payload": item}
                for item in loop.get("observations", []) if isinstance(item, dict)
            ]
    logical_text = json.dumps(
        [event for event in events if str(event.get("event_type", "")).startswith("logical.")],
        ensure_ascii=False,
        sort_keys=True,
    )
    identities = re.findall(
        r'192\.168\.0\.|"(?:A4|A5|A28|strong-4090)"|"deployment_id"',
        logical_text,
    )
    return {
        "manager_reasoning_turns": detail["manager_reasoning_turns"],
        "specialist_reasoning_turns": detail["specialist_reasoning_turns"],
        "tool_calls": detail["tool_calls"],
        "model_calls": detail["model_calls"],
        "subagent_calls": detail["subagent_calls"],
        "context_failure_count": len(cast(list[object], detail["context_failures"])),
        "graph_nodes": (
            0
            if graph is None
            else len(cast(list[object], cast(dict[str, object], graph)["nodes"]))
        ),
        "graph_edges": (
            0
            if graph is None
            else len(cast(list[object], cast(dict[str, object], graph)["edges"]))
        ),
        "reached_model_inference": extra["reached_model_inference"],
        "logical_privacy_pass": extra["logical_privacy_pass"] and not identities,
        "logical_identity_findings": identities,
        **summarize_profiles(profile_events),
        "profile_summary_source": "jsonl" if profile_events is events else "result-loop-fallback",
        **summarize_concurrency(events),
        "cost_decomposition": summarize_cost(events),
        "trace_e2e_latency_ms": trace_e2e_latency_ms,
        "trace_action_transfer_bytes": action_transfer_bytes,
        "trace_action_transfer_latency_ms": action_transfer_latency_ms,
    }


async def run_once(args: argparse.Namespace) -> None:
    validate_runtime_import_root()
    config = _yaml(args.config)
    _validate_config(config)
    harness_path = REPO / str(config["harness_manifest"])
    _validate_harness_manifest_hash(config, harness_path)
    harness = load_harness(harness_path)
    if harness.harness_id not in _SUPPORTED_HARNESS_IDS:
        raise RuntimeError("preliminary requires a supported frozen harness contract")
    if args.api_key_file is not None:
        _load_control_plane_key(
            args.api_key_file,
            str(harness.manager["api_key_env"]),
        )
    if _model_service_timeout_seconds(config) != harness.model_service_timeout_seconds:
        raise RuntimeError("model-service timeout drift from frozen harness")
    base = _yaml(REPO / str(config["source_experiment_config"]))
    bundle, source_manifest = _load_bundle(config, base, args)
    if harness.harness_id == "infra-aware-predecision-v1":
        if harness.runtime.get("profile_timing") != "fresh_before_every_manager_turn":
            raise RuntimeError("pre-decision profile timing drift")
        if harness.runtime.get("record_input_provenance") is not True:
            raise RuntimeError("pre-decision provenance recording drift")
        if harness.runtime.get("terminal_canonical_labels") != ["Yes", "No"]:
            raise RuntimeError("prospective terminal contract drift")
        # Output serialization is prospectively declared, not inferred from private gold.
        source_manifest["prospective_terminal_contract"] = {
            "original_public_bundle_sha256": _public_bundle_digest(bundle),
            "original_output_contract": bundle.execution.task.output_contract.model_dump(
                mode="json"
            ),
            "canonical_labels": ["Yes", "No"],
            "private_evaluator_unchanged": True,
        }
        task = bundle.execution.task.model_copy(update={
            "output_contract": OutputContract(
                format=OutputFormat.SHORT_TEXT, canonical_labels=("Yes", "No"),
            ),
        })
        bundle = replace(bundle, execution=bundle.execution.model_copy(update={"task": task}))
    benchmark_environment = _environment(base, str(config["task"]), bundle)
    network = cast(dict[str, Any], config["network"])
    environment = benchmark_environment.model_copy(
        update={
            "links": tuple(
                LinkSpec(
                    source_agent_id=source.agent_id,
                    target_agent_id=target.agent_id,
                    bandwidth_mbps=float(network["bandwidth_mbps"]),
                    rtt_ms=float(network["added_rtt_ms"]),
                )
                for source in benchmark_environment.agents
                for target in benchmark_environment.agents
                if source.agent_id != target.agent_id
            )
        }
    )
    registry = build_operator_catalog()
    operations = _operations(base)
    capabilities = build_static_capability_contract(environment, registry, operations)
    validate_harness(harness, environment, capabilities, operations)
    manifest = _freeze_cell(
        args,
        config,
        REPO / str(base["environment_config"]),
        harness_path,
        harness,
        bundle,
        source_manifest,
        _capability_sha256(capabilities),
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
    request_extra_body = harness.manager.get("request_extra_body")
    if request_extra_body is not None:
        if not isinstance(request_extra_body, dict):
            raise RuntimeError("manager request_extra_body must be a mapping")
        sdk_model = ModelRequestBodyAdapter(
            sdk_model,
            {
                str(key): value
                for key, value in cast(dict[object, object], request_extra_body).items()
            },
        )
    async with AsyncExitStack() as stack:
        clients = await _clients(
            stack,
            manifest.worker_urls,
            timeout_seconds=manifest.model_service_timeout_seconds,
        )
        await _assert_fresh(clients)
        runner = ControlPlaneBenchmarkRunner(
            RunnerConfig(
                environment=environment,
                worker_urls=manifest.worker_urls,
                planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
                output_root=args.output / "runs",
                max_planning_steps=harness.budget.max_manager_turns,
                http_timeout_seconds=manifest.model_service_timeout_seconds,
            ),
            None,
            operations,
            worker_clients=clients,
            profile_visibility=manifest.profile_visibility,
            loop_budget=harness.budget,
            logical_runtime=OpenAIAgentsNativeRuntime(
                name="sdk-native-manager",
                instructions=MANAGER_INSTRUCTIONS,
                model=sdk_model,
                registry=registry,
                available_operations=operations,
                enable_blind_verifier=True,
                predecision_profiles=harness.harness_id == "infra-aware-predecision-v1",
                record_input_provenance=harness.harness_id == "infra-aware-predecision-v1",
            ),
        )
        result = await runner.run(bundle, run_id=manifest.run_id)
    trace_path = args.output / "runs" / manifest.run_id / "trace.jsonl"
    initial_bytes = sum(item.bytes_transferred for item in result.initial_transfers)
    trace = _compact_trace(trace_path, result.model_dump(mode="json"))
    action_bytes = (
        int(trace["trace_action_transfer_bytes"])
        if result.telemetry is None
        else result.telemetry.action_transfer_bytes
    )
    e2e_latency_ms = (
        trace["trace_e2e_latency_ms"]
        if result.telemetry is None
        else result.telemetry.e2e_latency_ms
    )
    summary = {
        "harness_id": harness.harness_id,
        "task_label": manifest.task_label,
        "run_id": manifest.run_id,
        "profile_visibility": manifest.profile_visibility.value,
        "network_regime": manifest.network_regime,
        "bandwidth_mbps": manifest.bandwidth_mbps,
        "added_rtt_ms": manifest.added_rtt_ms,
        "execution_completed": result.execution_completed,
        "final_answer": result.final_answer,
        "evaluator_score": (
            None if result.evaluation is None else result.evaluation.benchmark_score
        ),
        "format_valid": (
            None if result.evaluation is None else result.evaluation.format_valid
        ),
        "failure": None if result.failure is None else result.failure.model_dump(mode="json"),
        "loop_usage": None if result.loop is None else result.loop.usage.model_dump(mode="json"),
        "e2e_latency_ms": e2e_latency_ms,
        "initial_transfer_bytes": initial_bytes,
        "action_transfer_bytes": action_bytes,
        "total_transferred_bytes": initial_bytes + action_bytes,
        "trace_summary": trace,
    }
    _write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_once(parse_args()))
