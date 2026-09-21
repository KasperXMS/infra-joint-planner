from datetime import datetime

from pydantic import Field, field_validator, model_validator

from infra_joint.core.base import ContractModel


class AgentSpec(ContractModel):
    agent_id: str = Field(min_length=1)
    device: str = Field(min_length=1)
    capabilities: frozenset[str] = frozenset()


class DeploymentSpec(ContractModel):
    deployment_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    modalities: frozenset[str] = frozenset({"text"})
    context_window: int = Field(gt=0)


class ArtifactPlacement(ContractModel):
    artifact_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)


class LinkSpec(ContractModel):
    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    bandwidth_mbps: float | None = Field(default=None, gt=0)
    rtt_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def endpoints_differ(self) -> "LinkSpec":
        if self.source_agent_id == self.target_agent_id:
            raise ValueError("a link must connect distinct agents")
        return self


class EnvironmentSpec(ContractModel):
    agents: tuple[AgentSpec, ...]
    deployments: tuple[DeploymentSpec, ...]
    initial_placements: tuple[ArtifactPlacement, ...] = ()
    links: tuple[LinkSpec, ...] = ()

    @model_validator(mode="after")
    def references_exist(self) -> "EnvironmentSpec":
        agent_ids = {agent.agent_id for agent in self.agents}
        if len(agent_ids) != len(self.agents):
            raise ValueError("agent_id values must be unique")
        deployment_ids = {deployment.deployment_id for deployment in self.deployments}
        if len(deployment_ids) != len(self.deployments):
            raise ValueError("deployment_id values must be unique")
        for deployment in self.deployments:
            if deployment.agent_id not in agent_ids:
                raise ValueError(f"unknown deployment agent: {deployment.agent_id}")
        for placement in self.initial_placements:
            if placement.agent_id not in agent_ids:
                raise ValueError(f"unknown placement agent: {placement.agent_id}")
        for link in self.links:
            if {link.source_agent_id, link.target_agent_id} - agent_ids:
                raise ValueError("link references an unknown agent")
        return self


class AgentRuntimeState(ContractModel):
    agent_id: str = Field(min_length=1)
    available: bool
    in_flight: int = Field(default=0, ge=0)
    queue_depth: int | None = Field(default=None, ge=0)


class DeploymentRuntimeState(ContractModel):
    deployment_id: str = Field(min_length=1)
    available: bool


class ArtifactRuntimeState(ContractModel):
    artifact_id: str = Field(min_length=1)
    locations: tuple[str, ...]

    @field_validator("locations")
    @classmethod
    def locations_are_unique(cls, locations: tuple[str, ...]) -> tuple[str, ...]:
        if len(locations) != len(set(locations)):
            raise ValueError("artifact locations must be unique")
        return locations


class LinkRuntimeState(ContractModel):
    source_agent_id: str = Field(min_length=1)
    target_agent_id: str = Field(min_length=1)
    available: bool
    bandwidth_mbps: float | None = Field(default=None, gt=0)
    rtt_ms: float | None = Field(default=None, ge=0)


class InfrastructureState(ContractModel):
    agents: tuple[AgentRuntimeState, ...]
    deployments: tuple[DeploymentRuntimeState, ...]
    artifacts: tuple[ArtifactRuntimeState, ...]
    links: tuple[LinkRuntimeState, ...]
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value
