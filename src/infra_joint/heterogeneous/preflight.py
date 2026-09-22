from collections.abc import Mapping

from infra_joint.core.state import EnvironmentSpec
from infra_joint.heterogeneous.contracts import EquivalentModelReplicaSet
from infra_joint.worker.server import WorkerStateResponse


class HeterogeneousPreflightError(RuntimeError):
    pass


def validate_heterogeneous_preflight(
    environment: EnvironmentSpec,
    worker_states: Mapping[str, WorkerStateResponse],
    replica_set: EquivalentModelReplicaSet,
    *,
    required_agent_ids: frozenset[str],
    rtx_agent_id: str,
) -> None:
    """Fail closed unless the declared heterogeneous execution surface exists."""

    environment_agents = {item.agent_id for item in environment.agents}
    missing_environment = sorted(required_agent_ids - environment_agents)
    if missing_environment:
        raise HeterogeneousPreflightError(
            f"required heterogeneous agents missing from environment: {missing_environment}"
        )
    if rtx_agent_id not in required_agent_ids:
        raise HeterogeneousPreflightError("RTX agent must be a required heterogeneous agent")
    if set(worker_states) != environment_agents:
        raise HeterogeneousPreflightError(
            "Worker /state responses must exactly cover EnvironmentSpec agents"
        )
    unavailable = sorted(
        agent_id
        for agent_id, state in worker_states.items()
        if not state.available or state.agent_id != agent_id
    )
    if unavailable:
        raise HeterogeneousPreflightError(f"required Workers unavailable: {unavailable}")

    environment_deployments = {item.deployment_id: item for item in environment.deployments}
    for replica in replica_set.replicas:
        deployment = environment_deployments.get(replica.deployment_id)
        if deployment is None:
            raise HeterogeneousPreflightError(
                f"replica deployment absent from environment: {replica.deployment_id}"
            )
        if deployment.agent_id != replica.agent_id:
            raise HeterogeneousPreflightError(
                f"replica agent/deployment binding mismatch: {replica.replica_id}"
            )
        if deployment.context_window != replica.context_window:
            raise HeterogeneousPreflightError(f"replica context mismatch: {replica.replica_id}")
        if deployment.reserved_output_tokens != replica.max_output_tokens:
            raise HeterogeneousPreflightError(
                f"replica output limit mismatch: {replica.replica_id}"
            )
        state_deployments = {
            item.deployment_id: item for item in worker_states[replica.agent_id].deployments
        }
        state_deployment = state_deployments.get(replica.deployment_id)
        if state_deployment is None:
            raise HeterogeneousPreflightError(
                f"replica deployment absent from Worker /state: {replica.deployment_id}"
            )
        if (
            state_deployment.model_id != deployment.model_id
            or state_deployment.context_window != deployment.context_window
            or state_deployment.reserved_output_tokens != deployment.reserved_output_tokens
            or state_deployment.modalities != deployment.modalities
        ):
            raise HeterogeneousPreflightError(
                f"replica Worker deployment contract mismatch: {replica.deployment_id}"
            )

    replica_agents = {item.agent_id for item in replica_set.replicas}
    if rtx_agent_id not in replica_agents:
        raise HeterogeneousPreflightError("equivalent replica set does not include RTX agent")
    if replica_agents == {rtx_agent_id}:
        raise HeterogeneousPreflightError("equivalent replica set lacks an AGX target")
