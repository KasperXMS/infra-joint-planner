import asyncio

from infra_joint.core.errors import ExecutionErrorCode, TypedExecutionError
from infra_joint.core.state import DeploymentSpec, EnvironmentSpec
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.client import WorkerClient
from infra_joint.worker.server import WorkerStateResponse


async def validate_worker_surfaces(
    environment: EnvironmentSpec,
    registry: OperatorRegistry,
    worker_clients: dict[str, WorkerClient],
) -> dict[str, WorkerStateResponse]:
    expected_agents = {agent.agent_id for agent in environment.agents}
    if set(worker_clients) != expected_agents:
        raise TypedExecutionError(
            ExecutionErrorCode.SURFACE_MISMATCH,
            "configured worker clients do not exactly match EnvironmentSpec agents",
        )
    states = await asyncio.gather(
        *(worker_clients[agent_id].get_state() for agent_id in sorted(expected_agents))
    )
    by_agent = {state.agent_id: state for state in states}
    if set(by_agent) != expected_agents:
        raise TypedExecutionError(
            ExecutionErrorCode.SURFACE_MISMATCH,
            "worker /state agent IDs do not match EnvironmentSpec",
        )
    agent_specs = {agent.agent_id: agent for agent in environment.agents}
    deployments_by_agent: dict[str, dict[str, DeploymentSpec]] = {
        agent_id: {} for agent_id in expected_agents
    }
    for deployment in environment.deployments:
        deployments_by_agent[deployment.agent_id][deployment.deployment_id] = deployment
    for agent_id, state in by_agent.items():
        expected_operators = {
            operator_id
            for operator_id, spec in registry.specs().items()
            if spec.capability_requirements <= agent_specs[agent_id].capabilities
        }
        if set(state.operators) != expected_operators:
            raise TypedExecutionError(
                ExecutionErrorCode.SURFACE_MISMATCH,
                f"operator surface mismatch on worker: {agent_id}",
            )
        expected = deployments_by_agent[agent_id]
        actual = {deployment.deployment_id: deployment for deployment in state.deployments}
        if set(actual) != set(expected):
            raise TypedExecutionError(
                ExecutionErrorCode.SURFACE_MISMATCH,
                f"deployment IDs mismatch on worker: {agent_id}",
            )
        for deployment_id, actual_deployment in actual.items():
            expected_deployment = expected[deployment_id]
            if (
                actual_deployment.model_id != expected_deployment.model_id
                or actual_deployment.modalities != expected_deployment.modalities
                or actual_deployment.context_window != expected_deployment.context_window
                or actual_deployment.reserved_output_tokens
                != expected_deployment.reserved_output_tokens
                or actual_deployment.image_token_cost != expected_deployment.image_token_cost
            ):
                raise TypedExecutionError(
                    ExecutionErrorCode.SURFACE_MISMATCH,
                    f"deployment contract mismatch: {deployment_id}",
                )
    return by_agent
