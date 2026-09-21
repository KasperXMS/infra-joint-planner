# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict, cast
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from infra_joint.core.action import FinishDecision, JointAction, JointDecision
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
from infra_joint.runtime.executor import ActionExecutor, ExecutionResult


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


class RunResult(TypedDict):
    final_answer: str
    evaluation: EvaluationResult
    decisions: tuple[JointDecision, ...]
    observations: tuple[ExecutionResult, ...]


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
        decision = await self._planner.decide(context)
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="planner.end",
            payload={"decision": decision.model_dump(mode="json")},
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
        answer = await self._finalizer.finalize(
            state["task"],
            tuple(state["decisions"]),
            tuple(state["observations"]),
        )
        trace_state = self._emit_from_values(
            run_id=state["run_id"],
            event_index=cast(int, trace_state["event_index"]),
            parent_event_id=cast(str, trace_state["parent_event_id"]),
            event_type="finalize.end",
            payload={"answer": answer},
        )
        return {"final_answer": answer, **trace_state}

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

    async def run(self, task: TaskContract, *, run_id: str | None = None) -> RunResult:
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
        initial: PlanningState = {
            "run_id": resolved_run_id,
            "event_index": 1,
            "parent_event_id": first_event_id,
            "task": task,
            "remaining_steps": self._max_planning_steps,
            "decisions": [],
            "observations": [],
            "infrastructure": None,
            "pending_decision": None,
            "final_answer": None,
            "evaluation": None,
        }
        state = cast(PlanningState, await self._graph.ainvoke(initial))
        final_answer = state["final_answer"]
        evaluation = state["evaluation"]
        if final_answer is None or evaluation is None:
            raise RuntimeError("planning graph ended without finalization and evaluation")
        self._emit_from_values(
            run_id=resolved_run_id,
            event_index=state["event_index"],
            parent_event_id=state["parent_event_id"],
            event_type="run.end",
            payload={"execution_completed": True},
        )
        return RunResult(
            final_answer=final_answer,
            evaluation=evaluation,
            decisions=tuple(state["decisions"]),
            observations=tuple(state["observations"]),
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
