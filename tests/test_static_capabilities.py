import json

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.contracts import ExecutionRequirements
from infra_joint.core.state import AgentSpec, DeploymentSpec, EnvironmentSpec
from infra_joint.operators.catalog import build_operator_catalog


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(
                agent_id="private-worker-a",
                device="private-device-a",
                capabilities=frozenset(
                    {"model", "retrieval", "structured", "media.image"}
                ),
            ),
            AgentSpec(
                agent_id="private-worker-b",
                device="private-device-b",
                capabilities=frozenset(
                    {"model", "retrieval", "structured", "media.image"}
                ),
            ),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="private-deployment-a",
                agent_id="private-worker-a",
                model_id="private-model-a",
                modalities=frozenset({"text", "image"}),
                context_window=16_384,
                reserved_output_tokens=1_024,
            ),
            DeploymentSpec(
                deployment_id="private-deployment-b",
                agent_id="private-worker-b",
                model_id="private-model-b",
                modalities=frozenset({"text", "image"}),
                context_window=16_384,
                reserved_output_tokens=1_024,
            ),
        ),
    )


def test_static_capability_contract_aggregates_without_physical_identity() -> None:
    contract = build_static_capability_contract(
        environment(),
        build_operator_catalog(),
        ("bm25_retrieve", "invoke_model", "sample_frames"),
    )

    assert tuple(item.operator for item in contract.operators) == (
        "bm25_retrieve",
        "invoke_model",
        "sample_frames",
    )
    assert len(contract.model_classes) == 1
    model_class = contract.model_classes[0]
    assert model_class.capability_class == "model-class-01"
    assert model_class.modalities == frozenset({"text", "image"})
    assert model_class.context_window == 16_384
    assert model_class.reserved_output_tokens == 1_024
    assert model_class.quality_classes == frozenset()

    serialized = json.dumps(contract.model_dump(mode="json"), sort_keys=True)
    for private in (
        "private-worker",
        "private-device",
        "private-deployment",
        "private-model",
        "agent_id",
        "deployment_id",
        "availability",
    ):
        assert private not in serialized


def test_static_capability_contract_classifies_model_requirements() -> None:
    contract = build_static_capability_contract(
        environment(),
        build_operator_catalog(),
        ("invoke_model",),
    )

    assert contract.matching_model_classes(
        ExecutionRequirements(
            modalities=frozenset({"text", "image"}),
            min_context_tokens=16_384,
            reserved_output_tokens=1_024,
        )
    ) == ("model-class-01",)
    assert not contract.matching_model_classes(
        ExecutionRequirements(min_context_tokens=16_385)
    )
    assert not contract.matching_model_classes(
        ExecutionRequirements(quality_class="high_quality")
    )
