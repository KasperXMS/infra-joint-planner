"""Remote-only, bounded context/Gate 1 validation. Never dispatches benchmarks."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from openai import AsyncOpenAI

from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.verification import OpenAIAgentsBlindVerifier
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.evaluation.trace import JsonlTraceWriter
from infra_joint.experiments.manager_context import (
    ManagerContextConfig,
    ManagerContextLimitExceeded,
    OllamaManagerContextPreflight,
    truncation_events,
)
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.workflow.trace import WorkflowTraceRecorder

try:
    from lightweight_planner_compatibility_v1 import SyntheticGateway
    from lightweight_planner_roles_v1 import role_isolated_sdk
except ModuleNotFoundError:
    from scripts.lightweight_planner_compatibility_v1 import SyntheticGateway
    from scripts.lightweight_planner_roles_v1 import role_isolated_sdk


ROOT = Path("/home/super/xiaoming/lightweight-planner-competence-v1")
SKILLS_SHA = "d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422"
JOURNAL_SHA = "e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9"
CONFIG = ManagerContextConfig(
    model="qwen-vl8b-resident-32k-v1",
    digest="8af2c13de2205715e2088787387b9a7d29d63f4c628a270ea66d56c41a7c4936",
    model_blob="sha256-1329cd5ab37e5ef6faef37cd8ff8660ffc96ed5b47b34fddf8eb0912e6c82466",
    template_sha256="b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315",
    ollama_url="http://127.0.0.1:11437",
    runner_url="http://127.0.0.1:43715",
)


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def task() -> TaskContract:
    return TaskContract(
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


INSTRUCTIONS = (
    "Complete this synthetic tool protocol test. "
    "First use read_artifact on synthetic-source. Inspect typed failures and "
    "retry the read once if not ready. Then invoke_model on synthetic-source "
    "and return its successful text. No delegation is needed for this test."
)


def capacity_wire(target: int, filler: int, tools: list[Any]) -> tuple[dict, dict]:
    key = hashlib.sha256(str(target).encode()).hexdigest()[:8]
    expected = {"head": f"HEAD_{key}", "middle": f"MIDDLE_{key}", "tail": f"TAIL_{key}"}
    data = (
        f"HEAD_SENTINEL={expected['head']}\n"
        + " x" * (filler // 2)
        + f"\nMIDDLE_SENTINEL={expected['middle']}\n"
        + " x" * (filler - filler // 2)
        + f"\nTAIL_SENTINEL={expected['tail']}\n"
    )
    return {
        "model": CONFIG.model,
        "max_tokens": 2048,
        "parallel_tool_calls": True,
        "messages": [
            {
                "role": "system",
                "content": "This is a synthetic context integrity test. "
                "Read the HEAD_SENTINEL, MIDDLE_SENTINEL, and TAIL_SENTINEL values in the data. "
                "Return only a JSON object with keys head, middle, tail and their exact values. "
                "Do not call tools. The repeated x text is padding.",
            },
            {"role": "user", "content": data},
        ],
        "tools": tools,
    }, expected


async def calibrated_wire(target: int, tools: list, guard: Any) -> tuple[dict, dict, dict]:
    filler = target - 3000
    for _ in range(3):  # Token-count calibration only, zero generation or semantic tuning.
        wire, expected = capacity_wire(target, filler, tools)
        receipt = await guard.inspect(wire)
        delta = target - receipt["prompt_tokens"]
        if delta == 0:
            return wire, expected, receipt
        filler += delta
        if filler < 0:
            break
    raise RuntimeError("synthetic length could not be calibrated within three count-only calls")


async def sdk_smoke(sdk: Any, client: AsyncOpenAI, out: Path) -> dict:
    local = sdk.OpenAIChatCompletionsModel(model=CONFIG.model, openai_client=client)
    cloud_attempts = []

    def block_cloud(request: httpx.Request) -> httpx.Response:
        cloud_attempts.append(request.url.path)
        raise RuntimeError("compatibility smoke cannot issue cloud requests")

    async with httpx.AsyncClient(transport=httpx.MockTransport(block_cloud)) as cloud_http:  # noqa: SIM117
        async with AsyncOpenAI(
            base_url="https://llm-6tbxas81ayf65rd1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            api_key="unused-blocked-transport",
            max_retries=0,
            http_client=cloud_http,
        ) as cloud:
            strong = sdk.OpenAIChatCompletionsModel(model="qwen3.8-max", openai_client=cloud)
            roles = role_isolated_sdk(
                sdk,
                manager_model=local,
                specialist_model=strong,
                manager_model_id=CONFIG.model,
                specialist_model_id="qwen3.8-max",
            )
            constructed = {}

            def construct(**kwargs: Any) -> object:
                if kwargs["name"] == "manager":
                    kwargs["model_settings"] = replace(kwargs["model_settings"], max_tokens=2048)
                agent = roles.Agent(**kwargs)
                constructed[kwargs["name"]] = agent
                return agent

            facade = SimpleNamespace(**{**sdk.__dict__, "Agent": construct})
            # Original fixed strong Verifier is constructed separately, not substituted.
            verifier = OpenAIAgentsBlindVerifier(model=strong, sdk_module=sdk)
            registry, gateway = build_operator_catalog(), SyntheticGateway()
            runtime = OpenAIAgentsNativeRuntime(
                name="manager",
                instructions=INSTRUCTIONS,
                model=local,
                registry=registry,
                available_operations=tuple(registry),
                sdk_module=facade,
                record_input_provenance=True,
            )
            result = await runtime.run(
                task(),
                gateway,
                budget=AgentLoopBudget(
                    max_manager_turns=6,
                    max_subagent_turns=2,
                    max_tool_model_calls=6,
                    max_created_subagents=1,
                    max_active_subagents=1,
                ),
                trace=WorkflowTraceRecorder(
                    "context-gate-sdk", JsonlTraceWriter(out / "trace.jsonl")
                ),
            )
            write_new(out / "native-result.json", result.model_dump(mode="json"))
            isolation = bool(
                constructed["manager"].model is local
                and constructed["bounded_specialist"].model is strong
                and constructed["bounded_specialist"].model_settings.max_tokens is None
                and verifier._agent.model is strong
                and verifier._agent.model_settings.temperature == 0
                and verifier._agent.model_settings.tool_choice == "required"
                and not cloud_attempts
            )
            return {
                "native_protocol_passed": result.final_answer == "A"
                and gateway.read_failed
                and "invoke_model" in gateway.calls
                and result.usage.manager_turns >= 3,
                "original_strict_read_retry_passed": gateway.calls.count("read_artifact") >= 2,
                "gateway_calls": gateway.calls,
                "usage": result.usage.model_dump(mode="json"),
                "final_answer": result.final_answer,
                "role_isolation_passed": isolation,
                "specialist_model": "qwen3.8-max",
                "verifier_model": "qwen3.8-max",
                "cloud_transport_attempts": len(cloud_attempts),
                "scope": "strong roles constructed with exact settings; not invoked",
            }


async def sdk_parallel(sdk: Any, out: Path) -> dict:
    """Real SDK with scripted HTTP responses; no extra model generation."""

    class BarrierGateway(SyntheticGateway):
        active = 0
        peak = 0

        def __init__(self):
            super().__init__()
            self.ready = asyncio.Event()

        async def execute_batch(self, actions: tuple, *, expose_profile: bool) -> tuple:
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.active == 2:
                self.ready.set()
            await asyncio.wait_for(self.ready.wait(), timeout=5)
            try:
                return await super().execute_batch(actions, expose_profile=expose_profile)
            finally:
                self.active -= 1

    calls = []

    def scripted(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        msg: dict[str, Any] = {"role": "assistant", "content": "A"}
        reason = "stop"
        if len(calls) == 1:
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"parallel-{i}",
                        "type": "function",
                        "function": {
                            "name": "invoke_model",
                            "arguments": json.dumps(
                                {
                                    "inputs": ["synthetic-source"],
                                    "arguments": {"prompt": "Return A"},
                                }
                            ),
                        },
                    }
                    for i in range(2)
                ],
            }
            reason = "tool_calls"
        return httpx.Response(
            200,
            json={
                "id": f"mock-{len(calls)}",
                "object": "chat.completion",
                "created": 0,
                "model": CONFIG.model,
                "choices": [{"index": 0, "message": msg, "finish_reason": reason}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(scripted)) as http,
        AsyncOpenAI(
            base_url="http://scripted/v1", api_key="unused", http_client=http, max_retries=0
        ) as client,
    ):
        model = sdk.OpenAIChatCompletionsModel(model=CONFIG.model, openai_client=client)
        registry, gateway = build_operator_catalog(), BarrierGateway()
        runtime = OpenAIAgentsNativeRuntime(
            name="manager",
            instructions=INSTRUCTIONS,
            model=model,
            registry=registry,
            available_operations=tuple(registry),
            sdk_module=sdk,
        )
        result = await runtime.run(task(), gateway)
    receipt = {
        "passed": gateway.peak == 2 and result.final_answer == "A",
        "peak_concurrent_actions": gateway.peak,
        "scripted_http_requests": len(calls),
        "live_model_requests": 0,
        "gateway_calls": gateway.calls,
    }
    write_new(out / "sdk-parallel.json", receipt)
    return receipt


async def run(args: argparse.Namespace) -> dict:
    if sys.platform != "linux" or args.output.resolve().parent != ROOT / "context-repair-001":
        raise RuntimeError("Gate 1 evidence must remain in its new controller namespace")
    args.output.mkdir(exist_ok=False)
    out = args.output
    log = Path(
        "/home/super/xiaoming/resident-model-pool-v1/services/start-004/"
        "resident-4090-gpu1-vl8b-v1-server.log"
    )
    journal = Path(
        "/home/super/xiaoming/large-scale-cost-guidance-resident-v1/phase2-attempts.jsonl"
    )
    assert hashlib.sha256(journal.read_bytes()).hexdigest() == JOURNAL_SHA
    assert hashlib.sha256(args.skills.read_bytes()).hexdigest() == SKILLS_SHA
    log_offset = log.stat().st_size
    write_new(
        out / "protocol.json",
        {
            "version": "manager-context-gate-1-v2",
            "config": asdict(CONFIG),
            "targets_total_prompt_tokens": [8192, 16384, 24576, 30720, 30721, 42272],
            "reserved_output_tokens": 2048,
            "accepted_inference_max": 6,
            "sdk_inference_request_max": 8,
            "helper_request_max": 512,
            "deadline_seconds": 1800,
            "per_inference_timeout_seconds": 180,
            "acceptance": "four exact context tiers preserve rendered markers, provider count, "
            "sentinel echoes and no truncation; paired legal wire unchanged; both overflows reject "
            "before inference; SDK native schema/typed failure/multiturn/terminal; role isolation; "
            "real SDK scripted concurrency. Exact reread is an optional diagnostic.",
            "formal_cells_allowed": 0,
            "phase2_resume_allowed": False,
            "skills_sha256": SKILLS_SHA,
            "journal_sha256": JOURNAL_SHA,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    sdk = importlib.import_module("agents")
    sdk.set_tracing_disabled(True)
    requests, responses, capacity = [], [], []
    raw_schema_checks = []
    clocks = {}
    phase = "context"
    baseline = None
    native = None
    parallel = None
    error = None
    guard = None

    async def helper_quota(request: httpx.Request) -> None:
        nonlocal helper_count
        helper_count += 1
        if helper_count > 512:
            raise RuntimeError("context helper request quota exhausted")

    async def capture_request(request: httpx.Request) -> None:
        if len(requests) >= 14 or sum(r["phase"] == "sdk" for r in requests) >= 8:
            raise RuntimeError("synthetic inference quota exhausted")
        raw = await request.aread()
        requests.append({"phase": phase, "sha256": hashlib.sha256(raw).hexdigest()})
        clocks[id(request)] = perf_counter()
        (out / f"request-{len(requests):02d}.json").open("xb").write(raw)

    async def capture_response(response: httpx.Response) -> None:
        raw = await response.aread()
        if phase == "sdk" and response.status_code == 200:
            wire = json.loads(response.request.content)
            schemas = {t["function"]["name"]: t["function"]["parameters"] for t in wire["tools"]}
            for call in response.json()["choices"][0]["message"].get("tool_calls", []):
                name = call["function"]["name"]
                arguments = json.loads(call["function"]["arguments"])
                errors = [
                    e.message for e in Draft202012Validator(schemas[name]).iter_errors(arguments)
                ]
                raw_schema_checks.append({"tool": name, "valid": not errors, "errors": errors})
        responses.append(
            {
                "phase": phase,
                "status": response.status_code,
                "usage": response.json().get("usage"),
                "latency_ms": (perf_counter() - clocks[id(response.request)]) * 1000,
            }
        )
        (out / f"response-{len(responses):02d}.json").open("xb").write(raw)

    helper_count = 0
    try:
        async with httpx.AsyncClient(event_hooks={"request": [helper_quota]}) as helper:
            guard = OllamaManagerContextPreflight(CONFIG, helper)
            async with httpx.AsyncClient(
                timeout=180,
                event_hooks={
                    "request": [guard.request_hook, capture_request],
                    "response": [capture_response, guard.response_hook],
                },
            ) as http:
                tools = json.loads((ROOT / "gate-002/request-01.json").read_text())["tools"]
                for target in (8192, 16384, 24576, 30720, 30721, 42272):
                    wire, expected, count = await calibrated_wire(target, tools, guard)
                    raw = json.dumps(wire, ensure_ascii=False).encode()
                    write_new(out / f"capacity-{target}-request.json", wire)
                    if target == 8192:
                        async with httpx.AsyncClient(
                            timeout=180,
                            event_hooks={
                                "request": [capture_request],
                                "response": [capture_response],
                            },
                        ) as original:
                            res = await original.post(
                                CONFIG.ollama_url + "/v1/chat/completions",
                                content=raw,
                                headers={"Content-Type": "application/json"},
                            )
                            res.raise_for_status()
                            baseline = {
                                "wire_sha256": hashlib.sha256(raw).hexdigest(),
                                "prompt_tokens": res.json()["usage"]["prompt_tokens"],
                            }
                    before = len(requests)
                    try:
                        res = await http.post(
                            CONFIG.ollama_url + "/v1/chat/completions",
                            content=raw,
                            headers={"Content-Type": "application/json"},
                        )
                        res.raise_for_status()
                        content = res.json()["choices"][0]["message"]["content"]
                        echoed = json.loads(
                            content.strip().removeprefix("```json").removesuffix("```").strip()
                        )
                        capacity.append(
                            {
                                "target": target,
                                "preflight": count,
                                "provider_prompt_tokens": res.json()["usage"]["prompt_tokens"],
                                "echo_correct": echoed == expected,
                                "inference_requests": 1,
                                "wire_sha256": hashlib.sha256(raw).hexdigest(),
                                "passed": target <= 30720 and echoed == expected,
                            }
                        )
                    except ManagerContextLimitExceeded as exc:
                        capacity.append(
                            {
                                "target": target,
                                "preflight": count,
                                "error_code": exc.code,
                                "inference_requests": len(requests) - before,
                                "passed": target > 30720 and len(requests) == before,
                            }
                        )
                phase = "sdk"
                async with AsyncOpenAI(
                    base_url=CONFIG.ollama_url + "/v1",
                    api_key="ollama",
                    max_retries=0,
                    timeout=180,
                    http_client=http,
                ) as client:
                    native = await asyncio.wait_for(sdk_smoke(sdk, client, out), timeout=600)
            parallel = await sdk_parallel(sdk, out)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)[:2000]}
    finally:
        with log.open("rb") as stream:
            stream.seek(log_offset)
            delta = stream.read()
        (out / "server-log-delta.txt").open("xb").write(delta)
        warnings = truncation_events(delta.decode(errors="replace"))
        paired = bool(
            baseline
            and capacity
            and baseline["wire_sha256"] == capacity[0].get("wire_sha256")
            and baseline["prompt_tokens"] == capacity[0].get("provider_prompt_tokens")
        )
        passed = bool(
            not error
            and len(capacity) == 6
            and all(row["passed"] for row in capacity)
            and paired
            and not warnings
            and native
            and native["native_protocol_passed"]
            and native["role_isolation_passed"]
            and raw_schema_checks
            and all(row["valid"] for row in raw_schema_checks)
            and parallel
            and parallel["passed"]
            and hashlib.sha256(journal.read_bytes()).hexdigest() == JOURNAL_SHA
            and hashlib.sha256(args.skills.read_bytes()).hexdigest() == SKILLS_SHA
        )
        receipt = {
            "version": "manager-context-gate-1-v2",
            "ended_utc": datetime.now(UTC).isoformat(),
            "gate1_passed": passed,
            "error": error,
            "capacity": capacity,
            "paired_wire_passed": paired,
            "native_smoke": native,
            "raw_schema_checks": raw_schema_checks,
            "sdk_parallel": parallel,
            "truncation_warnings": warnings,
            "manager_inference_requests": len(requests),
            "helper_requests": helper_count,
            "provider_responses": responses,
            "preflight_receipts": guard.receipts if guard else [],
            "server_log_delta_sha256": hashlib.sha256(delta).hexdigest(),
            "formal_execution_allowed": False,
            "formal_cells": 0,
            "cloud_requests": 0,
            "historical_phase2_resumed": False,
            "skills_sha256": SKILLS_SHA,
            "journal_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
        }
        write_new(out / "receipt.json", receipt)
    print(
        json.dumps(
            {
                k: v
                for k, v in receipt.items()
                if k not in {"preflight_receipts", "provider_responses"}
            }
        )
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skills", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(run(args), timeout=1800))


if __name__ == "__main__":
    main()
