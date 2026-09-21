from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
import pytest

from infra_joint.core.action import (
    JointAction,
    PhysicalDecision,
    PhysicalPolicy,
    SemanticAction,
)
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkSpec,
)
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.operators.builtin import read_artifact_spec, unavailable_handler
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import RuntimeExecutor
from infra_joint.worker.artifact_fetcher import FetchedArtifact
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.model_backend import ModelDeployment, StaticModelBackend
from infra_joint.worker.server import create_worker_app


class SourceClientFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, source_url: str) -> FetchedArtifact:
        path = urlparse(source_url).path
        response = await self._client.get(path)
        response.raise_for_status()
        return FetchedArtifact(
            content=response.content,
            media_type=response.headers["content-type"].split(";", maxsplit=1)[0],
            sha256_hex=response.headers.get("x-artifact-sha256"),
        )


@pytest.mark.asyncio
async def test_runtime_triggers_worker_to_worker_artifact_pull() -> None:
    source_store = InMemoryArtifactStore(
        (StoredArtifact.create("doc-1", "text/plain", b"distributed evidence"),)
    )
    target_store = InMemoryArtifactStore()
    source_app = create_worker_app(
        "source",
        {},
        artifact_store=source_store,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source_app),
        base_url="http://source",
    ) as source_http:
        target_app = create_worker_app(
            "target",
            {
                "reader-v1": ModelDeployment(
                    deployment_id="reader-v1",
                    model_id="reader",
                    backend=StaticModelBackend("unused"),
                    modalities=frozenset({"text"}),
                    context_window=4096,
                    reserved_output_tokens=512,
                    image_token_cost=4096,
                )
            },
            artifact_store=target_store,
            artifact_fetcher=SourceClientFetcher(source_http),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target_app),
            base_url="http://target",
        ) as target_http:
            clients = {
                "source": HttpWorkerClient("source", source_http),
                "target": HttpWorkerClient("target", target_http),
            }
            environment = EnvironmentSpec(
                agents=(
                    AgentSpec(agent_id="source", device="disk"),
                    AgentSpec(agent_id="target", device="cpu"),
                ),
                deployments=(
                    DeploymentSpec(
                        deployment_id="reader-v1",
                        agent_id="target",
                        model_id="reader",
                        context_window=4096,
                    ),
                ),
                links=(
                    LinkSpec(
                        source_agent_id="source",
                        target_agent_id="target",
                        bandwidth_mbps=None,
                        rtt_ms=None,
                    ),
                ),
            )
            initial_state = InfrastructureState(
                agents=(
                    AgentRuntimeState(agent_id="source", available=True),
                    AgentRuntimeState(agent_id="target", available=True),
                ),
                deployments=(),
                artifacts=(ArtifactRuntimeState(artifact_id="doc-1", locations=("source",)),),
                links=(),
                observed_at=datetime.now(UTC),
            )
            registry = OperatorRegistry()
            registry.register(read_artifact_spec(), unavailable_handler)
            executor = RuntimeExecutor(registry, environment, clients)
            result = await executor.execute(
                JointAction(
                    semantic=SemanticAction(operator="read_artifact", inputs=("doc-1",)),
                    physical=PhysicalDecision(
                        policy=PhysicalPolicy.TARGET_AGENT,
                        target_agent_id="target",
                    ),
                ),
                initial_state,
            )

            assert result.output == {"text": "distributed evidence"}
            assert target_store.get("doc-1").content == b"distributed evidence"

            observed = await LiveWorkerObserver(environment, clients).observe()

    artifact = next(item for item in observed.artifacts if item.artifact_id == "doc-1")
    assert artifact.locations == ("source", "target")
    assert observed.deployments[0].available
    assert observed.links[0].available
    assert observed.links[0].bandwidth_mbps is None


@pytest.mark.asyncio
async def test_pull_rejects_checksum_mismatch() -> None:
    source_store = InMemoryArtifactStore((StoredArtifact.create("doc", "text/plain", b"actual"),))
    source_app = create_worker_app("source", {}, artifact_store=source_store)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=source_app), base_url="http://source"
    ) as source_http:
        target_app = create_worker_app(
            "target",
            {},
            artifact_fetcher=SourceClientFetcher(source_http),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target_app), base_url="http://target"
        ) as target_http:
            response = await target_http.post(
                "/artifact/pull",
                json={
                    "artifact_id": "doc",
                    "source_url": "http://source/artifact/doc",
                    "expected_sha256": "0" * 64,
                },
            )
    assert response.status_code == 409
