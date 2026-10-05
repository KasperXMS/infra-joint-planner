# Resident cell 050: exact Blind-Verifier provider-policy audit

2026-10-06. Preserve this nominal failed outcome; do not retry, replace, censor
its input, tune prompts or impute a benchmark score. It is not a semantic wrong
answer, an operational outage or evidence of a physical runtime defect.

## Original terminal finding

Condition: MultiHop representative 1 / P1 / Slow / C, task
`multihop-rag-train-4b6de4acbde051fee1f727f3`.
Run: `large-scale-cost-guidance-resident-v1-phase1-multihop_rag-1-29e45040dce39dae-p1-slow-C-attempt1`.
P1=`deepseek-v4-pro`; independent fixed Blind Verifier=`qwen3.8-max`.
Same three hash-nonsemantic shards, initial placement, resident model pool,
32K/2048 contracts, finite operators, scheduler and frozen budgets.

Original journal sequence 100 settled **confounder** at
`2026-10-05T20:52:13.281096Z`, with the single gate
`unclassified_API_failure_requires_audit`. Original admission canonical SHA:
`48dabb39ed935e03cac68a2f5b7f01373c40555e678e89ad7782407a525f7081`.
The journal and original admission remain unchanged. Queue 005 and its atomic
process had actually exited before offline review; no pending reservation.

Terminal code `logical_loop_failed`, exception `AgentLoopError`. Actual raw SDK
HTTP receipts: thirteen Manager calls succeeded, four Verifier calls succeeded,
and the fifth Verifier call returned HTTP 400. Failed call ID
`55e5d446a8144ce18098db6635cd80bd-1`; provider code and type both exactly
`data_inspection_failed`, with the exact provider input-policy message expected
by the existing reviewer. Failed call usage is absent. No operational incident,
terminal answer or evaluator invocation is recorded; evaluation/format/quality
are **missing**, not zero or invalid-by-inference.

## Independent review and immutable classification

The unchanged single-gate reviewer independently reproduced the full original
admission, verified the frozen execution/source environment, actual recipient
privacy/method input checks, owning Worker exits and five-model residency, then
bound all 102 original evidence files. It classified exactly one provider
input-policy refusal, zero JSON parse failures and zero record-field failures.
No broad HTTP-400 allowlist or semantic/runtime repair was added.

Append-only sidecar under remote `provider-policy-adjudications/`, same run ID:
canonical SHA `f0105d6c39f2c242d890aa55171bd7c894512f9fafde13f3475c6b278ef84212`.
Effective classification: **valid nominal provider-input-policy failure**;
`replacement_authorized=false`, `formal_execution_changed=false`.
Keep the original confounder receipt as history, use only its verified exact
sidecar for the effective ledger view. This does not turn failure into completed
execution and does not establish what content triggered the provider's filter.

The first read-only reviewer invocation lacked the archived deployment's
required `INFRA_JOINT_CODE_REVISION` and stopped before creating a sidecar.
`review-console-050-001.log` is preserved. The second invocation explicitly used
the revision already bound by `execution-freeze-001.json`, not the newer local
documentation revision; `review-console-050-002.log` records successful review.
This was an offline-command correction, not a measured attempt replacement.

## What actually executed before the refusal

| Measurement | Observed receipt scope |
| --- | --- |
| Manager / Verifier calls | 13 / 5, including the refused Verifier call |
| Specialists created / specialist turns | 0 / 0 |
| Physical actions | 11, all succeeded |
| Tool executions / actual physical inference | 6 BM25 / 5 |
| Submitted physical context rejects | 0 |
| Model input / output tokens | 30,022 / 1,629 across five returned inferences |
| Model finish reasons | five `stop` |
| E2E until explicit run.failed | 505.204 s |
| Fixed initial placement | 7,696,522 bytes / 22.040 s |
| Complete action movement | 0 bytes / 0 s |
| Complete tool-only work | 3.078 s |
| Complete physical backend work | 560.983 s |
| Manager / measured Verifier work | 95.837 / 11.524 s |
| Cloud API known subtotal | USD 0.1502642674, seventeen known calls |
| Complete cloud API cost | unknown; one refused call has unknown usage |
| Quotes / consumed / discarded / stale | 12 / 11 / 1 / 0 |
| Quote-control work | 7.591 s |
| Graph nodes / declared artifact edges / snapshots | 11 / 4 / 34 |
| Actual maximum action concurrency / overlapping wall time | 6 / 194.983 s |

Six shard-local BM25 executions ran on A4/A5/A28. The five successful model
actions used A4 VL4B twice, A5 VL8B, A28 27B and strong GPU0 27B: four actual
resident instances, not all five pool instances. Independent actions of one
logical owner overlapped; no specialist is implied. Actual maximum action
concurrency six must not be renamed six concurrent model inferences or six
agents. All nodes succeeded physically, but the control plane failed later.

Complete backend work exceeds E2E because intervals overlap. Inclusive Worker
operator work already includes model actions and cannot be added to backend
work. Failed Verifier timing/cost must not be imputed from successful calls.
Initial placement is fixed setup, separate from Agent-controlled movement.
Quotes rejected by phase restrictions and discarded proposals are not extra
physical calls; quote-induced causal revision rate remains unknown. A provider
refusal following successful reasoning/model execution cannot be recast as
evidence-loss, stopping failure, budget exhaustion or a wrong benchmark answer.

## Control-only continuation

Before the new control freeze: full pytest passed (1077 collected tests), Ruff
passed, strict Pyright reported zero errors/warnings, and `git diff --check`
passed. No source, Manager, Verifier, budget, tool, evaluator or routing change.

New `queue-control-freeze-005.json` canonical SHA:
`58fc2a4e578129ea4fa4a2bca50a2da2855f79b39146bc721c08238012565bac`;
file SHA `e526c180a93e967bfbfd1c75bbf4e5d0d88ff8984b1fe0d49f8fefd02a0082a6`.
It binds the new sidecar and unchanged exact reviewers/ledger/controller.
Frozen measured execution remains revision
`90fd30c531f3ad879dcaf5394b7633bcf7b07c3b`, canonical freeze
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.

Queue 006 PID `2356386` started `2026-10-05T21:00:33.268372Z`, actual cmdline
verified again at `21:01:59Z`. Only never-started remaining scheduled cells may
run. Cell 050 is never retried; all five original rejected admissions and
verified classification sidecars remain immutable. Re-read actual process state
before inferring current liveness from these historical receipts.

The effective new nominal boundary is fifty, including classified failed
provider outcomes, not fifty successful completions. Old 42 remain closed,
unpooled and separately counted toward the global cap. Full 168-cell execution
and comprehensive private semantic/recipient/failure/adoption audit are still
required before pruning, preregistered Phase II and all final reports/Q1–Q10.
This audit is not a winner claim or full-goal completion.
