# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from infra_joint.core.action import FinishDecision, JointAction, JointDecision
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import TaskContract
from infra_joint.evaluation.evaluator import EvaluationResult, Evaluator
from infra_joint.infrastructure.observer import InfrastructureObserver
from infra_joint.planning.finalize import Finalizer
from infra_joint.planning.planner import BlindPlanner, BlindPlannerContext
from infra_joint.runtime.executor import ActionExecutor, ExecutionResult


class PlanningState(TypedDict):
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
    ) -> None:
        if max_planning_steps < 1:
            raise ValueError("max_planning_steps must be positive")
        self._planner = planner
        self._observer = observer
        self._executor = executor
        self._finalizer = finalizer
        self._evaluator = evaluator
        self._max_planning_steps = max_planning_steps
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

    async def _observe(self, state: PlanningState) -> dict[str, InfrastructureState]:
        del state
        return {"infrastructure": await self._observer.observe()}

    @staticmethod
    def _route_after_observe(state: PlanningState) -> Literal["plan", "finalize"]:
        return "plan" if state["remaining_steps"] > 0 else "finalize"

    async def _plan(self, state: PlanningState) -> dict[str, object]:
        context = BlindPlannerContext(
            task=state["task"],
            decisions=tuple(state["decisions"]),
            observations=tuple(state["observations"]),
            remaining_steps=state["remaining_steps"],
        )
        decision = await self._planner.decide(context)
        return {
            "pending_decision": decision,
            "decisions": [*state["decisions"], decision],
            "remaining_steps": state["remaining_steps"] - 1,
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
        observation = await self._executor.execute(decision, infrastructure)
        return {"observations": [*state["observations"], observation]}

    async def _finalize(self, state: PlanningState) -> dict[str, str]:
        answer = await self._finalizer.finalize(
            state["task"],
            tuple(state["decisions"]),
            tuple(state["observations"]),
        )
        return {"final_answer": answer}

    async def _evaluate(self, state: PlanningState) -> dict[str, EvaluationResult]:
        answer = state["final_answer"]
        if answer is None:
            raise RuntimeError("evaluate node requires a final answer")
        result = await self._evaluator.evaluate(state["task"], answer)
        return {"evaluation": result}

    async def run(self, task: TaskContract) -> RunResult:
        initial: PlanningState = {
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
        return RunResult(
            final_answer=final_answer,
            evaluation=evaluation,
            decisions=tuple(state["decisions"]),
            observations=tuple(state["observations"]),
        )
