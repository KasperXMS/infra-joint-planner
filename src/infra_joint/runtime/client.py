from typing import Protocol

import httpx

from infra_joint.core.action import SemanticAction
from infra_joint.worker.server import ExecuteOperatorRequest, ExecuteOperatorResponse


class WorkerClient(Protocol):
    agent_id: str

    async def execute_operator(
        self, action: SemanticAction, deployment_id: str | None
    ) -> ExecuteOperatorResponse: ...


class HttpWorkerClient:
    def __init__(self, agent_id: str, client: httpx.AsyncClient) -> None:
        self.agent_id = agent_id
        self._client = client

    async def execute_operator(
        self, action: SemanticAction, deployment_id: str | None
    ) -> ExecuteOperatorResponse:
        request = ExecuteOperatorRequest(action=action, deployment_id=deployment_id)
        response = await self._client.post(
            "/execute/operator",
            content=request.model_dump_json(),
            headers={"content-type": "application/json"},
        )
        response.raise_for_status()
        return ExecuteOperatorResponse.model_validate(response.json())
