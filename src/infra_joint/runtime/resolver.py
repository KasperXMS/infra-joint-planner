from dataclasses import dataclass
from enum import StrEnum

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy, SemanticAction
from infra_joint.core.state import DeploymentSpec, EnvironmentSpec, InfrastructureState
from infra_joint.operators.registry import OperatorSpec


class ResolutionErrorCode(StrEnum):
    INFEASIBLE_BINDING = "infeasible_binding"
    MISSING_INPUT = "missing_input"
    UNSUPPORTED_MODALITY = "unsupported_modality"
    CONTEXT_LIMIT_EXCEEDED = "context_limit_exceeded"


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
        available_deployments = {item.deployment_id for item in state.deployments if item.available}
        artifact_locations = {item.artifact_id: set(item.locations) for item in state.artifacts}
        missing = [
            artifact_id for artifact_id in action.inputs if artifact_id not in artifact_locations
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

        if "model" in operator.capability_requirements:
            return self._resolve_model(
                decision,
                action,
                feasible_agents,
                deployments,
                available_deployments,
                artifact_locations,
                state,
            )

        if decision.policy == PhysicalPolicy.TARGET_AGENT:
            target = decision.target_agent_id
            if target not in feasible_agents:
                raise BindingResolutionError(
                    ResolutionErrorCode.INFEASIBLE_BINDING,
                    f"explicit target agent is infeasible: {target}",
                )
            return ResolvedBinding((target,))  # type: ignore[arg-type]

        if decision.policy == PhysicalPolicy.TARGET_DEPLOYMENT:
            raise BindingResolutionError(
                ResolutionErrorCode.INFEASIBLE_BINDING,
                "non-model operator cannot target a model deployment",
            )

        data_local_agents = set(feasible_agents)
        for artifact_id in action.inputs:
            data_local_agents &= artifact_locations[artifact_id]

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

    def _resolve_model(
        self,
        decision: PhysicalDecision,
        action: SemanticAction,
        feasible_agents: set[str],
        deployments: dict[str, DeploymentSpec],
        available_deployments: set[str],
        artifact_locations: dict[str, set[str]],
        state: InfrastructureState,
    ) -> ResolvedBinding:
        candidates = [
            deployment
            for deployment in deployments.values()
            if deployment.deployment_id in available_deployments
            and deployment.agent_id in feasible_agents
        ]
        if decision.policy == PhysicalPolicy.TARGET_DEPLOYMENT:
            candidates = [
                item for item in candidates if item.deployment_id == decision.target_deployment_id
            ]
        elif decision.policy == PhysicalPolicy.TARGET_AGENT:
            candidates = [item for item in candidates if item.agent_id == decision.target_agent_id]
        elif decision.policy == PhysicalPolicy.DATA_LOCAL:
            candidates = [
                item
                for item in candidates
                if all(item.agent_id in artifact_locations[value] for value in action.inputs)
            ]
        if not candidates:
            raise BindingResolutionError(
                ResolutionErrorCode.INFEASIBLE_BINDING,
                "no available deployment satisfies the requested placement",
            )
        preflight = [(item, self._model_request_error(item, action, state)) for item in candidates]
        candidates = [item for item, error in preflight if error is None]
        if not candidates:
            _, error = sorted(preflight, key=lambda value: value[0].deployment_id)[0]
            if error is None:
                raise RuntimeError("model preflight produced an inconsistent result")
            raise BindingResolutionError(*error)
        ranked = sorted(
            candidates,
            key=lambda item: (
                sum(item.agent_id not in artifact_locations[value] for value in action.inputs),
                item.deployment_id,
            ),
        )
        selected = ranked[0]
        return ResolvedBinding((selected.agent_id,), selected.deployment_id)

    @staticmethod
    def _model_request_error(
        deployment: DeploymentSpec,
        action: SemanticAction,
        state: InfrastructureState,
    ) -> tuple[ResolutionErrorCode, str] | None:
        artifacts = {item.artifact_id: item for item in state.artifacts}
        estimated = len(str(action.arguments.get("prompt", "")).encode("utf-8"))
        for artifact_id in action.inputs:
            artifact = artifacts[artifact_id]
            if artifact.media_type is None or artifact.size_bytes is None:
                return (
                    ResolutionErrorCode.INFEASIBLE_BINDING,
                    f"artifact metadata is unavailable: {artifact_id}",
                )
            if artifact.media_type.startswith("image/"):
                if "image" not in deployment.modalities:
                    return (
                        ResolutionErrorCode.UNSUPPORTED_MODALITY,
                        f"deployment does not support image artifact: {artifact_id}",
                    )
                estimated += deployment.image_token_cost
            elif artifact.media_type.startswith("text/") or artifact.media_type in {
                "application/json",
                "application/jsonl",
                "application/x-ndjson",
            }:
                estimated += artifact.size_bytes
            else:
                return (
                    ResolutionErrorCode.UNSUPPORTED_MODALITY,
                    f"unsupported model artifact media type: {artifact.media_type}",
                )
        if estimated + deployment.reserved_output_tokens > deployment.context_window:
            return (
                ResolutionErrorCode.CONTEXT_LIMIT_EXCEEDED,
                "context limit exceeded before transfer: "
                f"estimated_input={estimated}, "
                f"reserved_output={deployment.reserved_output_tokens}, "
                f"context_window={deployment.context_window}",
            )
        return None

    @staticmethod
    def _raise_no_feasible_agent() -> None:
        raise BindingResolutionError(
            ResolutionErrorCode.INFEASIBLE_BINDING,
            "no available agent satisfies the requested policy and capabilities",
        )
