import asyncio
import json
from pathlib import Path

import httpx
import pytest

from infra_joint.control.contracts import LogicalToolAction
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.physical import PhysicalExecutionService
from infra_joint.control.validation import SemanticActionValidator
from infra_joint.core.state import AgentSpec, EnvironmentSpec
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.infrastructure.diagnostics import (
    JsonlObserverDiagnostics,
    ObservationDiagnostic,
    diagnostic_action_ids,
    observer_diagnostic_scope,
)
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import RuntimeExecutor
from infra_joint.worker.artifact_store import FileArtifactStore, StoredArtifact
from infra_joint.worker.server import WorkerStateResponse, create_worker_app


class DiagnosticSink:
    def __init__(self) -> None:
        self.items: list[ObservationDiagnostic] = []

    def append(self, diagnostic: ObservationDiagnostic) -> None:
        self.items.append(diagnostic)


class IntermittentClient(HttpWorkerClient):
    unavailable = False

    async def get_state(self) -> WorkerStateResponse:
        if self.unavailable:
            raise httpx.ReadTimeout("synthetic probe failure")
        return await super().get_state()


@pytest.mark.asyncio
async def test_persisted_artifact_probe_failure_and_recovery_without_semantic_change(
    tmp_path: Path,
) -> None:
    artifact = StoredArtifact.create("synthetic-doc", "text/plain", b"synthetic evidence")
    store = FileArtifactStore(tmp_path)
    store.put(artifact)
    app = create_worker_app("host", {}, artifact_store=store)
    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="host", device="synthetic"),),
        deployments=(),
    )
    sink = DiagnosticSink()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as http:
        client = IntermittentClient("host", http)
        observer = LiveWorkerObserver(environment, {"host": client}, diagnostic_sink=sink)
        assert (await observer.observe()).artifacts[0].artifact_id == "synthetic-doc"
        assert sink.items[-1].artifact_visibility[0].status == "PRESENT"
        client.unavailable = True
        snapshot = await observer.observe()
        assert snapshot.artifacts == ()  # Existing fail-closed snapshot semantics unchanged.
        assert not snapshot.agents[0].available
        assert FileArtifactStore(tmp_path).get("synthetic-doc") == artifact
        assert sink.items[-1].artifact_visibility[0].status == "HOST_UNREACHABLE"
        assert sink.items[-1].probes[0].probe_error_type == "ReadTimeout"
        registry = build_operator_catalog()
        physical = PhysicalExecutionService(
            registry,
            environment,
            observer,
            RuntimeExecutor(registry, environment, {"host": client}),
        )
        task = TaskContract(
            task_id="synthetic", benchmark_id="synthetic", objective="Read synthetic evidence",
            artifacts=(ArtifactSpec(
                artifact_id="synthetic-doc", logical_type="text", media_type="text/plain",
                source_ref="private://synthetic", size_bytes=len(artifact.content),
            ),),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT), evaluator_id="private",
        )
        validator = SemanticActionValidator(task, registry, ("read_artifact",))
        gateway = RuntimeActionGateway(validator, physical)
        action = LogicalToolAction(
                action_id="read",
                owner_agent_id="manager",
                operator="read_artifact",
                inputs=("synthetic-doc",),
        )
        validator.validate_batch((action,))  # Logical artifact readiness remains true.
        outcome = (await gateway.execute_batch((action,), expose_profile=False))[0]
        assert outcome.observation.failure_code == "missing_input"
        assert outcome.observation.physical_profile is None
        assert "host" not in outcome.observation.model_dump_json()
        assert sink.items[-1].action_ids == ("read",)
        assert "synthetic-doc" in validator.known_artifacts
        client.unavailable = False
        assert (await observer.observe()).artifacts[0].artifact_id == "synthetic-doc"
        assert sink.items[-1].artifact_visibility[0].status == "PRESENT"
        assert store.delete("synthetic-doc")
        assert (await observer.observe()).artifacts == ()
        assert sink.items[-1].artifact_visibility[0].status == "ABSENT"
        assert len({item.observation_id for item in sink.items}) == len(sink.items)


@pytest.mark.asyncio
async def test_unseen_artifact_on_incomplete_census_is_unknown() -> None:
    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="host", device="synthetic"),),
        deployments=(),
    )
    sink = DiagnosticSink()
    observer = LiveWorkerObserver(
        environment, {}, diagnostic_sink=sink, expected_artifact_ids=("not-yet-observed",)
    )
    assert (await observer.observe()).artifacts == ()
    assert sink.items[-1].artifact_visibility[0].status == "UNKNOWN"


@pytest.mark.asyncio
async def test_diagnostic_failure_does_not_change_observer_result() -> None:
    class BrokenSink:
        def append(self, diagnostic: ObservationDiagnostic) -> None:
            raise OSError("synthetic diagnostic disk failure")

    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="host", device="synthetic"),),
        deployments=(),
    )
    state = await LiveWorkerObserver(environment, {}, diagnostic_sink=BrokenSink()).observe()
    assert state.artifacts == ()


@pytest.mark.asyncio
async def test_private_sidecar_and_parallel_action_correlation(tmp_path: Path) -> None:
    environment = EnvironmentSpec(
        agents=(AgentSpec(agent_id="internal-worker", device="synthetic"),), deployments=(),
    )
    path = tmp_path / "private" / "observer-diagnostics.jsonl"
    observer = LiveWorkerObserver(
        environment, {}, diagnostic_sink=JsonlObserverDiagnostics(path),
    )

    async def probe_for_action(action_id: str) -> None:
        with observer_diagnostic_scope((action_id,)):
            await asyncio.sleep(0)
            await observer.observe()

    await asyncio.gather(probe_for_action("a"), probe_for_action("b"))
    assert diagnostic_action_ids() == ()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert {tuple(r["action_ids"]) for r in records} == {("a",), ("b",)}
    assert all(r["visibility"] == "private-physical-diagnostics-only" for r in records)
    assert all(r["probes"][0]["worker_id"] == "internal-worker" for r in records)
