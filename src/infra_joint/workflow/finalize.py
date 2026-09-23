from infra_joint.core.workflow import WorkflowPlan
from infra_joint.workflow.orchestrator import WorkflowExecutionResult


def extract_terminal_answer(
    plan: WorkflowPlan,
    result: WorkflowExecutionResult,
) -> str:
    """Deterministically extract the designated terminal agent's inline result."""

    terminal = plan.terminal_model_node()
    records = tuple(item for item in result.records if item.node_id == terminal.node_id)
    if len(records) != 1:
        raise ValueError("terminal model node must have exactly one execution record")
    execution = records[0].execution
    if execution is None:
        raise ValueError("terminal model node has no execution result")
    answer = execution.output.get("text")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("terminal model node must return non-empty inline text")
    return answer.strip()
