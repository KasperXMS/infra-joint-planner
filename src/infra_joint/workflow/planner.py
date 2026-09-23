import json
from collections import deque
from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import WorkflowPlan
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.planner import CompletionBackend, logical_task_payload
from infra_joint.worker.model_backend import ModelCallTelemetry, ModelRequest
from infra_joint.workflow.workload import WorkloadSpec


class WorkflowPlannerOutcome(ContractModel):
    plan: WorkflowPlan
    model_telemetry: ModelCallTelemetry | None = None


class WorkflowPlanningError(ValueError):
    pass


class WorkflowPlanner(Protocol):
    async def plan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> WorkflowPlannerOutcome: ...


class ScriptedWorkflowPlanner:
    """Deterministic plan-once planner used for substrate and scheduler tests."""

    def __init__(self, plans: Iterable[WorkflowPlan]) -> None:
        self._plans = deque(plans)

    async def plan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> WorkflowPlannerOutcome:
        del task, workload
        if not self._plans:
            raise RuntimeError("scripted workflow planner has no plan remaining")
        return WorkflowPlannerOutcome(plan=self._plans.popleft())


class LLMWorkflowPlanner:
    """Plan-once semantic MAS planner over fixed model instances.

    The prompt deliberately excludes worker placement, links, load, availability, and
    evaluator-private information. Physical execution-path decisions belong to the
    orchestrator and scheduler.
    """

    def __init__(
        self,
        backend: CompletionBackend,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
    ) -> None:
        self._backend = backend
        self._registry = registry
        self._environment = environment

    async def plan(
        self,
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> WorkflowPlannerOutcome:
        try:
            workload.validate_against(task, self._environment, self._registry)
        except (KeyError, ValueError) as exc:
            raise WorkflowPlanningError(str(exc)) from exc
        completion = await self._backend.invoke(
            ModelRequest(prompt=self.render_prompt(task, workload))
        )
        try:
            raw = json.loads(completion.text)
            plan = WorkflowPlan.model_validate(raw)
            self._validate_plan(plan, task, workload)
        except (json.JSONDecodeError, ValidationError, KeyError, ValueError) as exc:
            raise WorkflowPlanningError(
                "workflow planner must return one valid WorkflowPlan JSON object: "
                f"{exc}"
            ) from exc
        return WorkflowPlannerOutcome(plan=plan, model_telemetry=completion.telemetry)

    def _validate_plan(
        self,
        plan: WorkflowPlan,
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> None:
        plan.validate_against(task, self._environment, self._registry)
        plan.terminal_model_node()
        available_operations = set(workload.available_operations)
        available_instances = {
            item.model_instance_id for item in workload.available_model_instances
        }
        for agent in plan.agents:
            if agent.model_instance_id not in available_instances:
                raise ValueError(
                    f"logical agent uses unavailable model instance: {agent.model_instance_id}"
                )
            if not set(agent.allowed_operations) <= available_operations:
                raise ValueError(
                    f"logical agent uses operations outside WorkloadSpec: {agent.agent_id}"
                )
        agent_count = len(plan.agents)
        if workload.min_agents is not None and agent_count < workload.min_agents:
            raise ValueError("workflow has fewer agents than WorkloadSpec minimum")
        if workload.max_agents is not None and agent_count > workload.max_agents:
            raise ValueError("workflow has more agents than WorkloadSpec maximum")

    def render_prompt(self, task: TaskContract, workload: WorkloadSpec) -> str:
        available = set(workload.available_operations)
        tools = [
            tool
            for tool in self._registry.planner_tools()
            if tool["function"]["name"] in available
        ]
        workload_payload = workload.model_dump(mode="json")
        for instance in workload_payload["available_model_instances"]:
            instance["modalities"] = sorted(instance["modalities"])
        payload = {
            "task": logical_task_payload(task),
            "workload": workload_payload,
            "available_operator_schemas": tools,
        }
        shape: dict[str, Any] = {
            "agents": [
                {
                    "agent_id": "logical-agent-id",
                    "role": "semantic role",
                    "objective": "role objective",
                    "model_instance_id": "one available fixed model instance",
                    "allowed_operations": ["subset of available operations"],
                }
            ],
            "nodes": [
                {
                    "node_id": "node-id",
                    "agent_id": "logical-agent-id",
                    "operator": "available operator",
                    "inputs": ["task or upstream artifact id"],
                    "arguments": {},
                    "outputs": ["new artifact id"],
                }
            ],
            "edges": [
                {
                    "producer_node": "upstream-node-id",
                    "consumer_node": "downstream-node-id",
                    "artifact_id": "exact produced and consumed artifact id",
                }
            ],
        }
        return "\n".join(
            (
                "Synthesize one complete logical workflow DAG for the task.",
                "Plan once. Decide logical agents, roles, fixed model-instance bindings, "
                "semantic operations, dependencies, parallel branches, and final synthesis.",
                "Use multiple logical agents only when the task decomposition warrants it; "
                "a single logical agent is valid.",
                "Do not output next-action decisions or request replanning.",
                "Do not invent operators, model instances, task artifacts, or schemas.",
                "The fixed model instances may be shared by multiple logical agents.",
                "Do not decide hosts, devices, artifact placement, transfers, network routes, "
                "deployment migration, or generic-operator placement.",
                "Every non-task input produced by a node must have an exact WorkflowEdge.",
                "Create exactly one terminal sink node. It must use invoke_model and produce "
                "the benchmark answer inline. Every other branch must feed that terminal "
                "synthesis node.",
                "invoke_model may declare zero outputs for a terminal observation or exactly one "
                "text output for downstream agents. For a materialized model output, set "
                "arguments.output_artifact_id equal to that output ID, set "
                "output_semantic_type, and use output_media_type text/plain or application/json.",
                "Return exactly one JSON object with no Markdown or surrounding text.",
                f"WorkflowPlan form: {json.dumps(shape, separators=(',', ':'))}",
                "Planning input:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )
