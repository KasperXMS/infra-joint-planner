"""Bounded synthetic SDK-native compatibility gate; never a benchmark runner."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import httpx
from openai import AsyncOpenAI

from infra_joint.control.contracts import LogicalObservation
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog


class SyntheticGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.read_failed = False

    def validate_batch(self, actions: tuple[Any, ...]) -> None:
        for action in actions:
            if action.inputs != ("synthetic-source",):
                raise ValueError("synthetic gate accepts only its synthetic source")

    async def execute_batch(self, actions: tuple[Any, ...], *, expose_profile: bool) -> tuple:
        self.validate_batch(actions)
        if expose_profile:
            raise AssertionError("synthetic gate is Blind")
        results = []
        for action in actions:
            operator = getattr(action, "operator", "invoke_model")
            self.calls.append(operator)
            failure = operator == "read_artifact" and not self.read_failed
            if failure:
                self.read_failed = True
            state = InfrastructureState(
                agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now(UTC)
            )
            results.append(
                PhysicalExecutionOutcome(
                    observation=LogicalObservation(
                        action_id=action.action_id,
                        owner_agent_id=action.owner_agent_id,
                        succeeded=not failure,
                        output={} if failure else {"text": "A"},
                        failure_code="artifact_not_materialized" if failure else None,
                        failure_message="Synthetic transient readiness failure"
                        if failure
                        else None,
                    ),
                    infrastructure_before=state,
                    infrastructure_after=state,
                )
            )
        return tuple(results)

    async def profile_overview(self) -> None:
        raise AssertionError("Blind synthetic gate must not request infrastructure")


async def run_gate(args: argparse.Namespace) -> dict:
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat()
    source = Path(__file__).read_bytes()
    requests = []
    responses = []
    latencies = []
    clocks = {}

    async def on_request(request: httpx.Request) -> None:
        if len(requests) >= 8:
            raise RuntimeError("synthetic gate HTTP request quota exhausted")
        raw = await request.aread()
        requests.append(json.loads(raw))
        clocks[id(request)] = perf_counter()
        (args.output / f"request-{len(requests):02d}.json").write_bytes(raw)

    async def on_response(response: httpx.Response) -> None:
        raw = await response.aread()
        responses.append({"status": response.status_code, "body": json.loads(raw)})
        latencies.append((perf_counter() - clocks[id(response.request)]) * 1000)
        (args.output / f"response-{len(responses):02d}.json").write_bytes(raw)

    sdk = importlib.import_module("agents")
    sdk.set_tracing_disabled(True)
    original_agent = sdk.Agent

    def agent(**kwargs: Any) -> object:
        # One declared output cap; no prompt/parameter search or semantic repair.
        kwargs["model_settings"] = replace(kwargs["model_settings"], max_tokens=2048)
        return original_agent(**kwargs)

    facade = SimpleNamespace(**{**sdk.__dict__, "Agent": agent})
    registry = build_operator_catalog()
    gateway = SyntheticGateway()
    result = None
    error = None
    try:
        async with httpx.AsyncClient(  # noqa: SIM117 - retain the audited first-run layout
            event_hooks={"request": [on_request], "response": [on_response]}
        ) as http:
            async with AsyncOpenAI(
                base_url=args.base_url,
                api_key="ollama",
                max_retries=0,
                timeout=180,
                http_client=http,
            ) as client:
                model = sdk.OpenAIChatCompletionsModel(model=args.model, openai_client=client)
                task = TaskContract(
                    task_id="lightweight-synthetic-native-gate-v1",
                    benchmark_id="synthetic",
                    objective="Read the synthetic source, recover if it is not ready, then use "
                    "invoke_model on that source and return its choice exactly.",
                    artifacts=(
                        ArtifactSpec(
                            artifact_id="synthetic-source",
                            logical_type="synthetic evidence",
                            media_type="text/plain",
                            size_bytes=1,
                            source_ref="private://synthetic-gate",
                        ),
                    ),
                    output_contract=OutputContract(format=OutputFormat.CHOICE, choices=("A", "B")),
                    evaluator_id="synthetic-not-a-benchmark",
                )
                runtime = OpenAIAgentsNativeRuntime(
                    name="manager",
                    instructions="Complete this synthetic tool protocol test. "
                    "First use read_artifact on synthetic-source. Inspect typed failures and "
                    "retry the read once if not ready. Then invoke_model on synthetic-source "
                    "and return its successful text. No delegation is needed for this test.",
                    model=model,
                    registry=registry,
                    available_operations=tuple(registry),
                    sdk_module=facade,
                    record_input_provenance=True,
                )
                result = await asyncio.wait_for(
                    runtime.run(
                        task,
                        gateway,
                        budget=AgentLoopBudget(
                            max_manager_turns=6,
                            max_subagent_turns=2,
                            max_tool_model_calls=6,
                            max_created_subagents=1,
                            max_active_subagents=1,
                        ),
                    ),
                    timeout=600,
                )
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)[:2000]}
    passed = bool(
        result
        and result.final_answer == "A"
        and gateway.read_failed
        and gateway.calls.count("read_artifact") >= 2
        and "invoke_model" in gateway.calls
    )
    record = {
        "version": "lightweight-native-compatibility-v1",
        "started_utc": started,
        "ended_utc": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "model": args.model,
        "base_url": args.base_url,
        "requests": len(requests),
        "request_cap": 8,
        "manager_turn_cap": 6,
        "output_cap": 2048,
        "timeout_seconds": 600,
        "benchmark_cells": 0,
        "cloud_requests": 0,
        "passed_native_smoke": passed,
        "gateway_calls": gateway.calls,
        "error": error,
        "request_latencies_ms": latencies,
        "provider_usage": [r["body"].get("usage") for r in responses],
        "http_statuses": [r["status"] for r in responses],
        "final_answer": result.final_answer if result else None,
        "context_full_envelope_validated": False,
        "parallel_call_execution_validated": False,
        "formal_gate_passed": False,
    }
    (args.output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run_gate(parser.parse_args()))


if __name__ == "__main__":
    main()
