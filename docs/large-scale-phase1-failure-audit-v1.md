# Phase I failure audit — in progress

2026-10-05. **First cell's repaired attempt admitted; original attempt excluded.**
One valid Phase I sample at this checkpoint. This is not the required completed
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
