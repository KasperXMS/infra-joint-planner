from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import Field, ValidationError

from infra_joint.agents.context import AgentTaskView
from infra_joint.control.contracts import LogicalAction, StaticCapabilityContract
from infra_joint.control.static_feasibility import StaticFeasibilityError
from infra_joint.control.workflow import (
    SemanticWorkflowPlan,
    WorkflowDependency,
    canonical_sha256,
)
from infra_joint.control.workflow_validation import (
    WorkflowValidationError,
    validate_semantic_workflow,
)
from infra_joint.core.base import ContractModel
from infra_joint.core.task import TaskContract
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.planning.planner import CompletionBackend
from infra_joint.worker.model_backend import ModelRequest


class PriorWorkflowGenerator(Protocol):
    def provenance(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> PriorGeneratorProvenance: ...

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        public_bundle_sha256: str | None = None,
    ) -> PriorGenerationResult: ...


class PriorGeneratorProvenance(ContractModel):
    generator_id: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PriorAttemptReference(ContractModel):
    attempt_id: str = Field(min_length=1)
    directory: str = Field(min_length=1)


class PriorGenerationResult(ContractModel):
    plan: SemanticWorkflowPlan
    provenance: PriorGeneratorProvenance
    attempt: PriorAttemptReference | None = None


class PriorWorkflowDraft(ContractModel):
    """Infrastructure-free semantic content proposed by the LLM prior generator."""

    schema_version: Literal["prior-workflow-draft-v1"] = "prior-workflow-draft-v1"
    actions: tuple[LogicalAction, ...]
    dependencies: tuple[WorkflowDependency, ...] = ()
    terminal_action_id: str = Field(min_length=1)

    def canonical_sha256(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class PriorAttemptStore:
    """Durable, secret-free evidence for exactly one prior backend attempt."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def begin(
        self,
        *,
        task: TaskContract,
        provenance: PriorGeneratorProvenance,
        capabilities: StaticCapabilityContract,
        public_bundle_sha256: str,
    ) -> PriorAttemptReference:
        attempt_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:12]}"
        directory = self._root / _safe_name(task.task_id) / attempt_id
        directory.mkdir(parents=True, exist_ok=False)
        _write_json(
            directory / "request_metadata.json",
            {
                "task_id": task.task_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "generator_id": provenance.generator_id,
                "generator_version": provenance.generator_version,
                "model_id": provenance.model_id,
                "prompt_sha256": provenance.prompt_sha256,
                "static_capability_sha256": canonical_sha256(
                    capabilities.model_dump(mode="json")
                ),
                "public_bundle_sha256": public_bundle_sha256,
                "attempt_id": attempt_id,
            },
        )
        return PriorAttemptReference(attempt_id=attempt_id, directory=str(directory))

    @staticmethod
    def persist_backend_failure(reference: PriorAttemptReference, exc: BaseException) -> None:
        directory = Path(reference.directory)
        (directory / "raw_completion.txt").write_text("", encoding="utf-8")
        _write_json(directory / "parse_result.json", {"status": "skipped"})
        _write_json(
            directory / "validation_result.json",
            {
                "attempt_status": "backend_failed",
                "exception_type": type(exc).__name__,
                "message": str(exc) or type(exc).__name__,
            },
        )

    @staticmethod
    def persist_raw_completion(reference: PriorAttemptReference, content: str) -> None:
        Path(reference.directory, "raw_completion.txt").write_text(content, encoding="utf-8")

    @staticmethod
    def persist_parse_failure(reference: PriorAttemptReference, exc: BaseException) -> None:
        directory = Path(reference.directory)
        _write_json(
            directory / "parse_result.json",
            {
                "status": "failed",
                "exception_type": type(exc).__name__,
                "message": str(exc) or type(exc).__name__,
            },
        )
        _write_json(
            directory / "validation_result.json",
            {"attempt_status": "parse_failed", "semantic_validation": "not_run"},
        )

    @staticmethod
    def persist_parsed_draft(
        reference: PriorAttemptReference,
        draft: PriorWorkflowDraft,
    ) -> None:
        directory = Path(reference.directory)
        _write_json(
            directory / "parse_result.json",
            {"status": "passed", "draft_sha256": draft.canonical_sha256()},
        )
        _write_json(directory / "draft.json", draft.model_dump(mode="json"))

    @staticmethod
    def persist_constructed_g0(
        reference: PriorAttemptReference,
        plan: SemanticWorkflowPlan,
    ) -> None:
        _write_json(
            Path(reference.directory, "constructed-g0.json"),
            plan.model_dump(mode="json"),
        )

    @staticmethod
    def persist_validation_failure(
        reference: PriorAttemptReference,
        exc: WorkflowValidationError,
    ) -> None:
        static_failure = isinstance(exc.__cause__, StaticFeasibilityError)
        status = "static_feasibility_failed" if static_failure else "semantic_validation_failed"
        _write_json(
            Path(reference.directory, "validation_result.json"),
            {
                "attempt_status": status,
                "semantic_validation": "passed" if static_failure else "failed",
                "static_feasibility": "failed" if static_failure else "not_run",
                "exception_type": type(exc).__name__,
                "message": str(exc) or type(exc).__name__,
            },
        )

    @staticmethod
    def persist_validation_passed(
        reference: PriorAttemptReference,
        plan: SemanticWorkflowPlan,
    ) -> None:
        _write_json(
            Path(reference.directory, "validation_result.json"),
            {
                "attempt_status": "awaiting_freeze",
                "semantic_validation": "passed",
                "static_feasibility": "passed",
                "constructed_g0_version": plan.version,
                "plan_sha256": plan.canonical_sha256(),
            },
        )

    @staticmethod
    def persist_frozen_success(
        reference: PriorAttemptReference,
        plan: SemanticWorkflowPlan,
        frozen_path: Path,
    ) -> None:
        _write_json(
            Path(reference.directory, "validation_result.json"),
            {
                "attempt_status": "frozen_success",
                "semantic_validation": "passed",
                "static_feasibility": "passed",
                "constructed_g0_version": plan.version,
                "plan_sha256": plan.canonical_sha256(),
                "frozen_prior_path": str(frozen_path),
            },
        )


class StaticPriorWorkflowGenerator:
    def __init__(
        self,
        plan: SemanticWorkflowPlan,
        registry: OperatorRegistry,
        *,
        generator_id: str = "static-prior",
    ) -> None:
        self._plan = plan
        self._registry = registry
        self._generator_id = generator_id

    def provenance(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> PriorGeneratorProvenance:
        del task, capabilities
        return PriorGeneratorProvenance(
            generator_id=self._generator_id,
            generator_version="static-prior-v1",
            model_id="static",
            prompt_sha256=canonical_sha256(
                {"kind": "static-prior", "plan_sha256": self._plan.canonical_sha256()}
            ),
        )

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        public_bundle_sha256: str | None = None,
    ) -> PriorGenerationResult:
        del public_bundle_sha256
        if self._plan.version != 0:
            raise ValueError("prior workflow G0 must have version zero")
        validate_semantic_workflow(self._plan, task, capabilities, self._registry)
        return PriorGenerationResult(
            plan=self._plan,
            provenance=self.provenance(task, capabilities),
        )


class LLMPriorWorkflowGenerator:
    """Generate a complete semantic G0 without any infrastructure input."""

    def __init__(
        self,
        backend: CompletionBackend,
        registry: OperatorRegistry,
        *,
        model_id: str,
        generator_id: str = "llm-prior",
        attempt_store: PriorAttemptStore | None = None,
    ) -> None:
        self._backend = backend
        self._registry = registry
        self._model_id = model_id
        self._generator_id = generator_id
        self._attempt_store = attempt_store

    def provenance(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> PriorGeneratorProvenance:
        return PriorGeneratorProvenance(
            generator_id=self._generator_id,
            generator_version="llm-prior-v2",
            model_id=self._model_id,
            prompt_sha256=canonical_sha256(self.render_prompt(task, capabilities)),
        )

    async def generate(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        *,
        public_bundle_sha256: str | None = None,
    ) -> PriorGenerationResult:
        prompt = self.render_prompt(task, capabilities)
        provenance = self.provenance(task, capabilities)
        attempt: PriorAttemptReference | None = None
        if self._attempt_store is not None:
            if public_bundle_sha256 is None:
                raise ValueError("audited LLM prior generation requires public bundle SHA-256")
            attempt = self._attempt_store.begin(
                task=task,
                provenance=provenance,
                capabilities=capabilities,
                public_bundle_sha256=public_bundle_sha256,
            )
        try:
            completion = await self._backend.invoke(ModelRequest(prompt=prompt))
        except BaseException as exc:
            if attempt is not None:
                PriorAttemptStore.persist_backend_failure(attempt, exc)
            raise
        if attempt is not None:
            PriorAttemptStore.persist_raw_completion(attempt, completion.text)
        try:
            draft = PriorWorkflowDraft.model_validate_json(completion.text)
        except ValidationError as exc:
            if attempt is not None:
                PriorAttemptStore.persist_parse_failure(attempt, exc)
            raise ValueError("prior generator returned an invalid semantic workflow draft") from exc
        if attempt is not None:
            PriorAttemptStore.persist_parsed_draft(attempt, draft)
        plan = SemanticWorkflowPlan(
            workflow_id=_workflow_id(task, provenance, draft),
            version=0,
            actions=draft.actions,
            dependencies=draft.dependencies,
            terminal_action_id=draft.terminal_action_id,
        )
        if attempt is not None:
            PriorAttemptStore.persist_constructed_g0(attempt, plan)
        try:
            validate_semantic_workflow(plan, task, capabilities, self._registry)
        except WorkflowValidationError as exc:
            if attempt is not None:
                PriorAttemptStore.persist_validation_failure(attempt, exc)
            raise
        if attempt is not None:
            PriorAttemptStore.persist_validation_passed(attempt, plan)
        return PriorGenerationResult(
            plan=plan,
            provenance=provenance,
            attempt=attempt,
        )

    def render_prompt(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
    ) -> str:
        payload = {
            "task": AgentTaskView.from_contract(task).model_dump(mode="json", by_alias=True),
            "static_capabilities": capabilities.model_dump(mode="json"),
            "workflow_output_schema": PriorWorkflowDraft.model_json_schema(),
        }
        return "\n".join(
            (
                "Produce one complete infrastructure-independent semantic workflow G0.",
                "Use only the finite system-owned actions and abstract model requirements.",
                "Never mention workers, devices, deployments, placement, routes, bandwidth, "
                "latency, queue, load, evaluator metadata, gold, or source references.",
                "Return exactly one prior-workflow-draft-v1 JSON object with no Markdown.",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            )
        )


class FrozenPriorWorkflow(ContractModel):
    schema_version: Literal["frozen-prior-workflow-v1"] = "frozen-prior-workflow-v1"
    generator_id: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
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
        generation: PriorGenerationResult,
        capabilities: StaticCapabilityContract,
        public_bundle_sha256: str,
    ) -> FrozenPriorWorkflow:
        plan = generation.plan
        if plan.version != 0:
            raise ValueError("frozen prior workflow G0 must have version zero")
        return cls(
            task_id=task.task_id,
            generator_id=generation.provenance.generator_id,
            generator_version=generation.provenance.generator_version,
            task_view_sha256=canonical_sha256(
                AgentTaskView.from_contract(task).model_dump(mode="json", by_alias=True)
            ),
            public_bundle_sha256=public_bundle_sha256,
            plan_sha256=plan.canonical_sha256(),
            prior_model=generation.provenance.model_id,
            prompt_sha256=generation.provenance.prompt_sha256,
            capability_sha256=canonical_sha256(capabilities.model_dump(mode="json")),
            generated_at=datetime.now(UTC),
            plan=plan,
        )

    def verify(
        self,
        task: TaskContract,
        capabilities: StaticCapabilityContract,
        public_bundle_sha256: str,
        expected_provenance: PriorGeneratorProvenance,
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
        if self.generator_id != expected_provenance.generator_id:
            raise ValueError("frozen prior generator ID mismatch")
        if self.generator_version != expected_provenance.generator_version:
            raise ValueError("frozen prior generator version mismatch")
        if self.prior_model != expected_provenance.model_id:
            raise ValueError("frozen prior model mismatch")
        if self.prompt_sha256 != expected_provenance.prompt_sha256:
            raise ValueError("frozen prior prompt mismatch")
        if self.capability_sha256 != expected_capabilities:
            raise ValueError("frozen prior does not match the static capability contract")
        if self.plan_sha256 != self.plan.canonical_sha256():
            raise ValueError("frozen prior plan hash mismatch")


class PriorWorkflowStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def path_for(self, task_id: str) -> Path:
        return self._root / f"{_safe_name(task_id)}.json"

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


def _workflow_id(
    task: TaskContract,
    provenance: PriorGeneratorProvenance,
    draft: PriorWorkflowDraft,
) -> str:
    digest = canonical_sha256(
        {
            "task_id": task.task_id,
            "generator": provenance.model_dump(mode="json"),
            "draft_sha256": draft.canonical_sha256(),
        }
    )
    return f"prior-{digest[:32]}"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "task"


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
