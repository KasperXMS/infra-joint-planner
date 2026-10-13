# pyright: reportUnknownMemberType=false
"""Opt-in Harness v2.1 verifier boundary; frozen H1 behavior is unchanged."""

from __future__ import annotations

import importlib
import json
from typing import Any, cast

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from infra_joint.control.native_agents import (
    AgentLoopError,
    _deterministic_terminal_answer,  # pyright: ignore[reportPrivateUsage]
)
from infra_joint.control.verification import (
    BlindVerifier,
    VerificationContext,
    VerificationResponse,
    VerificationResult,
)


class TerminalContractVerifier:
    """Return synthesis feedback before the native runtime sees an unusable candidate.

    The underlying independent verifier still decides evidence sufficiency. This
    wrapper only applies the exact deterministic output-contract check that the
    runtime will apply when selecting a final answer.
    """

    def __init__(self, delegate: BlindVerifier) -> None:
        self.delegate = delegate

    async def verify(self, context: VerificationContext) -> VerificationResponse:
        response = await self.delegate.verify(context)
        verdict = response.result
        if verdict.status != "complete" or verdict.candidate_action_id is None:
            return response
        model_actions = {
            action.action_id
            for action in context.actions
            if action.action_type == "model" and action.owner_agent_id == "manager"
        }
        if verdict.candidate_action_id not in model_actions:
            return response
        observation = next(
            (
                item
                for item in context.observations
                if item.action_id == verdict.candidate_action_id
                and item.owner_agent_id == "manager"
                and item.succeeded
            ),
            None,
        )
        if observation is None or not isinstance(observation.output.get("text"), str):
            return response
        try:
            _deterministic_terminal_answer(context.task.output_contract, observation.output["text"])
        except AgentLoopError:
            return VerificationResponse(
                result=VerificationResult(
                    status="ready_for_synthesis",
                    failure_stage="none",
                    reason="Candidate fails the deterministic terminal output contract.",
                ),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
        return response


class BoundedProtocolVerifier:
    """Opt-in strict raw verdict validation with one bounded corrective SDK turn.

    A malformed tool call is returned to the independent Verifier as a typed
    protocol error. Valid verdicts stop immediately. This changes the number
    of allowed provider requests, so it must only be used by a new condition.
    """

    def __init__(
        self,
        *,
        model: object,
        max_attempts: int = 2,
        sdk_module: object | None = None,
    ) -> None:
        if max_attempts < 1 or max_attempts > 2:
            raise ValueError("Verifier protocol attempts must be one or two")
        sdk = sdk_module or importlib.import_module("agents")
        agent_constructor = sdk.__dict__["Agent"]
        tool_constructor = sdk.__dict__["FunctionTool"]
        settings_constructor = sdk.__dict__["ModelSettings"]
        result_constructor = sdk.__dict__["ToolsToFinalOutputResult"]
        schema = VerificationResult.model_json_schema()
        validator = Draft202012Validator(schema)

        async def submit_verification(_context: object, input_json: str) -> str:
            try:
                parsed = json.loads(input_json)
            except (ValueError, TypeError):
                return self._failure("schema_validation_failed", ("invalid_json",))
            errors = list(validator.iter_errors(parsed))
            if errors:
                paths = tuple(sorted({"/".join(map(str, item.absolute_path)) for item in errors}))
                return self._failure("schema_validation_failed", paths)
            try:
                verdict = VerificationResult.model_validate(parsed)
            except ValidationError as exc:
                paths = tuple(sorted({"/".join(map(str, item["loc"])) for item in exc.errors()}))
                return self._failure("semantic_validation_failed", paths)
            return verdict.model_dump_json()

        async def after_tool(_context: object, results: list[object]) -> object:
            if not results:
                return result_constructor(is_final_output=False, final_output=None)
            output = getattr(results[-1], "output", None)
            if isinstance(output, str):
                try:
                    parsed = json.loads(output)
                    if isinstance(parsed, dict) and parsed.get("succeeded") is False:
                        return result_constructor(is_final_output=False, final_output=None)
                    VerificationResult.model_validate(parsed)
                except (ValueError, TypeError, ValidationError):
                    return result_constructor(is_final_output=False, final_output=None)
                return result_constructor(is_final_output=True, final_output=output)
            return result_constructor(is_final_output=False, final_output=None)

        tool = tool_constructor(
            name="submit_verification",
            description=(
                "Submit exactly one resource-blind semantic evidence-sufficiency verdict. "
                "This tool records a verdict; it does not execute task actions or produce "
                "the benchmark answer."
            ),
            params_json_schema=schema,
            on_invoke_tool=submit_verification,
            strict_json_schema=False,
        )
        self._agent = agent_constructor(
            name="blind_evidence_verifier",
            instructions=self._instructions(),
            model=model,
            tools=[tool],
            tool_use_behavior=after_tool,
            model_settings=settings_constructor(
                temperature=0,
                parallel_tool_calls=False,
                tool_choice="required",
            ),
        )
        self._runner = sdk.__dict__["Runner"]
        self.max_attempts = max_attempts

    @staticmethod
    def _instructions() -> str:
        from infra_joint.control.verification import OpenAIAgentsBlindVerifier

        return OpenAIAgentsBlindVerifier.INSTRUCTIONS

    @staticmethod
    def _failure(code: str, paths: tuple[str, ...]) -> str:
        return json.dumps(
            {"succeeded": False, "failure_code": code, "invalid_fields": paths},
            sort_keys=True,
        )

    async def verify(self, context: VerificationContext) -> VerificationResponse:
        result = await self._runner.run(
            self._agent,
            input=context.model_dump_json(),
            max_turns=self.max_attempts,
        )
        raw = getattr(result, "final_output", None)
        if isinstance(raw, VerificationResult):
            verdict = raw
        elif isinstance(raw, str):
            verdict = VerificationResult.model_validate_json(raw)
        else:
            verdict = VerificationResult.model_validate(cast(Any, raw))
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
        return VerificationResponse(
            result=verdict,
            input_tokens=int(getattr(usage, "input_tokens", 0)),
            output_tokens=int(getattr(usage, "output_tokens", 0)),
        )
