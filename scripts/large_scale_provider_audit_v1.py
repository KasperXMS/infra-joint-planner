"""Non-benchmark native-tool compatibility probe; never starts Workers or tc."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import agents
import httpx
from openai import AsyncOpenAI
from run_predecision_matrix_v1 import write_new
from sdk_native_infra_preliminary_v1_3 import (
    ModelRequestBodyAdapter,
    _load_control_plane_key,
)

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import WorkflowGraphSnapshot
from infra_joint.control.verification import (
    OpenAIAgentsBlindVerifier,
    VerificationContext,
    VerifierBudgetView,
)
from infra_joint.core.task import OutputContract, OutputFormat

MODELS = ("deepseek-v4-pro", "qwen3.8-max")
BASE_URL = "https://llm-6tbxas81ayf65rd1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"


def synthetic_context() -> VerificationContext:
    return VerificationContext(
        task=AgentTaskView(task_id="synthetic-provider-compatibility", benchmark_id="synthetic",
                           objective="Return the integer seven.", artifacts=(),
                           output_contract=OutputContract(format=OutputFormat.SHORT_TEXT)),
        workflow=WorkflowGraphSnapshot(version=0, nodes=(), edges=()),
        actions=(), observations=(), produced_artifacts=(), phase="evidence_collection",
        remaining_budget=VerifierBudgetView(remaining_manager_turns=19,
                                            remaining_tool_model_calls=64,
                                            remaining_created_subagents=4,
                                            remaining_verifier_calls=19),
    )


def continuation_compatible(
    invocations: list[int], verdicts: list[str], final_output: str,
) -> bool:
    """Transport/schema continuation, not synthetic answer-format compliance."""
    return invocations == [7] and len(verdicts) == 1 and bool(final_output.strip())


def adjudicate_existing(output: Path) -> None:
    """Append a narrower compatibility finding without replaying or replacing evidence."""
    if (sys.platform != "linux"
            or output.resolve().parent != Path(
                "/home/super/xiaoming/large-scale-cost-guidance-v1/readiness")):
        raise RuntimeError("adjudication must stay in the new 4090 readiness namespace")
    failure = json.loads((output / "failure.json").read_text())
    outcomes = failure["outcomes"]
    requests = [json.loads(path.read_text()) for path in sorted(output.glob("request-*.json"))]
    responses = [json.loads(path.read_text())
                 for path in sorted(output.glob("response-*.json"))]
    usages = [json.loads(path.read_text()) for path in sorted(output.glob("usage-*.json"))]
    if (len(requests) != 3 or len(responses) != 3 or len(usages) != 3 or len(outcomes) != 1
            or [row["requested_model"] for row in usages]
            != ["deepseek-v4-pro", "qwen3.8-max", "deepseek-v4-pro"]
            or any(row["status"] != 200 for row in usages)):
        raise RuntimeError("original diagnostic is not the expected successful three-call chain")
    if (responses[0]["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
            != "record_integer"
            or responses[1]["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
            != "submit_verification"
            or not any(item["role"] == "tool" for item in requests[2]["messages"])):
        raise RuntimeError("native tool and fixed-Verifier continuation is not evidenced")
    outcome = outcomes[0]
    passed = continuation_compatible(outcome["tool_values"], outcome["verdicts"],
                                     outcome["final_output"])
    receipt = {"provider_compatibility_passed": passed, "formal_cells": 0,
               "synthetic_answer_format_valid": outcome["final_output"].strip() == "7",
               "original_failure_unchanged": True, "no_new_api_calls": True,
               "reason": "original gate conflated native continuation with toy answer format",
               "original_evidence_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in output.glob("*.json")}}
    write_new(output / "compatibility-adjudication-001.json", receipt)
    print(json.dumps({key: value for key, value in receipt.items()
                      if key != "original_evidence_sha256"}), flush=True)


async def probe(
    output: Path, api_key_file: Path, identifiers: tuple[str, ...] = MODELS,
) -> None:
    if (sys.platform != "linux"
            or output.parent != Path("/home/super/xiaoming/large-scale-cost-guidance-v1/readiness")
            or not output.name.startswith("provider-audit-")):
        raise RuntimeError("provider diagnostic evidence must stay in the new 4090 namespace")
    if not identifiers or any(identifier not in MODELS for identifier in identifiers):
        raise RuntimeError("diagnostic admits only the two requested exact model identifiers")
    output.mkdir(parents=True, exist_ok=False)
    agents.set_tracing_disabled(True)
    _load_control_plane_key(api_key_file, "DASHSCOPE_API_KEY")
    import os

    write_new(output / "attempt.json", {
        "diagnostic": "SDK native function tool + fixed Blind Qwen Verifier + continuation",
        "formal_cells": 0, "benchmark_payload": False, "tc": False, "workers": False,
        "planner_identifiers": identifiers, "verifier_identifier": "qwen3.8-max",
        "base_url": BASE_URL, "timeout_seconds": 180, "max_retries": 0,
        "enable_thinking": False, "source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
        "verifier_instruction_sha256": hashlib.sha256(
            OpenAIAgentsBlindVerifier.INSTRUCTIONS.encode()).hexdigest(),
        "synthetic_context": synthetic_context().model_dump(mode="json"),
    })
    receipts: list[dict[str, Any]] = []

    async def request_hook(request: httpx.Request) -> None:
        request.extensions["audit_started"] = perf_counter()
        request.extensions["audit_utc"] = datetime.now(UTC).isoformat()

    async def response_hook(response: httpx.Response) -> None:
        await response.aread()
        request = response.request
        try:
            payload = response.json()
        except ValueError:
            payload = None
        try:
            requested = json.loads(request.content)
        except ValueError:
            requested = {}
        index = len(receipts) + 1
        receipt = {
            "request_index": index, "started_utc": request.extensions.get("audit_utc"),
            "status": response.status_code,
            "latency_ms": (perf_counter() - request.extensions["audit_started"]) * 1000,
            "requested_model": requested.get("model"),
            "response_model": payload.get("model") if isinstance(payload, dict) else None,
            "usage": payload.get("usage") if isinstance(payload, dict) else None,
            "request_id": response.headers.get("x-request-id"),
        }
        receipts.append(receipt)
        # Only synthetic messages, not benchmark data; keys/headers are never persisted.
        write_new(output / f"request-{index:03}.json", requested)
        write_new(output / f"response-{index:03}.json", payload)
        write_new(output / f"usage-{index:03}.json", receipt)

    outcomes: list[dict[str, Any]] = []
    started = perf_counter()
    try:
        async with (
            httpx.AsyncClient(event_hooks={"request": [request_hook],
                                          "response": [response_hook]}) as http_client,
            AsyncOpenAI(base_url=BASE_URL, api_key=os.environ["DASHSCOPE_API_KEY"],
                        timeout=180, max_retries=0, http_client=http_client) as client,
        ):
            def model(identifier: str) -> ModelRequestBodyAdapter:
                return ModelRequestBodyAdapter(agents.OpenAIChatCompletionsModel(
                    model=identifier, openai_client=client), {"enable_thinking": False})

            fixed_verifier = OpenAIAgentsBlindVerifier(model=model("qwen3.8-max"))

            def recording_tool(
                invocations: list[int], verdicts: list[str],
            ) -> agents.FunctionTool:
                @agents.function_tool
                async def record_integer(value: int) -> str:
                    """Record the requested integer and exercise the fixed Blind Verifier."""
                    invocations.append(value)
                    response = await fixed_verifier.verify(synthetic_context())
                    verdicts.append(response.result.status)
                    return json.dumps({"recorded": value,
                                       "verification": response.result.model_dump(mode="json")})
                return record_integer

            for identifier in identifiers:
                invocations: list[int] = []
                verdicts: list[str] = []
                record_integer = recording_tool(invocations, verdicts)
                manager = agents.Agent(
                    name="synthetic_provider_manager",
                    instructions=("This is an API compatibility diagnostic, not a benchmark. "
                                  "Call record_integer exactly once with value 7. After its "
                                  "result returns, finish with exactly the recorded integer."),
                    model=model(identifier), tools=[record_integer],
                )
                result = await agents.Runner.run(manager, input="Perform the diagnostic.",
                                                 max_turns=4)
                passed = continuation_compatible(invocations, verdicts, str(result.final_output))
                outcomes.append({"planner": identifier, "verifier": "qwen3.8-max",
                                 "tool_values": invocations, "verdicts": verdicts,
                                 "native_tool_continuation_passed": passed,
                                 "exact_integer_format_valid":
                                     str(result.final_output).strip() == "7",
                                 "final_output": str(result.final_output)})
                if not passed:
                    raise RuntimeError("synthetic native-tool compatibility diagnostic failed")
        summary = {"passed": True, "formal_cells": 0, "outcomes": outcomes,
                   "http_requests": len(receipts), "usage_receipts": receipts,
                   "duration_ms": (perf_counter() - started) * 1000}
        write_new(output / "summary.json", summary)
        # No message bodies, credentials or reasoning text on the development PC.
        print(json.dumps({key: value for key, value in summary.items()
                          if key != "usage_receipts"}), flush=True)
    except BaseException as error:
        write_new(output / "failure.json", {
            "error_type": type(error).__name__, "formal_cells": 0,
            "outcomes": outcomes, "http_requests": len(receipts),
            "http_status": getattr(error, "status_code", None),
        })
        print(json.dumps({"passed": False, "error_type": type(error).__name__,
                          "formal_cells": 0, "http_requests": len(receipts)}), flush=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--adjudicate-existing", action="store_true")
    args = parser.parse_args()
    if args.adjudicate_existing:
        adjudicate_existing(args.output)
    else:
        asyncio.run(probe(args.output, args.api_key_file, tuple(args.models)))
