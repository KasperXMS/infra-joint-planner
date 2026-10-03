# pyright: reportPrivateUsage=false
"""Experimental Ledger adapter over the byte-for-byte frozen native runtime."""

from time import perf_counter
from typing import Any, cast

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalAgentSpec,
    PhysicalProfileView,
    ProfileVisibility,
    StaticCapabilityContract,
)
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX, SpentCostLedger, is_ledger_message
from infra_joint.control.loop import AgentLoopBudget, AgentLoopError, AgentLoopResult
from infra_joint.control.native_agents import OpenAIAgentsNativeRuntime, _NativeState
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.provenance import semantic_input_items
from infra_joint.core.task import TaskContract
from infra_joint.workflow.trace import WorkflowTraceRecorder


class LedgerActionGateway:
    """Observe returned receipts without changing resolution, execution or profiles."""

    def __init__(self, delegate: ActionGateway) -> None:
        self.delegate = delegate
        self.ledger = SpentCostLedger()
        self.started = perf_counter()

    def validate_batch(self, actions: tuple[LogicalAction, ...]) -> None:
        self.delegate.validate_batch(actions)

    async def profile_overview(self) -> PhysicalProfileView:
        return await self.delegate.profile_overview()

    async def execute_batch(
        self,
        actions: tuple[LogicalAction, ...],
        *,
        expose_profile: bool,
    ) -> tuple[PhysicalExecutionOutcome, ...]:
        outcomes = await self.delegate.execute_batch(actions, expose_profile=expose_profile)
        by_id = {item.observation.action_id: item for item in outcomes}
        if len(by_id) != len(outcomes) or set(by_id) != {item.action_id for item in actions}:
            raise ValueError("ledger gateway action/outcome set mismatch")
        for action in actions:
            self.ledger.record(action, by_id[action.action_id])
        return outcomes


class LedgerNativeRuntime(OpenAIAgentsNativeRuntime):
    """RouteA: semantic/static inputs plus measured spending, not Raw-Aware H_t."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["predecision_profiles"] = True
        super().__init__(**kwargs)

    async def run(
        self,
        task: TaskContract,
        gateway: ActionGateway,
        *,
        root_agent: LogicalAgentSpec | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        budget: AgentLoopBudget | None = None,
        trace: WorkflowTraceRecorder | None = None,
        static_capabilities: StaticCapabilityContract | None = None,
    ) -> AgentLoopResult:
        if profile_visibility != ProfileVisibility.BLIND:
            raise ValueError("Ledger-only variant does not inject Raw-Aware profiles")
        if trace is not None:
            trace.emit("method.variant.start", {
                "variant": "ledger-only-v0",
                "base_runtime": "OpenAIAgentsNativeRuntime",
                "current_dynamic_profile_injected": False,
                "measured_past_cost_feedback": True,
                "is_original_blind_baseline": False,
            })
        return await super().run(
            task, LedgerActionGateway(gateway), root_agent=root_agent,
            profile_visibility=profile_visibility, budget=budget, trace=trace,
            static_capabilities=static_capabilities,
        )

    @staticmethod
    def _predecision_run_config(sdk: object, state: _NativeState) -> object:
        # Compose the pinned SDK input filter; do not copy or weaken its privacy checks.
        config = cast(Any, OpenAIAgentsNativeRuntime._predecision_run_config(sdk, state))
        original = config.call_model_input_filter

        async def filter_input(data: Any) -> object:
            model_data = await original(data)
            items: list[Any] = list(model_data.input)
            is_manager = data.agent.name == state.root_agent.logical_agent_id
            if not is_manager:
                if any(is_ledger_message(item) for item in semantic_input_items(items)):
                    raise AgentLoopError("Blind recipient spent-cost ledger isolation violated")
                return model_data
            if not isinstance(state.gateway, LedgerActionGateway):
                raise RuntimeError("Ledger runtime requires its per-run accounting gateway")
            snapshot = state.gateway.ledger.snapshot(
                usage=state.usage(), budget=state.budget,
                logical_loop_elapsed_ms=(perf_counter() - state.gateway.started) * 1000,
            )
            decision_id = (
                f"{state.root_agent.logical_agent_id}:native-turn:"
                f"{state.turn_by_agent.get(state.root_agent.logical_agent_id, 0) + 1}"
            )
            state.emit("logical.cost_ledger.predecision", {
                "decision_id": decision_id, "ledger": snapshot.model_dump(mode="json"),
                "graph_version": state.graph.snapshot().version,
            })
            items = [item for item in items if not is_ledger_message(item)]
            items.append({
                "role": "user", "content": LEDGER_MESSAGE_PREFIX + snapshot.model_dump_json(),
            })
            return type(model_data)(input=items, instructions=model_data.instructions)

        config.call_model_input_filter = filter_input
        return config
