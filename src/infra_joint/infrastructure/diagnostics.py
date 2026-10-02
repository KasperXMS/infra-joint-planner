"""Private observer diagnostics, deliberately separate from scheduling state."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

from infra_joint.core.base import ContractModel

_ACTION_IDS: ContextVar[tuple[str, ...]] = ContextVar("observer_diagnostic_actions", default=())


@contextmanager
def observer_diagnostic_scope(action_ids: tuple[str, ...]) -> Generator[None, None, None]:
    """Correlate private probes with actions without changing observation inputs."""
    token = _ACTION_IDS.set(action_ids)
    try:
        yield
    finally:
        _ACTION_IDS.reset(token)


def diagnostic_action_ids() -> tuple[str, ...]:
    return _ACTION_IDS.get()


class ProbeDiagnostic(ContractModel):
    worker_id: str
    probe_started: datetime
    probe_finished: datetime
    probe_success: bool
    probe_latency_ms: float
    probe_error_type: str | None = None
    probe_error_message: str | None = None
    artifact_ids_reported: tuple[str, ...] = ()
    deployment_availability: dict[str, bool]


class ArtifactVisibilityDiagnostic(ContractModel):
    artifact_id: str
    status: Literal["PRESENT", "ABSENT", "HOST_UNREACHABLE", "UNKNOWN"]
    reported_hosts: tuple[str, ...] = ()
    previously_reported_hosts: tuple[str, ...] = ()
    unreachable_known_hosts: tuple[str, ...] = ()


class ObservationDiagnostic(ContractModel):
    schema_version: str = "observer-diagnostics-v1"
    visibility: str = "private-physical-diagnostics-only"
    observation_id: str
    timestamp: datetime
    action_ids: tuple[str, ...] = ()
    probes: tuple[ProbeDiagnostic, ...]
    artifact_visibility: tuple[ArtifactVisibilityDiagnostic, ...]
    construction_error_type: str | None = None
    construction_error_message: str | None = None


class ObserverDiagnosticSink(Protocol):
    def append(self, diagnostic: ObservationDiagnostic) -> None: ...


class JsonlObserverDiagnostics:
    """Private sidecar. Never inserted into LogicalObservation or profile inputs."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, diagnostic: ObservationDiagnostic) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(diagnostic.model_dump_json() + "\n")
