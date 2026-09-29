# Clean Blind baseline and action-budget diagnostic v1

## Scope and verdict

This run used the frozen SDK-native persistent Manager + bounded specialists control plane in
resource-blind mode. No Aware run was started, and no prompt, specialist instruction, benchmark
adapter, operator semantic, retrieval heuristic, model-requirement generation rule, or recovery
rule was changed.

The three requested questions have clear answers:

1. **Fresh stores removed the MultiHop harness confounder.** All three MultiHop cells ran without
   the historical `barb-poly-2` metadata collision or any other cross-run artifact collision. They
   are valid semantic/control-flow failures, although none reached terminal completion.
2. **More budget did not make Video or LongBench complete.** Video expanded from 2 to 7 to 8 real
   model inferences and became slower. LongBench first reached inference only at budget 32, after
   21 action positions from its first context failure, but still failed to stop and finalize.
3. **No observed failed model action required dynamic infrastructure information.** Video made 17
   model requests; all 17 were statically feasible, physically selected, and reached inference.
   Across LongBench and MultiHop, all seven model preflight failures were
   `context_limit_exceeded`; none was deployment unavailability or another dynamic feasibility
   failure.

The dominant current limitation is workflow composition plus stopping/over-expansion, not hidden
dynamic deployment availability. This evidence does not justify starting a formal Blind-vs-Aware
experiment yet.

## Frozen setting

- Tasks: Video-MME `848-1`, the frozen LongBench-v2 multi-document case, and the frozen
  MultiHop-RAG multi-source case.
- Network: native/unshaped.
- Scheduler: existing B0 locality-aware scheduler.
- Logical runtime: OpenAI Agents SDK native tools with bounded specialists-as-tools.
- Manager: `deepseek-chat`; instructions are unchanged.
- Physical model pool: the existing Qwen3.8 27B text+image deployments on A28 and the dual-4090
  host.
- Action budgets: 18, 24, and 32.
- Manager-turn rule: `ceil(2/3 * action budget)`, producing 12, 16, and 22 turns.
- Other bounds unchanged: 8 specialist turns, 4 created specialists, 2 active specialists.
- Repetitions: one; no retry and no replacement.
- Generic operator set unchanged: `aggregate_artifacts`, `aggregate_records`, `bm25_retrieve`,
  `derive_fields`, `extract_clip`, `filter_records`, `invoke_model`, `make_contact_sheet`,
  `read_artifact`, `sample_frames`, `select_fields`, and `top_k_records`.

Before the matrix, four new Worker processes were started on isolated ports with new artifact roots.
All four `/state` responses reported an empty artifact list. Existing Worker processes and historical
evidence were left intact. The runner also performs a fail-closed empty-store assertion before the
first cell. Derived artifacts retain per-run UUID namespaces, so later cells cannot collide with
earlier derived metadata.

The static capability contract visible to both future Blind and Aware modes contains:

- the finite operator vocabulary with input, argument, and output schemas;
- abstract supported modalities and capabilities;
- an anonymous model class with text+image support, a 16,384-token context envelope, and a
  1,024-token reserved-output envelope;
- task-visible artifact semantic/schema metadata.

It contains no worker/device/deployment identity, placement, network state, route, load/queue,
measured latency, or current availability. Blind receives no `PhysicalProfileView`.

## Nine-run diagnostic

`Model ms` is the sum across model calls and can exceed E2E when model calls overlap. Transfer bytes
use decimal MB below. A dash for score/format means that no terminal answer reached the evaluator.

| Task | Budget / Manager cap | Manager / specialist turns | Successful tool / model | Failed semantic / preflight | Actual inference | Specialists | E2E s | Transfer MB / ms | Model s | Result | Primary cause |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Video 848-1 | 18 / 12 | 12 / 3 | 15 / 2 | 0 / 0 | 2 | 1 | 612.0 | 160.95 / 7,678 | 438.7 | no terminal answer | stopping / over-expansion |
| LongBench multi-doc | 18 / 12 | 7 / 8 | 15 / 0 | 0 / 2 | 0 | 1 | 28.3 | 1.16 / 354 | 0.0 | no terminal answer | workflow composition |
| MultiHop multi-source | 18 / 12 | 10 / 0 | 17 / 0 | 0 / 0 | 0 | 0 | 19.9 | 7.90 / 897 | 0.0 | no terminal answer | workflow composition |
| Video 848-1 | 24 / 16 | 16 / 4 | 17 / 7 | 1 / 0 | 7 | 1 | 1,119.2 | 161.47 / 8,024 | 1,236.5 | no terminal answer | stopping / over-expansion |
| LongBench multi-doc | 24 / 16 | 13 / 8 | 20 / 0 | 0 / 2 | 0 | 2 | 41.3 | 1.27 / 668 | 0.0 | no terminal answer | workflow composition |
| MultiHop multi-source | 24 / 16 | 13 / 0 | 24 / 0 | 0 / 0 | 0 | 0 | 25.7 | 7.90 / 732 | 0.0 | no terminal answer | workflow composition |
| Video 848-1 | 32 / 22 | 22 / 8 | 24 / 8 | 0 / 0 | 8 | 2 | 1,828.5 | 161.81 / 8,031 | 2,111.0 | no terminal answer | stopping / over-expansion |
| LongBench multi-doc | 32 / 22 | 18 / 7 | 29 / 1 | 1 / 2 | 1 | 2 | 391.4 | 1.27 / 564 | 340.6 | no terminal answer | stopping after trial-and-error reduction |
| MultiHop multi-source | 32 / 22 | 14 / 0 | 31 / 0 | 0 / 1 | 0 | 0 | 39.9 | 7.87 / 1,143 | 0.0 | no terminal answer | workflow composition |

All nine runs ended with the typed `logical_loop_failed` result. The immediate limit was either the
tool/model-call budget or the uniformly scaled Manager-turn budget. No benchmark score was produced,
so this diagnostic provides no quality comparison.

## Video model-binding audit

Every Video `invoke_model` request is individually recorded as
`logical.model.requirements -> physical.execution -> logical.model.outcome`.

| Budget | Request groups | Static class match | Physical selection | Reached inference | Failed binding/preflight |
|---:|---|---:|---:|---:|---:|
| 18 | 2 × text+image, min context 1, reserve 1, no quality class | 2/2 | 2/2 | 2/2 | 0 |
| 24 | 7 × text+image, min context 1, reserve 1, no quality class | 7/7 | 7/7 | 7/7 | 0 |
| 32 | 2 × (1/1) and 6 × (16,000/1,024), text+image, no quality class | 8/8 | 8/8 | 8/8 | 0 |

All 17 actions selected the existing A28 Qwen deployment because the B0 scheduler preferred the
location of the generated visual artifacts. There was no repeated infeasible requirement in these
clean Video runs: static-impossible = 0, dynamic-unavailable = 0, and preflight failure = 0.

The failure instead worsened with budget. At 32 calls, the workflow created an OCR specialist and
submitted three simultaneous visual calls to A28. Nominal parallelism became same-device contention;
the workflow still expanded until the call budget was exhausted. This is a stopping/resource-use
failure, but it is not evidence that the logical layer needed dynamic availability to make a legal
model request.

## LongBench context and reduction behavior

- Budget 18: context failed at action ordinals 11 and 12; no inference followed. The remaining
  actions were three BM25 reductions and three reads before stop.
- Budget 24: context first failed at ordinal 6 and again at 16. Between those points the workflow
  performed field selection, four-way BM25 retrieval, and aggregation, then continued with more
  retrieval/reads. It never reached inference.
- Budget 32: context first failed at ordinal 6 and again at 21. The first successful inference was
  ordinal 27—**21 action positions after the first context failure**. The final viable path used
  further BM25 reduction and aggregation. The inference completed, but the Manager continued and
  exhausted the action budget instead of returning the model result.

The abstract 16,384/1,024 envelope was visible. The failed calls declared a statically supported
class but supplied artifact/prompt content that exceeded the concrete context preflight. These are
static capability/workflow-composition misuses, not current deployment unavailability. Budget 32
shows sensitivity at an intermediate milestone (inference becomes reachable), but not at the
required terminal-completion outcome.

## MultiHop clean-store behavior

The three clean runs had no artifact collision, missing artifact, transfer defect, or metadata
conflict. Each run performed 12 BM25 calls across the corpus shards:

- Budget 18: 12 retrieval, 4 aggregation, 1 read, 1 field-selection action.
- Budget 24: 12 retrieval, 8 filtering, 2 aggregation, 1 read, 1 field-selection action.
- Budget 32: 12 retrieval, 7 filtering, 4 aggregation, 4 reads, 4 field-selection actions, followed
  by one `invoke_model` attempt that failed artifact-aware context preflight.

Thus the historical system confounder is removed, and MultiHop now supplies a valid baseline failure
trace. The remaining failure is failure to transition from broad shard retrieval/reduction into a
bounded reasoning input and terminal answer. Raising the budget increases filtering/aggregation but
does not produce semantic reasoning.

## Failure taxonomy

| Category | Evidence in this diagnostic |
|---|---|
| Semantic reasoning failure | Not established: no run produced an evaluated terminal answer. |
| Workflow composition failure | Primary for LongBench 18/24 and all MultiHop cells; reduction/retrieval does not reliably form a bounded reasoning input. |
| Stopping / over-expansion failure | Primary for all Video cells and LongBench 32; completed model results are followed by more expansion. |
| Static capability misuse | Seven artifact-aware `context_limit_exceeded` preflights: six LongBench and one MultiHop. The abstract model class existed, but the actual input did not fit. |
| Dynamic physical feasibility failure | Zero. No `deployment_unavailable`, dynamic binding failure, or equivalent signal occurred. |
| Hard budget exhaustion | Present in all nine runs as the terminal typed failure; it is generally downstream of composition/stopping behavior. |
| System/harness confounder | No run-level confounder after fresh-store isolation. One campaign-level progress-serialization bug occurred after Video@18 had fully persisted; the matrix stopped, the result/trace were preserved, and a hash-recorded evidence-only amendment resumed at LongBench@18 without retrying the completed cell. |

## Evidence integrity and implementation audit

Remote evidence root:

`/home/super/xiaoming/resource_blind_live_validation_v1/evidence-blind-budget-diagnostic-v1`

It contains nine `result.json` files, nine full `trace.jsonl` files, the freeze manifest, a harness
amendment, `summary.json`, `analysis.json`, and `checksums.sha256`. The analysis contains no prompts
or evidence text. An actual-trace scan found zero physical/private identity hits in every run's
`logical.*` events. Raw datasets and traces were not routed through the local development machine.

Validation after the generic cleanup:

- pytest: 234 passed;
- Ruff: passed;
- strict Pyright with the remote project interpreter: 0 errors, 0 warnings;
- live dataset-free SDK adapter smoke: passed.

## Recommendation for the next experiment

Do not interpret the current failures as evidence for an Aware advantage. Dynamic infrastructure
information would not have prevented any of the seven observed model preflight failures, and Video's
17 requests were already physically feasible.

Before a formal Blind-vs-Aware comparison, freeze this diagnostic and decide whether the baseline is
competent enough for the intended claim. The narrowest justified follow-up is a generic,
resource-blind stopping/feasibility policy evaluation—not prompt tuning and not an Aware sweep:

1. require model requirements to account for the known context envelope and selected artifact sizes
   before submission;
2. define an explicit generic condition for returning a successful terminal model result instead of
   continuing evidence expansion;
3. validate those changes on separate development tasks, then refreeze before any comparison.

Those are method/baseline-design decisions, so they were not implemented in this stage.
