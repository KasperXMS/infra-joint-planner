import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from infra_joint.control.contracts import (
    LogicalObservation,
    LogicalOutput,
    LogicalToolAction,
    ProducedInformation,
)
from infra_joint.control.gateway import RuntimeActionGateway
from infra_joint.control.physical import PhysicalExecutionOutcome, PhysicalExecutionService
from infra_joint.control.validation import SemanticActionValidator, SemanticValidationError
from infra_joint.core.state import AgentSpec, EnvironmentSpec, InfrastructureState
from infra_joint.core.task import ArtifactSpec, OutputContract, OutputFormat, TaskContract
from infra_joint.infrastructure.observer import LiveWorkerObserver
from infra_joint.operators.catalog import build_operator_catalog
from infra_joint.runtime.action_receipts import FileActionReceiptStore
from infra_joint.runtime.client import HttpWorkerClient
from infra_joint.runtime.executor import RuntimeExecutor
from infra_joint.worker.artifact_store import InMemoryArtifactStore, StoredArtifact
from infra_joint.worker.server import create_worker_app


def _task() -> TaskContract:
    return TaskContract(
        task_id="receipt-test",
        benchmark_id="synthetic",
        objective="Read both sources.",
        artifacts=tuple(
            ArtifactSpec(
                artifact_id=name, logical_type="text", media_type="text/plain", size_bytes=3
            )
            for name in ("a", "b")
        ),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="private",
    )


def _action(name: str) -> LogicalToolAction:
    return LogicalToolAction(
        action_id=name,
        owner_agent_id="manager",
        operator="read_artifact",
        inputs=(name,),
        outputs=(
            LogicalOutput(artifact_id=f"out-{name}", semantic_type="text", media_type="text/plain"),
        ),
    )


class SplitPhysical:
    async def execute(
        self, action: LogicalToolAction, *, expose_profile: bool
    ) -> PhysicalExecutionOutcome:
        await asyncio.sleep(0)
        if action.action_id == "b":
            raise httpx.ReadError("reply lost")
        state = InfrastructureState(
            agents=(), deployments=(), artifacts=(), links=(), observed_at=datetime.now(UTC)
        )
        return PhysicalExecutionOutcome(
            observation=LogicalObservation(
                action_id=action.action_id,
                owner_agent_id=action.owner_agent_id,
                succeeded=True,
                produced_information=(
                    ProducedInformation(
                        artifact_id="out-a",
                        semantic_type="text",
                        media_type="text/plain",
                        size_bytes=3,
                    ),
                ),
            ),
            infrastructure_before=state,
            infrastructure_after=state,
        )


@pytest.mark.asyncio
async def test_parallel_failure_preserves_success_and_blocks_duplicate(tmp_path) -> None:
    validator = SemanticActionValidator(_task(), build_operator_catalog(), ("read_artifact",))
    receipts = FileActionReceiptStore(tmp_path / "receipts")
    gateway = RuntimeActionGateway(validator, SplitPhysical(), receipt_store=receipts)  # type: ignore[arg-type]
    with pytest.raises(httpx.ReadError) as raised:
        await gateway.execute_batch((_action("a"), _action("b")), expose_profile=False)
    assert validator.producer_of("out-a") == "a"
    assert validator.producer_of("out-b") is None
    assert receipts.get("a").status == "succeeded"
    assert receipts.get("b").status == "indeterminate"
    assert len(raised.value._infra_joint_settled_outcomes) == 1
    assert FileActionReceiptStore(tmp_path / "receipts").get("a").status == "succeeded"
    with pytest.raises(SemanticValidationError):
        await gateway.execute_batch((_action("a"),), expose_profile=False)


@pytest.mark.asyncio
async def test_cancelled_remote_action_remains_indeterminate(tmp_path) -> None:
    entered = asyncio.Event()

    class SlowPhysical:
        async def execute(self, action, *, expose_profile):
            entered.set()
            await asyncio.Event().wait()

    receipts = FileActionReceiptStore(tmp_path / "receipts")
    gateway = RuntimeActionGateway(
        SemanticActionValidator(_task(), build_operator_catalog(), ("read_artifact",)),
        SlowPhysical(),
        receipt_store=receipts,  # type: ignore[arg-type]
    )
    execution = asyncio.create_task(gateway.execute_batch((_action("a"),), expose_profile=False))
    await asyncio.wait_for(entered.wait(), timeout=1)
    execution.cancel()
    with pytest.raises(asyncio.CancelledError):
        await execution
    assert receipts.get("a").status == "indeterminate"


@pytest.mark.asyncio
async def test_worker_receipt_survives_lost_reply_and_prevents_replay(tmp_path) -> None:
    store = InMemoryArtifactStore((StoredArtifact.create("a", "text/plain", b"abc"),))
    app = create_worker_app(
        "worker",
        {},
        artifact_store=store,
        receipt_store=FileActionReceiptStore(tmp_path / "worker-receipts"),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as http:
        client = HttpWorkerClient("worker", http)
        from infra_joint.core.action import SemanticAction

        action = SemanticAction(operator="read_artifact", inputs=("a",), arguments={})
        first = await client.execute_operator_with_receipt(action, None, action_id="run-1:read-a")
        receipt = await client.get_action_receipt("run-1:read-a")
        assert receipt is not None and receipt.effective_status == "succeeded"
        second = await client.execute_operator_with_receipt(action, None, action_id="run-1:read-a")
        assert second == first
        assert FileActionReceiptStore(tmp_path / "worker-receipts").get("run-1:read-a") == receipt
        with pytest.raises(httpx.HTTPStatusError):
            await client.execute_operator_with_receipt(
                SemanticAction(operator="read_artifact", inputs=("b",), arguments={}),
                None,
                action_id="run-1:read-a",
            )


@pytest.mark.asyncio
async def test_controller_reconciles_worker_success_after_lost_reply(tmp_path) -> None:
    artifact_store = InMemoryArtifactStore((StoredArtifact.create("a", "text/plain", b"abc"),))
    app = create_worker_app(
        "worker",
        {},
        artifact_store=artifact_store,
        receipt_store=FileActionReceiptStore(tmp_path / "worker"),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://worker"
    ) as http:
        underlying = HttpWorkerClient("worker", http)

        class LostReplyClient:
            def __getattr__(self, name):
                return getattr(underlying, name)

            async def execute_operator_with_receipt(self, action, deployment_id, *, action_id):
                await underlying.execute_operator_with_receipt(
                    action, deployment_id, action_id=action_id
                )
                raise httpx.ReadError("reply lost after remote success")

        clients = {"worker": LostReplyClient()}
        environment = EnvironmentSpec(
            agents=(AgentSpec(agent_id="worker", device="edge"),), deployments=()
        )
        registry = build_operator_catalog()
        physical = PhysicalExecutionService(
            registry,
            environment,
            LiveWorkerObserver(environment, clients),
            RuntimeExecutor(registry, environment, clients),
        )
        receipts = FileActionReceiptStore(tmp_path / "controller")
        gateway = RuntimeActionGateway(
            SemanticActionValidator(_task(), registry, ("read_artifact",)),
            physical,
            receipt_store=receipts,
        )
        action = LogicalToolAction(
            action_id="read-a", owner_agent_id="manager", operator="read_artifact", inputs=("a",)
        )
        (outcome,) = await gateway.execute_batch((action,), expose_profile=False)
        assert outcome.observation.succeeded
        assert outcome.reconciled_from_worker_receipt
        assert outcome.execution is None  # recovered success does not fabricate service work
        assert receipts.get("read-a").status == "reconciled"
