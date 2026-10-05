# Resident-block checkpoint029

This is an incomplete, per-cell checkpoint, not the168-cell analysis, quality
aggregation or method-pruning decision. The historical42 samples remain closed
and unpooled, but count toward the420-substantive-cell cap. The requested PhaseII
and final Q1–Q10 characterization are not complete.

## Evidence and scope

Snapshot012, captured2026-10-05T19:12:16.736144Z, records29/168 effective admissions,
0pending and0unresolved confounders. Admission means a verified nominal outcome,
not necessarily successful completion: cell29 is an unevaluated provider refusal.
Three original rejection receipts remain immutable, with separate reproducible
reviews for model JSON parsing, absent-record-field misuse and provider policy.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Snapshot: `analysis/resident-snapshot-012.json`, file SHA:
`3ea87473c43b495417c4c3ff24a3d8d176f44f4d352f326fb83b7e7e0c0b5ce8`.
Measured execution canonical SHA remains
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.
No measured app, semantic instruction, budget, operator, scheduler, model or
dataset/evaluator changed. Worker processes/stores are fresh per cell; five
resident model instances remain attested before/after each completed attempt.
All dataset/model payload movement stays on4090/edges, never the development PC.

The table uses **frozen schedule ordinals**, not ad-hoc progress labels. Cell21
is Video representative2/P1/Fast/E; transient progress labels that omitted this
cell were shifted for later Video cells. Persisted condition IDs, journal,
schedule and evidence are unchanged. P1 is `deepseek-v4-pro`, P2 `qwen3.8-max`;
the independent Blind Verifier remains fixed `qwen3.8-max`.

## New per-cell receipts since checkpoint018

M/S/V means Manager/specialist/Verifier reasoning starts. Requests/infer/context
counts refer to physical model actions, not cloud reasoning. Work times below are
seconds. All successful rows have canonical terminal validity and original
evaluator invocation; their individual scores are shown without pooling.

| Cell/task | Planner/network/method | Completed /score | M/S/V | Physical actions | Model requests/infer/context | E2E s | Initial bytes/work s | Complete action bytes/work s | Tool-only work s | Backend model work s | API estimated USD |
| --- | --- | --- | --- | ---: | --- | ---: | --- | --- | ---: | ---: | ---: |
| 19/MultiHop2 | P1/Slow/B | yes/1.0 | 8/0/8 | 12 | 3/1/2 | 227.994 | 7,696,522/22.221 | 18,072/0.708 | 3.547 | 123.291 | 0.1471989038 |
| 20/MultiHop2 | P2/Fast/C | yes/1.0 | 6/0/3 | 3 | 1/1/0 | 164.266 | 7,696,522/1.046 | 5,204,596/0.998 | 1.247 | 138.590 | 0.0589978089 |
| 21/Video2 | P1/Fast/E | yes/1.0 | 4/0/4 | 2 | 1/1/0 | 73.625 | 7,037,220/0.658 | 0/0 | 1.630 | 31.453 | 0.0913511766 |
| 22/Video2 | P2/Slow/B0 | yes/1.0 | 6/0/6 | 3 | 2/1/1 | 116.952 | 7,037,220/19.710 | 0/0 | 1.322 | 37.891 | 0.1433269283 |
| 23/Video2 | P1/Slow/B1 | yes/1.0 | 4/0/4 | 2 | 1/1/0 | 100.371 | 7,037,220/19.705 | 0/0 | 1.631 | 37.687 | 0.0782216599 |
| 24/Video2 | P2/Fast/A | yes/1.0 | 6/0/6 | 4 | 3/2/1 | 73.925 | 7,037,220/0.651 | 0/0 | 1.637 | 26.065 | 0.1423443176 |
| 25/LongBench1 | P1/Fast/B0 | yes/1.0 | 10/12/10 | 39 | 3/1/2 | 174.139 | 514,789/0.116 | 0/0 | 1.417 | 0.487 | 0.6823166492 |
| 26/LongBench1 | P2/Slow/B1 | yes/1.0 | 7/0/7 | 8 | 2/1/1 | 68.886 | 514,789/1.561 | 9,428/0.292 | 0.773 | 13.994 | 0.1006451109 |
| 27/LongBench1 | P1/Slow/A | yes/1.0 | 9/0/9 | 17 | 3/1/2 | 127.160 | 514,789/1.634 | unknown/unknown | unknown | 19.196 | 0.1573889409 |
| 28/LongBench1 | P2/Fast/B | yes/1.0 | 8/0/8 | 6 | 3/1/2 | 66.223 | 514,789/0.499 | 217,558/0.071 | 0.188 | 12.037 | 0.1044645850 |
| 29/MultiHop1 | P1/Fast/B1 | no/unevaluated | 4/0/3 | 12 | 0/0/0 | 41.213 | 7,696,522/1.453 | 0/0 | 3.473 | 0 | unknown |

Representative IDs: MultiHop1 `4b6de4acbde051fee1f727f3`, MultiHop2
`fe71f374676e35359d12c83e`; LongBench1 `66f2c44e821e116aacb2b826`;
Video2 `131-3`. Full condition IDs, hashes and physical selections are preserved
in the snapshot and original evidence. All rows are n=1, without retry,
replacement, prompt tuning or trajectory repair.

Cell27 has two `artifact_too_large` failures with unmeasured failed execution
scope. Its original successful-transfer subtotal is12,667bytes/0.494s and
successful tool work1.676s; complete totals stay unknown, not those subtotals.
The E2E for cell29 comes from its exact `run.failed` event, since the failure
result has no normal telemetry/loop summary. Its graph contains12actions and
6edges, with6observed simultaneous actions, before the cloud refusal.

Latency scopes remain those documented in checkpoint018: raw Worker operator
latency includes model-action execution; backend service work is nested, not an
extra E2E term. Initial setup is separate from Agent-controlled artifact movement.
Transfer0 is zero measured artifact transfer, not zero RPC/API/context traffic.
API USD uses frozen regional list prices, not invoices. No cold-start subtraction
or estimated E2E was injected online.

## Mechanism observations, not causal conclusions

- Cell19/B and cell28/B have0optional-query attempts,0valid cards, and6observed
  eligible ready-action decisions each. Their actual root HTTP contexts included
  the optional interface; availability does not establish adoption.
- Cell20/C has3quotes,3authorized/consumed commits,0discarded/stale quotes and
  0.310s measured quote control work. Its quote-induced semantic revision rate
  remains unknown. This successful cell is not sufficient to claim C wins.
- Cell21/E saw frozen rules in4root inputs. Internal rule use is not observable.
- Cell25/B0 naturally created two specialists with12combined reasoning turns.
  Its graph has39nodes/38edges, max6concurrent actions and27cross-owner overlapping
  action pairs. This is real concurrency, not proof of lower E2E or sufficient
  evidence retention. It incurred considerably more cloud work than physical
  inference work in this single trajectory; matched full-block analysis is pending.

No mid-block pruning, cross-benchmark score pooling, causal Fast/Slow adaptation
claim or quality-conditioned method winner is inferred from these unmatched rows.
The full private semantic/evidence audit remains pending the inactive168-cell block.

## Exact cell29 provider refusal audit

Original run ID:
`large-scale-cost-guidance-resident-v1-phase1-multihop_rag-1-29e45040dce39dae-p1-fast-B1-attempt1`.
Original admission canonical SHA:
`0c1f3a8c2e4d60fc91572b7690b90caf17b8d4e93722e89b69d2bd5c75ca68c7`.
The fourth root Manager request, after three successful root calls and three
successful Blind Verifier calls, returned HTTP400 with exact provider error
code/type `data_inspection_failed` and input-policy message. The actual SDK
`BadRequestError` matches the terminal trace and original result. All7effective
SDK recipient contexts were independently checked; privacy/method gates found
no additional problem, all5models remained resident, and all4owned Workers exited.

The rejection's triggering content is **not identified** by this evidence. No
claim of an outage, bill exhaustion, dataset corruption, Planner semantic error
or particular offending keyword is made. This is a nominal **provider input-policy
failure**, not a correct/incorrect answer. The terminal answer and evaluation
remain absent. Failed-call token usage and complete API USD remain unknown;
6known call receipts subtotal USD0.2193035584, not a complete billed total.

The separate exact sidecar binds58original evidence files and reproduces the raw
HTTP proof; canonical SHA:
`ecd26e7453bcccc659d88812cc50eea47c18fa4aa456bea867d89cc060e5ad68`.
Path: `resident-provider-policy-adjudications/<run-id>.json`.
It preserves the original two-gate rejection (`terminal_failure_requires_system_audit`
plus `unclassified_API_failure_requires_audit`) while classifying the duplicate
gate as one refusal. It does not sanitize/censor inputs, change prompts, waive
other findings, authorize replacement or contact any model again.

Offline review commits `11d46cd` and `edb5c01` add this exact classification and
its tests. The first review console reused a generic parse-proof count label;
the follow-up explicitly separates provider-refusal and model-JSON counts. The
actual sidecar always contained the HTTP refusal proof, not a model parse error;
neither the sidecar nor historical console was overwritten.1076full pytest passed
(34.69s), Ruff/strictPyright/diff checks passed. Old single-gate policy reviews
and model/field proofs remain unchanged and separately hash-verified.

## Continuation and remaining gates

Queue004 was launched only after classification and a new immutable external
control freeze. Canonical SHA:
`20a314469fba9042805467548f82639609bb017ee6b0bd2162acb4349ba51e84`;
file SHA `9ae8d5b1412a4aeb84c18400b31661792725ec58d9e1daabba68242f0a897094`.
External audit sources live in `audit-tools/resident-policy-control-002`, not
the frozen measured app. Actual children still import only that frozen app's
`src`/`scripts` and use execution revision `90fd30c`.

Queue PID1941494 was confirmed live at19:13:54Z, validating immutable history
before the next reservation. Re-read later state; a live queue is not proof of
a running cell. Previously started29cells cannot be repeated; only never-started
cells continue. New unresolved findings stop the queue again. No operational
replacement has been used, and cell29 is not eligible for one.

Complete all168cells, then perform recipient/privacy, private evidence, failure,
adoption and quality audits before pruning. Only subsequently freeze a PhaseII
method set (at most4complete methods with `42+168+48m<=420`). No method set has
been selected, no PhaseII launched, and no new method/architecture implemented.
