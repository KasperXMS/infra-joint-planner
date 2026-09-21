from dataclasses import dataclass
from enum import StrEnum

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy, SemanticAction
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.operators.registry import OperatorSpec


class ResolutionErrorCode(StrEnum):
    INFEASIBLE_BINDING = "infeasible_binding"
    MISSING_INPUT = "missing_input"


class BindingResolutionError(RuntimeError):
    def __init__(self, code: ResolutionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ResolvedBinding:
    agent_ids: tuple[str, ...]
    deployment_id: str | None = None


class DeterministicResolver:
    """Resolve physical policy without silently changing explicit planner intent."""

    def resolve(
        self,
        decision: PhysicalDecision,
        action: SemanticAction,
        operator: OperatorSpec,
        environment: EnvironmentSpec,
        state: InfrastructureState,
    ) -> ResolvedBinding:
        available_agents = {item.agent_id for item in state.agents if item.available}
        agent_specs = {item.agent_id: item for item in environment.agents}
        deployments = {item.deployment_id: item for item in environment.deployments}
        available_deployments = {
            item.deployment_id for item in state.deployments if item.available
        }
        artifact_locations = {
            item.artifact_id: set(item.locations) for item in state.artifacts
        }
        missing = [
            artifact_id
            for artifact_id in action.inputs
            if artifact_id not in artifact_locations
        ]
        if missing:
            raise BindingResolutionError(
                ResolutionErrorCode.MISSING_INPUT,
                f"input artifacts are absent from infrastructure state: {missing}",
            )

        feasible_agents = {
            agent_id
            for agent_id in available_agents
            if agent_id in agent_specs
            and operator.capability_requirements <= agent_specs[agent_id].capabilities
        }

        if decision.policy == PhysicalPolicy.TARGET_AGENT:
            target = decision.target_agent_id
            if target not in feasible_agents:
                raise BindingResolutionError(
                    ResolutionErrorCode.INFEASIBLE_BINDING,
                    f"explicit target agent is infeasible: {target}",
                )
            return ResolvedBinding((target,))  # type: ignore[arg-type]

        if decision.policy == PhysicalPolicy.TARGET_DEPLOYMENT:
            deployment_id = decision.target_deployment_id
            deployment = deployments.get(deployment_id or "")
            if (
                deployment is None
                or deployment_id not in available_deployments
                or deployment.agent_id not in feasible_agents
            ):
                raise BindingResolutionError(
                    ResolutionErrorCode.INFEASIBLE_BINDING,
                    f"explicit target deployment is infeasible: {deployment_id}",
                )
            return ResolvedBinding((deployment.agent_id,), deployment_id)

        data_local_agents = set(feasible_agents)
        for artifact_id in action.inputs:
            data_local_agents &= artifact_locations[artifact_id]

        if decision.policy == PhysicalPolicy.PARALLEL_DATA_LOCAL:
            parallel_agents = sorted(
                feasible_agents
                & set().union(*(artifact_locations[item] for item in action.inputs))
            ) if action.inputs else sorted(feasible_agents)
            if not parallel_agents:
                self._raise_no_feasible_agent()
            return ResolvedBinding(tuple(parallel_agents))

        if decision.policy == PhysicalPolicy.DATA_LOCAL:
            if not data_local_agents:
                self._raise_no_feasible_agent()
            return ResolvedBinding((min(data_local_agents),))

        # AUTO: capability feasible, then minimum number of required transfers,
        # then stable agent ID tie-break.
        if not feasible_agents:
            self._raise_no_feasible_agent()
        ranked = sorted(
            feasible_agents,
            key=lambda agent_id: (
                sum(agent_id not in artifact_locations[item] for item in action.inputs),
                agent_id,
            ),
        )
        return ResolvedBinding((ranked[0],))

    @staticmethod
    def _raise_no_feasible_agent() -> None:
        raise BindingResolutionError(
            ResolutionErrorCode.INFEASIBLE_BINDING,
            "no available agent satisfies the requested policy and capabilities",
        )
