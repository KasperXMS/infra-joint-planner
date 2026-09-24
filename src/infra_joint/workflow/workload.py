from pydantic import Field, field_validator, model_validator

from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec
from infra_joint.core.task import (
    ArtifactCollectionRelation,
    ArtifactContentSchema,
    TaskContract,
)
from infra_joint.operators.registry import OperatorRegistry


class WorkloadArtifact(ContractModel):
    """Planner-visible artifact semantics without source or placement metadata."""

    artifact_id: str = Field(min_length=1)
    logical_type: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    content_schema: ArtifactContentSchema | None = None
    collection: ArtifactCollectionRelation | None = None


class AvailableModelInstance(ContractModel):
    """A fixed model instance identity; physical host placement is deliberately omitted."""

    model_instance_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    modalities: frozenset[str] = frozenset({"text"})
    context_window: int = Field(gt=0)
    reserved_output_tokens: int = Field(gt=0)
    image_token_cost: int = Field(gt=0)


class WorkloadSpec(ContractModel):
    """Capability envelope between a task and a workflow planner.

    This contract contains no solution graph, routing hint, infrastructure state, gold
    answer, or supporting evidence.
    """

    available_operations: tuple[str, ...]
    available_model_instances: tuple[AvailableModelInstance, ...]
    artifacts: tuple[WorkloadArtifact, ...]
    min_agents: int | None = Field(default=None, ge=1)
    max_agents: int | None = Field(default=None, ge=1)

    @field_validator("available_operations")
    @classmethod
    def operations_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("available_operations must be unique")
        if any(not value for value in values):
            raise ValueError("available_operations must not contain empty identifiers")
        return values

    @field_validator("available_model_instances")
    @classmethod
    def model_instances_are_unique(
        cls, values: tuple[AvailableModelInstance, ...]
    ) -> tuple[AvailableModelInstance, ...]:
        identifiers = [value.model_instance_id for value in values]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("model_instance_id values must be unique")
        return values

    @field_validator("artifacts")
    @classmethod
    def artifacts_are_unique(
        cls, values: tuple[WorkloadArtifact, ...]
    ) -> tuple[WorkloadArtifact, ...]:
        identifiers = [value.artifact_id for value in values]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("workload artifact identifiers must be unique")
        return values

    @model_validator(mode="after")
    def agent_limits_are_ordered(self) -> "WorkloadSpec":
        if (
            self.min_agents is not None
            and self.max_agents is not None
            and self.min_agents > self.max_agents
        ):
            raise ValueError("min_agents must not exceed max_agents")
        return self

    def validate_against(
        self,
        task: TaskContract,
        environment: EnvironmentSpec,
        registry: OperatorRegistry,
    ) -> None:
        unknown_operations = set(self.available_operations) - set(registry)
        if unknown_operations:
            raise ValueError(f"unknown workload operations: {sorted(unknown_operations)}")

        deployments = {item.deployment_id: item for item in environment.deployments}
        for instance in self.available_model_instances:
            deployment = deployments.get(instance.model_instance_id)
            if deployment is None:
                raise ValueError(
                    f"unknown workload model instance: {instance.model_instance_id}"
                )
            if deployment.model_id != instance.model_id:
                raise ValueError(
                    f"model identity mismatch for instance: {instance.model_instance_id}"
                )
            if deployment.modalities != instance.modalities:
                raise ValueError(
                    f"model modalities mismatch for instance: {instance.model_instance_id}"
                )
            if (
                deployment.context_window != instance.context_window
                or deployment.reserved_output_tokens != instance.reserved_output_tokens
                or deployment.image_token_cost != instance.image_token_cost
            ):
                raise ValueError(
                    f"model context contract mismatch for instance: "
                    f"{instance.model_instance_id}"
                )

        expected_artifacts = {
            item.artifact_id: {
                "logical_type": item.logical_type,
                "media_type": item.media_type,
                "size_bytes": item.size_bytes,
                "content_schema": item.content_schema,
                "collection": item.collection,
            }
            for item in task.artifacts
        }
        actual_artifacts = {
            item.artifact_id: {
                "logical_type": item.logical_type,
                "media_type": item.media_type,
                "size_bytes": item.size_bytes,
                "content_schema": item.content_schema,
                "collection": item.collection,
            }
            for item in self.artifacts
        }
        if actual_artifacts != expected_artifacts:
            raise ValueError("WorkloadSpec artifacts must exactly describe TaskContract artifacts")

    @classmethod
    def from_task_environment(
        cls,
        task: TaskContract,
        environment: EnvironmentSpec,
        *,
        available_operations: tuple[str, ...],
        min_agents: int | None = None,
        max_agents: int | None = None,
    ) -> "WorkloadSpec":
        return cls(
            available_operations=available_operations,
            available_model_instances=tuple(
                AvailableModelInstance(
                    model_instance_id=item.deployment_id,
                    model_id=item.model_id,
                    modalities=item.modalities,
                    context_window=item.context_window,
                    reserved_output_tokens=item.reserved_output_tokens,
                    image_token_cost=item.image_token_cost,
                )
                for item in environment.deployments
            ),
            artifacts=tuple(
                WorkloadArtifact(
                    artifact_id=item.artifact_id,
                    logical_type=item.logical_type,
                    media_type=item.media_type,
                    size_bytes=item.size_bytes,
                    content_schema=item.content_schema,
                    collection=item.collection,
                )
                for item in task.artifacts
            ),
            min_agents=min_agents,
            max_agents=max_agents,
        )
