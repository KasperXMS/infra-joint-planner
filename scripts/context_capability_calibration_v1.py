"""Diagnose a rejected formal G0 and calibrate the deployed model context boundary."""

# This diagnostic intentionally reuses the exact frozen formal-path builders and
# static-feasibility implementation. It never invokes a Planner.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Any, cast

from openai import AsyncOpenAI
from workflow_formal_preliminary_2x2_v1 import (
    DEFAULT_CONFIG,
    _environment,
    _load_bundle,
    _operations,
    _yaml,
)

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import LogicalModelAction
from infra_joint.control.static_feasibility import (
    ArtifactEnvelope,
    StaticFeasibilityError,
    _model_context,
    _topological_actions,
    _validate_output_media_types,
    _validate_schema_arguments,
    derive_output_envelopes,
)
from infra_joint.control.workflow import SemanticWorkflowPlan
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import (
    ModelRequest,
    OpenAICompatibleModelBackend,
    is_text_media_type,
    preflight_model_request,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_contribution(
    envelope: ArtifactEnvelope,
    image_token_cost: int,
) -> int | None:
    if envelope.media_type.startswith("image/"):
        return image_token_cost
    if is_text_media_type(envelope.media_type):
        return envelope.size_upper_bound_bytes
    return None


def _change_kind(output: int | None, inputs: tuple[ArtifactEnvelope, ...]) -> str:
    bounds = tuple(item.size_upper_bound_bytes for item in inputs)
    if output is None or any(item is None for item in bounds):
        return "unknown"
    input_total = sum(cast(int, item) for item in bounds)
    if output < input_total:
        return "reduction"
    if output > input_total:
        return "expansion"
    return "preserved"


def diagnose(args: argparse.Namespace) -> None:
    config = _yaml(args.config)
    bundle = _load_bundle(config, args)
    task = bundle.execution.task
    plan = SemanticWorkflowPlan.model_validate_json(
        (args.attempt / "constructed-g0.json").read_text("utf-8")
    )
    registry = build_operator_catalog()
    capabilities = build_static_capability_contract(
        _environment(config, bundle, "fast"),
        registry,
        _operations(config),
    )
    envelopes = {
        item.artifact_id: ArtifactEnvelope(
            artifact_id=item.artifact_id,
            media_type=item.media_type,
            size_upper_bound_bytes=item.size_bytes,
            content_schema=item.content_schema,
        )
        for item in task.artifacts
    }
    producer_by_artifact: dict[str, str] = {}
    consumer_by_artifact: dict[str, list[str]] = {}
    action_records: list[dict[str, Any]] = []
    target_record: dict[str, Any] | None = None

    for action in _topological_actions(plan):
        inputs = tuple(envelopes[item] for item in action.inputs)
        for artifact_id in action.inputs:
            consumer_by_artifact.setdefault(artifact_id, []).append(action.action_id)
        _validate_schema_arguments(action, inputs)
        _validate_output_media_types(action)
        feasible_classes = ()
        failure: str | None = None
        context_candidates: list[dict[str, Any]] = []
        if isinstance(action, LogicalModelAction):
            candidates = tuple(
                item
                for item in capabilities.model_classes
                if item.satisfies(action.requirements)
            )
            for model_class in candidates:
                contributions = [
                    {
                        "artifact_id": envelope.artifact_id,
                        "media_type": envelope.media_type,
                        "size_upper_bound_bytes": envelope.size_upper_bound_bytes,
                        "context_contribution": _artifact_contribution(
                            envelope,
                            model_class.image_token_cost,
                        ),
                    }
                    for envelope in inputs
                ]
                values = [item["context_contribution"] for item in contributions]
                total = (
                    len(action.prompt.encode("utf-8"))
                    + sum(cast(int, item) for item in values)
                    + model_class.reserved_output_tokens
                    if all(item is not None for item in values)
                    else None
                )
                context_candidates.append(
                    {
                        "capability_class": model_class.capability_class,
                        "context_window": model_class.context_window,
                        "deployment_reserved_output_tokens": (
                            model_class.reserved_output_tokens
                        ),
                        "prompt_bytes_conservative_tokens": len(
                            action.prompt.encode("utf-8")
                        ),
                        "inputs": contributions,
                        "total_conservative_context": total,
                        "excess": (
                            total - model_class.context_window
                            if total is not None
                            else None
                        ),
                    }
                )
            try:
                feasible_classes, _ = _model_context(action, inputs, capabilities)
            except StaticFeasibilityError as exc:
                failure = str(exc)

        outputs = (
            derive_output_envelopes(action, inputs, feasible_classes)
            if failure is None
            else ()
        )
        for output in outputs:
            envelopes[output.artifact_id] = output
            producer_by_artifact[output.artifact_id] = action.action_id
        record = {
            "action_id": action.action_id,
            "operator": "invoke_model"
            if isinstance(action, LogicalModelAction)
            else action.operator,
            "inputs": [item.artifact_id for item in inputs],
            "input_bounds": {
                item.artifact_id: item.size_upper_bound_bytes for item in inputs
            },
            "outputs": [
                {
                    "artifact_id": item.artifact_id,
                    "media_type": item.media_type,
                    "size_upper_bound_bytes": item.size_upper_bound_bytes,
                    "change": _change_kind(item.size_upper_bound_bytes, inputs),
                    "unknown_reasons": item.unknown_reasons,
                }
                for item in outputs
            ],
            "context_candidates": context_candidates,
            "failure": failure,
        }
        action_records.append(record)
        if action.action_id == args.action_id:
            target_record = record
            break

    if target_record is None:
        raise RuntimeError(f"target action was not reached: {args.action_id}")

    ancestors: set[str] = {args.action_id}
    changed = True
    while changed:
        changed = False
        for dependency in plan.dependencies:
            if (
                dependency.consumer_action_id in ancestors
                and dependency.producer_action_id not in ancestors
            ):
                ancestors.add(dependency.producer_action_id)
                changed = True
    evidence_path = [
        record for record in action_records if cast(str, record["action_id"]) in ancestors
    ]
    target_candidates = cast(list[dict[str, Any]], target_record["context_candidates"])
    required_values = {
        cast(int, item["total_conservative_context"])
        for item in target_candidates
        if item["total_conservative_context"] is not None
    }
    result = {
        "planner_backend_calls": 0,
        "attempt_id": args.attempt.name,
        "task_id": task.task_id,
        "action_id": args.action_id,
        "task_artifacts": [
            {
                "artifact_id": item.artifact_id,
                "media_type": item.media_type,
                "size_bytes": item.size_bytes,
                "content_schema": item.content_schema.model_dump(mode="json")
                if item.content_schema is not None
                else None,
            }
            for item in task.artifacts
        ],
        "model_classes": [item.model_dump(mode="json") for item in capabilities.model_classes],
        "required_context": next(iter(required_values))
        if len(required_values) == 1
        else None,
        "required_context_values": sorted(required_values),
        "current_context_windows": sorted(
            {item.context_window for item in capabilities.model_classes}
        ),
        "target": target_record,
        "evidence_path": evidence_path,
        "producer_by_artifact": producer_by_artifact,
        "consumer_by_artifact": consumer_by_artifact,
    }
    _write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def _payload(input_bytes: int) -> str:
    prefix = "Deterministic context calibration. Ignore filler and reply exactly OK.\n"
    unit = "0123456789abcdef"
    if input_bytes < len(prefix):
        raise ValueError("calibration input is too small")
    remaining = input_bytes - len(prefix)
    return prefix + (unit * ((remaining + len(unit) - 1) // len(unit)))[:remaining]


async def calibrate(args: argparse.Namespace) -> None:
    client = AsyncOpenAI(api_key="ollama-local-calibration", base_url=args.base_url)
    backend = OpenAICompatibleModelBackend(
        client,
        args.model,
        reasoning_effort="none",
        temperature=0,
    )
    rows: list[dict[str, Any]] = []
    try:
        for context_window in args.context_sizes:
            if context_window > args.runtime_hard_limit:
                rows.append(
                    {
                        "context_window": context_window,
                        "status": "not_tested_runtime_hard_limit",
                        "runtime_hard_limit": args.runtime_hard_limit,
                    }
                )
                continue
            input_bytes = context_window - args.reserved_output_tokens
            request = ModelRequest(
                prompt=_payload(input_bytes),
                max_output_tokens=args.reserved_output_tokens,
            )
            row: dict[str, Any] = {
                "context_window": context_window,
                "input_bytes": input_bytes,
                "reserved_output_tokens": args.reserved_output_tokens,
                "runtime_hard_limit": args.runtime_hard_limit,
                "ttft_ms": None,
                "peak_memory_bytes": None,
            }
            try:
                row["preflight_estimated_input"] = preflight_model_request(
                    request,
                    modalities=frozenset({"text", "image"}),
                    context_window=context_window,
                    reserved_output_tokens=args.reserved_output_tokens,
                    image_token_cost=2048,
                )
                row["preflight"] = "passed"
            except Exception as exc:
                row.update(
                    {
                        "preflight": "failed",
                        "status": "context_reject",
                        "failure_type": type(exc).__name__,
                        "failure_message": str(exc),
                    }
                )
                rows.append(row)
                continue
            started = perf_counter()
            try:
                completion = await backend.invoke(request)
                row.update(
                    {
                        "status": "pass",
                        "backend_completed": True,
                        "total_latency_ms": (perf_counter() - started) * 1000,
                        "model_service_latency_ms": (
                            completion.telemetry.service_latency_ms
                        ),
                        "backend_input_tokens": completion.telemetry.input_tokens,
                        "backend_output_tokens": completion.telemetry.output_tokens,
                        "finish_reason": completion.telemetry.finish_reason,
                        "output_nonempty": bool(completion.text.strip()),
                        "output_preview": completion.text[:160],
                        "oom": False,
                        "silent_truncation_observed": False,
                    }
                )
            except Exception as exc:
                message = str(exc)
                row.update(
                    {
                        "status": "backend_failure",
                        "backend_completed": False,
                        "total_latency_ms": (perf_counter() - started) * 1000,
                        "failure_type": type(exc).__name__,
                        "failure_message": message,
                        "oom": "out of memory" in message.lower()
                        or "oom" in message.lower(),
                    }
                )
            rows.append(row)
    finally:
        await client.close()
    successful = [item["context_window"] for item in rows if item["status"] == "pass"]
    failures = [
        item for item in rows if item["status"] not in {"pass", "not_tested_runtime_hard_limit"}
    ]
    result = {
        "planner_backend_calls": 0,
        "deployment": args.deployment,
        "base_url": args.base_url,
        "model": args.model,
        "runtime_hard_limit": args.runtime_hard_limit,
        "reserved_output_tokens": args.reserved_output_tokens,
        "rows": rows,
        "largest_tested_success": max(successful) if successful else None,
        "first_failure": failures[0]["context_window"] if failures else None,
        "failure_type": failures[0].get("failure_type") if failures else None,
        "recommended_context_window": max(successful) if successful else None,
        "ttft_note": "unavailable from the existing non-streaming formal backend telemetry",
        "peak_memory_note": "unavailable from the existing formal backend telemetry",
    }
    _write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


async def probe_ttft(args: argparse.Namespace) -> None:
    context_window = args.context_window
    input_bytes = context_window - args.reserved_output_tokens
    request = ModelRequest(
        prompt=_payload(input_bytes),
        max_output_tokens=args.reserved_output_tokens,
    )
    estimated = preflight_model_request(
        request,
        modalities=frozenset({"text", "image"}),
        context_window=context_window,
        reserved_output_tokens=args.reserved_output_tokens,
        image_token_cost=2048,
    )
    client = AsyncOpenAI(api_key="ollama-local-calibration", base_url=args.base_url)
    started = perf_counter()
    first_content_at: float | None = None
    output_parts: list[str] = []
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    try:
        stream = await client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=args.reserved_output_tokens,
            reasoning_effort="none",
            temperature=0,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.usage is not None:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens
            for choice in chunk.choices:
                if choice.finish_reason is not None:
                    finish_reason = choice.finish_reason
                content = choice.delta.content
                if content:
                    if first_content_at is None:
                        first_content_at = perf_counter()
                    output_parts.append(content)
    finally:
        await client.close()
    finished = perf_counter()
    output = "".join(output_parts)
    result = {
        "planner_backend_calls": 0,
        "deployment": args.deployment,
        "context_window": context_window,
        "input_bytes": input_bytes,
        "preflight_estimated_input": estimated,
        "reserved_output_tokens": args.reserved_output_tokens,
        "ttft_ms": (first_content_at - started) * 1000
        if first_content_at is not None
        else None,
        "total_latency_ms": (finished - started) * 1000,
        "backend_input_tokens": input_tokens,
        "backend_output_tokens": output_tokens,
        "finish_reason": finish_reason,
        "output_nonempty": bool(output.strip()),
        "output_preview": output[:160],
    }
    _write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    diagnosis = commands.add_parser("diagnose")
    diagnosis.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    diagnosis.add_argument("--attempt", type=Path, required=True)
    diagnosis.add_argument("--multihop-corpus", type=Path, required=True)
    diagnosis.add_argument("--multihop-queries", type=Path, required=True)
    diagnosis.add_argument("--action-id", default="analyze-sorcerer")
    diagnosis.add_argument("--output", type=Path, required=True)
    calibration = commands.add_parser("calibrate")
    calibration.add_argument("--deployment", required=True)
    calibration.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    calibration.add_argument("--model", default="qwen3.8-27b-v1")
    calibration.add_argument(
        "--context-sizes",
        nargs="+",
        type=int,
        default=(16384, 20480, 24576, 28672, 32768, 40960, 49152),
    )
    calibration.add_argument("--runtime-hard-limit", type=int, required=True)
    calibration.add_argument("--reserved-output-tokens", type=int, default=1024)
    calibration.add_argument("--output", type=Path, required=True)
    ttft = commands.add_parser("ttft-probe")
    ttft.add_argument("--deployment", required=True)
    ttft.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    ttft.add_argument("--model", default="qwen3.8-27b-v1")
    ttft.add_argument("--context-window", type=int, default=16384)
    ttft.add_argument("--reserved-output-tokens", type=int, default=1024)
    ttft.add_argument("--output", type=Path, required=True)
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "diagnose":
        diagnose(args)
    elif args.command == "calibrate":
        asyncio.run(calibrate(args))
    else:
        asyncio.run(probe_ttft(args))


if __name__ == "__main__":
    main()
