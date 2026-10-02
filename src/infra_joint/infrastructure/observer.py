import asyncio
import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from infra_joint.core.state import (
    AgentRuntimeState,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.infrastructure.diagnostics import (
    ArtifactVisibilityDiagnostic,
    ObservationDiagnostic,
    ObserverDiagnosticSink,
    ProbeDiagnostic,
    diagnostic_action_ids,
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
        *,
        diagnostic_sink: ObserverDiagnosticSink | None = None,
        expected_artifact_ids: tuple[str, ...] = (),
    ) -> None:
        self._environment = environment
        self._worker_clients = worker_clients
        self._diagnostic_sink = diagnostic_sink
        # This history informs diagnostics ONLY; it never restores scheduling visibility.
        self._diagnostic_hosts: dict[str, set[str]] = {
            artifact_id: set() for artifact_id in expected_artifact_ids
        }

    async def observe(self) -> InfrastructureState:
        probes: dict[str, ProbeDiagnostic] = {}

        async def probe(agent_id: str) -> WorkerStateResponse | BaseException:
            started_at = datetime.now(UTC)
            started = perf_counter()
            client = self._worker_clients.get(agent_id)
            try:
                if client is None:
                    raise RuntimeError("worker client is not configured")
                state = await client.get_state()
                if state.agent_id != agent_id:
                    raise RuntimeError("worker returned a mismatched agent_id")
                probes[agent_id] = self._probe_diagnostic(
                    agent_id, started_at, started, state, None
                )
                return state
            except Exception as exc:  # noqa: BLE001 - unavailability is observed state
                probes[agent_id] = self._probe_diagnostic(agent_id, started_at, started, None, exc)
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
                    self._record_diagnostics(
                        probes,
                        worker_states,
                        RuntimeError(
                            f"workers report inconsistent artifact metadata: {artifact.artifact_id}"
                        ),
                    )
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
        state = InfrastructureState(
            agents=agents,
            deployments=deployments,
            artifacts=artifacts,
            links=links,
            observed_at=datetime.now(UTC),
        )
        self._record_diagnostics(probes, worker_states, observed_at=state.observed_at)
        return state

    def _probe_diagnostic(
        self,
        agent_id: str,
        started_at: datetime,
        started: float,
        state: WorkerStateResponse | None,
        error: Exception | None,
    ) -> ProbeDiagnostic:
        reported: set[str] = (
            set() if state is None else {d.deployment_id for d in state.deployments}
        )
        return ProbeDiagnostic(
            worker_id=agent_id,
            probe_started=started_at,
            probe_finished=datetime.now(UTC),
            probe_success=state is not None,
            probe_latency_ms=(perf_counter() - started) * 1000,
            probe_error_type=None if error is None else type(error).__name__,
            probe_error_message=None if error is None else str(error),
            artifact_ids_reported=()
            if state is None
            else tuple(item.artifact_id for item in state.artifacts),
            deployment_availability={
                d.deployment_id: d.deployment_id in reported
                for d in self._environment.deployments
                if d.agent_id == agent_id
            },
        )

    def _record_diagnostics(
        self,
        probes: dict[str, ProbeDiagnostic],
        worker_states: dict[str, WorkerStateResponse],
        error: Exception | None = None,
        *,
        observed_at: datetime | None = None,
    ) -> None:
        current: dict[str, set[str]] = {}
        for host, state in worker_states.items():
            for artifact in state.artifacts:
                current.setdefault(artifact.artifact_id, set()).add(host)
        available = set(worker_states)
        statuses: list[ArtifactVisibilityDiagnostic] = []
        for artifact_id in sorted(set(self._diagnostic_hosts) | set(current)):
            history = self._diagnostic_hosts.get(artifact_id, set())
            hosts = current.get(artifact_id, set())
            unreachable = history - available
            if hosts:
                status = "PRESENT"
            elif unreachable:
                status = "HOST_UNREACHABLE"
            elif len(available) == len(self._environment.agents):
                status = "ABSENT"
            else:
                status = "UNKNOWN"
            statuses.append(
                ArtifactVisibilityDiagnostic(
                    artifact_id=artifact_id,
                    status=status,
                    reported_hosts=tuple(sorted(hosts)),
                    previously_reported_hosts=tuple(sorted(history)),
                    unreachable_known_hosts=tuple(sorted(unreachable)),
                )
            )
        for artifact_id, hosts in current.items():
            self._diagnostic_hosts.setdefault(artifact_id, set()).update(hosts)
        if self._diagnostic_sink is not None:
            diagnostic = ObservationDiagnostic(
                observation_id=str(uuid4()),
                timestamp=observed_at or datetime.now(UTC),
                action_ids=diagnostic_action_ids(),
                probes=tuple(probes[key] for key in sorted(probes)),
                artifact_visibility=tuple(statuses),
                construction_error_type=None if error is None else type(error).__name__,
                construction_error_message=None if error is None else str(error),
            )
            try:
                self._diagnostic_sink.append(diagnostic)
            except Exception:  # noqa: BLE001 - instrumentation must not alter execution
                logging.getLogger(__name__).exception("Private observer diagnostic write failed")
