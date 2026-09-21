import asyncio
from datetime import UTC, datetime
from typing import Protocol

from infra_joint.core.state import (
    AgentRuntimeState,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.server import WorkerStateResponse


class InfrastructureObserver(Protocol):
    async def observe(self) -> InfrastructureState: ...


class StaticObserver:
    """Deterministic observer used until live worker probing is introduced."""

    def __init__(self, state: InfrastructureState) -> None:
        self._state = state

    async def observe(self) -> InfrastructureState:
        return self._state


class LiveWorkerObserver:
    """Build a fresh infrastructure snapshot from worker-reported facts."""

    def __init__(
        self,
        environment: EnvironmentSpec,
        worker_clients: dict[str, WorkerClient],
    ) -> None:
        self._environment = environment
        self._worker_clients = worker_clients

    async def observe(self) -> InfrastructureState:
        async def probe(agent_id: str) -> WorkerStateResponse | BaseException:
            client = self._worker_clients.get(agent_id)
            if client is None:
                return RuntimeError("worker client is not configured")
            try:
                state = await client.get_state()
                if state.agent_id != agent_id:
                    return RuntimeError("worker returned a mismatched agent_id")
                return state
            except Exception as exc:  # noqa: BLE001 - unavailability is observed state
                return exc

        agent_ids = [agent.agent_id for agent in self._environment.agents]
        results = await asyncio.gather(*(probe(agent_id) for agent_id in agent_ids))
        worker_states = {
            agent_id: result
            for agent_id, result in zip(agent_ids, results, strict=True)
            if isinstance(result, WorkerStateResponse)
        }
        available_agents = set(worker_states)
        agents = tuple(
            AgentRuntimeState(
                agent_id=agent_id,
                available=agent_id in worker_states,
                in_flight=worker_states[agent_id].in_flight if agent_id in worker_states else 0,
                queue_depth=None,
            )
            for agent_id in agent_ids
        )
        deployments = tuple(
            DeploymentRuntimeState(
                deployment_id=deployment.deployment_id,
                available=(
                    deployment.agent_id in worker_states
                    and deployment.deployment_id
                    in {
                        item.deployment_id
                        for item in worker_states[deployment.agent_id].deployments
                    }
                ),
            )
            for deployment in self._environment.deployments
        )
        artifact_locations: dict[str, list[str]] = {}
        artifact_metadata: dict[str, tuple[str, int, str]] = {}
        for agent_id, worker_state in worker_states.items():
            for artifact in worker_state.artifacts:
                metadata = (
                    artifact.media_type,
                    artifact.size_bytes,
                    artifact.sha256_hex,
                )
                existing = artifact_metadata.setdefault(artifact.artifact_id, metadata)
                if existing != metadata:
                    raise RuntimeError(
                        f"workers report inconsistent artifact metadata: {artifact.artifact_id}"
                    )
                artifact_locations.setdefault(artifact.artifact_id, []).append(agent_id)
        artifacts = tuple(
            ArtifactRuntimeState(
                artifact_id=artifact_id,
                locations=tuple(sorted(locations)),
                media_type=artifact_metadata[artifact_id][0],
                size_bytes=artifact_metadata[artifact_id][1],
                sha256_hex=artifact_metadata[artifact_id][2],
            )
            for artifact_id, locations in sorted(artifact_locations.items())
        )
        links = tuple(
            LinkRuntimeState(
                source_agent_id=link.source_agent_id,
                target_agent_id=link.target_agent_id,
                available=(
                    link.source_agent_id in available_agents
                    and link.target_agent_id in available_agents
                ),
                bandwidth_mbps=link.bandwidth_mbps,
                rtt_ms=link.rtt_ms,
            )
            for link in self._environment.links
        )
        return InfrastructureState(
            agents=agents,
            deployments=deployments,
            artifacts=artifacts,
            links=links,
            observed_at=datetime.now(UTC),
        )
