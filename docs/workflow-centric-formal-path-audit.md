# Workflow-Centric Formal Path — Phase 1 Audit

## Scope and outcome

This change adds a parallel formal control path implementing:

\[
G_0=\pi_0(\tau,C),\qquad
G_{t+1}=\mathcal A(G_t,\phi(H_t)),\qquad
X_t=\Omega(G_t,H_t).
\]

It does not replace the SDK-native persistent-agent path or the legacy DAG/replanning path. It
does not change operator, worker, runtime, infrastructure, scheduler, benchmark-adapter, or
evaluator behavior. No formal benchmark, Blind-vs-Aware sweep, prompt tuning, RL, learned cost
model, or task-specific transformation was run.

## New semantic workflow contract

`control/workflow.py` defines an infrastructure-free `SemanticWorkflowPlan` built directly from
the existing `LogicalToolAction` and `LogicalModelAction` contracts. It contains only a workflow
ID/version, logical actions, explicit artifact/control dependencies, and a terminal action ID.
Strict models reject physical fields. A separate `WorkflowRuntimeState` partitions every action
into completed, running, or pending state.

The finite revision vocabulary is:

- `AddAction`
- `RemovePendingAction`
- `ReplacePendingAction`
- `AddDependency`
- `RemovePendingDependency`

`WorkflowPatch` is applied sequentially and fail-closed. Completed and running actions are
immutable, and dependencies entering completed/running consumers are immutable. Only the pending
suffix can change; executed work is never rolled back or replayed.

`control/workflow_validation.py` performs semantic-only validation. It does not accept or read an
`InfrastructureState`. It checks action/dependency identity, operator and argument schemas, static
model feasibility, unique artifact production, input provenance, dangling inputs, acyclicity,
terminal type/existence/reachability, and immutable-prefix revision rules.

## Prior generation and freeze contract

`control/prior.py` provides both `LLMPriorWorkflowGenerator` and
`StaticPriorWorkflowGenerator`. The LLM generator receives only:

- `AgentTaskView` (sanitized task);
- `StaticCapabilityContract` with operator schemas;
- the semantic workflow output schema.

It receives no infrastructure state. `PriorWorkflowStore` writes one fail-closed
`prior_workflows/<task-id>.json` record containing the plan, canonical plan hash, sanitized task
hash, public bundle hash, prior model, prompt hash, static-capability hash, generation timestamp,
and generator/schema version. An existing different record is never overwritten. Baseline and
adaptive runs therefore load and verify the same frozen G0 instead of independently calling the
prior model.

## Adaptation and KEEP baseline

`control/adaptation.py` defines `WorkflowAdaptationContext`, `KeepWorkflow`, `PatchWorkflow`, and
`WorkflowAdaptationPolicy`. `KeepWorkflowPolicy` implements the baseline exactly as
`A_base(G,H)=G`; it still executes through the same infrastructure-aware physical scheduler.

`LLMInfraAwareWorkflowAdapter` sees the sanitized task, current semantic plan, runtime partition,
sanitized observations, static capabilities, and anonymous `WorkflowPhysicalView`. Its prompt
treats G0 as semantically reasonable, requires KEEP absent a significant infrastructure
cost/feasibility issue, restricts changes to the finite patch schema, preserves evidence/semantics,
and prohibits physical identities or placement decisions.

## Workflow-level physical profile and cost

`control/workflow_profile.py` exposes anonymous per-pending-action ranges for feasible candidates,
input bytes, remote-input count, transfer latency, service latency, and queue pressure. It also
exposes predicted transfer bytes/latency, service and queue latency, critical path, total work, and
explicit unknown reasons. Physical exception details are reduced to stable abstract reason codes.

`control/workflow_cost.py` evaluates existing semantic actions without a legacy
`LogicalAgent.model_instance_id`. It reuses `PhysicalProfiler`, which enumerates capability-feasible
workers for tool actions and requirement-feasible deployments for model actions, then aggregates
measured transfer/service/queue ranges into workflow critical-path and total-work estimates.
Missing routes or profiles remain unknown rather than becoming zero.

## Adaptive executor state machine

`AdaptiveWorkflowExecutor` performs the following before every newly-ready frontier, including the
first:

1. obtain current infrastructure through the workflow profile provider;
2. construct anonymous `WorkflowPhysicalView`;
3. request KEEP or PATCH;
4. validate and apply a PATCH only to pending actions;
5. compute the ready frontier from artifact/control dependencies;
6. submit the whole frontier through the existing `ActionGateway`;
7. collect `LogicalObservation`s and update runtime/execution state.

There is no retry, rollback, hidden repair, or implicit serialization. Independent ready actions
are submitted together; dependency edits are the only way adaptation changes parallelism.
Terminal output is the successful terminal model action's inline `text`, with no hidden semantic
finalizer.

The mutable planned future and append-only actual execution are separate. Trace reconstruction uses:

- `workflow.plan.version`
- `workflow.plan.patch`
- `workflow.execution.snapshot`
- existing `physical.execution` events

## Formal runner

`AdaptiveWorkflowBenchmarkRunner` uses the existing worker-surface validation, artifact
materialization, `LiveWorkerObserver`, `PhysicalProfiler`, `PhysicalExecutionService`,
`RuntimeActionGateway`, `RuntimeExecutor`, and original private evaluator. It verifies or creates
the frozen prior before execution and persists the full adaptive execution result and JSONL trace.
The baseline is selected only by supplying `KeepWorkflowPolicy`; the substrate is otherwise
identical to the adaptive path.

## Deterministic tests and scripted smoke

Seventeen new deterministic tests cover the requested sixteen contract cases plus an end-to-end
runner integration:

- semantic workflow and static-capability validation;
- KEEP identity;
- add/replace/remove pending actions;
- add/remove dependencies;
- completed and running immutability;
- cycle, dangling input, terminal type, and terminal reachability rejection;
- one frozen G0 under different physical bindings;
- prior persistence/reuse and sanitized LLM prior input;
- anonymous semantic-workflow cost evaluation;
- version/patch/execution trace reconstruction and logical-view leakage checks;
- the original evaluator receiving the terminal answer through an actual ASGI Worker,
  `ActionGateway`, physical service, scheduler, and runtime.

Scripted Case A passed:

- fast profile: `large artifact -> model` remained G0 under KEEP;
- constrained profile: a bounded patch produced
  `large artifact -> BM25 reduction -> model`;
- both completed with the same terminal contract and no hidden execution repair.

Scripted Case B passed:

- G0 submitted three independent materialized model-analysis branches in one ready frontier before
  the terminal aggregation model;
- a dependency-only patch changed the three branches to three successive frontiers;
- the executor followed the explicit graph in both cases and never silently serialized the
  parallel version.

Validation results on 2026-09-30:

- full pytest: **251 passed**;
- Ruff: **all checks passed**;
- strict Pyright: **0 errors, 0 warnings**.

## Relationship to existing paths

The SDK-native Manager/subagents-as-tools runtime remains the open-ended logical-agent path. The
legacy workflow planner/replanner remains available for historical experiment reproduction. The new
formal path is parallel and workflow-centric: a frozen complete semantic prior is adapted only by
bounded pending-suffix patches, while all physical binding and execution remain owned by the same
existing physical substrate.

Phase 1 stops here. No formal benchmark or Aware experiment was started.
