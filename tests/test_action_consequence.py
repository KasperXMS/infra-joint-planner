import hashlib
import json
from datetime import UTC, datetime

import pytest
from test_control_plane import FrozenSelectionExecutor, SequencedObserver

from infra_joint.control.capabilities import build_static_capability_contract
from infra_joint.control.consequence import ActionConsequenceEstimator
from infra_joint.control.consequence_profiles import (
    CostHistory,
    EmpiricalConsequenceProfiles,
    ModelServiceSample,
)
from infra_joint.control.contracts import ExecutionRequirements, LogicalAction, LogicalModelAction
from infra_joint.control.cost_history import surface_hash
from infra_joint.control.physical import (
    PhysicalExecutionService,
    PhysicalSelection,
    PreparedPhysicalAction,
)
from infra_joint.control.validation import semantic_action
from infra_joint.core.action import PhysicalDecision, PhysicalPolicy
from infra_joint.core.state import (
    AgentRuntimeState,
    AgentSpec,
    ArtifactRuntimeState,
    DeploymentRuntimeState,
    DeploymentSpec,
    EnvironmentSpec,
    InfrastructureState,
    LinkRuntimeState,
)
from infra_joint.operators.catalog import build_operator_catalog


def environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        agents=tuple(AgentSpec(agent_id=identifier, device="private-hardware",
                               capabilities=frozenset({"model", "retrieval"}))
                     for identifier in ("private-A", "private-B", "private-C")),
        deployments=(DeploymentSpec(deployment_id="private-model", agent_id="private-A",
                                    model_id="private-blob", context_window=32768,
                                    reserved_output_tokens=2048, image_token_cost=2048,
                                    modalities=frozenset({"text", "image"})),),
    )


def snapshot(*, size: int | None = 100, media: str = "text/plain",
             local: bool = False, bandwidth: float | None = 3) -> InfrastructureState:
    return InfrastructureState(
        agents=tuple(AgentRuntimeState(agent_id=item.agent_id, available=True)
                     for item in environment().agents),
        deployments=(DeploymentRuntimeState(deployment_id="private-model", available=True),),
        artifacts=(ArtifactRuntimeState(artifact_id="source-中文", media_type=media,
                                        size_bytes=size, locations=("private-A",) if local
                                        else ("private-C", "private-B")),),
        links=(LinkRuntimeState(source_agent_id="private-B", target_agent_id="private-A",
                                available=True, bandwidth_mbps=bandwidth),
               LinkRuntimeState(source_agent_id="private-C", target_agent_id="private-A",
                                available=True, bandwidth_mbps=100)),
        observed_at=datetime(2026, 10, 4, tzinfo=UTC),
    )


def action(**overrides: object) -> LogicalModelAction:
    values: dict[str, object] = {
        "action_id": "reason", "owner_agent_id": "manager", "inputs": ("source-中文",),
        "prompt": "Solve.",
    }
    return LogicalModelAction.model_validate(values | overrides)


def prepare(current: InfrastructureState, logical: LogicalAction) -> PreparedPhysicalAction:
    encoded = json.dumps(current.model_dump(mode="json"), ensure_ascii=False,
                         separators=(",", ":"), sort_keys=True).encode()
    return PreparedPhysicalAction(
        batch_id="decision-01", logical_action=logical, semantic_action=semantic_action(logical),
        selection=PhysicalSelection(decision=PhysicalDecision(policy=PhysicalPolicy.AUTO),
                                     selected_agent_id="private-A",
                                     selected_deployment_id="private-model", rationale="test"),
        shared_snapshot_observed_at=current.observed_at,
        shared_snapshot_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def estimator(history: CostHistory | None = None) -> ActionConsequenceEstimator:
    return ActionConsequenceEstimator(
        environment=environment(), static_capabilities=build_static_capability_contract(
            environment(), build_operator_catalog(), ("invoke_model",)),
        profiles=EmpiricalConsequenceProfiles(history or CostHistory()),
        network_category="constrained",
        reachable_workers=frozenset(item.agent_id for item in environment().agents),
    )


def test_transfer_matches_executor_source_not_cheapest_and_configured_not_observed() -> None:
    current = snapshot(size=375000)
    card = estimator().evaluate(prepare(current, action()), current)
    assert card.movement is not None
    assert card.movement.bytes_upper_bound == 375000
    assert card.movement.configured_serialization_ms == 1000
    assert card.movement.empirical_transfer_receipts[0].source == "unknown"
    assert card.context is not None and card.context.envelope_fits is False
    for private in ("private-", "source-中文", "deployment", "route", "gold"):
        assert private not in card.model_dump_json()
    assert card.predicts_answer_quality is False
    assert card.output_size_upper_bound is None


def test_local_transfer_zero_but_model_service_supported_only_by_matching_history() -> None:
    current = snapshot(local=True)
    history = CostHistory(models=tuple(ModelServiceSample(
        sample_sha256=f"{i:064x}", model_class="model-class-01",
        execution_surface_sha256=surface_hash("private-model"), conservative_input_tokens=106,
        image_count=0, output_budget=2048, service_latency_ms=10 + 10 * i,
    ) for i in range(3)))
    card = estimator(history).evaluate(prepare(current, action()), current)
    assert card.movement is not None and card.context is not None
    assert card.movement.remote_inputs == 0
    assert card.movement.bytes_upper_bound == 0
    assert card.movement.configured_serialization_ms == 0
    assert card.context.conservative_input_tokens == 106
    assert card.context.reserved_output_tokens == 2048
    assert card.model_service is not None and card.model_service.p50_ms == 20


def test_images_use_static_context_cost_not_jpeg_payload_bytes() -> None:
    current = snapshot(size=100000, media="image/jpeg")
    card = estimator().evaluate(prepare(current, action()), current)
    assert card.context is not None
    assert card.context.image_count == 1
    assert card.context.conservative_input_tokens == 2054
    assert card.context.envelope_fits is True


def test_unknown_remote_size_not_zero_and_unavailable_link_not_faked_latency() -> None:
    for current in (snapshot(size=None), snapshot(bandwidth=None)):
        card = estimator().evaluate(prepare(current, action()), current)
        assert card.movement is not None
        assert card.movement.configured_serialization_ms is None
        assert card.movement.empirical_transfer_receipts[0].source == "unknown"
    current = snapshot(size=None)
    card = estimator().evaluate(prepare(current, action()), current)
    assert card.movement is not None and card.movement.bytes_upper_bound is None
    assert card.context is not None and card.context.envelope_fits is None


def test_snapshot_changes_reject_quote_even_if_observed_timestamp_unchanged() -> None:
    current = snapshot()
    with pytest.raises(ValueError, match="snapshot differs"):
        estimator().evaluate(prepare(current, action()), snapshot(size=200))


def test_real_prepare_plus_quote_performs_no_execution_or_observer_call() -> None:
    current = snapshot()
    observer = SequencedObserver(current)
    executor = FrozenSelectionExecutor()
    physical = PhysicalExecutionService(build_operator_catalog(), environment(), observer,
                                        executor)  # type: ignore[arg-type]
    prepared = physical.prepare_batch((action(),), current, batch_id="quote", expose_profile=False)
    card = estimator().evaluate(prepared[0], current)
    assert card.physical_selection_succeeded
    assert observer.calls == 0 and executor.decisions == []


def test_static_impossible_request_not_dynamic_unavailability_or_failure_text_leak() -> None:
    current = snapshot()
    observer = SequencedObserver(current)
    executor = FrozenSelectionExecutor()
    physical = PhysicalExecutionService(build_operator_catalog(), environment(), observer,
                                        executor)  # type: ignore[arg-type]
    logical = action(requirements=ExecutionRequirements(min_context_tokens=40000))
    prepared = physical.prepare_batch((logical,), current, batch_id="quote", expose_profile=False)
    card = estimator().evaluate(prepared[0], current)
    assert card.static_request_supported is False
    assert card.physical_selection_succeeded is False
    assert card.selection_failure_code is not None
    assert card.movement is None  # No invented transfer target when no binding exists.
    assert "private-" not in card.model_dump_json()
    assert executor.decisions == []
