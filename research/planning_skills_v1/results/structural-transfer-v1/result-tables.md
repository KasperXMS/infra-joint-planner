# Audited synthetic workflow results

All frozen episodes are included. Completion, numeric task success and submitted-policy compliance are separate metrics. Raw generations, per-decision values and submitted values remain in the private evidence archive.

| Model | Condition | Completion | Numeric success | Policy-compliant submission | Turns | Prompt tokens | Output tokens | Median E2E, s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-4B | none | 24/48 | 0/48 | 0/48 | 2,151 | 6,259,550 | 54,722 | 82.19 |
| Qwen3.5-4B | static_system | 30/48 | 1/48 | 1/48 | 1,941 | 6,122,834 | 49,995 | 60.72 |
| Qwen3.5-4B | binding_system | 42/48 | 2/48 | 0/48 | 1,298 | 4,809,681 | 31,851 | 26.27 |
| Qwen3.5-4B | unbound_system | 38/48 | 2/48 | 0/48 | 1,565 | 6,257,913 | 40,028 | 31.93 |
| Qwen3.5-9B | none | 29/48 | 1/48 | 0/48 | 1,953 | 5,753,312 | 61,513 | 77.62 |
| Qwen3.5-9B | static_system | 38/48 | 3/48 | 0/48 | 1,625 | 4,853,922 | 54,578 | 46.25 |
| Qwen3.5-9B | binding_system | 48/48 | 7/48 | 5/48 | 1,073 | 3,520,838 | 27,636 | 34.83 |
| Qwen3.5-9B | unbound_system | 47/48 | 3/48 | 1/48 | 1,127 | 3,799,671 | 28,147 | 36.50 |

Prompt/output counts include failed workflows. E2E reflects the frozen mixed-condition tensor batches. Batch service wall is counted once in summary.json; summed overlapping request latency is not GPU kernel time. Local GPU USD is unknown (JSON null / empty CSV cell), and cloud API calls are absent.

## Failures and verification

| Model | Condition | Schema-valid / raw actions | JSON / schema failures | Dependency mismatch | Stale/invalid | Non-root verify | Phase / terminal errors | Turn exhaustion | Verify calls, all workflows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-4B | none | 2151/2151 | 0 / 0 | 979 | 0 | 0 | 0 / 0 | 24 | 41 |
| Qwen3.5-4B | static_system | 1941/1941 | 0 / 0 | 344 | 38 | 0 | 0 / 0 | 18 | 54 |
| Qwen3.5-4B | binding_system | 1298/1298 | 0 / 0 | 96 | 0 | 0 | 0 / 0 | 6 | 73 |
| Qwen3.5-4B | unbound_system | 1565/1565 | 0 / 0 | 30 | 0 | 0 | 0 / 119 | 10 | 67 |
| Qwen3.5-9B | none | 1953/1953 | 0 / 0 | 1083 | 0 | 0 | 0 / 0 | 19 | 49 |
| Qwen3.5-9B | static_system | 1625/1625 | 0 / 0 | 551 | 0 | 0 | 0 / 0 | 10 | 65 |
| Qwen3.5-9B | binding_system | 1073/1073 | 0 / 0 | 0 | 0 | 0 | 0 / 0 | 0 | 80 |
| Qwen3.5-9B | unbound_system | 1127/1127 | 0 / 0 | 9 | 11 | 0 | 0 / 0 | 1 | 78 |

All other typed errors, context rejections, legal deadlines and finish reasons remain in summary.json and per-episode tables. Expected source updates/transient notices are excluded from unexpected-error counts. Correct submitted provenance after earlier wrong computations is a behavioral diagnostic; it does not prove that the model recognized its semantic error.

## Paired success contrasts

Intervals resample graph clusters and retain paired update variants. They are exploratory uncertainty summaries on a selected synthetic stress distribution, not universal significance claims.

| Model | Treatment minus baseline | Mean TSR difference, pp | Cluster bootstrap 95%, pp | Rescues / regressions |
| --- | --- | --- | --- | --- |
| Qwen3.5-4B | binding_system - unbound_system | +0.00 | [-8.33, 10.42] | 2 / 2 |
| Qwen3.5-4B | binding_system - static_system | +2.08 | [-6.25, 12.50] | 2 / 1 |
| Qwen3.5-4B | unbound_system - static_system | +2.08 | [0.00, 6.25] | 2 / 1 |
| Qwen3.5-4B | static_system - none | +2.08 | [0.00, 6.25] | 1 / 0 |
| Qwen3.5-9B | binding_system - unbound_system | +8.33 | [-10.42, 27.08] | 7 / 3 |
| Qwen3.5-9B | binding_system - static_system | +8.33 | [-8.33, 27.08] | 7 / 3 |
| Qwen3.5-9B | unbound_system - static_system | +0.00 | [-8.33, 10.42] | 2 / 2 |
| Qwen3.5-9B | static_system - none | +4.17 | [0.00, 12.50] | 3 / 1 |

Runtime condition names ending in `_system` put the generic static bank in the system message; their observation-only dynamic block is the latest user message. Joined/unjoined blocks match facts and tokenizer length at the same state, not total tokens along divergent trajectories.
