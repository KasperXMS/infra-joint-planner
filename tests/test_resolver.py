from datetime import UTC, datetime

import pytest

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy, SemanticAction
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
)
from infra_joint.operators.registry import OperatorSpec
from infra_joint.runtime.resolver import (
    BindingResolutionError,
    DeterministicResolver,
    ResolutionErrorCode,
)


@pytest.fixture
def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="edge", device="orin", capabilities=frozenset({"text"})),
            AgentSpec(agent_id="gpu", device="4090", capabilities=frozenset({"text", "vision"})),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="vlm",
                agent_id="gpu",
                model_id="vision-model",
                modalities=frozenset({"text", "image"}),
                context_window=32768,
            ),
        ),
    )


@pytest.fixture
def state() -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="edge", available=True),
            AgentRuntimeState(agent_id="gpu", available=True),
        ),
        deployments=(DeploymentRuntimeState(deployment_id="vlm", available=True),),
        artifacts=(ArtifactRuntimeState(artifact_id="image", locations=("edge",)),),
        links=(),
        observed_at=datetime.now(UTC),
    )


def test_auto_prefers_data_local_feasible_agent(
    environment: EnvironmentSpec, state: InfrastructureState
) -> None:
    resolver = DeterministicResolver()
    binding = resolver.resolve(
        PhysicalDecision(policy=PhysicalPolicy.AUTO),
        SemanticAction(operator="inspect", inputs=("image",)),
        OperatorSpec(
            operator_id="inspect",
            description="Inspect input",
            capability_requirements=frozenset({"text"}),
        ),
        environment,
        state,
    )
    assert binding.agent_ids == ("edge",)


def test_explicit_infeasible_target_is_not_overridden(
    environment: EnvironmentSpec, state: InfrastructureState
) -> None:
    resolver = DeterministicResolver()
    with pytest.raises(BindingResolutionError) as error:
        resolver.resolve(
            PhysicalDecision(
                policy=PhysicalPolicy.TARGET_AGENT,
                target_agent_id="edge",
            ),
            SemanticAction(operator="inspect", inputs=("image",)),
            OperatorSpec(
                operator_id="inspect",
                description="Inspect an image",
                capability_requirements=frozenset({"vision"}),
            ),
            environment,
            state,
        )
    assert error.value.code == ResolutionErrorCode.INFEASIBLE_BINDING


def test_auto_accounts_for_capability_before_locality(
    environment: EnvironmentSpec, state: InfrastructureState
) -> None:
    resolver = DeterministicResolver()
    binding = resolver.resolve(
        PhysicalDecision(policy=PhysicalPolicy.AUTO),
        SemanticAction(operator="inspect", inputs=("image",)),
        OperatorSpec(
            operator_id="inspect",
            description="Inspect an image",
            capability_requirements=frozenset({"vision"}),
        ),
        environment,
        state,
    )
    assert binding.agent_ids == ("gpu",)
