# Workflow-Centric Formal Path: Experiment-Readiness Audit

## Scope and outcome

This change hardens the existing workflow-centric formal path without changing its architecture:

\[
G_0=\pi_0(\tau,C),\qquad
G_{t+1}=\mathcal A(G_t,\phi(H_t)),\qquad
X_t=\Omega(G_t,H_t).
\]

The physical substrate and its behavior remain unchanged: `ActionGateway`,
`PhysicalExecutionService`, `RuntimeExecutor`, worker APIs, benchmark adapters/evaluators,
the SDK-native open-ended runtime, the legacy workflow/replanning path, and
`AutoPhysicalScheduler` were not modified. No Video-MME, LongBench, MultiHop, Blind-vs-Aware,
network sweep, or prompt-tuning experiment was run.

## Static feasibility of G0

`control/static_feasibility.py` now performs a topological, fail-closed analysis whenever
`validate_semantic_workflow()` validates G0 or a revised workflow. It initializes artifact
envelopes from the public `TaskContract`, migrates the existing generic structured-data checks,
and propagates media type, semantic schema, and a conservative size upper bound through the DAG.

For every `LogicalModelAction`, validation considers the complete declared input envelope:

- UTF-8 prompt bytes as the conservative prompt-token bound used by runtime preflight;
- text/JSON artifact byte upper bounds;
- the static model class's image-token cost for each image input;
- the model class's full reserved-output budget.

At least one anonymous `StaticModelCapabilityClass` must satisfy both the action requirements and
the resulting context envelope. Unknown text/JSON input bounds and oversized direct inputs are
rejected before execution; they are not truncated or silently accepted. Blind and Aware use this
same static analyzer.

## Future artifact envelope propagation

The analyzer has explicit propagation rules for `bm25_retrieve`, `filter_records`,
`select_fields`, `derive_fields`, `aggregate_records`, `top_k_records`,
`aggregate_artifacts`, `sample_frames`, `extract_clip`, `make_contact_sheet`, and
`invoke_model`.

Known bounds are carried forward conservatively. For example, BM25 uses `top_k`, record-count,
and maximum-record-size metadata, contact sheets use the declared grid dimensions, and model
outputs use the feasible static model classes' reserved-output envelopes. When a trustworthy
bound cannot be derived (for example, an encoded sampled-frame size), the envelope contains an
explicit unknown reason rather than zero.

The workflow cost evaluator combines this static envelope with current materialized artifacts and
simulates the same ready frontiers used by `AdaptiveWorkflowExecutor`. Every action in a frontier
is enumerated and selected against one frozen pre-frontier projected infrastructure snapshot. Only
after the whole frontier is evaluated are updates batch-applied. A sibling action therefore cannot
consume an output or input replica that another sibling has not yet finished producing.

At each frontier boundary, predicted successful actions add their selected worker as a replica for
every localized input, while each future output is placed only at its selected execution worker. A
pending `raw -> reduce -> model` chain therefore gives the model node the reduction's predicted
size and location, and later reuse of a previously localized `raw` artifact does not charge the
same transfer again. If size, location, route, or service profile is unknown, the corresponding
field and aggregate remain `None` with a stable reason code; the profile does not manufacture
`0 bytes`, `(0, 0)` remote inputs, or `local`.

## Candidate-correlated workflow cost

`control/workflow_cost.py` now enumerates real feasible tool workers or model deployments and
keeps each candidate's complete tuple together:

- transfer bytes and latency;
- service latency;
- queue pressure and queue latency;
- total predicted latency.

The evaluator invokes the same `AutoPhysicalScheduler.select()` implementation used by physical
execution against each frozen pre-frontier state. It also models `RuntimeExecutor` localization's
deterministic source choice when estimating transfer latency. Aggregate transfer, service, queue,
total-work, and critical-path predictions use only the selected binding for each action. Anonymous
min/max ranges remain available to the adapter, but they are not combined component-wise into an
unattainable synthetic minimum.

An internal diagnostic result records the predicted selected worker/deployment and component
costs for tests and audit; physical identities are not included in `WorkflowPhysicalView` seen by
the logical adapter. Regression coverage constructs A/B/C candidates whose transfer and service
minima belong to different candidates and verifies both that no fictitious low aggregate is
created and that the predicted binding equals the actual scheduler selection.

## Frontier concurrency and critical path

Selected actions are grouped by physical worker within each ready frontier. Singleton groups use
the ordinary measured `ExecutionCostProfile`. A worker-level group with concurrency greater than
one requires a matching `ConcurrentServiceProfile` for every selected action. The profile records
operator, optional deployment scope, concurrency, adjusted per-action service latency, and
calibration source.

No unmeasured contention assumption is permitted. If any concurrent action lacks a matching
profile, its contention-adjusted service, queue, total-work contribution, and the aggregate
critical path remain unknown. The logical view receives
`concurrent_service_profile_unavailable`; it does not receive worker/deployment identities.
Selected identities and concurrency groups remain only in internal audit diagnostics.

When all selected binding components are known, critical path follows the pending DAG:

\[
finish(v)=\max_{u\in pred(v)}finish(u)+cost(v).
\]

Independent actions in one frontier therefore overlap, while an explicit dependency revision
turns the corresponding costs into a serial path. Same-worker actions use their calibrated
contention-adjusted service times in this calculation. Unknown transfer, service, queue, or
concurrency data makes the critical path `None` instead of contributing a silent zero.

## Frozen-prior provenance and formal mode

Prior metadata now comes from the generator that made the call. Both static and LLM generators
return `PriorGenerationResult(plan, provenance)`. LLM provenance hashes the exact rendered prompt
submitted to its backend and records generator ID/version and model ID; static generation records
an explicit deterministic static provenance.

On load, the frozen prior fails closed on:

- frozen-record schema version (enforced by the literal schema during parsing);
- generator ID and generator version;
- prior model ID;
- exact prompt SHA-256;
- static capability SHA-256;
- sanitized task SHA-256 and public bundle SHA-256;
- embedded plan SHA-256 and the G0 version invariant.

`AdaptiveWorkflowBenchmarkRunner` now defaults to `require_frozen_prior=True`. A missing prior or
any provenance mismatch fails before artifact materialization or workflow execution. Development
mode remains available only by explicitly passing `require_frozen_prior=False`.
`prepare_prior_workflow()` is the recommended preparation entry point: it generates, validates,
and freezes G0 without executing the benchmark. The runner no longer accepts manually supplied
`prior_model` or `prior_prompt` metadata.

## Adaptation overhead

Every adaptation decision now produces `WorkflowAdaptationTelemetry` containing:

- wall-clock adaptation latency;
- backend/model service latency when applicable;
- input and output tokens when reported by the backend;
- KEEP/PATCH decision type;
- patch edit count.

The executor stores the ordered telemetry records in the persisted execution result and emits a
`workflow.adaptation` JSONL event for each decision. `KeepWorkflowPolicy` records its deterministic
near-zero policy overhead without pretending that a model call occurred.

## Terminal output contract

Terminal model output remains the final answer; there is no hidden semantic finalizer. After a
non-empty terminal answer is produced, generic validation separately checks:

- `CHOICE`: exact membership in the declared choices;
- `JSON`/`STRUCTURED`: JSON parsing and Draft 2020-12 schema validation;
- `SHORT_TEXT`: the existing non-empty text rule.

The persisted result distinguishes `execution.completed`,
`terminal_output_contract_valid`, and the original benchmark evaluator result. A non-empty but
malformed answer is therefore a format/quality result, not a physical or workflow execution
failure.

## `owner_agent_id` semantics

In the workflow-centric formal path, `owner_agent_id` is only a logical role, provenance, and
grouping annotation. It does not imply independent conversational memory, a separate reasoning
state, or MAS communication semantics. Those properties remain part of the SDK-native agent path,
not this formal workflow contract.

## Deterministic validation

The added and updated tests cover:

1. rejection of an oversized direct model input during plan validation;
2. static feasibility after a generic BM25 reduction;
3. derived artifact size propagation through the DAG;
4. non-zero/non-local prediction for an unmaterialized derived artifact;
5. candidate-correlated A/B/C costing without synthetic minima;
6. cost-evaluator and `AutoPhysicalScheduler` binding agreement;
7. frozen prior model/prompt mismatch rejection;
8. formal-mode rejection when no frozen prior exists;
9. complete LLM adaptation telemetry and trace persistence;
10. separate recording of invalid choice and JSON terminal outputs;
11. the existing constrained-network scripted PATCH/reduction smoke;
12. the existing fast-network scripted KEEP smoke;
13. same-frontier snapshot isolation for two model actions sharing one input;
14. input-localization replica propagation into a later frontier;
15. future output placement propagation into its downstream consumer;
16. selected binding agreement with scheduler calls on the matching projected snapshots;
17. same-worker concurrency detection and measured concurrency adjustment;
18. fail-unknown behavior when the concurrent service profile is absent;
19. different-worker parallel critical-path prediction;
20. parallel-to-serial critical-path change after adding a dependency;
21. default frozen-prior enforcement and explicit development opt-out;
22. the complete regression suite.

The scripted constrained case still patches `large artifact -> model` into
`large artifact -> BM25 reduction -> model` and completes. The fast case keeps G0 unchanged and
completes. These are deterministic synthetic/integration smokes only.

Validation results on 2026-09-30:

- full pytest: **263 passed**;
- Ruff: **all checks passed**;
- strict Pyright: **0 errors, 0 warnings**;
- `git diff --check`: **passed**.

The formal path is now ready for experiment-design review. This work stops before any formal
benchmark or Aware experiment.
