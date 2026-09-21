from datetime import UTC, datetime

import pytest

from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
    LinkSpec,
)
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.experiments.preliminary import (
    AwarePlannerContext,
    LLMNaiveAwarePlanner,
    NetworkRegime,
)
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.worker.model_backend import StaticModelBackend


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=(
            AgentSpec(agent_id="EDGE", device="edge", capabilities=frozenset({"structured"})),
            AgentSpec(agent_id="GPU", device="gpu", capabilities=frozenset({"model"})),
        ),
        deployments=(
            DeploymentSpec(
                deployment_id="gpu-text",
                agent_id="GPU",
                model_id="text-model",
                modalities=frozenset({"text"}),
                context_window=4096,
            ),
        ),
        links=(
            LinkSpec(
                source_agent_id="EDGE",
                target_agent_id="GPU",
                bandwidth_mbps=3,
                rtt_ms=50,
            ),
        ),
    )


def state() -> InfrastructureState:
    return InfrastructureState(
        agents=(
            AgentRuntimeState(agent_id="EDGE", available=True),
            AgentRuntimeState(agent_id="GPU", available=True),
        ),
        deployments=(DeploymentRuntimeState(deployment_id="gpu-text", available=True),),
        artifacts=(
            ArtifactRuntimeState(
                artifact_id="records",
                locations=("EDGE",),
                media_type="application/json",
                size_bytes=2,
                sha256_hex="0" * 64,
            ),
        ),
        links=(
            LinkRuntimeState(
                source_agent_id="EDGE",
                target_agent_id="GPU",
                available=True,
                bandwidth_mbps=3,
                rtt_ms=50,
            ),
        ),
        observed_at=datetime.now(UTC),
    )


def task() -> TaskContract:
    return TaskContract(
        task_id="task",
        benchmark_id="benchmark",
        objective="answer the question",
        artifacts=(
            ArtifactSpec(
                artifact_id="records",
                logical_type="records",
                media_type="application/json",
                size_bytes=2,
                source_ref="private-host://must-not-leak",
            ),
        ),
        output_contract=OutputContract(format=OutputFormat.CHOICE, choices=("A", "B")),
        evaluator_id="private-evaluator",
    )


def test_aware_prompt_adds_physical_state_without_source_reference() -> None:
    planner = LLMNaiveAwarePlanner(
        StaticModelBackend('{"decision_type":"finish","reason":"done"}'),
        build_operator_catalog(),
        environment(),
    )
    prompt = planner.render_prompt(
        AwarePlannerContext(
            task=task(),
            decisions=(),
            observations=(),
            infrastructure=state(),
            remaining_steps=8,
        )
    )

    assert '"bandwidth_mbps":3.0' in prompt
    assert '"locations":["EDGE"]' in prompt
    assert "private-host" not in prompt
    assert "gold" not in prompt.casefold()


@pytest.mark.asyncio
async def test_aware_planner_accepts_explicit_physical_decision() -> None:
    backend = StaticModelBackend(
        """{
          "decision_type":"action",
          "semantic":{"operator":"filter_records","inputs":["records"],"arguments":{
            "field":"date","op":"eq","value":"today","output_artifact_id":"filtered"
          }},
          "physical":{"policy":"target_agent","target_agent_id":"EDGE"}
        }"""
    )
    planner = LLMNaiveAwarePlanner(backend, build_operator_catalog(), environment())
    outcome = await planner.decide(
        AwarePlannerContext(
            task=task(),
            decisions=(),
            observations=(),
            infrastructure=state(),
            remaining_steps=8,
        )
    )

    assert outcome.decision.decision_type == "action"
    assert outcome.decision.physical.target_agent_id == "EDGE"


def test_network_regime_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        NetworkRegime("invalid", 0, 0)
