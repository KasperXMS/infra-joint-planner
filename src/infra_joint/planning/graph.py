# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Literal, TypedDict, cast
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import Field

from infra_joint.core.action import FinishDecision, JointAction, JointDecision
from infra_joint.core.base import ContractModel
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.evaluation.evaluator import EvaluationResult, Evaluator
from infra_joint.evaluation.trace import TraceEvent, TraceSink
from infra_joint.infrastructure.observer import InfrastructureObserver
from infra_joint.planning.finalize import Finalizer
from infra_joint.planning.planner import (
    BlindPlanner,
    BlindPlannerContext,
    PlannerObservation,
)
from infra_joint.runtime.executor import (
    ActionExecutor,
    ArtifactTransferTelemetry,
    ExecutionResult,
)
from infra_joint.worker.model_backend import ModelCallTelemetry


class PlannerCallTelemetry(ContractModel):
    latency_ms: float = Field(ge=0)
    model: ModelCallTelemetry | None = None


class FinalizerCallTelemetry(ContractModel):
    latency_ms: float = Field(ge=0)
    model: ModelCallTelemetry | None = None


class RunTelemetry(ContractModel):
    e2e_latency_ms: float = Field(ge=0)
    planner_calls: tuple[PlannerCallTelemetry, ...]
    finalizer: FinalizerCallTelemetry
    total_operator_latency_ms: float = Field(ge=0)
    total_transfer_bytes: int = Field(ge=0)
    total_transfer_duration_ms: float = Field(ge=0)


class PlanningState(TypedDict):
    run_id: str
    event_index: int
    parent_event_id: str | None
    task: TaskContract
    remaining_steps: int
    decisions: list[JointDecision]
    observations: list[ExecutionResult]
    infrastructure: InfrastructureState | None
    pending_decision: JointDecision | None
    final_answer: str | None
    evaluation: EvaluationResult | None
    planner_telemetry: list[PlannerCallTelemetry]
    finalizer_telemetry: FinalizerCallTelemetry | None


class RunResult(TypedDict):
    final_answer: str
    evaluation: EvaluationResult
    decisions: tuple[JointDecision, ...]
    observations: tuple[ExecutionResult, ...]
    initial_transfers: tuple[ArtifactTransferTelemetry, ...]
    telemetry: RunTelemetry


class PlanningGraph:
    def __init__(
        self,
        planner: BlindPlanner,
        observer: InfrastructureObserver,
        executor: ActionExecutor,
        finalizer: Finalizer,
        evaluator: Evaluator,
        max_planning_steps: int,
        trace_sink: TraceSink | None = None,
    ) -> None:
        if max_planning_steps < 1:
            raise ValueError("max_planning_steps must be positive")
        self._planner = planner
        self._observer = observer
        self._executor = executor
        self._finalizer = finalizer
        self._evaluator = evaluator
        self._max_planning_steps = max_planning_steps
        self._trace_sink = trace_sink
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(PlanningState)
        graph.add_node("observe", self._observe)
        graph.add_node("plan", self._plan)
        graph.add_node("execute", self._execute)
        graph.add_node("finalize", self._finalize)
        graph.add_node("evaluate", self._evaluate)
        graph.add_edge(START, "observe")
        graph.add_conditional_edges(
            "observe",
            self._route_after_observe,
            {"plan": "plan", "finalize": "finalize"},
        )
        graph.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {"execute": "execute", "finalize": "finalize"},
        )
        graph.add_edge("execute", "observe")
        graph.add_edge("finalize", "evaluate")
        graph.add_edge("evaluate", END)
        return graph.compile()

    async def _observe(self, state: PlanningState) -> dict[str, object]:
        infrastructure = await self._observer.observe()
        trace_state = self._emit(
            state,
            "infra.snapshot",
            infrastructure.model_dump(mode="json"),
        )
        return {"infrastructure": infrastructure, **trace_state}

    @staticmethod
    def _route_after_observe(state: PlanningState) -> Literal["plan", "finalize"]:
        return "plan" if state["remaining_steps"] > 0 else "finalize"

    async def _plan(self, state: PlanningState) -> dict[str, object]:
        context = BlindPlannerContext(
            task=state["task"],
            decisions=tuple(state["decisions"]),
            observations=tuple(
                PlannerObservation.from_execution(observation)
                for observation in state["observations"]
            ),
            remaining_steps=state["remaining_steps"],
        )
        trace_state = self._emit(
            state,
            "planner.start",
            {"remaining_steps": state["remaining_steps"]},
        )
        started = perf_counter()
        outcome = await self._planner.decide(context)
        planner_telemetry = PlannerCallTelemetry(
            latency_ms=(perf_counter() - started) * 1000,
            model=outcome.model_telemetry,
        )
        decision = outcome.decision
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="planner.end",
            payload={
                "decision": decision.model_dump(mode="json"),
                "telemetry": planner_telemetry.model_dump(mode="json"),
            },
        )
        proposed_type = (
            "joint_action.proposed" if isinstance(decision, JointAction) else "finish.proposed"
        )
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type=proposed_type,
            payload=decision.model_dump(mode="json"),
        )
        return {
            "pending_decision": decision,
            "decisions": [*state["decisions"], decision],
            "remaining_steps": state["remaining_steps"] - 1,
            "planner_telemetry": [
                *state["planner_telemetry"],
                planner_telemetry,
            ],
            **trace_state,
        }

    @staticmethod
    def _route_after_plan(state: PlanningState) -> Literal["execute", "finalize"]:
        decision = state["pending_decision"]
        if decision is None:
            raise RuntimeError("plan node did not produce a decision")
        return "finalize" if isinstance(decision, FinishDecision) else "execute"

    async def _execute(self, state: PlanningState) -> dict[str, object]:
        decision = state["pending_decision"]
        if not isinstance(decision, JointAction):
            raise TypeError("execute node requires a JointAction")
        infrastructure = state["infrastructure"]
        if infrastructure is None:
            raise RuntimeError("execute node requires an infrastructure snapshot")
        trace_state = self._emit(
            state,
            "operator.start",
            {"operator": decision.semantic.operator},
        )
        observation = await self._executor.execute(decision, infrastructure)
        for transfer in observation.transfers:
            trace_state = self._emit_from_values(
                run_id=state["run_id"],
                event_index=cast(int, trace_state["event_index"]),
                parent_event_id=cast(str, trace_state["parent_event_id"]),
                event_type="artifact.transfer.end",
                payload=transfer.model_dump(mode="json"),
            )
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="operator.end",
            payload=observation.model_dump(mode="json"),
        )
        return {"observations": [*state["observations"], observation], **trace_state}

    async def _finalize(self, state: PlanningState) -> dict[str, object]:
        trace_state = self._emit(state, "finalize.start", {})
        started = perf_counter()
        outcome = await self._finalizer.finalize(
            state["task"],
            tuple(state["decisions"]),
            tuple(state["observations"]),
        )
        telemetry = FinalizerCallTelemetry(
            latency_ms=(perf_counter() - started) * 1000,
            model=outcome.model_telemetry,
        )
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="finalize.end",
            payload={
                "answer": outcome.answer,
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )
        return {
            "final_answer": outcome.answer,
            "finalizer_telemetry": telemetry,
            **trace_state,
        }

    async def _evaluate(self, state: PlanningState) -> dict[str, object]:
        answer = state["final_answer"]
        if answer is None:
            raise RuntimeError("evaluate node requires a final answer")
        result = await self._evaluator.evaluate(state["task"], answer)
        trace_state = self._emit(
            state,
            "evaluation.result",
            result.model_dump(mode="json"),
        )
        return {"evaluation": result, **trace_state}

    async def run(
        self,
        task: TaskContract,
        *,
        run_id: str | None = None,
        initial_transfers: tuple[ArtifactTransferTelemetry, ...] = (),
    ) -> RunResult:
        run_started = perf_counter()
        resolved_run_id = run_id or str(uuid4())
        first_event_id = "000000-task.start"
        self._append_trace(
            TraceEvent(
                run_id=resolved_run_id,
                step_id=first_event_id,
                parent_id=None,
                event_type="task.start",
                timestamp=datetime.now(UTC),
                payload={
                    "task_id": task.task_id,
                    "benchmark_id": task.benchmark_id,
                },
            )
        )
        event_index = 1
        parent_event_id = first_event_id
        for transfer in initial_transfers:
            trace_state = self._emit_from_values(
                run_id=resolved_run_id,
                event_index=event_index,
                parent_event_id=parent_event_id,
                event_type="artifact.materialize.end",
                payload=transfer.model_dump(mode="json"),
            )
            event_index = cast(int, trace_state["event_index"])
            parent_event_id = cast(str, trace_state["parent_event_id"])
        initial: PlanningState = {
            "run_id": resolved_run_id,
            "event_index": event_index,
            "parent_event_id": parent_event_id,
            "task": task,
            "remaining_steps": self._max_planning_steps,
            "decisions": [],
            "observations": [],
            "infrastructure": None,
            "pending_decision": None,
            "final_answer": None,
            "evaluation": None,
            "planner_telemetry": [],
            "finalizer_telemetry": None,
        }
        state = cast(PlanningState, await self._graph.ainvoke(initial))
        final_answer = state["final_answer"]
        evaluation = state["evaluation"]
        if final_answer is None or evaluation is None:
            raise RuntimeError("planning graph ended without finalization and evaluation")
        finalizer_telemetry = state["finalizer_telemetry"]
        if finalizer_telemetry is None:
            raise RuntimeError("planning graph ended without finalizer telemetry")
        telemetry = RunTelemetry(
            e2e_latency_ms=(perf_counter() - run_started) * 1000,
            planner_calls=tuple(state["planner_telemetry"]),
            finalizer=finalizer_telemetry,
            total_operator_latency_ms=sum(
                observation.operator_latency_ms for observation in state["observations"]
            ),
            total_transfer_bytes=sum(
                transfer.bytes_transferred
                for transfer in (
                    *initial_transfers,
                    *(
                        transfer
                        for observation in state["observations"]
                        for transfer in observation.transfers
                    ),
                )
            ),
            total_transfer_duration_ms=sum(
                transfer.duration_ms
                for transfer in (
                    *initial_transfers,
                    *(
                        transfer
                        for observation in state["observations"]
                        for transfer in observation.transfers
                    ),
                )
            ),
        )
        self._emit_from_values(
            run_id=resolved_run_id,
            event_index=state["event_index"],
            parent_event_id=state["parent_event_id"],
            event_type="run.end",
            payload={
                "execution_completed": True,
                "telemetry": telemetry.model_dump(mode="json"),
            },
        )
        return RunResult(
            final_answer=final_answer,
            evaluation=evaluation,
            decisions=tuple(state["decisions"]),
            observations=tuple(state["observations"]),
            initial_transfers=initial_transfers,
            telemetry=telemetry,
        )

    def _emit(
        self,
        state: PlanningState,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        return self._emit_from_values(
            run_id=state["run_id"],
            event_index=state["event_index"],
            parent_event_id=state["parent_event_id"],
            event_type=event_type,
            payload=payload,
        )

    def _emit_from_values(
        self,
        *,
        run_id: str,
        event_index: int,
        parent_event_id: str | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        step_id = f"{event_index:06d}-{event_type}"
        self._append_trace(
            TraceEvent(
                run_id=run_id,
                step_id=step_id,
                parent_id=parent_event_id,
                event_type=event_type,
                timestamp=datetime.now(UTC),
                payload=payload,
            )
        )
        return {"event_index": event_index + 1, "parent_event_id": step_id}

    def _append_trace(self, event: TraceEvent) -> None:
        if self._trace_sink is not None:
            self._trace_sink.append(event)
