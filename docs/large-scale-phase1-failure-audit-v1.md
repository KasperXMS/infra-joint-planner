# Phase I failure audit — in progress

2026-10-05. **One attempted cell, zero admitted formal samples.** This is a
checkpoint, not the required completed 168-cell audit. No method pruning is allowed.

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

**Still required before resumption:** make formal generated Worker configs use the
repaired binary, update the accounting implementation provenance without changing
prices, freeze/audit the repaired execution, authorize only the affected cell's
new attempt, then continue the unchanged 168-cell order. The repair is not yet
verified through a formal Worker run. No second nominal cell or Phase II has run.
