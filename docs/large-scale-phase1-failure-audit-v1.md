# Phase I failure audit — in progress

2026-10-05. **First cell's repaired attempt admitted; original attempt excluded.**
Fourteen effective valid Phase I samples at the latest checkpoint. This is not the completed
168-cell audit. No method pruning is allowed.

## First attempt

Frozen order's first cell is Video-MME position 1 (602-2), Qwen3.8-Max, Fast, B1.
Execution revision: 5ca3fff16c66e6dafaf583d53e5d07dfc88a2a28.

| Metric | Observed |
|---|---:|
| Execution completed | yes |
| Original evaluator score | 1.0 |
| Terminal format valid | yes |
| E2E | 188.076 s |
| Initial placement bytes / time | 213,739,837 / 18.897 s |
| Action transfer bytes | 0 |
| Manager / specialist / Verifier turns | 9 / 14 / 9 |
| Created specialists / peak active | 2 / 1 |
| Budget-counted tool/model calls | 34 |
| Actual metered cloud API calls | 32 |
| Original list-price API USD summary | approximately 0.429820 |
| Admission | system/harness confounder; excluded pending repair rerun |

Score 1 is preserved, not promoted: required video sampling repeatedly failed
because the advertised media surface's executable lacked an H.264 decoder.
This is not a valid quality/cost comparison or evidence of a method benefit.

All original result/JSONL trace, 32 raw request/response/usage receipts, worker
stores and admission remain immutable remotely. Recipient/method scans found no
privacy issues. Worker shutdown was verified; tc restored exactly.

## Two identified defects

1. **Audit/accounting:** fixed 40-digit Decimal summation of already-rounded
   per-call USD receipts was order-dependent. Completion order versus UUID-sorted
   audit changed the last decimal place (for example total
   0.4298197012981836059474614331840710081186 versus
   0.4298197012981836059474614331840710081187). Individual usage/model/cost receipts
   matched. This is a genuine accounting/audit defect, not different billing.
2. **Primary experimental confounder:** the Jetson software build contained
   libdav1d but no native H.264 decoder. These six frozen original videos are H.264.
   Worker startup's existing AV1 probe did not establish H.264 executability.
   Multiple sample_frames actions failed with “no decoder found for: h264”.

## Repair status

- Revision 5bfadbe adds exact, order-independent summation of frozen per-call
  Decimal receipts, with permutation regression coverage. It changes no rates,
  FX, per-call charge, Agent feedback, prompt or objective.
- Append-only generic-repair authorization binds original admission, independent
  repair audit and new execution freeze. It does not permit retrying valid Agent
  failures or wrong answers.
- Isolated FFmpeg 8.0.1 / dav1d 1.4.3 build adds the native H.264 decoder/parser,
  preserving the old version family, AV1 support and historical binary. No runtime
  fallback is added. A build-tool wheel layout error was diagnosed/tested; its
  original failed bootstrap log is preserved separately.
- Identical repaired ARM binary SHA-256:
  d45da9277fbb9931ac5e0ddc324b5371a742db28c245b49023e9e31b56661f0c.
- All A4/A5/A28 passed actual H.264 and AV1 first-frame extraction through the
  repaired binary. H.264 probe comes directly from frozen original video 131-3:
  bytes moved only 4090 → Jetsons, never through the development PC. Each produced
  one nonempty JPEG; no Planner/Verifier/physical-model call occurred.
- Full pytest **703 passed**, Ruff passed, strict Pyright zero errors/warnings,
  diff check passed.

Remote receipts:

- readiness/first-cell-confounder-diagnosis-001.json
- readiness/decoder-repair-validation-001.json
- A28 environment-repair-001/build-completed.json
- Original failed bootstrap and successful build process/log receipts are retained.

## Repaired execution freeze and queue resumption

Execution revision 94c9bac62daa30d70ed319d741a17c54e6ec96cd adds only the formal
environment/accounting repair bridge. Generated Jetson configs change only the
FFmpeg executable; the strong-4090 config is unchanged. All model/operator
contracts, timeouts, budgets, Agent instructions, methods, scheduler and task
representations remain frozen. Eight additional regression tests bring the full
suite to **711 passed**; Ruff, strict Pyright and diff check passed.

All four new source deployments match (364 source/script/config files). The
original 5ca3fff applications remain separately preserved. A receipt-helper
import error happened after deployment had completed; independent hash
reconciliation established completion and no deployment was repeated.

- New execution freeze: execution-freeze-002.json, canonical SHA-256
  50e2fbcac51693695e551f0b09bd83f332891a1e4c2e6a48b393fd3874d569d8.
- New calculator provenance: preparation/pricing-002/price-freeze.json, file SHA-256
  74b74f0809b88fb01798287bc1bfb999622db4379acd76b387e82c159b76900a.
  Original price/FX/date/source receipts are unchanged; pricing-001 is preserved.
- Independent repair audit: readiness/generic-repair-audit-001.json, canonical
  SHA-256 5f1532dc6ae4416f882b49e4941049d12c0b122bb27e0e6035c610340f41d18e.
  It binds the original admission and all original evidence hashes, source-change
  allowlist, unchanged control/physical contracts, tests and actual codec probes.
- Original 32 raw HTTP calls pass the repaired per-call usage/cost and recipient
  scans. Original order-dependent aggregate output is not overwritten.
- Strong-4090 also passed real H.264 and AV1 JPEG extraction. No Agent/model call
  or tc shaping occurred during repair verification.
- The append-only ledger authorizes a generic repair rerun for only the original
  confounded cell. It does not authorize replacing ordinary semantic failures.

At the resumption checkpoint, actual queue PID 1344958 and attempt2 child PID
1345330 were verified live. The queue retains the original 168-cell order and
requires admission after every attempt. This is a launch checkpoint, **not proof
that the repaired cell passed**. No Phase II gate or method pruning is authorized.

## Affected-cell attempt2: admitted

The same frozen cell's attempt2 subsequently completed with original evaluator
score 1.0 and valid terminal format. Admission reports no problems. Real Worker
sample_frames executed successfully, followed by one physical model inference.
One context rejection and other typed semantic failures are retained as ordinary
Agent continuation/recovery, not implementation confounders.

| Metric | Repaired attempt2 |
|---|---:|
| E2E | 229.841 s |
| Initial placement bytes / time | 213,739,837 / 18.605 s |
| Action transfer bytes / work | 772,094 / 0.907 s |
| Manager / specialist / Verifier turns | 5 / 0 / 5 |
| Budget-counted tool/model calls | 3 |
| Physical inference calls / service work | 1 / 119.155 s |
| Cloud HTTP calls | 10 |
| List-price API USD | 0.227856507527338922919517931410196787095255 |
| Admission / original score | valid / 1.0 |

Original attempt1 result, raw trace and accounting remain unchanged. These two
stochastic trajectories across a genuine environment repair are **not a paired
method comparison** and do not prove cost improvement.

The queue proceeded to the original second scheduled cell: Video 602-2,
DeepSeek V4 Pro, Slow, B0 Blind, attempt1. No task/method/order replacement or
prompt/budget tuning occurred. It was verified live, not adjudicated completed.

## Subsequent valid admissions

The DeepSeek/Slow/B0 cell subsequently completed with format validity and score
1.0, followed by Qwen/Slow/E and DeepSeek/Fast/D, also valid completed score-1.0
samples. All four valid admissions have no unresolved implementation/recipient/
cleanup findings; original attempt1 remains excluded and unchanged. These are
four conditions on one video question, not four independent tasks or a global
accuracy claim. Exact telemetry and mechanism use are in Phase I results.

E did not query; D did not perform a multi-candidate comparison. D's two
phase-restricted proposal failures and discarded quote are ordinary frozen
control behavior, not reasons to retry/tune. The next original LongBench-2 /
DeepSeek / Fast / B0 cell is live and has typed context/semantic recovery events;
no conclusion is made before its terminal result/admission. Phase II is gated.

## LongBench quality failures are retained, not repaired

LongBench position 2 / DeepSeek / Fast / B0 and Qwen / Slow / B1 both completed
with valid terminal format, original evaluation score 0.0 and clean admission.
Each recovered from typed context/semantic failures and reached one successful
physical inference. There is no known implementation confounder in these samples;
they are retained as wrong answers. No retry, replacement, instruction/strategy
change or budget increase is authorized on this basis.

Their exact primary semantic/evidence/stopping cause is not inferred from score
alone; comprehensive private evidence/terminal-path audit remains required after
the 168-cell block. The next original LongBench-2 / DeepSeek / Slow / A cell was
verified live at this checkpoint. Full Phase I/II gates remain unsatisfied.

## Ten-admission checkpoint: ordinary failure/recovery remains valid

Government / DeepSeek / Slow / A and Qwen / Fast / B subsequently also completed
with score 0.0 and clean admission. Both reached one physical inference after
typed context/semantic recovery. No answer repair or replacement occurred.

Academic / Qwen / Fast / A and DeepSeek / Slow / B1 completed with score 1.0.
The DeepSeek trajectory naturally created two simultaneously active specialists,
used 62 physical calls and recovered from artifact-size/context/semantic failures.
Completion does not erase those failed calls, and success near the 64-call guard
does not authorize increasing the budget or modifying stopping logic.

All ten admissions have no unresolved findings. The one original excluded attempt
is unchanged. Detailed evidence adequacy, quality-failure causes and causal
method use await the post-block audit; no supporting-reference bodies are read
for online strategy. The collector reads settled evidence only and exports
bounded cost/count/hash metadata. It neither controls the queue nor supplies
feedback to recipients. Latest local regression remains 725 tests passed,
Ruff/strict Pyright passed; formal execution stays 94c9bac.

Snapshot-007 binds this checkpoint (hash in the results report). The next original
Academic / Qwen / Slow / B0 attempt and its parent queue were verified live.
Ten of 168 nominal samples is incomplete: no method pruning or Phase II.

## Eleven-admission checkpoint and offline graph audit

Academic / Qwen / Slow / B0 also completes with score 1.0, clean admission and one
created specialist. Four context failures and other typed semantic/phase failures
remain visible; one physical inference succeeds and the original evaluator runs.
No method/Planner/task replacement occurs. The next Academic / DeepSeek / Fast /
E attempt and parent queue are confirmed owned/live, not presumed complete.

All eleven admitted traces have append-only DAGs, complete action lifetimes and
zero dependency-order violations in a separate read-only structural audit. This
does not resolve semantic adequacy, private evidence retention or quote-induced
revision. It does prevent counting status snapshots as workflow evolution or
mistaking dependency width for measured concurrency. Source/data remain remote;
only bounded scalar/hash metadata enter reports. Twelve offline tests bring full
pytest to 737 passed; Ruff/strict Pyright/diff pass. Formal code remains 94c9bac.

Snapshot-008 and graph-audit-001 hashes are in the results report. All Phase I/II
gates remain unsatisfied until all 168 nominal samples and full audits complete.

## Exact model JSON failure is not a harness repair or replacement

Academic / DeepSeek / Fast / E attempt1 completed, format-valid, score1.0, but
the conservative gate stopped on validation_failed. A specialist requested one
materialized application/json model output. Frozen Worker code awaited backend
completion, then json.loads rejected its text. This is model-format behavior,
not a broken parser, missing operator or evaluator mismatch. The Agent recovered.

Independent full admission re-audit reproduced the original receipt and confirmed
no other findings/incidents across 31 actual HTTP contexts/model/usage/price
receipts, event chain, observer, persistence, Worker shutdown and tc cleanup.
No supporting evidence or gold was used. A sidecar binds 147 original evidence
hashes, the unchanged execution freeze and Worker implementation; original
admission canonical SHA is dd9762e620283a5cc7276fed3de290363b39462106148b1c93da21ed289a9d0b.

The exact-case review cannot waive other validation, privacy, physical or service
failures. Original journal settlement/admission/result/trace remain intact. The
effective view has twelve valid samples and one original decoder confounder;
two original gate rejections remain visible. No cell is repeated or repaired.

Three successful model telemetry receipts plus one proved post-inference parse
failure establish at least four inferences. Failed inference tokens/service work
remain unknown. Frozen reached_model_inference=false is not universal evidence
of no inference; the spent ledger already retained unknown work/inference for
this failure. No online feedback or Agent/physical behavior is changed.

Regression covers quality-independent narrow admission, immutable evidence,
sidecar/source tampering, next-cell-only resumption and bounded proof hashing.
Full pytest758/Ruff/strict Pyright/diff pass. The new offline controller and its
supplemental freeze sit outside unchanged formal app94c9bac. Hashes are in results.
Parent1660678 / child1661081 were verified live on the next original MultiHop-1 /
Qwen / Fast / B. Full Phase I/II gates remain unsatisfied.

## First MultiHop admission and offline collector cost

MultiHop-1 / Qwen / Fast / B is a valid, normally completed score-1 sample. A
context rejection is followed by natural additional retrieval and successful
terminal inference. All twelve BM25 actions succeed; no historical artifact
collision, admission finding or operational incident is recorded. SDK phase
rejects remain ordinary recorded trajectory behavior, not tuning opportunities.
Private supporting-evidence coverage and primary semantic diagnoses still wait
for the complete Phase I audit; no supporting bodies enter live feedback.

The read-only snapshot collector inherited a membership property that reran
sidecar proof checks separately for every scheduled cell during journal replay.
This made the diagnostic unnecessarily slow, not the frozen Agent execution.
The new offline-only collector verifies once per membership calculation and uses
one checked attempt population for counts. Regression proves no persistent cache
hides drift and proof errors still propagate; all 760 tests/Ruff/Pyright pass.
The superseded owned stdin collector was stopped only after exact process/env
checks; the queue and formal cell were untouched. Original evidence and prior
collectors/checkpoints remain intact. New collector v1-6, snapshot-010 hashes
and the latest pending condition are in the results report. No experiment rerun.

## First MultiHop wrong answer: not an execution defect

MultiHop-1 / DeepSeek / Slow / A completes and reaches its original evaluator,
score 0.0. There is no terminal failure or admission finding. Fourteen Manager
turns and 26 physical calls do not exhaust the 20/64 horizon. Two model context
rejects are followed by three successful inferences (all normal stop); no service
timeout or operational incident is observed. Twenty-one tools succeed. Model
work is 789.002 s and cloud API estimate USD 0.492382; costly/wrong is not hidden
or replaced. Fine-grained primary semantic cause remains unassigned until the
full Phase I evidence audit. Snapshot-011 and current next-cell proof are in
results; no prompt, budget, stopping or retrieval change is authorized by this
ordinary quality failure.
