from typing import Protocol
from urllib.parse import quote

import httpx

from infra_joint.core.action import SemanticAction
from infra_joint.core.errors import FailureDetail, TypedExecutionError
from infra_joint.worker.server import (
    ExecuteOperatorRequest,
    ExecuteOperatorResponse,
    PullArtifactRequest,
    PullArtifactResponse,
    PutArtifactResponse,
    WorkerStateResponse,
)


class WorkerClient(Protocol):
    agent_id: str

    async def execute_operator(
        self, action: SemanticAction, deployment_id: str | None
    ) -> ExecuteOperatorResponse: ...

    async def get_state(self) -> WorkerStateResponse: ...

    def artifact_url(self, artifact_id: str) -> str: ...

    async def pull_artifact(
        self,
        artifact_id: str,
        source_url: str,
        expected_sha256: str | None = None,
    ) -> PullArtifactResponse: ...

    async def put_artifact(
        self,
        artifact_id: str,
        media_type: str,
        content: bytes,
        expected_sha256: str,
    ) -> PutArtifactResponse: ...


class HttpWorkerClient:
    def __init__(self, agent_id: str, client: httpx.AsyncClient) -> None:
        self.agent_id = agent_id
        self._client = client

    async def get_state(self) -> WorkerStateResponse:
        response = await self._client.get("/state")
        response.raise_for_status()
        return WorkerStateResponse.model_validate(response.json())

    def artifact_url(self, artifact_id: str) -> str:
        path = f"artifact/{quote(artifact_id, safe='')}"
        return str(self._client.base_url.join(path))

    async def pull_artifact(
        self,
        artifact_id: str,
        source_url: str,
        expected_sha256: str | None = None,
    ) -> PullArtifactResponse:
        request = PullArtifactRequest(
            artifact_id=artifact_id,
            source_url=source_url,
            expected_sha256=expected_sha256,
        )
        response = await self._client.post(
            "/artifact/pull",
            content=request.model_dump_json(),
            headers={"content-type": "application/json"},
        )
        response.raise_for_status()
        return PullArtifactResponse.model_validate(response.json())

    async def put_artifact(
        self,
        artifact_id: str,
        media_type: str,
        content: bytes,
        expected_sha256: str,
    ) -> PutArtifactResponse:
        response = await self._client.put(
            f"/artifact/{quote(artifact_id, safe='')}",
            content=content,
            headers={
                "content-type": media_type,
                "x-artifact-sha256": expected_sha256,
            },
        )
        response.raise_for_status()
        return PutArtifactResponse.model_validate(response.json())

    async def execute_operator(
        self, action: SemanticAction, deployment_id: str | None
    ) -> ExecuteOperatorResponse:
        request = ExecuteOperatorRequest(action=action, deployment_id=deployment_id)
        response = await self._client.post(
            "/execute/operator",
            content=request.model_dump_json(),
            headers={"content-type": "application/json"},
        )
        if response.is_error:
            self._raise_typed_error(response)
        response.raise_for_status()
        return ExecuteOperatorResponse.model_validate(response.json())

    @staticmethod
    def _raise_typed_error(response: httpx.Response) -> None:
        try:
            detail = FailureDetail.model_validate(response.json().get("detail"))
        except (ValueError, AttributeError):
            return
        raise TypedExecutionError(detail.code, detail.message)
