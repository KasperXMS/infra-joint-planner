from __future__ import annotations

import asyncio
import copy
import importlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import Field

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import (
    ExecutionRequirements,
    LogicalAction,
    LogicalAgentSpec,
    LogicalModelAction,
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
    ProfileVisibility,
    SubagentResult,
)
from infra_joint.control.gateway import ActionGateway
from infra_joint.control.graph import ExecutionGrownGraph
from infra_joint.control.loop import (
    AgentLoopBudget,
    AgentLoopError,
    AgentLoopResult,
    AgentLoopUsage,
    PlannerStepTelemetry,
)
from infra_joint.control.physical import PhysicalExecutionOutcome
from infra_joint.control.validation import SemanticValidationError
from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputFormat, TaskContract
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.workflow.trace import WorkflowTraceRecorder


class _FunctionToolConstructor(Protocol):
    def __call__(self, **kwargs: Any) -> object: ...


class _AgentConstructor(Protocol):
    def __call__(self, **kwargs: Any) -> object: ...


class _RunnerType(Protocol):
    @staticmethod
    async def run(
        agent: object,
        input: str,
        *,
        context: object,
        max_turns: int,
        hooks: object,
    ) -> object: ...


class _AgentObject(Protocol):
    def as_tool(self, **kwargs: Any) -> _FunctionToolObject: ...


class _FunctionToolObject(Protocol):
    on_invoke_tool: Any


class SpecialistRequest(ContractModel):
    """Structured input to the SDK-native bounded specialist agent tool."""

    logical_agent_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    input_artifacts: tuple[str, ...] = ()


@dataclass(slots=True)
class _NativeState:
    task: TaskContract
    task_view: AgentTaskView
    gateway: ActionGateway
    graph: ExecutionGrownGraph
    budget: AgentLoopBudget
    visibility: ProfileVisibility
    root_agent: LogicalAgentSpec
    trace: WorkflowTraceRecorder | None
    observations: list[LogicalObservation] = field(
        default_factory=lambda: list[LogicalObservation]()
    )
    subagent_results: list[SubagentResult] = field(
        default_factory=lambda: list[SubagentResult]()
    )
    planner_steps: list[PlannerStepTelemetry] = field(
        default_factory=lambda: list[PlannerStepTelemetry]()
    )
    accessible: dict[str, set[str]] = field(
        default_factory=lambda: dict[str, set[str]]()
    )
    produced: dict[str, set[str]] = field(
        default_factory=lambda: dict[str, set[str]]()
    )
    actions: dict[str, LogicalAction] = field(
        default_factory=lambda: dict[str, LogicalAction]()
    )
    turn_by_agent: dict[str, int] = field(
        default_factory=lambda: dict[str, int]()
    )
    llm_started: dict[str, float] = field(
        default_factory=lambda: dict[str, float]()
    )
    manager_turns: int = 0
    subagent_turns: int = 0
    tool_model_calls: int = 0
    created_subagents: int = 0
    active_subagents: int = 0
    peak_active_subagents: int = 0
    fatal_error: AgentLoopError | None = None
    state_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def emit(self, event_type: str, payload: dict[str, object]) -> None:
        if self.trace is not None:
            self.trace.emit(event_type, payload)

    def usage(self) -> AgentLoopUsage:
        return AgentLoopUsage(
            manager_turns=self.manager_turns,
            subagent_turns=self.subagent_turns,
            tool_model_calls=self.tool_model_calls,
            created_subagents=self.created_subagents,
            peak_active_subagents=self.peak_active_subagents,
        )


class _NativeHooks:
    def __init__(self, state: _NativeState) -> None:
        self._state = state

    async def on_llm_start(
        self,
        context: object,
        agent: object,
        system_prompt: str | None,
        input_items: list[object],
    ) -> None:
        del system_prompt, input_items
        owner = self._owner(context, agent)
        self._state.turn_by_agent[owner] = self._state.turn_by_agent.get(owner, 0) + 1
        self._state.llm_started[owner] = perf_counter()
        if owner == self._state.root_agent.logical_agent_id:
            self._state.manager_turns += 1
        else:
            self._state.subagent_turns += 1
        self._state.emit(
            "logical.reasoning.started",
            {
                "decision_id": self._decision_id(owner),
                "logical_agent_id": owner,
            },
        )

    async def on_llm_end(
        self,
        context: object,
        agent: object,
        response: object,
    ) -> None:
        del response
        owner = self._owner(context, agent)
        latency = (perf_counter() - self._state.llm_started.pop(owner, perf_counter())) * 1000
        telemetry = PlannerStepTelemetry(logical_agent_id=owner, latency_ms=latency)
        self._state.planner_steps.append(telemetry)
        self._state.emit(
            "logical.reasoning.completed",
            {
                "decision_id": self._decision_id(owner),
                "logical_agent_id": owner,
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )

    async def on_agent_start(self, context: object, agent: object) -> None:
        del context, agent

    async def on_agent_end(self, context: object, agent: object, output: object) -> None:
        del context, agent, output

    async def on_handoff(
        self,
        context: object,
        from_agent: object,
        to_agent: object,
    ) -> None:
        del context, from_agent, to_agent

    async def on_tool_start(
        self,
        context: object,
        agent: object,
        tool: object,
    ) -> None:
        del context, agent, tool

    async def on_tool_end(
        self,
        context: object,
        agent: object,
        tool: object,
        result: object,
    ) -> None:
        del context, agent, tool, result

    def _owner(self, context: object, agent: object) -> str:
        name = str(getattr(agent, "name", self._state.root_agent.logical_agent_id))
        return _logical_owner(context, name)

    def _decision_id(self, owner: str) -> str:
        return f"{owner}:native-turn:{self._state.turn_by_agent.get(owner, 0)}"


class OpenAIAgentsNativeRuntime:
    """SDK-native persistent logical runtime over the unchanged ActionGateway.

    Operators are genuine SDK function tools. The model never emits a custom decision or
    action discriminator; SDK tool calls are translated internally to logical actions.
    """

    def __init__(
        self,
        *,
        name: str,
        instructions: str,
        model: object,
        registry: OperatorRegistry,
        available_operations: Iterable[str],
        sdk_module: object | None = None,
    ) -> None:
        self._name = name
        self._instructions = instructions
        self._model = model
        self._registry = registry
        self._available_operations = tuple(sorted(set(available_operations)))
        self._sdk_module = sdk_module
        unknown = sorted(item for item in self._available_operations if item not in registry)
        if unknown:
            raise ValueError(f"native tool space references unknown operators: {unknown}")

    async def run(
        self,
        task: TaskContract,
        gateway: ActionGateway,
        *,
        root_agent: LogicalAgentSpec | None = None,
        profile_visibility: ProfileVisibility = ProfileVisibility.BLIND,
        budget: AgentLoopBudget | None = None,
        trace: WorkflowTraceRecorder | None = None,
    ) -> AgentLoopResult:
        root = root_agent or LogicalAgentSpec(
            logical_agent_id="manager",
            role="global task manager",
            objective="solve the task using bounded tools and specialist agents",
        )
        resolved_budget = budget or AgentLoopBudget()
        task_view = AgentTaskView.from_contract(task)
        state = _NativeState(
            task=task,
            task_view=task_view,
            gateway=gateway,
            graph=ExecutionGrownGraph(),
            budget=resolved_budget,
            visibility=profile_visibility,
            root_agent=root,
            trace=trace,
            accessible={root.logical_agent_id: {item.artifact_id for item in task_view.artifacts}},
            produced={root.logical_agent_id: set()},
        )
        state.emit(
            "logical.loop.start",
            {
                "task": task_view.model_dump(mode="json"),
                "profile_visibility": profile_visibility.value,
                "root_agent": root.model_dump(mode="json"),
                "budget": resolved_budget.model_dump(mode="json"),
                "adapter": "openai-agents-sdk-native-tools-v1",
            },
        )
        state.emit("workflow.graph.snapshot", state.graph.snapshot().model_dump(mode="json"))

        sdk = self._sdk_module or _load_native_agents_sdk()
        function_tools = [
            self._function_tool(sdk, state, self._registry.binding(name).spec)
            for name in self._available_operations
        ]
        hooks = _sdk_hooks(sdk, state)
        specialist = self._agent(
            sdk,
            name="bounded_specialist",
            instructions=self._specialist_instructions(),
            tools=function_tools,
            max_parallel=True,
        )
        specialist_tool = self._specialist_tool(
            specialist, state, resolved_budget, hooks
        )
        manager = self._agent(
            sdk,
            name=root.logical_agent_id,
            instructions=self._manager_instructions(),
            tools=[*function_tools, specialist_tool],
            max_parallel=True,
        )
        runner = cast(_RunnerType, sdk.__dict__["Runner"])
        try:
            result = await runner.run(
                manager,
                input=self._manager_input(task_view),
                context=state,
                max_turns=resolved_budget.max_manager_turns,
                hooks=hooks,
            )
        except Exception as exc:
            if type(exc).__name__ == "MaxTurnsExceeded":
                raise AgentLoopError("manager turn budget exhausted") from exc
            raise
        if state.fatal_error is not None:
            raise state.fatal_error
        output = getattr(result, "final_output", None)
        if not isinstance(output, str) or not output.strip():
            raise AgentLoopError("SDK-native manager returned no textual final answer")
        answer = output.strip()
        terminal = self._terminal_source(state, answer)
        _validate_output_contract(task, answer)
        loop_result = AgentLoopResult(
            final_answer=answer,
            terminal_action_id=terminal,
            observations=tuple(state.observations),
            subagent_results=tuple(state.subagent_results),
            graph_snapshots=state.graph.snapshots,
            planner_steps=tuple(state.planner_steps),
            budget=resolved_budget,
            usage=state.usage(),
        )
        state.emit(
            "logical.loop.end",
            {
                "terminal_action_id": terminal,
                "final_answer": answer,
                "graph_version": state.graph.snapshot().version,
                "usage": state.usage().model_dump(mode="json"),
            },
        )
        return loop_result

    def _function_tool(
        self,
        sdk: object,
        state: _NativeState,
        spec: OperatorSpec,
    ) -> object:
        constructor = cast(_FunctionToolConstructor, sdk.__dict__["FunctionTool"])

        async def invoke(context: object, input_json: str) -> str:
            return await self._invoke_operator(state, context, spec, input_json)

        return constructor(
            name=spec.operator_id,
            description=spec.description,
            params_json_schema=_native_tool_schema(spec),
            on_invoke_tool=invoke,
            strict_json_schema=False,
        )

    def _agent(
        self,
        sdk: object,
        *,
        name: str,
        instructions: str,
        tools: list[object],
        max_parallel: bool,
    ) -> object:
        constructor = cast(_AgentConstructor, sdk.__dict__["Agent"])
        settings_constructor = cast(Any, sdk.__dict__.get("ModelSettings"))
        settings = (
            settings_constructor(parallel_tool_calls=max_parallel)
            if settings_constructor is not None
            else None
        )
        kwargs: dict[str, object] = {
            "name": name,
            "instructions": instructions,
            "model": self._model,
            "tools": tools,
        }
        if settings is not None:
            kwargs["model_settings"] = settings
        return constructor(**kwargs)

    def _specialist_tool(
        self,
        specialist: object,
        state: _NativeState,
        budget: AgentLoopBudget,
        hooks: object,
    ) -> object:
        specialist_agent = cast(_AgentObject, specialist)

        def input_builder(options: dict[str, object]) -> str:
            return json.dumps(options["params"], ensure_ascii=False, sort_keys=True)

        tool = specialist_agent.as_tool(
            tool_name="consult_specialist",
            tool_description=(
                "Delegate a bounded semantic subtask to a specialist. Pass only artifacts "
                "needed by that specialist; its result returns to the manager."
            ),
            max_turns=budget.max_subagent_turns,
            hooks=hooks,
            parameters=SpecialistRequest,
            input_builder=input_builder,
        )
        original = tool.on_invoke_tool

        async def invoke(context: object, input_json: str) -> str:
            request = SpecialistRequest.model_validate_json(input_json)
            parent = state.root_agent.logical_agent_id
            async with state.state_lock:
                missing = sorted(set(request.input_artifacts) - state.accessible[parent])
                if missing:
                    return _failure_result(
                        f"subagent:{request.logical_agent_id}",
                        parent,
                        "artifact_not_accessible",
                        f"specialist input artifacts are unavailable: {missing}",
                    )
                if state.created_subagents >= budget.max_created_subagents:
                    state.fatal_error = AgentLoopError("created subagent budget exceeded")
                    return _failure_result(
                        f"subagent:{request.logical_agent_id}",
                        parent,
                        "budget_exhausted",
                        "created subagent budget exceeded",
                    )
                if state.active_subagents >= budget.max_active_subagents:
                    return _failure_result(
                        f"subagent:{request.logical_agent_id}",
                        parent,
                        "active_subagent_budget_exceeded",
                        "active subagent budget exceeded",
                    )
                if request.logical_agent_id in state.accessible:
                    return _failure_result(
                        f"subagent:{request.logical_agent_id}",
                        parent,
                        "duplicate_logical_agent",
                        "logical agent ID already exists",
                    )
                state.created_subagents += 1
                state.active_subagents += 1
                state.peak_active_subagents = max(
                    state.peak_active_subagents, state.active_subagents
                )
                state.accessible[request.logical_agent_id] = set(request.input_artifacts)
                state.produced[request.logical_agent_id] = set()
            state.emit(
                "logical.subagent.start",
                request.model_dump(mode="json"),
            )
            try:
                result = await original(context, input_json)
                answer = result if isinstance(result, str) else json.dumps(result)
                owned_actions = [
                    action_id
                    for action_id, action in state.actions.items()
                    if action.owner_agent_id == request.logical_agent_id
                ]
                terminal = (
                    owned_actions[-1]
                    if owned_actions
                    else f"subagent:{request.logical_agent_id}"
                )
                subagent_result = SubagentResult(
                    call_id=str(getattr(context, "tool_call_id", request.logical_agent_id)),
                    logical_agent_id=request.logical_agent_id,
                    terminal_action_id=terminal,
                    answer=answer,
                )
                state.subagent_results.append(subagent_result)
                handoff = sorted(state.produced[request.logical_agent_id])
                state.accessible[parent].update(handoff)
                if handoff:
                    state.emit(
                        "logical.information.handoff",
                        {
                            "source_logical_agent_id": request.logical_agent_id,
                            "target_logical_agent_id": parent,
                            "artifact_ids": handoff,
                        },
                    )
                state.emit("logical.subagent.end", subagent_result.model_dump(mode="json"))
                return answer
            finally:
                async with state.state_lock:
                    state.active_subagents -= 1

        tool.on_invoke_tool = invoke
        return tool

    async def _invoke_operator(
        self,
        state: _NativeState,
        context: object,
        spec: OperatorSpec,
        input_json: str,
    ) -> str:
        owner = _logical_owner(context, state.root_agent.logical_agent_id)
        call_id = str(getattr(context, "tool_call_id", f"call-{len(state.actions) + 1}"))
        action_id = f"{owner}:{call_id}"
        try:
            payload = cast(dict[str, object], json.loads(input_json))
        except (json.JSONDecodeError, TypeError) as exc:
            return self._record_logical_failure(
                state,
                action_id,
                owner,
                "semantic_validation_failed",
                f"invalid SDK tool arguments: {exc}",
            )
        inputs = tuple(str(item) for item in cast(list[object], payload.get("inputs", [])))
        arguments = cast(dict[str, Any], payload.get("arguments", {}))
        try:
            action = _logical_action(spec, action_id, owner, inputs, arguments, payload)
        except (ValueError, TypeError) as exc:
            return self._record_logical_failure(
                state, action_id, owner, "semantic_validation_failed", str(exc)
            )

        async with state.state_lock:
            if state.tool_model_calls >= state.budget.max_tool_model_calls:
                state.fatal_error = AgentLoopError("tool/model call budget exceeded")
                return self._record_logical_failure(
                    state,
                    action_id,
                    owner,
                    "budget_exhausted",
                    "tool/model call budget exceeded",
                )
            available = state.accessible.setdefault(owner, set())
            missing = sorted(set(inputs) - available)
            if missing:
                return self._record_logical_failure(
                    state,
                    action_id,
                    owner,
                    "artifact_not_materialized",
                    f"input artifacts are unavailable to the current agent: {missing}",
                )
            decision_id = (
                f"{owner}:native-turn:{state.turn_by_agent.get(owner, 1)}"
            )
            batch_id = f"{decision_id}:batch:{call_id}"
            validation = {
                "batch_id": batch_id,
                "decision_id": decision_id,
                "logical_agent_id": owner,
                "action_ids": [action_id],
                "input_artifact_ids": list(inputs),
                "same_batch_dependencies": [],
            }
            try:
                state.gateway.validate_batch((action,))
            except SemanticValidationError as exc:
                state.emit(
                    "logical.batch.validation",
                    {**validation, "status": "rejected", "reason": str(exc)},
                )
                return self._record_logical_failure(
                    state,
                    action_id,
                    owner,
                    "semantic_validation_failed",
                    str(exc),
                )
            state.emit(
                "logical.batch.validation",
                {**validation, "status": "accepted", "all_inputs_materialized": True},
            )
            state.tool_model_calls += 1
            state.actions[action_id] = action
            pending = state.graph.add((action,))
            state.emit("workflow.graph.snapshot", pending.model_dump(mode="json"))
            running = state.graph.mark_running((action_id,))
            state.emit("workflow.graph.snapshot", running.model_dump(mode="json"))
            state.emit(
                "logical.batch.started",
                {
                    "batch_id": batch_id,
                    "decision_id": decision_id,
                    "logical_agent_id": owner,
                    "action_ids": [action_id],
                    "agent_state": "waiting_on_physical",
                },
            )

        try:
            outcomes = await state.gateway.execute_batch(
                (action,), expose_profile=state.visibility == ProfileVisibility.AWARE
            )
        except asyncio.CancelledError:
            await self._close_interrupted_action(
                state,
                action_id=action_id,
                owner=owner,
                batch_id=batch_id,
                decision_id=decision_id,
                code="action_cancelled",
                message="SDK cancelled the in-flight tool call",
            )
            raise
        except Exception as exc:
            await self._close_interrupted_action(
                state,
                action_id=action_id,
                owner=owner,
                batch_id=batch_id,
                decision_id=decision_id,
                code="physical_execution_failed",
                message=f"unrecoverable physical execution error: {type(exc).__name__}",
            )
            raise
        outcome = outcomes[0]
        observation = outcome.observation
        async with state.state_lock:
            state.observations.append(observation)
            if observation.succeeded:
                produced = {item.artifact_id for item in observation.produced_information}
                state.accessible[owner].update(produced)
                state.produced[owner].update(produced)
            finished = state.graph.mark_finished(
                (action_id,) if observation.succeeded else (),
                () if observation.succeeded else (action_id,),
            )
            state.emit("workflow.graph.snapshot", finished.model_dump(mode="json"))
            self._emit_outcome(state, batch_id, action_id, outcome)
            state.emit(
                "logical.batch.completed",
                {
                    "batch_id": batch_id,
                    "decision_id": decision_id,
                    "logical_agent_id": owner,
                    "action_ids": [action_id],
                    "succeeded_action_ids": [action_id] if observation.succeeded else [],
                    "failed_action_ids": [] if observation.succeeded else [action_id],
                    "agent_state": "ready_for_reasoning",
                },
            )
        return observation.model_dump_json(exclude_none=True)

    async def _close_interrupted_action(
        self,
        state: _NativeState,
        *,
        action_id: str,
        owner: str,
        batch_id: str,
        decision_id: str,
        code: str,
        message: str,
    ) -> None:
        observation = LogicalObservation(
            action_id=action_id,
            owner_agent_id=owner,
            succeeded=False,
            failure_code=code,
            failure_message=message,
        )
        async with state.state_lock:
            state.observations.append(observation)
            finished = state.graph.mark_finished((), (action_id,))
            state.emit("workflow.graph.snapshot", finished.model_dump(mode="json"))
            state.emit("logical.observation", observation.model_dump(mode="json"))
            state.emit(
                "logical.batch.completed",
                {
                    "batch_id": batch_id,
                    "decision_id": decision_id,
                    "logical_agent_id": owner,
                    "action_ids": [action_id],
                    "succeeded_action_ids": [],
                    "failed_action_ids": [action_id],
                    "agent_state": "ready_for_reasoning",
                },
            )

    def _record_logical_failure(
        self,
        state: _NativeState,
        action_id: str,
        owner: str,
        code: str,
        message: str,
    ) -> str:
        observation = LogicalObservation(
            action_id=action_id,
            owner_agent_id=owner,
            succeeded=False,
            failure_code=code,
            failure_message=message,
        )
        state.observations.append(observation)
        state.emit("logical.observation", observation.model_dump(mode="json"))
        return observation.model_dump_json(exclude_none=True)

    @staticmethod
    def _emit_outcome(
        state: _NativeState,
        batch_id: str,
        action_id: str,
        outcome: PhysicalExecutionOutcome,
    ) -> None:
        state.emit("logical.observation", outcome.observation.model_dump(mode="json"))
        payload: dict[str, object] = {"batch_id": batch_id, "action_id": action_id}
        if outcome.selection is not None:
            payload["selection"] = outcome.selection.model_dump(mode="json")
        if outcome.execution is not None:
            payload["execution"] = outcome.execution.model_dump(mode="json")
        if outcome.failure is not None:
            payload["failure"] = outcome.failure.model_dump(mode="json")
        state.emit("physical.execution", payload)

    def _manager_instructions(self) -> str:
        return (
            self._instructions
            + "\nUse the SDK function tools directly; never write a ManagerDecision, action_type, "
            "decision_type, future DAG, worker, deployment, route, or placement. Tool results are "
            "typed logical observations. After a failed tool call, inspect its failure and choose "
            "a "
            "legal next tool call. Independent ready tools may be called in parallel. A dependent "
            "tool may be called only after its producer result returns. Use consult_specialist for "
            "bounded delegation; you retain the global task and final-answer ownership. Before "
            "finishing, invoke the logical model tool successfully. Return exactly that successful "
            "invoke_model text as your final response, with no explanation or wrapper."
        )

    @staticmethod
    def _specialist_instructions() -> str:
        return (
            "You are a bounded semantic specialist invoked as an SDK agent tool. Follow the role, "
            "objective, instruction, and allowed input_artifacts in your tool input. Use only the "
            "SDK function tools supplied to you. Never mention or request infrastructure identity. "
            "Inspect typed tool failures and continue with a corrected legal action when possible. "
            "Call dependent tools only after producer results return. Return a concise evidence "
            "result to the manager; do not claim global final-answer ownership."
        )

    @staticmethod
    def _manager_input(task: AgentTaskView) -> str:
        return json.dumps(
            {"task": task.model_dump(mode="json")},
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _terminal_source(state: _NativeState, answer: str) -> str:
        matches = [
            item.action_id
            for item in state.observations
            if item.owner_agent_id == state.root_agent.logical_agent_id
            and item.succeeded
            and isinstance(state.actions.get(item.action_id), LogicalModelAction)
            and item.output.get("text") == answer
        ]
        if not matches:
            raise AgentLoopError(
                "terminal answer must exactly match a successful manager invoke_model result"
            )
        return matches[-1]


def _native_tool_schema(spec: OperatorSpec) -> dict[str, Any]:
    input_schema = copy.deepcopy(
        spec.input_schema
        or {"type": "array", "items": {"type": "string"}}
    )
    argument_schema = _nest_local_references(
        copy.deepcopy(spec.argument_schema or {"type": "object"}),
        "#/properties/arguments",
    )
    properties: dict[str, Any] = {
        "inputs": input_schema,
        "arguments": argument_schema,
    }
    if spec.operator_id == "invoke_model":
        properties["requirements"] = {
            "type": "object",
            "properties": {
                "modalities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "min_context_tokens": {"type": "integer", "minimum": 1},
                "reserved_output_tokens": {"type": "integer", "minimum": 1},
                "required_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "quality_class": {
                    "type": ["string", "null"],
                    "enum": ["standard", "high_quality", "low_latency", None],
                },
            },
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": ["inputs", "arguments"],
        "additionalProperties": False,
    }


def _nest_local_references(value: object, prefix: str) -> object:
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, nested in cast(dict[object, object], value).items():
            if key == "$ref" and isinstance(nested, str) and nested.startswith("#/"):
                result[str(key)] = prefix + nested[1:]
            else:
                result[str(key)] = _nest_local_references(nested, prefix)
        return result
    if isinstance(value, list):
        return [
            _nest_local_references(item, prefix)
            for item in cast(list[object], value)
        ]
    return value


def _logical_owner(context: object, fallback: str) -> str:
    tool_input = getattr(context, "tool_input", None)
    if isinstance(tool_input, dict):
        value = cast(dict[object, object], tool_input).get("logical_agent_id")
        if isinstance(value, str) and value:
            return value
    agent = getattr(context, "agent", None)
    name = getattr(agent, "name", None)
    return name if isinstance(name, str) and name else fallback


def _logical_action(
    spec: OperatorSpec,
    action_id: str,
    owner: str,
    inputs: tuple[str, ...],
    arguments: dict[str, Any],
    payload: dict[str, object],
) -> LogicalAction:
    outputs = _logical_outputs(spec.operator_id, arguments)
    if spec.operator_id == "invoke_model":
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("invoke_model requires a textual prompt")
        requirements_payload = payload.get("requirements", {})
        if not isinstance(requirements_payload, dict):
            raise ValueError("invoke_model requirements must be an object")
        requirements = ExecutionRequirements.model_validate(requirements_payload)
        return LogicalModelAction(
            action_id=action_id,
            owner_agent_id=owner,
            inputs=inputs,
            outputs=outputs,
            prompt=prompt,
            requirements=requirements,
        )
    return LogicalToolAction(
        action_id=action_id,
        owner_agent_id=owner,
        inputs=inputs,
        outputs=outputs,
        operator=spec.operator_id,
        arguments=arguments,
    )


def _logical_outputs(
    operator: str,
    arguments: dict[str, Any],
) -> tuple[LogicalOutput, ...]:
    if operator == "sample_frames":
        prefix = arguments.get("output_prefix")
        count = arguments.get("max_frames")
        if isinstance(prefix, str) and isinstance(count, int):
            return tuple(
                LogicalOutput(
                    artifact_id=f"{prefix}/frame-{index:06d}.jpg",
                    semantic_type="sampled_video_frame",
                    media_type="image/jpeg",
                )
                for index in range(1, count + 1)
            )
    artifact_id = arguments.get("output_artifact_id")
    if not isinstance(artifact_id, str):
        return ()
    media_type = {
        "extract_clip": "video/mp4",
        "make_contact_sheet": "image/jpeg",
        "invoke_model": str(arguments.get("output_media_type", "text/plain")),
    }.get(operator, "application/json")
    semantic_type = str(
        arguments.get("output_semantic_type", f"{operator}_result")
    )
    return (
        LogicalOutput(
            artifact_id=artifact_id,
            semantic_type=semantic_type,
            media_type=media_type,
        ),
    )


def _failure_result(action_id: str, owner: str, code: str, message: str) -> str:
    return LogicalObservation(
        action_id=action_id,
        owner_agent_id=owner,
        succeeded=False,
        failure_code=code,
        failure_message=message,
    ).model_dump_json(exclude_none=True)


def _validate_output_contract(task: TaskContract, answer: str) -> None:
    contract = task.output_contract
    if contract.format == OutputFormat.CHOICE:
        if contract.choices is None or answer not in contract.choices:
            raise AgentLoopError("terminal answer violates the choice output contract")
        return
    if contract.format == OutputFormat.SHORT_TEXT:
        if not answer.strip():
            raise AgentLoopError("terminal answer violates the short-text output contract")
        return
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise AgentLoopError("terminal answer is not valid JSON") from exc
    schema = contract.schema_definition
    if schema is None:
        raise AgentLoopError("structured output contract has no schema")
    errors = cast(
        Iterator[JsonSchemaValidationError],
        Draft202012Validator(schema).iter_errors(parsed),  # pyright: ignore[reportUnknownMemberType]
    )
    error = next(errors, None)
    if error is not None:
        raise AgentLoopError(f"terminal answer violates output schema: {error.message}")


def _load_native_agents_sdk() -> object:
    try:
        module = importlib.import_module("agents")
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed; install the project's 'agents' extra"
        ) from exc
    required = ("Agent", "FunctionTool", "ModelSettings", "Runner")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise RuntimeError(f"OpenAI Agents SDK is missing required APIs: {missing}")
    return module


def _sdk_hooks(sdk: object, state: _NativeState) -> object:
    delegate = _NativeHooks(state)
    base = sdk.__dict__.get("RunHooks")
    if base is None:
        return delegate

    class SdkNativeHooks(base):  # type: ignore[valid-type, misc]
        async def on_llm_start(
            self,
            context: object,
            agent: object,
            system_prompt: str | None,
            input_items: list[object],
        ) -> None:
            await delegate.on_llm_start(
                context, agent, system_prompt, input_items
            )

        async def on_llm_end(
            self,
            context: object,
            agent: object,
            response: object,
        ) -> None:
            await delegate.on_llm_end(context, agent, response)

        async def on_agent_start(self, context: object, agent: object) -> None:
            await delegate.on_agent_start(context, agent)

        async def on_agent_end(
            self, context: object, agent: object, output: object
        ) -> None:
            await delegate.on_agent_end(context, agent, output)

        async def on_handoff(
            self,
            context: object,
            from_agent: object,
            to_agent: object,
        ) -> None:
            await delegate.on_handoff(context, from_agent, to_agent)

        async def on_tool_start(
            self, context: object, agent: object, tool: object
        ) -> None:
            await delegate.on_tool_start(context, agent, tool)

        async def on_tool_end(
            self,
            context: object,
            agent: object,
            tool: object,
            result: object,
        ) -> None:
            await delegate.on_tool_end(context, agent, tool, result)

    return SdkNativeHooks()
