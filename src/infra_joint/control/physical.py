from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Literal, Protocol, cast

from pydantic import Field

from infra_joint.control.contracts import (
    LogicalAction,
    LogicalModelAction,
    LogicalObservation,
    PhysicalProfileView,
    ProducedInformation,
)
from infra_joint.control.validation import semantic_action
from infra_joint.core.action import JointAction, PhysicalDecision, PhysicalPolicy, SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.core.errors import TypedExecutionError
from infra_joint.core.state import DeploymentSpec, EnvironmentSpec, InfrastructureState
from infra_joint.infrastructure.observer import InfrastructureObserver
from infra_joint.operators.artifacts import ProducedArtifact
from infra_joint.operators.registry import OperatorRegistry
from infra_joint.runtime.executor import ExecutionResult, RuntimeExecutor
from infra_joint.runtime.resolver import (
    BindingResolutionError,
    DeterministicResolver,
    ResolutionErrorCode,
    ResolvedBinding,
)
from infra_joint.workflow.costing import ExecutionCostProfile

NetworkClass = Literal["local", "constrained", "moderate", "fast", "unknown"]


class PhysicalFeasibilityError(RuntimeError):
    """No current physical binding can satisfy a valid logical action."""


class PhysicalSelection(ContractModel):
    decision: PhysicalDecision
    selected_agent_id: str = Field(min_length=1)
    selected_deployment_id: str | None = None
    rationale: str = Field(min_length=1)


class PhysicalExecutionOutcome(ContractModel):
    observation: LogicalObservation
    infrastructure_before: InfrastructureState
    infrastructure_after: InfrastructureState
    selection: PhysicalSelection | None = None
    execution: ExecutionResult | None = None
    failure: PhysicalFailureTelemetry | None = None


class PhysicalFailureTelemetry(ContractModel):
    operator: str = Field(min_length=1)
    stage: Literal["selection", "execution"]
    failure_code: str = Field(min_length=1)
    failure_message: str = Field(min_length=1)
    duration_ms: float = Field(ge=0)


class PhysicalActionScheduler(Protocol):
    def select(
        self,
        action: LogicalAction,
        semantic: SemanticAction,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> PhysicalSelection: ...


class PhysicalFeasibilityValidator:
    """Validate current device/deployment feasibility after semantic validation."""

    def __init__(
        self,
        *,
        deployment_quality_classes: Mapping[str, frozenset[str]] | None = None,
    ) -> None:
        self._quality_classes = dict(deployment_quality_classes or {})
        self._resolver = DeterministicResolver()

    def validate_tool(
        self,
        semantic: SemanticAction,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> ResolvedBinding:
        return self._resolver.resolve(
            PhysicalDecision(policy=PhysicalPolicy.AUTO),
            semantic,
            registry.binding(semantic.operator).spec,
            environment,
            infrastructure,
        )

    def model_candidates(
        self,
        action: LogicalModelAction,
        semantic: SemanticAction,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> tuple[DeploymentSpec, ...]:
        available_agents = {
            item.agent_id for item in infrastructure.agents if item.available
        }
        available_deployments = {
            item.deployment_id for item in infrastructure.deployments if item.available
        }
        agents = {item.agent_id: item for item in environment.agents}
        operator = registry.binding("invoke_model").spec
        feasible: list[DeploymentSpec] = []
        preflight_errors: list[BindingResolutionError] = []
        saw_modality_mismatch = False
        saw_context_mismatch = False
        for deployment in environment.deployments:
            host = agents[deployment.agent_id]
            if (
                deployment.deployment_id not in available_deployments
                or deployment.agent_id not in available_agents
                or not action.requirements.required_capabilities <= host.capabilities
                or not operator.capability_requirements <= host.capabilities
            ):
                continue
            if not action.requirements.modalities <= deployment.modalities:
                saw_modality_mismatch = True
                continue
            if (
                deployment.context_window < action.requirements.min_context_tokens
                or deployment.reserved_output_tokens
                < action.requirements.reserved_output_tokens
            ):
                saw_context_mismatch = True
                continue
            quality = action.requirements.quality_class
            if quality is not None and quality not in self._quality_classes.get(
                deployment.deployment_id, frozenset()
            ):
                continue
            try:
                self._resolver.resolve(
                    PhysicalDecision(
                        policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                        target_deployment_id=deployment.deployment_id,
                    ),
                    semantic,
                    operator,
                    environment,
                    infrastructure,
                )
            except BindingResolutionError as exc:
                preflight_errors.append(exc)
                continue
            feasible.append(deployment)
        if feasible:
            return tuple(feasible)
        if preflight_errors:
            raise preflight_errors[0]
        if saw_context_mismatch:
            raise BindingResolutionError(
                ResolutionErrorCode.CONTEXT_LIMIT_EXCEEDED,
                "no available deployment satisfies the requested context/output budget",
            )
        if saw_modality_mismatch:
            raise BindingResolutionError(
                ResolutionErrorCode.UNSUPPORTED_MODALITY,
                "no available deployment satisfies the requested modalities",
            )
        raise BindingResolutionError(
            ResolutionErrorCode.INFEASIBLE_BINDING,
            "no available deployment satisfies model capability/quality requirements",
        )


class AutoPhysicalScheduler:
    """System-owned locality resolver with no logical-agent deployment binding."""

    def __init__(
        self,
        *,
        deployment_quality_classes: Mapping[str, frozenset[str]] | None = None,
    ) -> None:
        self._feasibility = PhysicalFeasibilityValidator(
            deployment_quality_classes=deployment_quality_classes
        )

    def select(
        self,
        action: LogicalAction,
        semantic: SemanticAction,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> PhysicalSelection:
        if not isinstance(action, LogicalModelAction):
            resolved = self._feasibility.validate_tool(
                semantic,
                environment,
                infrastructure,
                registry,
            )
            return PhysicalSelection(
                decision=PhysicalDecision(policy=PhysicalPolicy.AUTO),
                selected_agent_id=resolved.agent_ids[0],
                rationale="AUTO selected a capability-feasible data-local worker",
            )

        candidates = self.feasible_model_deployments(
            action,
            semantic,
            environment,
            infrastructure,
            registry,
        )
        artifact_locations = {
            item.artifact_id: frozenset(item.locations) for item in infrastructure.artifacts
        }
        selected = min(
            candidates,
            key=lambda item: (
                sum(item.agent_id not in artifact_locations[value] for value in semantic.inputs),
                item.deployment_id,
            ),
        )
        return PhysicalSelection(
            decision=PhysicalDecision(
                policy=PhysicalPolicy.TARGET_DEPLOYMENT,
                target_deployment_id=selected.deployment_id,
            ),
            selected_agent_id=selected.agent_id,
            selected_deployment_id=selected.deployment_id,
            rationale=(
                "physical layer selected a requirement-feasible deployment with minimum "
                "input movement"
            ),
        )

    def feasible_model_deployments(
        self,
        action: LogicalModelAction,
        semantic: SemanticAction,
        environment: EnvironmentSpec,
        infrastructure: InfrastructureState,
        registry: OperatorRegistry,
    ) -> tuple[DeploymentSpec, ...]:
        return self._feasibility.model_candidates(
            action,
            semantic,
            environment,
            infrastructure,
            registry,
        )


class PhysicalProfiler:
    """Convert physical facts and measured profiles into an identifier-free view."""

    def __init__(
        self,
        environment: EnvironmentSpec,
        registry: OperatorRegistry,
        profiles: tuple[ExecutionCostProfile, ...] = (),
        *,
        scheduler: AutoPhysicalScheduler | None = None,
    ) -> None:
        self._environment = environment
        self._registry = registry
        self._profiles = profiles
        self._scheduler = scheduler or AutoPhysicalScheduler()

    def for_action(
        self,
        action: LogicalAction,
        infrastructure: InfrastructureState,
    ) -> PhysicalProfileView:
        semantic = semantic_action(action)
        artifact_by_id = {item.artifact_id: item for item in infrastructure.artifacts}
        input_bytes = sum(
            artifact_by_id[item].size_bytes or 0
            for item in semantic.inputs
            if item in artifact_by_id
        )
        candidate_agents: list[tuple[str, str | None]] = []
        preflight_unknown: list[str] = []
        if isinstance(action, LogicalModelAction):
            try:
                deployments = self._scheduler.feasible_model_deployments(
                    action,
                    semantic,
                    self._environment,
                    infrastructure,
                    self._registry,
                )
            except BindingResolutionError as exc:
                deployments = ()
                preflight_unknown.append(f"{exc.code.value}: {exc}")
            candidate_agents = [
                (item.agent_id, item.deployment_id) for item in deployments
            ]
        else:
            operator = self._registry.binding(action.operator).spec
            live = {item.agent_id for item in infrastructure.agents if item.available}
            candidate_agents = [
                (item.agent_id, None)
                for item in self._environment.agents
                if item.agent_id in live
                and operator.capability_requirements <= item.capabilities
            ]

        remote_counts: list[int] = []
        transfer_latencies: list[float] = []
        service_latencies: list[float] = []
        queue_units: list[int] = []
        unknown: list[str] = list(preflight_unknown)
        runtime_agents = {item.agent_id: item for item in infrastructure.agents}
        for agent_id, deployment_id in candidate_agents:
            remote = 0
            transfer = 0.0
            complete_transfer = True
            for artifact_id in semantic.inputs:
                artifact = artifact_by_id.get(artifact_id)
                if artifact is None or artifact.size_bytes is None:
                    complete_transfer = False
                    continue
                if agent_id in artifact.locations:
                    continue
                remote += 1
                estimate = self._best_transfer_ms(
                    artifact.locations,
                    agent_id,
                    artifact.size_bytes,
                    infrastructure,
                )
                if estimate is None:
                    complete_transfer = False
                else:
                    transfer += estimate
            remote_counts.append(remote)
            if complete_transfer:
                transfer_latencies.append(transfer)
            profile = self._matching_profile(
                semantic.operator,
                agent_id,
                deployment_id,
                input_bytes,
            )
            if profile is not None:
                service_latencies.append(profile.service_latency_ms)
            runtime = runtime_agents.get(agent_id)
            if runtime is not None:
                queue_units.append(
                    runtime.queue_depth
                    if runtime.queue_depth is not None
                    else runtime.in_flight
                )
        if not candidate_agents:
            unknown.append("no feasible candidates")
        if candidate_agents and len(transfer_latencies) != len(candidate_agents):
            unknown.append("one or more transfer routes lack measurements")
        if candidate_agents and len(service_latencies) != len(candidate_agents):
            unknown.append("one or more service profiles are unavailable")
        return PhysicalProfileView(
            candidate_count=len(candidate_agents),
            input_bytes=input_bytes,
            remote_input_count_range=_range(remote_counts) or (0, 0),
            transfer_latency_ms_range=_range(transfer_latencies),
            service_latency_ms_range=_range(service_latencies),
            queue_pressure_range=_range(queue_units),
            network_class=self._network_class(infrastructure, remote_counts),
            unknown_reasons=tuple(unknown),
        )

    def overview(self, infrastructure: InfrastructureState) -> PhysicalProfileView:
        available_agents = tuple(item for item in infrastructure.agents if item.available)
        bandwidths = [
            item.bandwidth_mbps
            for item in infrastructure.links
            if item.available and item.bandwidth_mbps is not None
        ]
        queue = [
            item.queue_depth if item.queue_depth is not None else item.in_flight
            for item in available_agents
        ]
        return PhysicalProfileView(
            candidate_count=len(available_agents),
            input_bytes=0,
            remote_input_count_range=(0, 0),
            queue_pressure_range=_range(queue),
            network_class=_classify_bandwidth(bandwidths),
            unknown_reasons=() if bandwidths else ("network measurements unavailable",),
        )

    def _matching_profile(
        self,
        operator: str,
        agent_id: str,
        deployment_id: str | None,
        input_units: int,
    ) -> ExecutionCostProfile | None:
        candidates = [
            item
            for item in self._profiles
            if item.operator == operator
            and item.agent_id in {agent_id, "*"}
            and (
                (deployment_id is None and item.deployment_id is None)
                or item.deployment_id == deployment_id
            )
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda item: (
                item.agent_id != agent_id,
                abs((item.input_units or 0) - input_units),
                item.service_latency_ms,
            ),
        )

    @staticmethod
    def _best_transfer_ms(
        sources: tuple[str, ...],
        target: str,
        size_bytes: int,
        infrastructure: InfrastructureState,
    ) -> float | None:
        estimates = [
            link.rtt_ms
            + size_bytes * 8 / (link.bandwidth_mbps * 1_000_000) * 1000
            for link in infrastructure.links
            if link.available
            and link.source_agent_id in sources
            and link.target_agent_id == target
            and link.rtt_ms is not None
            and link.bandwidth_mbps is not None
        ]
        return min(estimates) if estimates else None

    @staticmethod
    def _network_class(
        infrastructure: InfrastructureState,
        remote_counts: list[int],
    ) -> NetworkClass:
        if remote_counts and max(remote_counts) == 0:
            return "local"
        bandwidths = [
            item.bandwidth_mbps
            for item in infrastructure.links
            if item.available and item.bandwidth_mbps is not None
        ]
        return _classify_bandwidth(bandwidths)


class PhysicalExecutionService:
    """Narrow physical boundary above the unchanged RuntimeExecutor."""

    def __init__(
        self,
        registry: OperatorRegistry,
        environment: EnvironmentSpec,
        observer: InfrastructureObserver,
        executor: RuntimeExecutor,
        *,
        scheduler: PhysicalActionScheduler | None = None,
        profiler: PhysicalProfiler | None = None,
    ) -> None:
        self._registry = registry
        self._environment = environment
        self._observer = observer
        self._executor = executor
        self._scheduler = scheduler or AutoPhysicalScheduler()
        self._profiler = profiler or PhysicalProfiler(environment, registry)

    async def profile_overview(self) -> PhysicalProfileView:
        return self._profiler.overview(await self._observer.observe())

    async def execute(
        self,
        action: LogicalAction,
        *,
        expose_profile: bool,
    ) -> PhysicalExecutionOutcome:
        before = await self._observer.observe()
        semantic = semantic_action(action)
        profile = self._profiler.for_action(action, before) if expose_profile else None
        selection: PhysicalSelection | None = None
        stage: Literal["selection", "execution"] = "selection"
        physical_started = perf_counter()
        try:
            selection = self._scheduler.select(
                action,
                semantic,
                self._environment,
                before,
                self._registry,
            )
            stage = "execution"
            physical_started = perf_counter()
            execution = await self._executor.execute(
                JointAction(semantic=semantic, physical=selection.decision), before
            )
            after = await self._observer.observe()
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
                output=execution.output,
                produced_information=self._produced_information(action, execution, after),
                physical_profile=profile,
            )
            return PhysicalExecutionOutcome(
                observation=observation,
                infrastructure_before=before,
                infrastructure_after=after,
                selection=selection,
                execution=execution,
            )
        except (BindingResolutionError, PhysicalFeasibilityError, TypedExecutionError) as exc:
            after = await self._observer.observe()
            if isinstance(exc, (BindingResolutionError, TypedExecutionError)):
                code_value = exc.code.value
            else:
                code_value = "physical_feasibility_failed"
            observation = LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=False,
                failure_code=code_value,
                failure_message=str(exc),
                physical_profile=profile,
            )
            failure = PhysicalFailureTelemetry(
                operator=semantic.operator,
                stage=stage,
                failure_code=code_value,
                failure_message=str(exc),
                duration_ms=(perf_counter() - physical_started) * 1000,
            )
            return PhysicalExecutionOutcome(
                observation=observation,
                infrastructure_before=before,
                infrastructure_after=after,
                selection=selection,
                failure=failure,
            )

    @staticmethod
    def _produced_information(
        action: LogicalAction,
        execution: ExecutionResult,
        infrastructure: InfrastructureState,
    ) -> tuple[ProducedInformation, ...]:
        if not action.outputs:
            return ()
        metadata: list[ProducedArtifact]
        if "artifacts" in execution.output:
            raw = execution.output["artifacts"]
            if not isinstance(raw, list):
                raise ValueError("worker artifacts output must be a list")
            metadata = [
                ProducedArtifact.model_validate(item)
                for item in cast(list[object], raw)
            ]
        elif "artifact_id" in execution.output:
            metadata = [ProducedArtifact.model_validate(execution.output)]
        else:
            raise ValueError("declared logical outputs were not materialized by the worker")
        declared = {item.artifact_id: item for item in action.outputs}
        runtime = {item.artifact_id: item for item in infrastructure.artifacts}
        if set(item.artifact_id for item in metadata) != set(declared):
            raise ValueError("materialized outputs do not match logical action declarations")
        return tuple(
            ProducedInformation(
                artifact_id=item.artifact_id,
                semantic_type=declared[item.artifact_id].semantic_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                sha256_hex=runtime[item.artifact_id].sha256_hex,
            )
            for item in metadata
        )


def _range[T: int | float](values: list[T]) -> tuple[T, T] | None:
    return (min(values), max(values)) if values else None


def _classify_bandwidth(values: list[float]) -> NetworkClass:
    if not values:
        return "unknown"
    representative = min(values)
    if representative <= 5:
        return "constrained"
    if representative < 30:
        return "moderate"
    return "fast"
