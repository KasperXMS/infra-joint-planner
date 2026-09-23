from collections.abc import Sequence

import pytest

import scripts.heterogeneous_experiment_v1 as experiment_module
from infra_joint.workflow.runner import (
    PersistedWorkflowRunResult,
    WorkflowRunFailure,
)
from scripts.heterogeneous_experiment_v1 import (
    cleanup_generated_artifacts,
    finish_reason_validation_error,
)


def test_finish_reason_validation_does_not_mask_primary_workflow_failure() -> None:
    result = PersistedWorkflowRunResult.model_construct(
        execution_completed=False,
        failure=WorkflowRunFailure(
            code="internal_error",
            exception_type="RuntimeError",
            message="prepositioned artifact mismatch",
        ),
        workflow=None,
    )

    assert finish_reason_validation_error(result) is None


@pytest.mark.asyncio
async def test_artifact_cleanup_records_one_idempotent_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OneTransientFailureRunner:
        attempts: dict[str, int] = {}

        async def run(self, ssh_target: str, command: Sequence[str]) -> str:
            del command
            attempts = self.attempts.get(ssh_target, 0) + 1
            self.attempts[ssh_target] = attempts
            if ssh_target == "edge@192.168.0.105" and attempts == 1:
                raise RuntimeError("injected missing exit status")
            return ""

    monkeypatch.setattr(
        experiment_module,
        "SshCommandRunner",
        OneTransientFailureRunner,
    )

    recoveries = await cleanup_generated_artifacts(("generated-artifact",))

    assert len(recoveries) == 1
    assert "A5" in recoveries[0]
    assert "retry succeeded" in recoveries[0]


@pytest.mark.asyncio
async def test_artifact_cleanup_fails_closed_after_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PersistentFailureRunner:
        async def run(self, ssh_target: str, command: Sequence[str]) -> str:
            del command
            if ssh_target == "edge@192.168.0.105":
                raise RuntimeError("injected persistent failure")
            return ""

    monkeypatch.setattr(
        experiment_module,
        "SshCommandRunner",
        PersistentFailureRunner,
    )

    with pytest.raises(RuntimeError, match="A5 cleanup failed after one.*retry"):
        await cleanup_generated_artifacts(("generated-artifact",))
