import json
from collections import deque
from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import ValidationError

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import TaskContract
from infra_joint.core.workflow import (
    WorkflowPlan,
    feasible_operations_for_model_instance,
)
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
        plan.validate_against(
            task,
            self._environment,
            self._registry,
            workload.available_operations,
        )
        plan.terminal_model_node()
        available_instances = {
            item.model_instance_id for item in workload.available_model_instances
        }
        for agent in plan.agents:
            if agent.model_instance_id not in available_instances:
                raise ValueError(
                    f"logical agent uses unavailable model instance: {agent.model_instance_id}"
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
            "system_context_preflight_guidance": self._context_preflight_guidance(
                task, workload
            ),
            "system_feasible_operations_by_model_instance": {
                instance.model_instance_id: sorted(
                    feasible_operations_for_model_instance(
                        instance.model_instance_id,
                        self._environment,
                        self._registry,
                        workload.available_operations,
                    )
                )
                for instance in workload.available_model_instances
            },
            "available_operator_schemas": tools,
        }
        shape: dict[str, Any] = {
            "agents": [
                {
                    "agent_id": "logical-agent-id",
                    "role": "semantic role",
                    "objective": "role objective",
                    "model_instance_id": "one available fixed model instance",
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
                "Artifact content_schema fields are authoritative. Operator field arguments "
                "such as text_field, field, fields, group_by, and derivation sources must name "
                "fields declared by the relevant input artifact schema.",
                "Model modalities and context limits are semantic capability contracts, not "
                "infrastructure state. Before every invoke_model node, keep the prompt plus all "
                "text/JSON input artifact upper bounds and image_token_cost values within that "
                "agent's context_window after reserved_output_tokens. UTF-8 artifact bytes are "
                "the conservative text-token upper bound used by runtime.",
                "No operator implicitly summarizes or truncates. BM25 returns complete top-k "
                "records, aggregate_artifacts concatenates complete record arrays, and "
                "select_fields projects fields without shortening their values. Use their "
                "declared schemas and bounded-size facts accordingly.",
                "Plan validation will reject an oversized model input and will not lower top_k "
                "or repair the workflow. For a BM25 result sent to a model, conservatively bound "
                "its bytes as 2 + top_k * (input max_record_bytes + 129), then add the model "
                "prompt bytes, task objective bytes, the 2048-byte safety margin, and reserved "
                "output. As a concrete capability example, when max_record_bytes is about 3200 "
                "and context_window is 16384, top_k=3 is safe while top_k=12 or 20 is not. "
                "Retrieve separately from shards if useful, but keep the total records entering "
                "the final model within the same bound.",
                "For a fan-in over every record artifact listed in "
                "system_context_preflight_guidance, obey its "
                "max_equal_bm25_top_k_per_artifact and max_invoke_prompt_bytes values. A zero "
                "cap means the complete fan-in is illegal: use separately bounded model calls "
                "to materialize concise evidence notes before terminal synthesis. These are "
                "system-derived semantic context limits, not infrastructure hints.",
                "The task objective and output contract are prompt context, not artifact IDs; "
                "never put names such as task, objective, question, or output_contract in a "
                "node.inputs list unless that exact ID appears in initial_artifacts or is produced "
                "by an upstream node.",
                "For several large shards, if the union of retrieved records would exceed the "
                "final model context, do not aggregate those records directly into the final call. "
                "Use explicit invoke_model nodes on separately bounded retrieval results to "
                "materialize concise evidence notes, then pass those bounded text outputs to the "
                "terminal model. This is an explicit planned semantic action, never an implicit "
                "runtime summary.",
                "The system defines each model instance's feasible operators. Select node "
                "operators only from system_feasible_operations_by_model_instance for the "
                "owning agent's binding. Do not declare agent capabilities or action spaces.",
                "The fixed model instances may be shared by multiple logical agents.",
                "Do not decide hosts, devices, artifact placement, transfers, network routes, "
                "deployment migration, or generic-operator placement.",
                "Every non-task input produced by a node must have an exact WorkflowEdge.",
                "Create exactly one terminal sink node. It must use invoke_model and produce "
                "the benchmark answer inline. Every other branch must feed that terminal "
                "synthesis node.",
                "The terminal node prompt must require exactly the task output_contract. For a "
                "choice contract, return only one declared label with no explanation.",
                "For sample_frames, node.outputs must enumerate every deterministic generated "
                "ID from output_prefix/frame-000001.jpg through max_frames, and downstream "
                "nodes must consume those exact IDs. The filename component is always the literal "
                "frame-NNNNNN.jpg; for output_prefix=clipframe the first output is exactly "
                "clipframe/frame-000001.jpg, never clipframe/clipframe-000001.jpg.",
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

    @staticmethod
    def _context_preflight_guidance(
        task: TaskContract,
        workload: WorkloadSpec,
    ) -> list[dict[str, Any]]:
        """Expose conservative fan-in bounds without physical infrastructure state."""

        record_artifacts = [
            artifact
            for artifact in workload.artifacts
            if artifact.content_schema is not None
            and artifact.content_schema.kind == "record_array"
            and artifact.content_schema.max_record_bytes is not None
        ]
        if not record_artifacts:
            return []
        max_invoke_prompt_bytes = 1_024
        fixed_input_bytes = (
            len(task.objective.encode("utf-8"))
            + 2_048
            + max_invoke_prompt_bytes
        )
        per_equal_top_k_bytes = sum(
            artifact.content_schema.max_record_bytes + 129
            for artifact in record_artifacts
            if artifact.content_schema is not None
            and artifact.content_schema.max_record_bytes is not None
        )
        json_container_bytes = 2 * len(record_artifacts)
        guidance: list[dict[str, Any]] = []
        for instance in workload.available_model_instances:
            available_bytes = (
                instance.context_window
                - instance.reserved_output_tokens
                - fixed_input_bytes
                - json_container_bytes
            )
            guidance.append(
                {
                    "model_instance_id": instance.model_instance_id,
                    "record_artifact_ids": [
                        artifact.artifact_id for artifact in record_artifacts
                    ],
                    "max_equal_bm25_top_k_per_artifact": max(
                        0, available_bytes // per_equal_top_k_bytes
                    ),
                    "max_invoke_prompt_bytes": max_invoke_prompt_bytes,
                    "assumption": (
                        "one BM25 result from every listed artifact enters the same "
                        "invoke_model call"
                    ),
                }
            )
        return guidance
