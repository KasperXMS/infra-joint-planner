# pyright: reportPrivateUsage=false
"""Separate B/D/E experiments over the frozen SDK loop and physical substrate."""

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

from infra_joint.control.consequence import ActionConsequenceEstimator
from infra_joint.control.consequence_profiles import EmpiricalConsequenceProfiles, NetworkCategory
from infra_joint.control.contracts import (
    LogicalAction,
    LogicalAgentSpec,
    ProfileVisibility,
    StaticCapabilityContract,
)
from infra_joint.control.gateway import ActionGateway, RuntimeActionGateway
from infra_joint.control.ledger_native import LedgerActionGateway
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError, AgentLoopResult
from infra_joint.control.method_usage import meter_agent
from infra_joint.control.native_agents import (
    OpenAIAgentsNativeRuntime,
    _logical_owner,
    _native_tool_schema,
    _NativeState,
)
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.provenance import semantic_input_items
from infra_joint.control.quote import QuoteLedgerGateway, ReadyActionQuotes
from infra_joint.control.quote_native import QuoteNativeRuntime, _OperatorHandler
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorSpec
from infra_joint.workflow.trace import WorkflowTraceRecorder

RULE_PREFIX = "Frozen trace-distilled cost heuristics (advisory, not task evidence): "


def semantic_fingerprint(action: LogicalAction) -> str:
    """Match optional forecasts only to identical semantic requests, not similar actions."""
    from infra_joint.control.provenance import provenance_sha256

    payload = action.model_dump(mode="json")
    payload.pop("action_id")
    return provenance_sha256(payload)


class ComparisonGateway(QuoteLedgerGateway):
    def __init__(self, delegate: ActionGateway, quotes: ReadyActionQuotes) -> None:
        super().__init__(delegate, quotes)
        self.comparison_groups: dict[str, list[str]] = {}
        self.selected_groups: set[str] = set()
        self.rules: dict[str, Any] | None = None


class OptionalCardGateway(ComparisonGateway):
    """B/E never require quoting/authorization and never constrain the physical resolver."""

    async def execute_batch(
        self, actions: tuple[LogicalAction, ...], *, expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        if expose_profile:
            raise ValueError("B/E do not expose raw profiles")
        outcomes = await LedgerActionGateway.execute_batch(self, actions, expose_profile=False)
        by_id = {outcome.observation.action_id: outcome for outcome in outcomes}
        for action in actions:
            outcome = by_id[action.action_id]
            matches = [p for p in self.quotes._quotes.values()
                       if p.status == "pending"
                       and self.quotes.clock() - p.created_at <= self.quotes.quote_ttl_seconds
                       and semantic_fingerprint(p.action) == semantic_fingerprint(action)]
            if matches:
                pending = matches[-1]
                pending.status = "observed_optional"
                self.quotes.emit("logical.cost_card.matched", {
                    "card_id": pending.quote.quote_id, "action_id": action.action_id,
                    "exact_semantic_fingerprint": semantic_fingerprint(action),
                })
                self.quotes.observe(pending, outcome)
        return outcomes


@dataclass
class _DirectHandler:
    runtime: "BDENativeRuntime"
    state: _NativeState
    spec: OperatorSpec

    async def __call__(self, context: object, arguments: str) -> str:
        return await OpenAIAgentsNativeRuntime._invoke_operator(
            self.runtime, self.state, context, self.spec, arguments,
        )


class BDENativeRuntime(QuoteNativeRuntime):
    """B optional cards; D bounded comparison; E B + independently frozen trace heuristics."""

    def __init__(self, *, route: str, rules: dict[str, Any] | None = None, **kwargs: Any) -> None:
        if route not in {"B", "D", "E"} or (route == "E") != (rules is not None):
            raise ValueError("B/D have no rules; E requires a frozen rule manifest")
        super().__init__(**kwargs)
        self.route = route
        self.rules = rules

    async def run(
        self, task: TaskContract, gateway: ActionGateway, *,
        root_agent: LogicalAgentSpec | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        budget: AgentLoopBudget | None = None, trace: WorkflowTraceRecorder | None = None,
        static_capabilities: StaticCapabilityContract | None = None,
    ) -> AgentLoopResult:
        if profile_visibility != ProfileVisibility.BLIND or static_capabilities is None:
            raise ValueError("B/D/E require semantic/static inputs without raw profiles")
        physical = self._quote_physical
        if physical is None:
            if not isinstance(gateway, RuntimeActionGateway):
                raise ValueError("BDE requires the existing physical gateway")
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
            physical=physical, estimator=estimator, gateway=gateway, emit=emit,
            owner_agent_id=root_agent.logical_agent_id if root_agent else "manager",
            quote_ttl_seconds=self._quote_ttl_seconds, max_proposals=self._max_quote_proposals,
        )
        wrapped = (ComparisonGateway(gateway, quotes) if self.route == "D"
                   else OptionalCardGateway(gateway, quotes))
        wrapped.rules = self.rules
        emit("method.variant.start", {
            "variant": f"route-{self.route.lower()}-v0",
            "current_dynamic_profile_injected": False,
            "manager_only_cost_feedback": True,
            "optional_cost_queries": self.route != "D",
            "maximum_comparison_candidates": 3 if self.route == "D" else None,
            "frozen_rules": self.rules,
            "is_original_blind_baseline": False,
        })
        try:
            return await OpenAIAgentsNativeRuntime.run(
                self, task, wrapped, root_agent=root_agent, profile_visibility=profile_visibility,
                budget=budget, trace=trace, static_capabilities=static_capabilities,
            )
        finally:
            emit("logical.cost_quote.run.end", {"route": self.route, **quotes.summary()})

    @staticmethod
    def _predecision_run_config(sdk: object, state: _NativeState) -> object:
        config = cast(Any, QuoteNativeRuntime._predecision_run_config(sdk, state))
        original = config.call_model_input_filter

        async def filter_input(data: Any) -> object:
            model_data = await original(data)
            items: list[Any] = list(model_data.input)
            if data.agent.name != state.root_agent.logical_agent_id:
                if contains_bde_feedback(semantic_input_items(items)):
                    raise AgentLoopError("Blind recipient BDE cost isolation violated")
            else:
                rules = cast(ComparisonGateway, state.gateway).rules
                if rules is None:
                    return model_data
                items = [i for i in items if not is_rule_message(i)]
                items.append({"role": "user", "content": RULE_PREFIX
                              + json.dumps(rules, sort_keys=True)})
                state.emit("logical.cost_rules.predecision", {"rules": rules,
                           "graph_version": state.graph.snapshot().version})
            return type(model_data)(input=items, instructions=model_data.instructions)

        config.call_model_input_filter = filter_input
        return config

    def _function_tool(self, sdk: object, state: _NativeState, spec: OperatorSpec) -> object:
        if self.route == "D":
            return super()._function_tool(sdk, state, spec)
        tool = cast(Any, OpenAIAgentsNativeRuntime._function_tool(self, sdk, state, spec))
        tool.on_invoke_tool = _DirectHandler(self, state, spec)
        return tool

    def _agent(
        self, sdk: object, *, name: str, instructions: str, tools: list[object],
        max_parallel: bool, tool_use_behavior: object | None = None,
    ) -> object:
        handlers = [h for tool in tools if isinstance(
            h := getattr(tool, "on_invoke_tool", None), (_DirectHandler, _OperatorHandler))]
        if not handlers:
            raise ValueError("BDE tool binding state missing")
        state = handlers[0].state
        is_manager = name == state.root_agent.logical_agent_id
        constructor = sdk.__dict__["FunctionTool"]
        if self.route == "D":
            agent = cast(Any, super()._agent(
                sdk, name=name, instructions=instructions, tools=tools,
                max_parallel=max_parallel, tool_use_behavior=tool_use_behavior))
            if is_manager:
                async def compare(context: object, arguments: str) -> str:
                    return await self._compare(state, context, arguments)

                agent.tools.append(constructor(
                    name="compare_ready_actions",
                    description="Compare 1 to 3 alternative ready actions YOU propose. Returns "
                    "cost vectors and quote IDs without executing. Choose at most one per "
                    "comparison using commit_quote; semantic adequacy is your responsibility. "
                    "Unknown costs are unknown, not zero. No quality ranking is provided.",
                    params_json_schema=comparison_schema(
                        self._registry, self._available_operations),
                    on_invoke_tool=compare,
                    strict_json_schema=False,
                ))
            return agent
        extras: list[object] = []
        if is_manager:
            for handler in handlers:
                async def estimate(
                    ctx: object, args: str, spec: OperatorSpec = handler.spec,
                ) -> str:
                    value = json.loads(await super(BDENativeRuntime, self)._propose(
                        state, ctx, spec, args))
                    if "quote_id" not in value:
                        return json.dumps(value)
                    result: dict[str, object] = {
                              "card_id": value["quote_id"], "consequence": value["consequence"],
                              "query_latency_ms": value["quote_control_latency_ms"],
                              "advisory_only": True,
                              "next_step": "Use an ordinary execution tool if you choose; "
                                           "no query or commit is required."}
                    state.emit("logical.cost_card.returned", result)
                    return json.dumps(result)

                extras.append(constructor(
                    name="estimate_" + handler.spec.operator_id,
                    description="Optional read-only consequence query for the same ready action "
                    "arguments as " + handler.spec.operator_id + ". Does not execute/reserve. "
                    "Unknown costs stay unknown; this does not assess answer quality.",
                    params_json_schema=_native_tool_schema(handler.spec),
                    on_invoke_tool=estimate, strict_json_schema=False,
                ))
        agent = OpenAIAgentsNativeRuntime._agent(
            self, sdk, name=name, instructions=instructions, tools=[*tools, *extras],
            max_parallel=max_parallel, tool_use_behavior=tool_use_behavior,
        )
        return meter_agent(agent, state, name)

    async def _compare(self, state: _NativeState, context: object, arguments: str) -> str:
        owner = _logical_owner(context, state.root_agent.logical_agent_id)
        identifier = f"{owner}:{getattr(context, 'tool_call_id', 'comparison')}"
        try:
            value: dict[str, Any] = json.loads(arguments)
            raw_candidates: Any = value["candidates"]
            if (set(value) != {"candidates"} or not isinstance(raw_candidates, list)
                    or not 1 <= len(cast(list[Any], raw_candidates)) <= 3):
                raise ValueError("1 to 3 candidates required")
            candidates = cast(list[dict[str, Any]], raw_candidates)
            # Atomic readiness admission: do not partially quote a producer-consumer chain.
            for item in candidates:
                if not isinstance(cast(object, item), dict) or not isinstance(
                    item.get("payload"), dict,
                ):
                    raise ValueError("candidate/payload must be objects")
                if set(item) != {"operator", "payload"}:
                    raise ValueError("invalid candidate fields")
                if item["operator"] not in self._available_operations:
                    raise ValueError("unknown operator")
                if set(item["payload"].get("inputs", [])) - state.accessible.get(owner, set()):
                    raise ValueError("every candidate input must already be materialized")
        except (ValueError, TypeError, KeyError):
            return self._quote_failure(state, identifier, "invalid_ready_candidates")
        results: list[dict[str, Any]] = []
        for index, item in enumerate(candidates):
            ctx = SimpleNamespace(agent=SimpleNamespace(name=owner),
                                  tool_call_id=f"{getattr(context, 'tool_call_id', 'comparison')}-"
                                               f"candidate-{index}")
            result = json.loads(await super()._propose(
                state, ctx, self._registry.binding(item["operator"]).spec,
                json.dumps(item["payload"])))
            results.append(result)
        identifiers = [r["quote_id"] for r in results if "quote_id" in r]
        gateway = cast(Any, self._quote_gateway(state))
        gateway.comparison_groups[identifier] = identifiers
        response: dict[str, object] = {"comparison_id": identifier, "candidates": results,
                    "selected_by_system": None, "quality_estimated": False,
                    "next_step": "Choose at most one quote_id with commit_quote or discard."}
        state.emit("logical.cost_candidates.returned", response)
        return json.dumps(response)

    async def _quote_control(
        self, state: _NativeState, context: object, operation: str, input_json: str,
    ) -> str:
        if operation == "commit_quote":
            try:
                quote_id = json.loads(input_json)["quote_id"]
            except (ValueError, KeyError, TypeError):
                return await super()._quote_control(state, context, operation, input_json)
            gateway = cast(Any, self._quote_gateway(state))
            for group, members in gateway.comparison_groups.items():
                if quote_id in members:
                    if group in gateway.selected_groups:
                        return self._quote_failure(state, group, "comparison_already_selected")
                    gateway.selected_groups.add(group)
                    state.emit("logical.cost_candidates.selected", {
                        "comparison_id": group, "quote_id": quote_id,
                        "decision_owner": "manager", "system_selected": False,
                    })
                    for other in members:
                        if other != quote_id and gateway.quotes._quotes[other].status == "pending":
                            gateway.quotes.discard(other, owner=gateway.quotes.owner_agent_id)
        return await super()._quote_control(state, context, operation, input_json)


def comparison_schema(registry: Any, operations: tuple[str, ...]) -> dict[str, Any]:
    return {"type": "object", "properties": {"candidates": {
        "type": "array", "minItems": 1, "maxItems": 3,
        "items": {"oneOf": [{"type": "object", "properties": {
            "operator": {"const": op}, "payload": _native_tool_schema(registry.binding(op).spec)},
            "required": ["operator", "payload"], "additionalProperties": False}
            for op in operations]}}}, "required": ["candidates"], "additionalProperties": False}


def contains_bde_feedback(value: object) -> bool:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if {"card_id", "consequence"} <= mapping.keys() or "comparison_id" in mapping:
            return True
        return any(contains_bde_feedback(v) for v in mapping.values())
    if isinstance(value, list):
        return any(contains_bde_feedback(v) for v in cast(list[object], value))
    if isinstance(value, str):
        if RULE_PREFIX in value:
            return True
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return False
        return contains_bde_feedback(parsed) if not isinstance(parsed, str) else False
    return False


def is_rule_message(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    content = cast(dict[str, Any], item).get("content")
    return isinstance(content, str) and content.startswith(RULE_PREFIX)
