# Workflow-Centric Formal Preliminary 2x2 v1: Stopped at Prior Freeze

## Outcome

The 2x2 execution matrix was **not started**. The single permitted resource-blind prior call
returned a syntactically valid `SemanticWorkflowPlan` whose `version` was not zero. The frozen
formal path rejected it with:

```text
ValueError: prior workflow G0 must have version zero
```

This occurred inside `LLMPriorWorkflowGenerator.generate()` after its one backend invocation and
before `prepare_prior_workflow()` could create a `FrozenPriorWorkflow`. In accordance with the
frozen protocol, the run stopped without retrying, changing the prompt, normalizing the model
output, hand-editing a plan, selecting a replacement task, or executing any experimental cell.

## Frozen intended setting

- Code revision used remotely: `bf829231a268fd9ea47e897396f7b7e0918b6a88`
- Task: `multihop-multisource`
- Source task: `multihop-rag-train-9bae0079038050a37a1ae583`
- Representation: the previously validated complete 609-document corpus split losslessly into
  three content-hash shards; the shards jointly form the complete corpus.
- Initial placement: one shard each on `A4`, `A5`, and `A28`.
- Prior generator: `LLMPriorWorkflowGenerator`
- Prior model: `deepseek-chat`
- Prior visibility: sanitized task plus static capability contract; no infrastructure state or
  private evaluator data.
- Fast: 100 Mbps plus 5 ms added RTT.
- Slow: 3 Mbps plus 50 ms added RTT.
- Methods: `KeepWorkflowPolicy` and `LLMInfraAwareWorkflowAdapter`.
- Formal runner setting: `require_frozen_prior=True`.
- Retry/replacement/repetition: disabled / disabled / one intended primary run per cell.

The task was chosen because its distributed corpus has a clear raw-shard movement versus local
retrieval/reduction trade-off and requires no video decoding.

## Prior-freeze audit

| Check | Result |
|---|---|
| Planner backend calls | 1 |
| Returned object parsed as `SemanticWorkflowPlan` | yes |
| `plan.version == 0` | no |
| Static feasibility reached | no; version invariant rejected first |
| Frozen-prior file written | no |
| Prior plan SHA-256 available | no |
| Worker processes/stores created for cells | no |
| Artifacts materialized | no |
| Network shaping applied | no |
| Experimental cells executed | 0 |

The first attempted preparation command initially stopped before any API call because a
non-interactive SSH shell did not inherit `DEEPSEEK_API_KEY`. The harness was then changed only to
reuse the repository's existing API-key-file loader. The one backend call described above happened
after that environment-only correction. No evidence directory or partial frozen prior was left by
either preparation attempt.

The failed backend completion was held only in process memory by the capturing wrapper and the
exception occurred before preparation evidence was persisted. Consequently, the durable audit can
prove the fail-closed control path and one-call execution from the exception location, but it does
not contain the raw rejected completion or its exact nonzero version value. This is an evidence
limitation and no value is reconstructed or guessed.

## Four-cell table

| Network | Method | Frozen G0 | Decision | Completion | Quality | E2E | Bytes | Status |
|---|---|---|---|---|---|---|---|---|
| Fast | KEEP baseline | unavailable | unavailable | not run | unavailable | unavailable | unavailable | stopped before matrix |
| Fast | Infra-aware | unavailable | unavailable | not run | unavailable | unavailable | unavailable | stopped before matrix |
| Slow | KEEP baseline | unavailable | unavailable | not run | unavailable | unavailable | unavailable | stopped before matrix |
| Slow | Infra-aware | unavailable | unavailable | not run | unavailable | unavailable | unavailable | stopped before matrix |

## Adapter, patch, and cost evidence

There were no adapter decisions, patch edits, workflow versions, predicted costs, physical
selections, transfers, model-service calls on Workers, benchmark outputs, or evaluator results.
Unknown values remain unknown; no profile or execution value is imputed.

## Conclusion

This attempt does **not** answer whether infrastructure state rationally triggers a workflow
structure change. It provides neither a KEEP/PATCH reversal nor a cost/quality comparison. The
failure is a prior-generation output-contract failure before the infrastructure experiment, not
evidence for or against the proposed adaptation mechanism.

The experiment must not expand to another task or a bandwidth sweep. Any follow-up should be a
separately reviewed experiment revision that explicitly authorizes a new prior call and first
decides how failed-prior evidence is persisted. The current no-retry attempt is closed.
