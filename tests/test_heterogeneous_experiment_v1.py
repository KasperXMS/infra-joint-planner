from infra_joint.workflow.runner import (
    PersistedWorkflowRunResult,
    WorkflowRunFailure,
)
from scripts.heterogeneous_experiment_v1 import finish_reason_validation_error


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
