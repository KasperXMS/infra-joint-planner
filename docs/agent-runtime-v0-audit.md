# Agent Runtime v0 finalization audit

Branch: `open-ended-mas-preliminary-v1`  
Implementation base: `6b5c500`

## Scope and result

Agent Runtime v0 retains the plan-once workflow architecture and the existing
infrastructure-aware orchestrator/scheduler behavior. No experiment runs, dynamic
replanning, retries, spawning/delegation, model substitution, migration/prefetch, RL, or
new scheduling policy were added.

The MAS benchmark path no longer calls `ContractAwareFinalizer`. It deterministically
extracts the non-empty `text` returned by the unique terminal `invoke_model` node and passes
that exact text to the unchanged private evaluator. Finalizer telemetry remains present for
trace compatibility, but its model telemetry is `null`.

`AgentExecutionContext` now contains an `AgentTaskView` rather than `TaskContract`.
`source_ref`, `evaluator_id`, and evaluator-private gold/supporting-evidence data are absent
from the view, effective agent prompts, and agent-level trace payloads.

`WorkflowPlan.validate_against` now validates `invoke_model` output cardinality, artifact-ID
agreement, and text media types before execution. The workflow planner and runner also
require one designated terminal model node before the orchestrator starts. Runtime checks
remain as defense in depth.

## Changed files

- `src/infra_joint/agents/__init__.py`
- `src/infra_joint/agents/context.py`
- `src/infra_joint/agents/manager.py`
- `src/infra_joint/core/workflow.py`
- `src/infra_joint/workflow/finalize.py`
- `src/infra_joint/workflow/planner.py`
- `src/infra_joint/workflow/runner.py`
- `tests/test_agent_runtime.py`
- `tests/test_workflow_contracts.py`
- `tests/test_workflow_planner.py`
- `tests/test_workflow_runner.py`

## Tests added or strengthened

- Terminal answer/evaluator test forbids any post-workflow model call and verifies the
  persisted/evaluated answer is the terminal agent output.
- Agent-context leakage test checks the context schema, effective prompt, and emitted agent
  traces for private source/evaluator/gold/supporting-evidence fields.
- Plan-contract tests cover multiple model outputs, mismatched output IDs, invalid media
  types, invalid inline materialization metadata, and a valid single text output.
- LLM workflow-planner test verifies an invalid generated plan fails during planning, before
  workflow execution.

## Verification

- Full pytest: `uv run python -m pytest` — **172 passed**.
- Ruff: `uv run ruff check .` — **passed**.
- Strict Pyright: `uv run pyright` — **0 errors, 0 warnings, 0 informations**.

## Final workflow

`Task -> WorkflowPlanner -> WorkflowPlan -> AgentManager -> AgentAction -> Infra-Aware Orchestrator -> RuntimeExecutor -> terminal agent answer -> evaluator`
