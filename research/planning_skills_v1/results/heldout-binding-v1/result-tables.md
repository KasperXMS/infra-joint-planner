# Audited synthetic workflow results

All frozen episodes are included. Completion, numeric task success and submitted-policy compliance are separate metrics. Raw generations, per-decision values and submitted values remain in the private evidence archive.

| Model | Condition | Completion | Numeric success | Policy-compliant submission | Turns | Prompt tokens | Output tokens | Median E2E, s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-4B | none | 36/36 | 0/36 | 0/36 | 700 | 1,290,103 | 16,842 | 21.21 |
| Qwen3.5-4B | static_system | 36/36 | 1/36 | 1/36 | 701 | 1,547,191 | 21,775 | 22.55 |
| Qwen3.5-4B | static | 6/36 | 0/36 | 0/36 | 2,018 | 6,848,330 | 57,539 | 96.74 |
| Qwen3.5-4B | local | 26/36 | 1/36 | 1/36 | 1,112 | 2,818,144 | 30,782 | 26.71 |
| Qwen3.5-4B | ledger_system | 29/36 | 0/36 | 0/36 | 999 | 3,380,976 | 31,327 | 27.29 |
| Qwen3.5-4B | binding_system | 36/36 | 5/36 | 4/36 | 639 | 1,790,113 | 17,972 | 22.91 |
| Qwen3.5-4B | unbound_system | 33/36 | 2/36 | 2/36 | 781 | 2,514,657 | 21,448 | 25.24 |
| Qwen3.5-9B | none | 33/36 | 2/36 | 2/36 | 808 | 1,718,159 | 21,367 | 26.73 |
| Qwen3.5-9B | static_system | 36/36 | 0/36 | 0/36 | 680 | 1,479,193 | 19,085 | 22.29 |
| Qwen3.5-9B | static | 29/36 | 1/36 | 1/36 | 957 | 3,005,718 | 43,560 | 31.25 |
| Qwen3.5-9B | local | 29/36 | 2/36 | 2/36 | 1,052 | 2,659,968 | 30,662 | 42.23 |
| Qwen3.5-9B | ledger_system | 29/36 | 0/36 | 0/36 | 1,085 | 3,763,013 | 35,055 | 42.59 |
| Qwen3.5-9B | binding_system | 36/36 | 5/36 | 4/36 | 633 | 1,746,728 | 15,235 | 23.45 |
| Qwen3.5-9B | unbound_system | 36/36 | 3/36 | 3/36 | 637 | 1,770,069 | 15,390 | 23.82 |

Prompt/output counts include failed workflows. E2E reflects the frozen mixed-condition tensor batches. Batch service wall is counted once in summary.json; summed overlapping request latency is not GPU kernel time. Local GPU USD is unknown (JSON null / empty CSV cell), and cloud API calls are absent.

## Failures and verification

| Model | Condition | Schema-valid / raw actions | JSON / schema failures | Dependency mismatch | Stale/invalid | Non-root verify | Phase / terminal errors | Turn exhaustion | Verify calls, all workflows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-4B | none | 700/700 | 0 / 0 | 20 | 0 | 0 | 0 / 0 | 0 | 60 |
| Qwen3.5-4B | static_system | 701/701 | 0 / 0 | 13 | 0 | 0 | 0 / 0 | 0 | 60 |
| Qwen3.5-4B | static | 2018/2018 | 0 / 0 | 348 | 1 | 798 | 0 / 0 | 30 | 815 |
| Qwen3.5-4B | local | 1112/1112 | 0 / 0 | 183 | 0 | 364 | 0 / 0 | 10 | 407 |
| Qwen3.5-4B | ledger_system | 999/999 | 0 / 0 | 285 | 1 | 52 | 0 / 0 | 7 | 105 |
| Qwen3.5-4B | binding_system | 639/639 | 0 / 0 | 0 | 0 | 0 | 0 / 0 | 0 | 60 |
| Qwen3.5-4B | unbound_system | 781/781 | 0 / 0 | 85 | 0 | 0 | 0 / 0 | 3 | 57 |
| Qwen3.5-9B | none | 808/808 | 0 / 0 | 185 | 2 | 0 | 0 / 0 | 3 | 57 |
| Qwen3.5-9B | static_system | 680/680 | 0 / 0 | 21 | 9 | 6 | 0 / 0 | 0 | 68 |
| Qwen3.5-9B | static | 957/957 | 0 / 0 | 194 | 0 | 143 | 0 / 0 | 7 | 193 |
| Qwen3.5-9B | local | 1052/1052 | 0 / 0 | 418 | 0 | 52 | 0 / 0 | 7 | 100 |
| Qwen3.5-9B | ledger_system | 1085/1085 | 0 / 0 | 260 | 0 | 82 | 0 / 0 | 7 | 132 |
| Qwen3.5-9B | binding_system | 633/633 | 0 / 0 | 0 | 1 | 1 | 0 / 0 | 0 | 62 |
| Qwen3.5-9B | unbound_system | 637/637 | 0 / 0 | 1 | 0 | 0 | 0 / 0 | 0 | 60 |

All other typed errors, context rejections, legal deadlines and finish reasons remain in summary.json and per-episode tables. Expected source updates/transient notices are excluded from unexpected-error counts. Correct submitted provenance after earlier wrong computations is a behavioral diagnostic; it does not prove that the model recognized its semantic error.

## Paired success contrasts

Intervals resample graph clusters and retain paired update variants. They are exploratory uncertainty summaries on a selected synthetic stress distribution, not universal significance claims.

| Model | Treatment minus baseline | Mean TSR difference, pp | Cluster bootstrap 95%, pp | Rescues / regressions |
| --- | --- | --- | --- | --- |
| Qwen3.5-4B | binding_system - unbound_system | +8.33 | [0.00, 22.22] | 4 / 1 |
| Qwen3.5-4B | binding_system - static_system | +11.11 | [0.00, 25.00] | 4 / 0 |
| Qwen3.5-4B | static_system - static | +2.78 | [0.00, 8.33] | 1 / 0 |
| Qwen3.5-4B | ledger_system - static_system | -2.78 | [-8.33, 0.00] | 0 / 1 |
| Qwen3.5-4B | local - static_system | +0.00 | [0.00, 0.00] | 0 / 0 |
| Qwen3.5-9B | binding_system - unbound_system | +5.56 | [0.00, 13.89] | 2 / 0 |
| Qwen3.5-9B | binding_system - static_system | +13.89 | [2.78, 27.78] | 5 / 0 |
| Qwen3.5-9B | static_system - static | -2.78 | [-8.33, 0.00] | 0 / 1 |
| Qwen3.5-9B | ledger_system - static_system | +0.00 | [0.00, 0.00] | 0 / 0 |
| Qwen3.5-9B | local - static_system | +5.56 | [0.00, 16.67] | 2 / 0 |

Runtime condition names ending in `_system` put the generic static bank in the system message; their observation-only dynamic block is the latest user message. Joined/unjoined blocks match facts and tokenizer length at the same state, not total tokens along divergent trajectories.
