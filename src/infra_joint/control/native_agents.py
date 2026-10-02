from __future__ import annotations

import asyncio
import copy
import importlib
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol, cast
from uuid import uuid4

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
    StaticCapabilityContract,
    StaticOperatorCapability,
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
from infra_joint.control.provenance import (
    PROFILE_MESSAGE_PREFIX,
    is_profile_message,
    provenance_sha256,
    semantic_input_items,
)
from infra_joint.control.validation import SemanticValidationError
from infra_joint.control.verification import (
    BlindVerifier,
    OpenAIAgentsBlindVerifier,
    VerificationContext,
    VerificationResult,
    VerificationTelemetry,
    VerifierActionView,
    VerifierBudgetView,
    VerifierObservation,
    invoke_verifier,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract
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
        **kwargs: Any,
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
    artifact_namespace: str
    static_capabilities: StaticCapabilityContract
    blind_verifier: BlindVerifier | None = None
    record_input_provenance: bool = False
    observations: list[LogicalObservation] = field(
        default_factory=lambda: list[LogicalObservation]()
    )
    subagent_results: list[SubagentResult] = field(
        default_factory=lambda: list[SubagentResult]()
    )
    planner_steps: list[PlannerStepTelemetry] = field(
        default_factory=lambda: list[PlannerStepTelemetry]()
    )
    verification_steps: list[VerificationTelemetry] = field(
        default_factory=lambda: list[VerificationTelemetry]()
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
    verifier_calls: int = 0
    phase: str = "evidence_collection"
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
            verifier_calls=self.verifier_calls,
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
        owner = self._owner(context, agent)
        self._state.turn_by_agent[owner] = self._state.turn_by_agent.get(owner, 0) + 1
        self._state.llm_started[owner] = perf_counter()
        if owner == self._state.root_agent.logical_agent_id:
            self._state.manager_turns += 1
        else:
            self._state.subagent_turns += 1
        if self._state.record_input_provenance:
            items = semantic_input_items(input_items)
            profile = next(
                (
                    json.loads(item["content"][len(PROFILE_MESSAGE_PREFIX):])
                    for item in reversed(items)
                    if item.get("role") == "user"
                    and isinstance(item.get("content"), str)
                    and item["content"].startswith(PROFILE_MESSAGE_PREFIX)
                ),
                None,
            )
            self._state.emit(
                "logical.reasoning.input",
                {
                    "decision_id": self._decision_id(owner),
                    "logical_agent_id": owner,
                    "input_items": items,
                    "input_sha256": provenance_sha256(items),
                    "instructions_sha256": provenance_sha256(system_prompt),
                    "current_anonymous_profile": profile,
                    "graph_version": self._state.graph.snapshot().version,
                    "available_artifact_ids": sorted(self._state.accessible.get(owner, set())),
                    "provider_private_reasoning_recorded": False,
                },
            )
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
        enable_blind_verifier: bool = False,
        blind_verifier: BlindVerifier | None = None,
        predecision_profiles: bool = False,
        record_input_provenance: bool = False,
    ) -> None:
        self._name = name
        self._instructions = instructions
        self._model = model
        self._registry = registry
        self._available_operations = tuple(sorted(set(available_operations)))
        self._sdk_module = sdk_module
        self._enable_blind_verifier = enable_blind_verifier or blind_verifier is not None
        self._blind_verifier = blind_verifier
        self._predecision_profiles = predecision_profiles
        self._record_input_provenance = record_input_provenance
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
        static_capabilities: StaticCapabilityContract | None = None,
    ) -> AgentLoopResult:
        root = root_agent or LogicalAgentSpec(
            logical_agent_id="manager",
            role="global task manager",
            objective="solve the task using bounded tools and specialist agents",
        )
        resolved_budget = budget or AgentLoopBudget()
        task_view = AgentTaskView.from_contract(task)
        sdk = self._sdk_module or _load_native_agents_sdk()
        verifier = self._blind_verifier
        if self._enable_blind_verifier and verifier is None:
            verifier = OpenAIAgentsBlindVerifier(model=self._model, sdk_module=sdk)
        resolved_capabilities = static_capabilities or StaticCapabilityContract(
            operators=tuple(
                StaticOperatorCapability(
                    operator=name,
                    description=self._registry.binding(name).spec.description,
                    input_schema=self._registry.binding(name).spec.input_schema
                    or {"type": "array"},
                    argument_schema=self._registry.binding(name).spec.argument_schema
                    or {"type": "object"},
                    output_schema=self._registry.binding(name).spec.output_schema or {},
                    required_capabilities=self._registry.binding(
                        name
                    ).spec.capability_requirements,
                )
                for name in self._available_operations
            ),
            model_classes=(),
        )
        state = _NativeState(
            task=task,
            task_view=task_view,
            gateway=gateway,
            graph=ExecutionGrownGraph(),
            budget=resolved_budget,
            visibility=profile_visibility,
            root_agent=root,
            trace=trace,
            artifact_namespace=f"derived/{uuid4().hex}",
            static_capabilities=resolved_capabilities,
            blind_verifier=verifier,
            record_input_provenance=self._record_input_provenance,
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
                "artifact_namespace": state.artifact_namespace,
                "static_capability_contract": resolved_capabilities.model_dump(mode="json"),
                "blind_verifier": {
                    "enabled": verifier is not None,
                    "max_calls": resolved_budget.max_verifier_calls,
                },
            },
        )
        state.emit("workflow.graph.snapshot", state.graph.snapshot().model_dump(mode="json"))

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
            tool_use_behavior=self._manager_tool_use_behavior(sdk, state),
        )
        runner = cast(_RunnerType, sdk.__dict__["Runner"])
        run_options: dict[str, object] = {}
        if self._predecision_profiles:
            run_options["run_config"] = self._predecision_run_config(sdk, state)
        try:
            result = await runner.run(
                manager,
                input=self._manager_input(task_view, resolved_capabilities),
                context=state,
                max_turns=resolved_budget.max_manager_turns,
                hooks=hooks,
                **run_options,
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
        if verifier is not None and state.phase not in {"synthesis", "complete"}:
            raise AgentLoopError(
                "Blind verifier did not authorize the terminal synthesis phase"
            )
        answer = _deterministic_terminal_answer(task.output_contract, output)
        terminal = self._terminal_source(state, answer, task.output_contract)
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
            verification_steps=tuple(state.verification_steps),
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

    @staticmethod
    def _predecision_run_config(sdk: object, state: _NativeState) -> object:
        """Fresh Manager H_t via SDK input filter, without modifying the SDK loop."""
        constructor = sdk.__dict__.get("RunConfig")
        if constructor is None:
            raise RuntimeError("pre-decision protocol requires SDK model-input filter APIs")

        async def filter_input(data: Any) -> object:
            model_data = data.model_data
            items: list[Any] = list(model_data.input)
            if (
                state.visibility == ProfileVisibility.AWARE
                and data.agent.name == state.root_agent.logical_agent_id
            ):
                decision_id = (
                    f"{state.root_agent.logical_agent_id}:native-turn:"
                    f"{state.turn_by_agent.get(state.root_agent.logical_agent_id, 0) + 1}"
                )
                profile = await state.gateway.profile_overview()
                state.emit(
                    "logical.profile.predecision",
                    {"decision_id": decision_id, "profile": profile.model_dump(mode="json")},
                )
                items = [item for item in items if not is_profile_message(item)]
                items.append({
                    "role": "user",
                    "content": PROFILE_MESSAGE_PREFIX + profile.model_dump_json(),
                })
            return type(model_data)(input=items, instructions=model_data.instructions)

        return constructor(call_model_input_filter=filter_input, tracing_disabled=True)

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
        tool_use_behavior: object | None = None,
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
        if tool_use_behavior is not None:
            kwargs["tool_use_behavior"] = tool_use_behavior
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
            return json.dumps(
                {
                    "assignment": options["params"],
                    "static_capability_contract": state.static_capabilities.model_dump(
                        mode="json"
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            )

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
            parent = state.root_agent.logical_agent_id
            call_id = str(getattr(context, "tool_call_id", "specialist"))
            if state.phase == "synthesis":
                return self._record_logical_failure(
                    state,
                    f"{parent}:{call_id}",
                    parent,
                    "phase_restricted",
                    "synthesis phase permits only invoke_model or a final response",
                )
            request = SpecialistRequest.model_validate_json(input_json)
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
                return json.dumps(
                    {
                        "specialist_answer": answer,
                        "produced_artifact_ids": handoff,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            finally:
                async with state.state_lock:
                    state.active_subagents -= 1

        tool.on_invoke_tool = invoke
        return tool

    def _manager_tool_use_behavior(
        self,
        sdk: object,
        state: _NativeState,
    ) -> object | None:
        if state.blind_verifier is None:
            return None
        result_constructor = sdk.__dict__["ToolsToFinalOutputResult"]

        async def after_batch(context: object, tool_results: list[object]) -> object:
            del context
            if not tool_results:
                return result_constructor(is_final_output=False, final_output=None)
            telemetry = await self._verify_manager_batch(state)
            if telemetry.result.status == "complete":
                raw_candidate, action_id = _latest_terminal_candidate(state)
                candidate = _deterministic_terminal_answer(
                    state.task_view.output_contract,
                    raw_candidate,
                )
                state.emit(
                    "logical.terminal.candidate_selected",
                    {
                        "source_action_id": action_id,
                        "verification_index": telemetry.verification_index,
                        "graph_version": telemetry.graph_version,
                        "deterministic_format_extraction": candidate != raw_candidate,
                    },
                )
                return result_constructor(
                    is_final_output=True,
                    final_output=candidate,
                )
            _attach_verification_feedback(tool_results[-1], telemetry)
            return result_constructor(is_final_output=False, final_output=None)

        return after_batch

    async def _verify_manager_batch(
        self,
        state: _NativeState,
    ) -> VerificationTelemetry:
        verifier = state.blind_verifier
        if verifier is None:
            raise RuntimeError("Blind verifier is not configured")
        async with state.state_lock:
            if state.verifier_calls >= state.budget.max_verifier_calls:
                raise AgentLoopError("verifier call budget exhausted")
            state.verifier_calls += 1
            verification_index = state.verifier_calls
            observations = tuple(
                VerifierObservation(
                    action_id=item.action_id,
                    owner_agent_id=item.owner_agent_id,
                    succeeded=item.succeeded,
                    output=item.output,
                    produced_information=item.produced_information,
                    failure_code=item.failure_code,
                    failure_message=item.failure_message,
                )
                for item in state.observations
            )
            operator_descriptions = {
                item.operator: item.description
                for item in state.static_capabilities.operators
            }
            actions = tuple(
                _verifier_action_view(action, operator_descriptions)
                for action in state.actions.values()
            )
            produced_by_id = {
                item.artifact_id: item
                for observation in observations
                for item in observation.produced_information
            }
            context = VerificationContext(
                task=state.task_view,
                workflow=state.graph.snapshot(),
                actions=actions,
                observations=observations,
                produced_artifacts=tuple(
                    produced_by_id[key] for key in sorted(produced_by_id)
                ),
                phase=cast(Any, state.phase),
                remaining_budget=VerifierBudgetView(
                    remaining_manager_turns=max(
                        state.budget.max_manager_turns - state.manager_turns,
                        0,
                    ),
                    remaining_tool_model_calls=max(
                        state.budget.max_tool_model_calls - state.tool_model_calls,
                        0,
                    ),
                    remaining_created_subagents=max(
                        state.budget.max_created_subagents - state.created_subagents,
                        0,
                    ),
                    remaining_verifier_calls=max(
                        state.budget.max_verifier_calls - state.verifier_calls,
                        0,
                    ),
                ),
            )
            state.emit(
                "logical.verification.started",
                {
                    "verification_index": verification_index,
                    "graph_version": context.workflow.version,
                    "phase": context.phase,
                },
            )
            if state.record_input_provenance:
                provenance = context.model_dump(mode="json")
                state.emit(
                    "logical.verification.input",
                    {
                        "verification_index": verification_index,
                        "context": provenance,
                        "context_sha256": provenance_sha256(provenance),
                    },
                )
        started = perf_counter()
        try:
            telemetry = await invoke_verifier(
                verifier,
                context,
                verification_index=verification_index,
            )
        except Exception as exc:
            async with state.state_lock:
                state.emit(
                    "logical.verification.failed",
                    {
                        "verification_index": verification_index,
                        "graph_version": context.workflow.version,
                        "phase": context.phase,
                        "latency_ms": (perf_counter() - started) * 1000,
                        "exception_type": type(exc).__name__,
                    },
                )
            raise AgentLoopError(
                f"Blind verifier failed: {type(exc).__name__}: {exc}"
            ) from exc
        raw_verdict = telemetry.result
        if (
            raw_verdict.status == "complete"
            and (
                state.task_view.output_contract.format == OutputFormat.CHOICE
                or state.task_view.output_contract.canonical_labels is not None
            )
        ):
            raw_candidate, _ = _latest_terminal_candidate(state)
            try:
                if state.task_view.output_contract.canonical_labels is not None:
                    _validate_answer_contract(
                        state.task_view.output_contract, raw_candidate.strip()
                    )
                else:
                    _leading_declared_choice(state.task_view.output_contract, raw_candidate)
            except AgentLoopError:
                telemetry = telemetry.model_copy(
                    update={
                        "result": VerificationResult(
                            status="ready_for_synthesis",
                            failure_stage="none",
                            reason=(
                                "The semantic answer candidate does not satisfy the declared "
                                "terminal label contract. Perform terminal synthesis again "
                                "under the task's output contract."
                            ),
                            missing_requirements=(),
                        )
                    }
                )
        async with state.state_lock:
            state.verification_steps.append(telemetry)
            if raw_verdict != telemetry.result:
                state.emit(
                    "logical.verification.terminal_contract_enforced",
                    {
                        "verification_index": telemetry.verification_index,
                        "graph_version": telemetry.graph_version,
                        "original_status": raw_verdict.status,
                        "effective_status": telemetry.result.status,
                        "output_format": state.task_view.output_contract.format.value,
                    },
                )
            state.emit(
                "logical.verification",
                {
                    "verification_index": telemetry.verification_index,
                    "graph_version": telemetry.graph_version,
                    "status": telemetry.result.status,
                    "failure_stage": telemetry.result.failure_stage,
                    "reason": telemetry.result.reason,
                    "missing_requirements": list(
                        telemetry.result.missing_requirements
                    ),
                    "latency_ms": telemetry.latency_ms,
                    "input_tokens": telemetry.input_tokens,
                    "output_tokens": telemetry.output_tokens,
                    "remaining_budget": telemetry.remaining_budget.model_dump(
                        mode="json"
                    ),
                },
            )
            previous = state.phase
            if telemetry.result.status == "complete":
                state.phase = "complete"
            elif telemetry.result.status == "ready_for_synthesis":
                state.phase = "synthesis"
            else:
                state.phase = "evidence_collection"
            if state.phase != previous:
                state.emit(
                    "logical.phase.changed",
                    {
                        "from": previous,
                        "to": state.phase,
                        "verification_index": telemetry.verification_index,
                        "graph_version": telemetry.graph_version,
                    },
                )
        return telemetry

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
        if state.phase == "synthesis" and spec.operator_id != "invoke_model":
            return self._record_logical_failure(
                state,
                action_id,
                owner,
                "phase_restricted",
                "synthesis phase permits only invoke_model or a final response",
            )
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
        if state.record_input_provenance:
            state.emit(
                "logical.action.selected",
                {
                    "action_id": action_id,
                    "decision_id": f"{owner}:native-turn:{state.turn_by_agent.get(owner, 1)}",
                    "logical_agent_id": owner,
                    "operator": spec.operator_id,
                    "selected_tool_arguments": payload,
                },
            )
        arguments = _with_schema_defaults(
            spec.argument_schema,
            cast(dict[str, Any], payload.get("arguments", {})),
        )
        arguments = _namespace_output_arguments(
            state.artifact_namespace,
            spec.operator_id,
            arguments,
        )
        arguments = _with_terminal_output_requirement(
            state,
            owner,
            spec.operator_id,
            arguments,
        )
        try:
            action = _logical_action(spec, action_id, owner, inputs, arguments, payload)
            _validate_dynamic_output_contract(state, action)
        except (ValueError, TypeError) as exc:
            return self._record_logical_failure(
                state, action_id, owner, "semantic_validation_failed", str(exc)
            )

        async with state.state_lock:
            if state.tool_model_calls >= state.budget.max_tool_model_calls:
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
            if isinstance(action, LogicalModelAction):
                self._emit_model_requirements(state, action)
            state.emit(
                "logical.batch.validation",
                {**validation, "status": "accepted", "all_inputs_materialized": True},
            )
            state.tool_model_calls += 1
            state.actions[action_id] = action
            if state.record_input_provenance:
                state.emit(
                    "logical.action.prepared",
                    {
                        "action": action.model_dump(mode="json"),
                        "input_lineage": {
                            artifact_id: next(
                                (
                                    producer.action_id for producer in state.actions.values()
                                    if any(o.artifact_id == artifact_id for o in producer.outputs)
                                ),
                                "initial_task_artifact",
                            )
                            for artifact_id in action.inputs
                        },
                    },
                )
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
            if state.record_input_provenance:
                state.emit("action.started", {
                    "action_id": action_id, "decision_id": decision_id,
                    "logical_agent_id": owner,
                })

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
            if isinstance(action, LogicalModelAction):
                self._emit_model_outcome(state, action, outcome)
            if state.record_input_provenance:
                state.emit("action.completed", {
                    "action_id": action_id, "decision_id": decision_id,
                    "logical_agent_id": owner, "succeeded": observation.succeeded,
                })
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
            if state.record_input_provenance:
                state.emit("action.completed", {
                    "action_id": action_id, "decision_id": decision_id,
                    "logical_agent_id": owner, "succeeded": False,
                })
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

    @staticmethod
    def _emit_model_requirements(
        state: _NativeState,
        action: LogicalModelAction,
    ) -> None:
        matches = state.static_capabilities.matching_model_classes(action.requirements)
        state.emit(
            "logical.model.requirements",
            {
                "action_id": action.action_id,
                "owner_agent_id": action.owner_agent_id,
                "requested": action.requirements.model_dump(mode="json"),
                "matching_model_classes": list(matches),
                "static_feasible": bool(matches),
                "classification": "static_feasible" if matches else "static_impossible",
            },
        )

    @staticmethod
    def _emit_model_outcome(
        state: _NativeState,
        action: LogicalModelAction,
        outcome: PhysicalExecutionOutcome,
    ) -> None:
        execution = outcome.execution
        state.emit(
            "logical.model.outcome",
            {
                "action_id": action.action_id,
                "owner_agent_id": action.owner_agent_id,
                "succeeded": outcome.observation.succeeded,
                "failure_code": outcome.observation.failure_code,
                "static_feasible": bool(
                    state.static_capabilities.matching_model_classes(
                        action.requirements
                    )
                ),
                "physical_selection_succeeded": outcome.selection is not None,
                "reached_model_inference": (
                    execution is not None and execution.model_telemetry is not None
                ),
            },
        )

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
    def _manager_input(
        task: AgentTaskView,
        static_capabilities: StaticCapabilityContract,
    ) -> str:
        return json.dumps(
            {
                "task": task.model_dump(mode="json"),
                "static_capability_contract": static_capabilities.model_dump(
                    mode="json"
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _terminal_source(
        state: _NativeState,
        answer: str,
        contract: OutputContract,
    ) -> str:
        matches: list[str] = []
        for item in state.observations:
            candidate = item.output.get("text")
            if (
                item.owner_agent_id != state.root_agent.logical_agent_id
                or not item.succeeded
                or not isinstance(state.actions.get(item.action_id), LogicalModelAction)
                or not isinstance(candidate, str)
            ):
                continue
            try:
                normalized = _deterministic_terminal_answer(contract, candidate)
            except AgentLoopError:
                continue
            if normalized == answer:
                matches.append(item.action_id)
        if not matches:
            raise AgentLoopError(
                "terminal answer must deterministically derive from a successful manager "
                "invoke_model result"
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


def _with_schema_defaults(
    schema: dict[str, Any] | None,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(arguments)
    if schema is None:
        return normalized
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return normalized
    for name, value in cast(dict[object, object], properties).items():
        if not isinstance(name, str) or name in normalized or not isinstance(value, dict):
            continue
        default = cast(dict[object, object], value).get("default")
        if default is not None:
            normalized[name] = copy.deepcopy(default)
    return normalized


def _with_terminal_output_requirement(
    state: _NativeState,
    owner: str,
    operator: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    contract = state.task_view.output_contract
    if (
        contract.canonical_labels is not None
        and owner == state.root_agent.logical_agent_id
        and operator == "invoke_model"
        and not arguments.get("output_artifact_id")
    ):
        prompt = arguments.get("prompt")
        if isinstance(prompt, str):
            return {
                **arguments,
                "prompt": prompt.rstrip() + "\n\nTerminal output contract: return exactly one "
                + f"declared label from {json.dumps(contract.canonical_labels)}. "
                + "No punctuation, Markdown, explanation, or wrapper.",
            }
    if (
        owner != state.root_agent.logical_agent_id
        or operator != "invoke_model"
        or contract.format != OutputFormat.CHOICE
        or contract.choices is None
    ):
        return arguments
    prompt = arguments.get("prompt")
    if not isinstance(prompt, str):
        return arguments
    choices = json.dumps(contract.choices, ensure_ascii=False, separators=(",", ":"))
    normalized = dict(arguments)
    normalized["prompt"] = (
        prompt.rstrip()
        + "\n\nTerminal output contract: begin the response with exactly one declared "
        + f"canonical choice label from {choices}. The label must be the first token and "
        + "may be followed by a delimiter and concise text. Do not put prose before the label."
    )
    return normalized


def _namespace_output_arguments(
    namespace: str,
    operator: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(arguments)
    key = "output_prefix" if operator == "sample_frames" else "output_artifact_id"
    value = normalized.get(key)
    if not isinstance(value, str) or not value:
        return normalized
    prefix = namespace.rstrip("/") + "/"
    normalized[key] = value if value.startswith(prefix) else prefix + value.lstrip("/")
    return normalized


def _validate_dynamic_output_contract(
    state: _NativeState,
    action: LogicalAction,
) -> None:
    if not isinstance(action, LogicalToolAction) or action.operator != "sample_frames":
        return
    if len(action.inputs) != 1:
        return
    duration = _known_video_duration(state, action.inputs[0])
    if duration is None:
        return
    interval = action.arguments.get("every_seconds")
    count = action.arguments.get("max_frames")
    if not isinstance(interval, (int, float)) or not isinstance(count, int):
        return
    if float(interval) * count <= duration:
        return
    raise ValueError(
        "sample_frames cannot materialize every declared output: "
        f"max_frames * every_seconds = {float(interval) * count:.3f}s exceeds "
        f"the known {duration:.3f}s input duration; lower max_frames or every_seconds"
    )


def _known_video_duration(state: _NativeState, artifact_id: str) -> float | None:
    for artifact in state.task_view.artifacts:
        if artifact.artifact_id != artifact_id or artifact.content_schema is None:
            continue
        return artifact.content_schema.duration_seconds
    for candidate in state.actions.values():
        if (
            not isinstance(candidate, LogicalToolAction)
            or candidate.operator != "extract_clip"
            or all(item.artifact_id != artifact_id for item in candidate.outputs)
        ):
            continue
        duration = candidate.arguments.get("duration_seconds")
        if isinstance(duration, (int, float)) and float(duration) > 0:
            return float(duration)
    return None


def _failure_result(action_id: str, owner: str, code: str, message: str) -> str:
    return LogicalObservation(
        action_id=action_id,
        owner_agent_id=owner,
        succeeded=False,
        failure_code=code,
        failure_message=message,
    ).model_dump_json(exclude_none=True)


def _attach_verification_feedback(
    tool_result: object,
    telemetry: VerificationTelemetry,
) -> None:
    original = getattr(tool_result, "output", None)
    parsed: dict[str, Any]
    if isinstance(original, str):
        try:
            decoded = json.loads(original)
        except json.JSONDecodeError:
            parsed = {"tool_result": original}
        else:
            parsed = (
                cast(dict[str, Any], decoded)
                if isinstance(decoded, dict)
                else {"tool_result": decoded}
            )
    else:
        parsed = {"tool_result": original}
    parsed["blind_verification"] = telemetry.result.model_dump(mode="json")
    parsed["remaining_logical_budget"] = telemetry.remaining_budget.model_dump(
        mode="json"
    )
    if telemetry.result.status == "ready_for_synthesis":
        parsed["verifier_feedback"] = (
            "The independent Blind verifier found the materialized semantic evidence "
            "sufficient. Stop evidence expansion and synthesize the requested answer "
            "from the currently available evidence."
        )
    else:
        parsed["verifier_feedback"] = (
            "The independent Blind verifier found the task incomplete. Continue from "
            "the stated semantic gaps; do not treat this verdict as a task answer."
        )
    updated = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    mutable_result = cast(Any, tool_result)
    mutable_result.output = updated
    run_item = getattr(tool_result, "run_item", None)
    if run_item is None:
        raise AgentLoopError("SDK tool batch has no result item for verifier feedback")
    run_item.output = updated
    raw_item = getattr(run_item, "raw_item", None)
    if isinstance(raw_item, dict):
        raw_item["output"] = updated
        return
    if hasattr(raw_item, "output"):
        try:
            mutable_raw_item = cast(Any, raw_item)
            mutable_raw_item.output = updated
            return
        except (AttributeError, TypeError):
            pass
    raise AgentLoopError("SDK tool result cannot carry verifier feedback")


def _latest_terminal_candidate(state: _NativeState) -> tuple[str, str]:
    for observation in reversed(state.observations):
        action = state.actions.get(observation.action_id)
        candidate = observation.output.get("text")
        if (
            observation.owner_agent_id == state.root_agent.logical_agent_id
            and observation.succeeded
            and isinstance(action, LogicalModelAction)
            and isinstance(candidate, str)
            and candidate.strip()
        ):
            return candidate.strip(), observation.action_id
    raise AgentLoopError(
        "Blind verifier returned complete without a successful manager model candidate"
    )


def _verifier_action_view(
    action: LogicalAction,
    operator_descriptions: dict[str, str],
) -> VerifierActionView:
    operator = "invoke_model" if isinstance(action, LogicalModelAction) else action.operator
    try:
        description = operator_descriptions[operator]
    except KeyError as exc:
        raise AgentLoopError(
            f"logical action has no static semantic operator description: {operator}"
        ) from exc
    if isinstance(action, LogicalModelAction):
        return VerifierActionView(
            action_id=action.action_id,
            owner_agent_id=action.owner_agent_id,
            action_type="model",
            operator=operator,
            description=description,
            inputs=action.inputs,
            outputs=action.outputs,
            prompt=action.prompt,
            requirements=action.requirements,
        )
    return VerifierActionView(
        action_id=action.action_id,
        owner_agent_id=action.owner_agent_id,
        action_type="tool",
        operator=operator,
        description=description,
        inputs=action.inputs,
        outputs=action.outputs,
        arguments=action.arguments,
    )


def _validate_output_contract(task: TaskContract, answer: str) -> None:
    _validate_answer_contract(task.output_contract, answer)


def _deterministic_terminal_answer(contract: OutputContract, answer: str) -> str:
    """Extract contract formatting without adding semantic reasoning.

    Choice extraction is intentionally narrow: a declared label must be exact,
    explicitly introduced, explicitly wrapped, or followed immediately by a
    formatting delimiter. Ambiguous free text remains invalid.
    """

    stripped = answer.strip()
    if contract.format != OutputFormat.CHOICE:
        _validate_answer_contract(contract, stripped)
        return stripped
    choices = contract.choices
    if choices is None:
        raise AgentLoopError("terminal answer violates the choice output contract")
    if stripped in choices:
        return stripped

    matches: set[str] = set()
    for choice in choices:
        label = re.escape(choice)
        patterns = (
            rf"(?is)^(?:answer|choice)\s*[:：]\s*{label}(?:\s|$|[.。:：;；,，\-–—])",
            rf"(?s)^\(\s*{label}\s*\)(?:\s|$|[.。:：;；,，\-–—])",
            rf"(?s)^\[\s*{label}\s*\](?:\s|$|[.。:：;；,，\-–—])",
            rf"(?s)^\*\*\s*{label}\s*(?:[.。])?\*\*(?:\s|$|[.:：;；,，\-–—])",
            rf"(?s)^__\s*{label}\s*(?:[.。])?__(?:\s|$|[.:：;；,，\-–—])",
            rf"(?s)^{label}(?:$|[.。:：;；,，\-–—\r\n])",
        )
        if any(re.match(pattern, stripped) is not None for pattern in patterns):
            matches.add(choice)
    if len(matches) != 1:
        raise AgentLoopError("terminal answer violates the choice output contract")
    return next(iter(matches))


def _leading_declared_choice(contract: OutputContract, answer: str) -> str:
    choices = contract.choices
    if contract.format != OutputFormat.CHOICE or choices is None:
        raise AgentLoopError("terminal answer violates the choice output contract")
    stripped = answer.strip()
    matches = {
        choice
        for choice in choices
        if re.match(
            rf"(?s)^{re.escape(choice)}(?:$|\s|[.。:：;；,，\-–—])",
            stripped,
        )
        is not None
    }
    if len(matches) != 1:
        raise AgentLoopError("terminal answer violates the choice output contract")
    return next(iter(matches))


def _validate_answer_contract(contract: OutputContract, answer: str) -> None:
    if contract.canonical_labels is not None:
        if answer not in contract.canonical_labels:
            raise AgentLoopError("terminal answer violates the canonical-label output contract")
        return
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
