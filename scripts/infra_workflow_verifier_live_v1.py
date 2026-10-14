"""Request-level v2.1 Verifier validation using private contexts in place."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import agents
from jsonschema import Draft202012Validator
from openai import AsyncOpenAI

from infra_joint.control.native_agents import AgentLoopError, _deterministic_terminal_answer
from infra_joint.control.verification import (
    VerificationContext,
    VerificationResult,
    candidate_output_sha256,
)
from infra_joint.control.verifier_stabilization import BoundedProtocolVerifier

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Draft202012Validator(VerificationResult.model_json_schema())


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_key(path: Path) -> str:
    values = [
        line.split("=", 1)[1].strip().strip("\"'")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("DASHSCOPE_API_KEY=")
    ]
    if len(values) != 1 or not values[0]:
        raise RuntimeError("expected exactly one DASHSCOPE_API_KEY assignment")
    return values[0]


def context_for(historical_root: Path, cell_id: str) -> tuple[VerificationContext, str]:
    cell = historical_root / "stage2" / "cells" / cell_id
    runs = [item for item in (cell / "runs").iterdir() if item.is_dir()]
    if len(runs) != 1:
        raise RuntimeError(f"expected one historical run for {cell_id}")
    trace_path = runs[0] / "trace.jsonl"
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    inputs = [
        event["payload"]["context"]
        for event in trace
        if event["event_type"] == "logical.verification.input"
    ]
    if not inputs:
        raise RuntimeError(f"missing historical Verifier input for {cell_id}")
    source_context = inputs[-1]
    # Historical trace serialization used the public alias of OutputContract.schema.
    normalized = json.loads(json.dumps(source_context))
    contract = normalized["task"]["output_contract"]
    if "schema_definition" in contract:
        contract["schema"] = contract.pop("schema_definition")
    context = VerificationContext.model_validate(normalized)
    raw_sha = hashlib.sha256(
        json.dumps(inputs[-1], sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return context, raw_sha


def original_failure(historical_root: Path, cell_id: str) -> dict[str, Any]:
    cell = historical_root / "stage2" / "cells" / cell_id
    failures = [item for item in read(cell / "verifier-schema.json") if not item["valid"]]
    if len(failures) != 1:
        raise RuntimeError(f"expected one historical raw-schema failure for {cell_id}")
    return {"raw_schema_valid": False, "failure_count": len(failures)}


def usage_fields(usage: object) -> dict[str, int | None]:
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    details = getattr(usage, "input_tokens_details", None)
    cached = getattr(details, "cached_tokens", None)
    return {
        "input_tokens": input_tokens if isinstance(input_tokens, int) else None,
        "output_tokens": output_tokens if isinstance(output_tokens, int) else None,
        "cached_input_tokens": cached if isinstance(cached, int) else None,
    }


def list_price_usd(usage: dict[str, int | None]) -> dict[str, float] | None:
    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]
    cached = usage["cached_input_tokens"]
    if input_tokens is None or output_tokens is None:
        return None
    # Frozen 2026-10-05 non-batch CNY list card and 2026-10-02 FX snapshot.
    usd_per_cny = 1.1225 / 7.5259
    low = (input_tokens * 1.5 + output_tokens * 36) / 1_000_000 * usd_per_cny
    high = (input_tokens * 12 + output_tokens * 36) / 1_000_000 * usd_per_cny
    result = {"lower_usd": low, "upper_usd": high}
    if cached is not None and 0 <= cached <= input_tokens:
        result["with_reported_cache_usd"] = (
            ((input_tokens - cached) * 12 + cached * 1.5 + output_tokens * 36)
            / 1_000_000
            * usd_per_cny
        )
    return result


def raw_call_status(response: object) -> dict[str, Any]:
    calls = [
        item
        for item in getattr(response, "output", ())
        if getattr(item, "type", None) == "function_call"
    ]
    if len(calls) != 1:
        return {"tool_call_count": len(calls), "raw_schema_valid": False, "error": "call_count"}
    call = calls[0]
    if getattr(call, "name", None) != "submit_verification":
        return {"tool_call_count": 1, "raw_schema_valid": False, "error": "tool_name"}
    arguments = getattr(call, "arguments", None)
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else None
    except json.JSONDecodeError:
        parsed = None
    if parsed is None:
        return {"tool_call_count": 1, "raw_schema_valid": False, "error": "arguments_json"}
    errors = list(SCHEMA.iter_errors(parsed))
    semantic_valid = False
    if not errors:
        try:
            VerificationResult.model_validate(parsed)
            semantic_valid = True
        except ValueError:
            pass
    return {
        "tool_call_count": 1,
        "raw_schema_valid": not errors,
        "semantic_valid": semantic_valid,
        "error_paths": sorted({"/".join(map(str, item.absolute_path)) for item in errors}),
        "status": parsed.get("status") if isinstance(parsed, dict) else None,
    }


class AuditModel(agents.Model):
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.attempts: list[dict[str, Any]] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        started = time.monotonic()
        try:
            response = await self.delegate.get_response(*args, **kwargs)
        except Exception as exc:
            self.attempts.append(
                {"exception_type": type(exc).__name__, "latency_s": time.monotonic() - started}
            )
            raise
        usage = usage_fields(getattr(response, "usage", None))
        self.attempts.append(
            {
                **raw_call_status(response),
                "latency_s": time.monotonic() - started,
                "usage": usage,
                "list_price_usd": list_price_usd(usage),
            }
        )
        return response

    async def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise RuntimeError("streaming is not part of this frozen validation")


def binding_status(context: VerificationContext, verdict: VerificationResult) -> str:
    if verdict.status != "complete":
        return "not_applicable"
    action_id = verdict.candidate_action_id
    if action_id is None:
        return "missing_candidate_action"
    if not any(
        item.action_id == action_id
        and item.owner_agent_id == "manager"
        and item.action_type == "model"
        for item in context.actions
    ):
        return "candidate_action_not_manager_model"
    observation = next(
        (
            item
            for item in context.observations
            if item.action_id == action_id and item.owner_agent_id == "manager" and item.succeeded
        ),
        None,
    )
    if observation is None or not isinstance(observation.output.get("text"), str):
        return "candidate_observation_missing"
    raw_text = observation.output["text"]
    if not raw_text.strip():
        return "candidate_empty"
    if (
        verdict.evidence_state_version is not None
        and verdict.evidence_state_version != context.workflow.version
    ):
        return "evidence_version_mismatch"
    if (
        verdict.candidate_output_sha256 is not None
        and verdict.candidate_output_sha256 != candidate_output_sha256(raw_text)
    ):
        return "candidate_hash_mismatch"
    try:
        _deterministic_terminal_answer(context.task.output_contract, raw_text)
    except AgentLoopError:
        return "terminal_contract_invalid"
    return "valid"


async def run(args: argparse.Namespace) -> None:
    config = read(args.config)
    selected = tuple(config["cases"])
    if len(selected) != 8 or len(set(selected)) != 8:
        raise RuntimeError("frozen selection must contain eight unique cases")
    historical_root = Path(config["historical_root"])
    contexts = [(cell_id, *context_for(historical_root, cell_id)) for cell_id in selected]
    original = {cell_id: original_failure(historical_root, cell_id) for cell_id in selected}
    if args.preflight_only:
        print(json.dumps({"cases_preflighted": len(contexts), "provider_requests": 0}))
        return
    if args.output.exists():
        raise FileExistsError("new result namespace already exists")
    if args.key_file is None:
        raise RuntimeError("--key-file required for live mode")
    agents.set_tracing_disabled(True)
    api_key = load_key(args.key_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    async with AsyncOpenAI(
        base_url=config["base_url"], api_key=api_key, max_retries=0, timeout=180
    ) as client:
        for cell_id, context, context_sha in contexts:
            delegate = agents.OpenAIChatCompletionsModel(
                model=config["model"], openai_client=client
            )
            from sdk_native_infra_preliminary_v1_3 import ModelRequestBodyAdapter

            model = AuditModel(ModelRequestBodyAdapter(delegate, config["request_extra_body"]))
            verifier = BoundedProtocolVerifier(model=model, max_attempts=2)
            try:
                response = await verifier.verify(context)
                verdict = response.result
                outcome = {
                    "status": verdict.status,
                    "schema_valid": True,
                    "semantic_valid": True,
                    "binding_status": binding_status(context, verdict),
                }
            except Exception as exc:
                outcome = {
                    "exception_type": type(exc).__name__,
                    "schema_valid": False,
                    "semantic_valid": False,
                }
            rows.append(
                {
                    "cell_id": cell_id,
                    "historical": original[cell_id],
                    "context_sha256": context_sha,
                    "attempts": model.attempts,
                    "provider_attempts": len(model.attempts),
                    "outcome": outcome,
                }
            )
            # Append after each decision; private contexts and answers never leave the source tree.
            args.output.write_text(
                json.dumps(
                    {
                        "condition_id": config["condition_id"],
                        "source_commit": config["source_commit"],
                        "raw_content_exported": False,
                        "completed_cases": len(rows),
                        "rows": rows,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "completed_cases": len(rows),
                        "cell_id": cell_id,
                        "attempts": len(model.attempts),
                        "outcome": outcome,
                    }
                ),
                flush=True,
            )
    del api_key
    os.environ.pop("DASHSCOPE_API_KEY", None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    asyncio.run(run(parser.parse_args()))
