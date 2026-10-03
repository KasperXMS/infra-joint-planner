"""Ready-action consequences: read-only, scheduler-consistent, quality-agnostic."""

import hashlib
import json
from typing import Literal

from pydantic import Field

from infra_joint.control.consequence_profiles import (
    EmpiricalConsequenceProfiles,
    EmpiricalLatency,
    NetworkCategory,
)
from infra_joint.control.contracts import LogicalModelAction, StaticCapabilityContract
from infra_joint.control.cost_history import surface_hash
from infra_joint.control.physical import PreparedPhysicalAction
from infra_joint.core.base import ContractModel
from infra_joint.core.state import EnvironmentSpec, InfrastructureState
from infra_joint.worker.model_backend import is_text_media_type


class MovementConsequence(ContractModel):
    remote_inputs: int = Field(ge=0)
    bytes_upper_bound: int | None = Field(default=None, ge=0)
    configured_serialization_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    empirical_transfer_receipts: tuple[EmpiricalLatency, ...] = ()
    configured_time_is_observed_latency: Literal[False] = False


class ContextConsequence(ContractModel):
    conservative_input_tokens: int | None = Field(default=None, ge=0)
    image_count: int = Field(ge=0)
    context_window: int = Field(gt=0)
    reserved_output_tokens: int = Field(gt=0)
    envelope_fits: bool | None
    basis: Literal["existing_preflight_envelope_not_tokenizer"] = (
        "existing_preflight_envelope_not_tokenizer"
    )


class ActionConsequence(ContractModel):
    operator: str
    static_request_supported: bool
    physical_selection_succeeded: bool
    selection_failure_code: str | None = None
    movement: MovementConsequence | None = None
    context: ContextConsequence | None = None
    model_service: EmpiricalLatency | None = None
    operator_wrapper: EmpiricalLatency | None = None
    output_size_upper_bound: int | None = Field(default=None, ge=0)
    output_size_basis: Literal["unknown"] = "unknown"
    predicts_answer_quality: Literal[False] = False
    reservation_or_execution_performed: Literal[False] = False
    current_queue_and_cache_effects_modeled: Literal[False] = False
    operator_parameters_conditioned: Literal[False] = False


class ActionConsequenceEstimator:
    """No worker client, inference backend, evaluator, artifact contents or mutation."""

    def __init__(
        self, *, environment: EnvironmentSpec, static_capabilities: StaticCapabilityContract,
        profiles: EmpiricalConsequenceProfiles, network_category: NetworkCategory,
        reachable_workers: frozenset[str],
    ) -> None:
        self.environment = environment
        self.static_capabilities = static_capabilities
        self.profiles = profiles
        self.network_category: NetworkCategory = network_category
        self.reachable_workers = reachable_workers

    def evaluate(
        self, prepared: PreparedPhysicalAction, snapshot: InfrastructureState,
    ) -> ActionConsequence:
        encoded = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if (prepared.shared_snapshot_observed_at != snapshot.observed_at
                or prepared.shared_snapshot_sha256 != hashlib.sha256(encoded).hexdigest()):
            raise ValueError("consequence snapshot differs from scheduler snapshot")
        action = prepared.logical_action
        is_model = isinstance(action, LogicalModelAction)
        static_supported = (bool(
            self.static_capabilities.matching_model_classes(action.requirements)
        ) if is_model else any(item.operator == prepared.semantic_action.operator
                               for item in self.static_capabilities.operators))
        if prepared.selection is None:
            if prepared.preparation_failure is None:
                raise ValueError("prepared action has neither selection nor typed failure")
            return ActionConsequence(
                operator=prepared.semantic_action.operator,
                static_request_supported=static_supported, physical_selection_succeeded=False,
                selection_failure_code=prepared.preparation_failure.failure_code,
            )
        selection = prepared.selection
        artifacts = {item.artifact_id: item for item in snapshot.artifacts}
        inputs = tuple(artifacts.get(identifier) for identifier in action.inputs)
        target = selection.selected_agent_id
        known_input_size = (sum(item.size_bytes for item in inputs
                                if item is not None and item.size_bytes is not None)
                            if all(item is not None and item.size_bytes is not None
                                   for item in inputs) else None)
        remote_inputs = 0
        movement_bytes: int | None = 0
        serialization_ms: float | None = 0
        transfer_profiles: list[EmpiricalLatency] = []
        links = {(link.source_agent_id, link.target_agent_id): link for link in snapshot.links}
        for item in inputs:
            if item is not None and target in item.locations:
                continue
            remote_inputs += 1
            if item is None or item.size_bytes is None:
                movement_bytes = None
                serialization_ms = None
                transfer_profiles.append(self._unknown("remote input size unknown"))
                continue
            if movement_bytes is not None:
                movement_bytes += item.size_bytes
            # Exactly RuntimeExecutor's first reachable lexicographic source, not cheapest link.
            sources = sorted(set(item.locations) & self.reachable_workers)
            if not sources:
                serialization_ms = None
                transfer_profiles.append(self._unknown("no reachable transfer source"))
                continue
            source = sources[0]
            link = links.get((source, target))
            if link is None or not link.available or link.bandwidth_mbps is None:
                serialization_ms = None
            elif serialization_ms is not None:
                serialization_ms += item.size_bytes * 8 / (link.bandwidth_mbps * 1000)
            # Zero-byte artifacts have no positive-size empirical transfer receipt.
            if item.size_bytes:
                transfer_profiles.append(self.profiles.transfer(
                    self.network_category, item.size_bytes,
                    path_surface_sha256=surface_hash(source, target),
                ))
        movement = MovementConsequence(
            remote_inputs=remote_inputs, bytes_upper_bound=movement_bytes,
            configured_serialization_ms=serialization_ms,
            empirical_transfer_receipts=tuple(transfer_profiles),
        )
        if not isinstance(action, LogicalModelAction):
            return ActionConsequence(
                operator=prepared.semantic_action.operator,
                static_request_supported=static_supported, physical_selection_succeeded=True,
                movement=movement, operator_wrapper=self.profiles.operator_work(
                    prepared.semantic_action.operator, known_input_size,
                    execution_surface_sha256=surface_hash(target),
                ),
            )
        deployment = next((item for item in self.environment.deployments
                           if item.deployment_id == selection.selected_deployment_id), None)
        if deployment is None or deployment.agent_id != target:
            raise ValueError("prepared model selection does not match environment")
        host = next(item for item in self.environment.agents if item.agent_id == target)
        classes = tuple(item for item in self.static_capabilities.model_classes
                        if item.satisfies(action.requirements)
                        and item.modalities == deployment.modalities
                        and item.capabilities == host.capabilities
                        and item.context_window == deployment.context_window
                        and item.reserved_output_tokens == deployment.reserved_output_tokens
                        and item.image_token_cost == deployment.image_token_cost
                        and item.max_output_bytes == deployment.max_output_bytes)
        envelope: int | None = len(action.prompt.encode("utf-8"))
        image_count = 0
        for item in inputs:
            if item is None or item.media_type is None:
                envelope = None
            elif item.media_type.startswith("image/"):
                image_count += 1
                if envelope is not None:
                    envelope += deployment.image_token_cost
            elif is_text_media_type(item.media_type) and item.size_bytes is not None:
                if envelope is not None:
                    envelope += item.size_bytes
            else:
                envelope = None
        context = ContextConsequence(
            conservative_input_tokens=envelope, image_count=image_count,
            context_window=deployment.context_window,
            reserved_output_tokens=deployment.reserved_output_tokens,
            envelope_fits=(envelope + deployment.reserved_output_tokens <= deployment.context_window
                           if envelope is not None else None),
        )
        service = (self.profiles.model_service(
            model_class=classes[0].capability_class,
            execution_surface_sha256=surface_hash(deployment.deployment_id),
            conservative_input_tokens=envelope, image_count=image_count,
            output_budget=deployment.reserved_output_tokens,
        ) if len(classes) == 1 else self._unknown("selected anonymous model class ambiguous"))
        return ActionConsequence(
            operator="invoke_model", static_request_supported=static_supported,
            physical_selection_succeeded=True, movement=movement, context=context,
            model_service=service,
        )

    def _unknown(self, reason: str) -> EmpiricalLatency:
        return EmpiricalLatency(source="unknown", sample_count=0,
                                minimum_support=self.profiles.minimum_support,
                                unknown_reason=reason)
