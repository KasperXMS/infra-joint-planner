"""Live, dataset-free compatibility smoke for the SDK-native logical adapter."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from openai import AsyncOpenAI

from infra_joint.control.contracts import LogicalModelAction, LogicalObservation
from infra_joint.control.loop import AgentLoopBudget
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.operators.catalog import build_operator_catalog


class ModelConstructor(Protocol):
    def __call__(self, **kwargs: Any) -> object: ...


class SmokeGateway:
    def __init__(self) -> None:
        self.call_count = 0

    def validate_batch(self, actions: tuple[LogicalModelAction, ...]) -> None:
        if len(actions) != 1:
            raise ValueError("smoke accepts one logical model action")
        if actions[0].inputs != ("source",):
            raise ValueError("smoke model action must consume source")

    async def execute_batch(
        self,
        actions: tuple[LogicalModelAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        self.validate_batch(actions)
        if expose_profile:
            raise ValueError("smoke must remain resource-blind")
        self.call_count += 1
        action = actions[0]
        state = InfrastructureState(
            agents=(),
            deployments=(),
            artifacts=(),
            links=(),
            observed_at=datetime.now(UTC),
        )
        return (
            PhysicalExecutionOutcome(
                observation=LogicalObservation(
                    action_id=action.action_id,
                    owner_agent_id=action.owner_agent_id,
                    succeeded=True,
                    output={"text": "A"},
                ),
                infrastructure_before=state,
                infrastructure_after=state,
            ),
        )

    async def profile_overview(self) -> None:
        raise AssertionError("Blind smoke must not request a physical profile")


def load_key(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("API key file is empty")
    return value


async def main_async(args: argparse.Namespace) -> None:
    key = load_key(args.api_key_file)
    os.environ["DEEPSEEK_API_KEY"] = key
    agents = importlib.import_module("agents")
    set_tracing_disabled = cast(
        Callable[[bool], None], agents.__dict__["set_tracing_disabled"]
    )
    model_constructor = cast(
        ModelConstructor, agents.__dict__["OpenAIChatCompletionsModel"]
    )
    set_tracing_disabled(True)
    model = model_constructor(
        model="deepseek-chat",
        openai_client=AsyncOpenAI(
            api_key=key,
            base_url="https://api.deepseek.com",
            timeout=180,
            max_retries=0,
        ),
    )
    task = TaskContract(
        task_id="native-sdk-adapter-smoke",
        benchmark_id="synthetic",
        objective="Use the source and return choice A.",
        artifacts=(
            ArtifactSpec(
                artifact_id="source",
                logical_type="synthetic evidence",
                media_type="text/plain",
                size_bytes=1,
                source_ref="private://synthetic",
            ),
        ),
        output_contract=OutputContract(
            format=OutputFormat.CHOICE,
            choices=("A", "B"),
        ),
        evaluator_id="private-synthetic-evaluator",
    )
    registry = build_operator_catalog()
    gateway = SmokeGateway()
    result = await OpenAIAgentsNativeRuntime(
        name="manager",
        instructions=(
            "Solve faithfully. Use invoke_model on source, then return exactly the successful "
            "model tool text."
        ),
        model=model,
        registry=registry,
        available_operations=("invoke_model",),
    ).run(
        task,
        gateway,  # type: ignore[arg-type]
        budget=AgentLoopBudget(
            max_manager_turns=4,
            max_subagent_turns=2,
            max_tool_model_calls=2,
            max_created_subagents=1,
            max_active_subagents=1,
        ),
    )
    if result.final_answer != "A" or gateway.call_count != 1:
        raise RuntimeError("SDK-native adapter smoke produced an unexpected result")
    print(
        json.dumps(
            {
                "final_answer": result.final_answer,
                "terminal_action_id": result.terminal_action_id,
                "tool_model_calls": result.usage.tool_model_calls,
                "manager_turns": result.usage.manager_turns,
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key-file", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
