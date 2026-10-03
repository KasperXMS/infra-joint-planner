# pyright: reportPrivateUsage=false
"""Isolated SDK-native Ledger+Quote adapter; frozen semantic/physical base stays intact."""

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

from infra_joint.control.consequence import ActionConsequenceEstimator
from infra_joint.control.consequence_profiles import (
    CostHistory,
    EmpiricalConsequenceProfiles,
    NetworkCategory,
)
from infra_joint.control.contracts import (
    LogicalAgentSpec,
    ProfileVisibility,
    StaticCapabilityContract,
)
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.ledger_native import LedgerNativeRuntime
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError, AgentLoopResult
from infra_joint.control.method_usage import meter_agent
from infra_joint.control.native_agents import (
    OpenAIAgentsNativeRuntime,
    _logical_action,
    _logical_owner,
    _namespace_output_arguments,
    _NativeState,
    _validate_dynamic_output_contract,
    _with_schema_defaults,
    _with_terminal_output_requirement,
)
from infra_joint.control.physical import PhysicalExecutionService
from infra_joint.control.provenance import semantic_input_items
from infra_joint.control.quote import QuoteLedgerGateway, QuoteProtocolError, ReadyActionQuotes
from infra_joint.control.validation import SemanticValidationError
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorSpec
from infra_joint.workflow.trace import WorkflowTraceRecorder


@dataclass
class _OperatorHandler:
    runtime: "QuoteNativeRuntime"
    state: _NativeState
    spec: OperatorSpec

    async def __call__(self, context: object, input_json: str) -> str:
        owner = _logical_owner(context, self.state.root_agent.logical_agent_id)
        if owner != self.state.root_agent.logical_agent_id:
            return await OpenAIAgentsNativeRuntime._invoke_operator(
                self.runtime, self.state, context, self.spec, input_json,
            )
        return await self.runtime._propose(self.state, context, self.spec, input_json)


class QuoteNativeRuntime(LedgerNativeRuntime):
    def __init__(
        self, *, physical: PhysicalExecutionService | None = None, environment: EnvironmentSpec,
        cost_history: CostHistory, network_category: str,
        reachable_workers: frozenset[str], quote_ttl_seconds: float = 120,
        max_quote_proposals: int = 128, **kwargs: Any,
    ) -> None:
        if network_category not in {"fast", "moderate", "constrained", "unknown"}:
            raise ValueError("unknown quote network category")
        super().__init__(**kwargs)
        self._quote_physical = physical
        self._quote_environment = environment
        self._quote_history = cost_history
        self._quote_network_category = network_category
        self._quote_workers = reachable_workers
        self._quote_ttl_seconds = quote_ttl_seconds
        self._max_quote_proposals = max_quote_proposals

    async def run(
        self, task: TaskContract, gateway: ActionGateway, *,
        root_agent: LogicalAgentSpec | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        budget: AgentLoopBudget | None = None, trace: WorkflowTraceRecorder | None = None,
        static_capabilities: StaticCapabilityContract | None = None,
    ) -> AgentLoopResult:
        if profile_visibility != ProfileVisibility.BLIND or static_capabilities is None:
            raise ValueError("Quote variant requires semantic/static inputs without raw profiles")
        physical = self._quote_physical
        if physical is None:
            # Bind to the service the unchanged formal runner creates for this run.
            from infra_joint.control.gateway import RuntimeActionGateway

            if not isinstance(gateway, RuntimeActionGateway):
                raise ValueError("Quote runner requires its concrete physical gateway")
            physical = gateway._physical
        estimator = ActionConsequenceEstimator(
            environment=self._quote_environment, static_capabilities=static_capabilities,
            profiles=EmpiricalConsequenceProfiles(self._quote_history),
            network_category=cast(NetworkCategory, self._quote_network_category),
            reachable_workers=self._quote_workers,
        )

        def emit(kind: str, payload: dict[str, Any]) -> object:
            return trace.emit(kind, payload) if trace is not None else None

        quotes = ReadyActionQuotes(
            physical=physical, estimator=estimator, gateway=gateway,
            owner_agent_id=root_agent.logical_agent_id if root_agent is not None else "manager",
            emit=emit, quote_ttl_seconds=self._quote_ttl_seconds,
            max_proposals=self._max_quote_proposals,
        )
        emit("method.variant.start", {
            "variant": "ledger-quote-v0", "is_original_blind_baseline": False,
            "current_dynamic_profile_injected": False, "manager_only_cost_quotes": True,
            "quote_ttl_seconds": self._quote_ttl_seconds,
            "max_quote_proposals": self._max_quote_proposals,
            "verifier_runs_after_semantic_results_not_quote_only_batches": True,
        })
        try:
            return await OpenAIAgentsNativeRuntime.run(
                self, task, QuoteLedgerGateway(gateway, quotes), root_agent=root_agent,
                profile_visibility=profile_visibility, budget=budget, trace=trace,
                static_capabilities=static_capabilities,
            )
        finally:
            emit("logical.cost_quote.run.end", quotes.summary())

    @staticmethod
    def _predecision_run_config(sdk: object, state: _NativeState) -> object:
        config = cast(Any, LedgerNativeRuntime._predecision_run_config(sdk, state))
        original = config.call_model_input_filter

        async def filter_input(data: Any) -> object:
            model_data = await original(data)
            if (data.agent.name != state.root_agent.logical_agent_id
                    and _contains_quote(semantic_input_items(list(model_data.input)))):
                raise AgentLoopError("Blind recipient action-cost quote isolation violated")
            return model_data

        config.call_model_input_filter = filter_input
        return config

    def _function_tool(self, sdk: object, state: _NativeState, spec: OperatorSpec) -> object:
        tool = cast(Any, OpenAIAgentsNativeRuntime._function_tool(self, sdk, state, spec))
        tool.on_invoke_tool = _OperatorHandler(self, state, spec)
        return tool

    def _agent(
        self, sdk: object, *, name: str, instructions: str, tools: list[object],
        max_parallel: bool, tool_use_behavior: object | None = None,
    ) -> object:
        bindings = [handler for tool in tools if isinstance(
            handler := getattr(tool, "on_invoke_tool", None), _OperatorHandler)]
        if bindings and name == bindings[0].state.root_agent.logical_agent_id:
            state = bindings[0].state
            constructor = sdk.__dict__["FunctionTool"]
            replacements: list[object] = []
            for tool in tools:
                handler = getattr(tool, "on_invoke_tool", None)
                if isinstance(handler, _OperatorHandler):
                    original = cast(Any, tool)
                    replacements.append(constructor(
                        name=original.name,
                        description=original.description + " Manager protocol: this call proposes "
                        "the action and returns a cost quote without executing. Call commit_quote "
                        "with its quote_id to execute exactly this proposal, or discard_quote "
                        "and propose a revised action. Costs do not predict semantic correctness.",
                        params_json_schema=original.params_json_schema,
                        on_invoke_tool=handler, strict_json_schema=False,
                    ))
                else:
                    replacements.append(tool)
            for operation in ("commit_quote", "discard_quote"):
                async def control(context: object, arguments: str, op: str = operation) -> str:
                    return await self._quote_control(state, context, op, arguments)

                replacements.append(constructor(
                    name=operation,
                    description=("Execute exactly one previously quoted ready action. "
                                 "No new action arguments or physical placement are accepted."
                                 if operation == "commit_quote" else
                                 "Decline a pending quote without executing. Use normal tools "
                                 "to propose any revised semantic action."),
                    params_json_schema={"type": "object", "properties": {
                        "quote_id": {"type": "string"}}, "required": ["quote_id"],
                        "additionalProperties": False},
                    on_invoke_tool=control, strict_json_schema=False,
                ))
            tools = replacements
        result = OpenAIAgentsNativeRuntime._agent(
            self, sdk, name=name, instructions=instructions, tools=tools,
            max_parallel=max_parallel, tool_use_behavior=tool_use_behavior,
        )
        return meter_agent(result, bindings[0].state, name) if bindings else result

    async def _propose(
        self, state: _NativeState, context: object, spec: OperatorSpec, input_json: str,
    ) -> str:
        owner = _logical_owner(context, state.root_agent.logical_agent_id)
        call_id = str(getattr(context, "tool_call_id", "proposal"))
        identifier = f"{owner}:{call_id}"
        if state.phase == "synthesis" and spec.operator_id != "invoke_model":
            return self._quote_failure(state, identifier, "phase_restricted")
        if state.tool_model_calls >= state.budget.max_tool_model_calls:
            return self._quote_failure(state, identifier, "budget_exhausted")
        try:
            raw = json.loads(input_json)
            if not isinstance(raw, dict):
                raise ValueError("tool arguments must be an object")
            payload = cast(dict[str, Any], raw)
            inputs = tuple(str(item) for item in payload.get("inputs", []))
            arguments = _with_schema_defaults(spec.argument_schema, payload.get("arguments", {}))
            arguments = _namespace_output_arguments(state.artifact_namespace, spec.operator_id,
                                                    arguments)
            arguments = _with_terminal_output_requirement(state, owner, spec.operator_id, arguments)
            action = _logical_action(spec, identifier, owner, inputs, arguments, payload)
            _validate_dynamic_output_contract(state, action)
            if set(inputs) - state.accessible.get(owner, set()):
                return self._quote_failure(state, identifier, "artifact_not_materialized")
        except (ValueError, TypeError):
            return self._quote_failure(state, identifier, "semantic_validation_failed")
        try:
            gateway = self._quote_gateway(state)
            quote = await gateway.quotes.propose(action, payload_json=input_json,
                                                operator=spec.operator_id)
            return quote.model_dump_json()
        except QuoteProtocolError as exc:
            return self._quote_failure(state, identifier, exc.code)
        except SemanticValidationError:
            return self._quote_failure(state, identifier, "semantic_validation_failed")

    async def _quote_control(
        self, state: _NativeState, context: object, operation: str, input_json: str,
    ) -> str:
        owner = _logical_owner(context, state.root_agent.logical_agent_id)
        identifier = f"{owner}:{getattr(context, 'tool_call_id', operation)}"
        try:
            raw = json.loads(input_json)
            if not isinstance(raw, dict):
                raise QuoteProtocolError("invalid_quote_control_arguments")
            payload = cast(dict[str, Any], raw)
            if (set(payload) != {"quote_id"}
                    or not isinstance(payload["quote_id"], str)):
                raise QuoteProtocolError("invalid_quote_control_arguments")
        except (ValueError, TypeError):
            return self._quote_failure(state, identifier, "invalid_quote_control_arguments")
        try:
            quotes = self._quote_gateway(state).quotes
            if operation == "discard_quote":
                quotes.discard(payload["quote_id"], owner=owner)
                return json.dumps({"discarded": True, "quote_id": payload["quote_id"]})
            pending = await quotes.authorize(payload["quote_id"], owner=owner)
        except QuoteProtocolError as exc:
            return self._quote_failure(state, identifier, exc.code)
        except SemanticValidationError:
            return self._quote_failure(state, identifier, "semantic_validation_failed")
        original_call_id = pending.action.action_id.removeprefix(owner + ":")
        original_context = SimpleNamespace(tool_call_id=original_call_id,
                                           agent=SimpleNamespace(name=owner))
        # Unexpected execution/identity failures propagate as harness failures, not Agent rejection.
        return await OpenAIAgentsNativeRuntime._invoke_operator(
            self, state, original_context, self._registry.binding(pending.operator).spec,
            pending.payload_json,
        )

    @staticmethod
    def _quote_gateway(state: _NativeState) -> QuoteLedgerGateway:
        if not isinstance(state.gateway, QuoteLedgerGateway):
            raise RuntimeError("Quote runtime requires its per-run accounting gateway")
        return state.gateway

    @staticmethod
    def _quote_failure(state: _NativeState, identifier: str, code: str) -> str:
        result: dict[str, object] = {
            "action_id": identifier, "succeeded": False, "failure_code": code,
            "message": "Quote rejected this call; inspect the code and decide again.",
        }
        state.emit("logical.cost_quote.rejected", result)
        return json.dumps(result)

    def _manager_tool_use_behavior(self, sdk: object, state: _NativeState) -> object | None:
        base_behavior = cast(Any, OpenAIAgentsNativeRuntime._manager_tool_use_behavior(
            self, sdk, state))
        if base_behavior is None:
            return None
        seen = (state.graph.snapshot().version, len(state.subagent_results),
                len(state.observations))
        constructor = sdk.__dict__["ToolsToFinalOutputResult"]

        async def after_batch(context: object, results: list[object]) -> object:
            nonlocal seen
            current = (state.graph.snapshot().version, len(state.subagent_results),
                       len(state.observations))
            if current == seen:
                state.emit("logical.cost_quote.control_only_batch", {
                    "graph_version": current[0], "verifier_invoked": False,
                })
                return constructor(is_final_output=False, final_output=None)
            seen = current
            return await base_behavior(context, results)

        return after_batch


def _contains_quote(value: object) -> bool:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if {"quote_id", "action_sha256", "consequence"} <= mapping.keys():
            return True
        return any(_contains_quote(item) for item in mapping.values())
    if isinstance(value, list):
        return any(_contains_quote(item) for item in cast(list[object], value))
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, RecursionError):
            return False
        return _contains_quote(parsed) if not isinstance(parsed, str) else False
    return False
