from typing import Any, Protocol

from pydantic import Field

from infra_joint.core.action import JointAction
from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.client import WorkerClient
from infra_joint.runtime.resolver import DeterministicResolver


class ExecutionResult(ContractModel):
    operator: str = Field(min_length=1)
    agent_ids: tuple[str, ...]
    deployment_id: str | None = None
    output: dict[str, Any]


class ActionExecutor(Protocol):
    async def execute(
        self, action: JointAction, infrastructure: InfrastructureState
    ) -> ExecutionResult: ...


class RuntimeExecutor:
    def __init__(
        self,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
        worker_clients: dict[str, WorkerClient],
        resolver: DeterministicResolver | None = None,
    ) -> None:
        self._registry = registry
        self._environment = environment
        self._worker_clients = worker_clients
        self._resolver = resolver or DeterministicResolver()

    async def execute(
        self, action: JointAction, infrastructure: InfrastructureState
    ) -> ExecutionResult:
        self._registry.validate_action(action.semantic)
        operator = self._registry.binding(action.semantic.operator).spec
        resolved = self._resolver.resolve(
            action.physical,
            action.semantic,
            operator,
            self._environment,
            infrastructure,
        )
        if len(resolved.agent_ids) != 1:
            raise NotImplementedError("parallel worker execution is not part of M1")
        agent_id = resolved.agent_ids[0]
        try:
            worker = self._worker_clients[agent_id]
        except KeyError as exc:
            raise RuntimeError(f"no worker client configured for agent: {agent_id}") from exc
        await self._localize_inputs(action, infrastructure, worker)
        response = await worker.execute_operator(action.semantic, resolved.deployment_id)
        return ExecutionResult(
            operator=response.operator,
            agent_ids=resolved.agent_ids,
            deployment_id=resolved.deployment_id,
            output=response.output,
        )

    async def _localize_inputs(
        self,
        action: JointAction,
        infrastructure: InfrastructureState,
        target: WorkerClient,
    ) -> None:
        locations = {
            artifact.artifact_id: set(artifact.locations) for artifact in infrastructure.artifacts
        }
        for artifact_id in action.semantic.inputs:
            current_locations = locations[artifact_id]
            if target.agent_id in current_locations:
                continue
            source_candidates = sorted(current_locations & self._worker_clients.keys())
            if not source_candidates:
                raise RuntimeError(f"no reachable source for artifact: {artifact_id}")
            source = self._worker_clients[source_candidates[0]]
            await target.pull_artifact(
                artifact_id=artifact_id,
                source_url=source.artifact_url(artifact_id),
            )
