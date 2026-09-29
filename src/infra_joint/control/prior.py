from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, ValidationError

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import StaticCapabilityContract
from infra_joint.control.workflow import SemanticWorkflowPlan, canonical_sha256
from infra_joint.control.workflow_validation import validate_semantic_workflow
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.planner import CompletionBackend
from infra_joint.worker.model_backend import ModelRequest


class PriorWorkflowGenerator(Protocol):
    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> SemanticWorkflowPlan: ...


class StaticPriorWorkflowGenerator:
    def __init__(self, plan: SemanticWorkflowPlan, registry: OperatorRegistry) -> None:
        self._plan = plan
        self._registry = registry

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> SemanticWorkflowPlan:
        if self._plan.version != 0:
            raise ValueError("prior workflow G0 must have version zero")
        validate_semantic_workflow(self._plan, task, capabilities, self._registry)
        return self._plan


class LLMPriorWorkflowGenerator:
    """Generate a complete semantic G0 without any infrastructure input."""

    def __init__(self, backend: CompletionBackend, registry: OperatorRegistry) -> None:
        self._backend = backend
        self._registry = registry

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> SemanticWorkflowPlan:
        completion = await self._backend.invoke(
            ModelRequest(prompt=self.render_prompt(task, capabilities))
        )
        try:
            plan = SemanticWorkflowPlan.model_validate_json(completion.text)
        except ValidationError as exc:
            raise ValueError("prior generator returned an invalid semantic workflow") from exc
        if plan.version != 0:
            raise ValueError("prior workflow G0 must have version zero")
        validate_semantic_workflow(plan, task, capabilities, self._registry)
        return plan

    def render_prompt(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> str:
        payload = {
            "task": AgentTaskView.from_contract(task).model_dump(mode="json", by_alias=True),
            "static_capabilities": capabilities.model_dump(mode="json"),
            "workflow_output_schema": SemanticWorkflowPlan.model_json_schema(),
        }
        return "\n".join(
            (
                "Produce one complete infrastructure-independent semantic workflow G0.",
                "Use only the finite system-owned actions and abstract model requirements.",
                "Never mention workers, devices, deployments, placement, routes, bandwidth, "
                "latency, queue, load, evaluator metadata, gold, or source references.",
                "Return exactly one semantic-workflow-v1 JSON object with no Markdown.",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )


class FrozenPriorWorkflow(ContractModel):
    schema_version: Literal["frozen-prior-workflow-v1"] = "frozen-prior-workflow-v1"
    generator_version: Literal["prior-generator-v1"] = "prior-generator-v1"
    task_id: str = Field(min_length=1)
    task_view_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_model: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_at: datetime
    plan: SemanticWorkflowPlan

    @classmethod
    def create(
        cls,
        *,
        task: TaskContract,
        plan: SemanticWorkflowPlan,
        capabilities: StaticCapabilityContract,
        public_bundle_sha256: str,
        prior_model: str,
        prompt: str,
    ) -> FrozenPriorWorkflow:
        if plan.version != 0:
            raise ValueError("frozen prior workflow G0 must have version zero")
        return cls(
            task_id=task.task_id,
            task_view_sha256=canonical_sha256(
                AgentTaskView.from_contract(task).model_dump(mode="json", by_alias=True)
            ),
            public_bundle_sha256=public_bundle_sha256,
            plan_sha256=plan.canonical_sha256(),
            prior_model=prior_model,
            prompt_sha256=canonical_sha256(prompt),
            capability_sha256=canonical_sha256(capabilities.model_dump(mode="json")),
            generated_at=datetime.now(UTC),
            plan=plan,
        )

    def verify(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        public_bundle_sha256: str,
    ) -> None:
        if self.plan.version != 0:
            raise ValueError("frozen prior workflow is not G0")
        expected_task = canonical_sha256(
            AgentTaskView.from_contract(task).model_dump(mode="json", by_alias=True)
        )
        expected_capabilities = canonical_sha256(capabilities.model_dump(mode="json"))
        if self.task_id != task.task_id or self.task_view_sha256 != expected_task:
            raise ValueError("frozen prior does not match the sanitized task")
        if self.public_bundle_sha256 != public_bundle_sha256:
            raise ValueError("frozen prior does not match the public artifact bundle")
        if self.capability_sha256 != expected_capabilities:
            raise ValueError("frozen prior does not match the static capability contract")
        if self.plan_sha256 != self.plan.canonical_sha256():
            raise ValueError("frozen prior plan hash mismatch")


class PriorWorkflowStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def path_for(self, task_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", task_id).strip("._") or "task"
        return self._root / f"{safe}.json"

    def save(self, frozen: FrozenPriorWorkflow) -> Path:
        path = self.path_for(frozen.task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = frozen.model_dump_json(indent=2)
        if path.exists():
            existing = FrozenPriorWorkflow.model_validate_json(path.read_text(encoding="utf-8"))
            if existing != frozen:
                raise FileExistsError("refusing to overwrite a different frozen prior workflow")
            return path
        path.write_text(rendered + "\n", encoding="utf-8")
        return path

    def load(self, task_id: str) -> FrozenPriorWorkflow:
        return FrozenPriorWorkflow.model_validate_json(
            self.path_for(task_id).read_text(encoding="utf-8")
        )
