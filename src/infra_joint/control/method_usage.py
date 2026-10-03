# pyright: reportPrivateUsage=false
"""Pass-through SDK model accounting shared by exploratory variants, not new reasoning."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from agents import Model

from infra_joint.control.ledger_native import LedgerNativeRuntime
from infra_joint.control.native_agents import _NativeState
from infra_joint.operators.registry import OperatorSpec


class MeasuredSDKModel(Model):
    def __init__(self, delegate: object, state: _NativeState, agent_name: str) -> None:
        self._delegate = cast(Any, delegate)
        self._state = state
        self._agent_name = agent_name

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        succeeded = False
        input_tokens: int | None = None
        output_tokens: int | None = None
        try:
            result = await self._delegate.get_response(*args, **kwargs)
            succeeded = True
            usage = getattr(result, "usage", None)
            if usage is not None:
                # SDK defaults absent provider usage to zero. Do not call those measured zeros.
                raw_input, raw_output = usage.input_tokens, usage.output_tokens
                input_tokens = raw_input if raw_input > 0 else None
                output_tokens = raw_output if raw_output > 0 else None
            return result
        finally:
            is_manager = self._agent_name == self._state.root_agent.logical_agent_id
            self._state.emit("logical.method.reasoning_usage", {
                "agent_name": self._agent_name,
                "recipient": "manager" if is_manager else "specialist",
                "succeeded": succeeded, "latency_ms": (perf_counter() - started) * 1000,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "unknown_sdk_zero_usage_is_measured_zero": False,
            })

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        # Frozen experiments are non-streaming; do not silently add an unmetered path.
        del args, kwargs
        raise RuntimeError("experimental usage meter requires the frozen non-streaming SDK path")
        yield  # pragma: no cover


def meter_agent(agent: object, state: _NativeState, name: str) -> object:
    result = cast(Any, agent)
    result.model = MeasuredSDKModel(result.model, state, name)
    return result


@dataclass
class _UsageToolBinding:
    state: _NativeState
    delegate: Any

    async def __call__(self, context: object, arguments: str) -> str:
        return await self.delegate(context, arguments)


class MeasuredLedgerRuntime(LedgerNativeRuntime):
    """RouteA with identical tools/instructions plus accounting used by RouteC too."""

    def _function_tool(self, sdk: object, state: _NativeState, spec: OperatorSpec) -> object:
        tool = cast(Any, super()._function_tool(sdk, state, spec))
        tool.on_invoke_tool = _UsageToolBinding(state, tool.on_invoke_tool)
        return tool

    def _agent(
        self, sdk: object, *, name: str, instructions: str, tools: list[object],
        max_parallel: bool, tool_use_behavior: object | None = None,
    ) -> object:
        bindings = [handler for tool in tools if isinstance(
            handler := getattr(tool, "on_invoke_tool", None), _UsageToolBinding)]
        result = super()._agent(sdk, name=name, instructions=instructions, tools=tools,
                                max_parallel=max_parallel, tool_use_behavior=tool_use_behavior)
        return meter_agent(result, bindings[0].state, name) if bindings else result
