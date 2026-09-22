import asyncio
from time import perf_counter
from urllib.parse import urlsplit

from pydantic import Field

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.server import (
    ExecuteOperatorResponse,
    PullArtifactResponse,
    PutArtifactResponse,
    WorkerStateResponse,
)


class NetworkRegime(ContractModel):
    regime_id: str = Field(min_length=1)
    bandwidth_mbps: float = Field(gt=0)
    added_rtt_ms: float = Field(ge=0)

    def transfer_service_time_ms(self, size_bytes: int) -> float:
        if size_bytes < 0:
            raise ValueError("transfer size must not be negative")
        return self.added_rtt_ms + size_bytes * 8 / (self.bandwidth_mbps * 1_000_000) * 1000


class RegimeWorkerClient:
    """Application-layer link emulator around the unchanged worker API.

    Artifact bytes still travel through the real worker-to-worker pull. The wrapper makes
    the observed pull service time at least RTT + serialization time for the frozen regime.
    It intentionally does not emulate shared-link contention or dynamic bandwidth.
    """

    def __init__(
        self,
        wrapped: WorkerClient,
        regime: NetworkRegime,
        worker_urls: dict[str, str],
    ) -> None:
        self.agent_id = wrapped.agent_id
        self._wrapped = wrapped
        self._regime = regime
        self._agent_by_authority = {
            urlsplit(url).netloc.casefold(): agent_id for agent_id, url in worker_urls.items()
        }

    async def execute_operator(
        self,
        action: SemanticAction,
        deployment_id: str | None,
    ) -> ExecuteOperatorResponse:
        return await self._wrapped.execute_operator(action, deployment_id)

    async def get_state(self) -> WorkerStateResponse:
        return await self._wrapped.get_state()

    def artifact_url(self, artifact_id: str) -> str:
        return self._wrapped.artifact_url(artifact_id)

    async def pull_artifact(
        self,
        artifact_id: str,
        source_url: str,
        expected_sha256: str | None = None,
    ) -> PullArtifactResponse:
        authority = urlsplit(source_url).netloc.casefold()
        source_agent_id = self._agent_by_authority.get(authority)
        if source_agent_id is None:
            raise ValueError("artifact source URL is outside the frozen worker set")
        if source_agent_id == self.agent_id:
            raise ValueError("network emulation must not be used for a local artifact")
        started = perf_counter()
        response = await self._wrapped.pull_artifact(
            artifact_id,
            source_url,
            expected_sha256,
        )
        elapsed_ms = (perf_counter() - started) * 1000
        target_ms = self._regime.transfer_service_time_ms(response.size_bytes)
        remaining_ms = max(0.0, target_ms - elapsed_ms)
        if remaining_ms:
            await asyncio.sleep(remaining_ms / 1000)
        return response

    async def put_artifact(
        self,
        artifact_id: str,
        media_type: str,
        content: bytes,
        expected_sha256: str,
    ) -> PutArtifactResponse:
        return await self._wrapped.put_artifact(
            artifact_id,
            media_type,
            content,
            expected_sha256,
        )
