import asyncio

import pytest
from pydantic import ValidationError

from infra_joint.control.feasibility_interface import ActionFeasibilityAssessment
from infra_joint.control.recovery import interrupted_snapshot, reject_resume
from infra_joint.control.verifier_offline import analyze_verifier_trace
from infra_joint.runtime.action_receipts import ActionReceipt, FileActionReceiptStore


@pytest.mark.asyncio
async def test_cancelled_run_persists_interrupted_result(tmp_path) -> None:
    from infra_joint.benchmarks.base import (
        AdaptationBundle,
        AdaptedExecutionCase,
        BenchmarkSettingKind,
        ValidityAssessment,
    )
    from infra_joint.config import PlannerConfig, RunnerConfig, StaticBackendConfig
    from infra_joint.control.runner import ControlPlaneBenchmarkRunner, PersistedControlPlaneResult
    from infra_joint.core.state import EnvironmentSpec
    from infra_joint.core.task import OutputContract, OutputFormat, TaskContract

    task = TaskContract(
        task_id="cancel-test",
        benchmark_id="synthetic",
        objective="Return A.",
        artifacts=(),
        output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
        evaluator_id="unused",
    )

    class PrivateEvaluation:
        task_id = "cancel-test"
        evaluator_id = "unused"

        def build_evaluator(self):
            raise AssertionError("cancelled run cannot evaluate")

    class CancelledRuntime:
        async def run(self, *_args, **_kwargs):
            raise asyncio.CancelledError()

    bundle = AdaptationBundle(
        execution=AdaptedExecutionCase(
            task=task,
            transformations=(),
            validity=ValidityAssessment(
                information_equivalent=True,
                query_equivalent=True,
                evaluator_equivalent=True,
                setting_kind=BenchmarkSettingKind.OFFICIAL_EQUIVALENT,
            ),
        ),
        private_evaluation=PrivateEvaluation(),  # type: ignore[arg-type]
    )
    runner = ControlPlaneBenchmarkRunner(
        RunnerConfig(
            environment=EnvironmentSpec(agents=(), deployments=()),
            worker_urls={},
            planner=PlannerConfig(model=StaticBackendConfig(response="unused")),
            output_root=tmp_path / "runs",
        ),
        None,
        (),
        worker_clients={},
        logical_runtime=CancelledRuntime(),  # type: ignore[arg-type]
    )
    with pytest.raises(asyncio.CancelledError):
        await runner.run(bundle, run_id="cancelled")
    result = PersistedControlPlaneResult.model_validate_json(
        (tmp_path / "runs" / "cancelled" / "result.json").read_text(encoding="utf-8")
    )
    assert result.interrupted and not result.execution_completed
    assert result.recovery is not None and result.recovery.resume_supported is False
    with pytest.raises(FileExistsError):
        await runner.run(bundle, run_id="cancelled")


def test_no_resume_snapshot_retains_confirmed_and_uncertain_receipts(tmp_path) -> None:
    receipts = FileActionReceiptStore(tmp_path / "receipts")
    digest = "a" * 64
    receipts.put(ActionReceipt(action_id="done", request_sha256=digest, status="reserved"))
    receipts.put(ActionReceipt(action_id="done", request_sha256=digest, status="started"))
    receipts.put(
        ActionReceipt(
            action_id="done", request_sha256=digest, status="succeeded", response={"ok": True}
        )
    )
    receipts.put(ActionReceipt(action_id="unknown", request_sha256=digest, status="reserved"))
    receipts.put(ActionReceipt(action_id="unknown", request_sha256=digest, status="started"))
    snapshot = interrupted_snapshot("run-1", FileActionReceiptStore(tmp_path / "receipts"))
    assert snapshot.confirmed_action_ids == ("done",)
    assert snapshot.indeterminate_action_ids == ("unknown",)
    with pytest.raises(RuntimeError, match="Never replay an indeterminate action"):
        reject_resume(snapshot)


def test_feasibility_contract_requires_unknowns_to_stay_unknown() -> None:
    with pytest.raises(ValidationError):
        ActionFeasibilityAssessment(
            action_id="a",
            feasible=True,
            modality_supported=None,
            context_budget="unknown",
            input_reduction_needed=None,
            certainty="unknown",
        )
    valid = ActionFeasibilityAssessment(
        action_id="a",
        feasible=None,
        modality_supported=None,
        context_budget="unknown",
        input_reduction_needed=None,
        certainty="unknown",
    )
    assert valid.feasible is None


def test_offline_verifier_fingerprints_preserve_final_independent_call() -> None:
    context = {
        "task": {"output_contract": {"format": "short_text"}},
        "phase": "evidence_collection",
        "remaining_budget": {"remaining_manager_turns": 3},
        "observations": [{"action_id": "bad", "failure_code": "schema_validation_failed"}],
        "produced_artifacts": [],
    }
    events = []
    for index in (1, 2, 3):
        events.append(
            {
                "event_type": "logical.verification.input",
                "payload": {"verification_index": index, "context": context},
            }
        )
        events.append(
            {
                "event_type": "logical.verification",
                "payload": {
                    "verification_index": index,
                    "status": "continue",
                    "input_tokens": 10,
                    "output_tokens": 2,
                },
            }
        )
    summary = analyze_verifier_trace(events)
    assert summary.verifier_calls == 3
    assert summary.repeated_schema_failure == 2
    assert summary.no_new_semantic_evidence == 2
    assert summary.same_candidate == 2
    assert summary.strict_duplicate_nonfinal_calls == 1
    assert summary.hypothetical_input_tokens == 10
    assert summary.actual_calls_skipped == 0
