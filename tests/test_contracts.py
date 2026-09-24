from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from infra_joint.core.action import PhysicalDecision, PhysicalPolicy
from infra_joint.core.state import InfrastructureState
from infra_joint.core.task import (
    ArtifactCollectionRelation,
    ArtifactSpec,
    CollectionCompleteness,
    OutputContract,
    OutputFormat,
    PartitionSemantics,
    TaskContract,
)


def test_task_contract_rejects_unknown_infrastructure_fields() -> None:
    with pytest.raises(ValidationError):
        TaskContract(
            task_id="task-1",
            benchmark_id="demo",
            objective="Answer the question",
            artifacts=(),
            output_contract=OutputContract(
                format=OutputFormat.CHOICE,
                choices=("A", "B"),
            ),
            evaluator_id="exact-choice-v1",
            target_agent_id="edge-a4",  # type: ignore[call-arg]
        )


def test_task_contract_rejects_duplicate_artifacts() -> None:
    artifact = ArtifactSpec(
        artifact_id="input",
        logical_type="document",
        media_type="text/plain",
        size_bytes=10,
    )
    with pytest.raises(ValidationError, match="artifact_id values must be unique"):
        TaskContract(
            task_id="task-1",
            benchmark_id="demo",
            objective="Answer",
            artifacts=(artifact, artifact),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
            evaluator_id="exact-v1",
        )


def test_complete_collection_requires_every_declared_partition() -> None:
    relation = ArtifactCollectionRelation(
        collection_id="corpus",
        partition_index=0,
        partition_count=2,
        partition_method="hash",
        partition_semantics=PartitionSemantics.NON_SEMANTIC,
        completeness=CollectionCompleteness.UNION_IS_COMPLETE,
    )

    with pytest.raises(ValidationError, match="every partition"):
        TaskContract(
            task_id="task-1",
            benchmark_id="demo",
            objective="Answer",
            artifacts=(
                ArtifactSpec(
                    artifact_id="shard-0",
                    logical_type="corpus_shard",
                    media_type="application/json",
                    size_bytes=10,
                    collection=relation,
                ),
            ),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
            evaluator_id="exact-v1",
        )


def test_physical_target_must_match_policy() -> None:
    with pytest.raises(ValidationError, match="requires only target_agent_id"):
        PhysicalDecision(policy=PhysicalPolicy.TARGET_AGENT)

    with pytest.raises(ValidationError, match="does not accept an explicit target"):
        PhysicalDecision(policy=PhysicalPolicy.AUTO, target_agent_id="agent-a")


def test_infrastructure_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        InfrastructureState(
            agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now()
        )

    state = InfrastructureState(
        agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now(UTC)
    )
    assert state.observed_at.tzinfo is UTC
