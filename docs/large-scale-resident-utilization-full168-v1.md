# Resident pool utilization — reviewed Phase I, all168 effective cells

2026-10-07, Asia/Hong_Kong. This is the closed resident/diverse-pool Phase I,
not the historical42, discarded confounded attempts or live held-out outcomes.
No scheduler, model pool, static capability or Agent behavior was changed.

## Measured deployment use

Counts below refer to returned physical-model telemetry, not requested model
actions, Cloud Planner calls, calibrated probes or all inference attempts.
Distinct run counts overlap across deployments and must not be added as runs.

| Resident deployment | Returned inference receipts | Distinct effective runs | Returned backend work s | Input / output tokens | Finish reasons |
| --- | ---: | ---: | ---: | --- | --- |
| A4 / Qwen3-VL4B Instruct | 129 | 101 | 4,441.345 | 649,650 / 13,326 | 128stop / 1length |
| A5 / Qwen3-VL8B Instruct | 13 | 10 | 679.883 | 75,067 / 2,199 | 13stop |
| A28 / Qwen3.5-27.3B | 53 | 40 | 7,886.706 | 325,826 / 6,887 | 53stop |
| strongGPU0 / Qwen3.5-27.3B | 31 | 30 | 40.855 | 11,941 / 2,732 | 31stop |
| strongGPU1 / Qwen3-VL8B Instruct | 0 | 0 | 0 in returned population | 0 / 0 in returned population | None |

There are226 returned receipts. Their13,048.788s of backend service work is
summed work, not wall-clock E2E and not complete work for all attempted inference.
Three confirmed post-inference JSON failures have no returned service/token
telemetry; they stay separately unmeasured, not zero or part of226. Successful
generic tool receipts are A4=554, A5=235, A28=177, strongWorker=0. The strongWorker
nevertheless has actual GPU0 model execution. All four Workers thus have real
execution, but all five resident model instances do not have benchmark inference.

GPU1 remained resident and available under the frozen validation contract;
zero returned benchmark receipts does not imply that it failed readiness or
never executed its separate synthetic calibration. Do not invent benchmark
utilization, force route traffic to it, restart models or alter locality policy
to produce a uniform table.

The single length receipt is a nonterminal Video1/Qwen/Slow/B specialist action,
`video-analyst:call_f26f7a1e68734f239ebd23f8`. Its recorded request reserves2048
output tokens; it returns1197input/2048output, finish_reason=length, and materializes
a text artifact. That run later completes with a valid canonical terminal and
original score1. This is an explicitly recorded output-budget endpoint, not proof
of hidden input truncation or semantic sufficiency. No automatic regeneration or
budget change was made. The completed terminal-output audit remains separate.

## Population lineage

The old first109 utilization snapshot is immutable, but is not simply a prefix
of today's effective168. Eleven of its E attempt1 runs were subsequently
source-bound classified as confounded by the generic E query-contract repair;
their original traces are still preserved, but they are not effective samples
in this full table. The98 shared effective run IDs retain exactly the same
trace hashes and per-deployment returned receipt counts. No old receipt is
edited, relabelled as the repaired execution, or mixed into the new population.

Each effective membership is bound to current snapshot053, comprehensive review,
original trace and original source epoch. Selected and executed deployment IDs
must agree and belong to the five-instance pool. Returned model and successful
tool counts are cross-checked against each run's source projection. Residency
validation passes per effective run. Independent readback reconciles the five
deployment counts/tokens/finish reasons/work sums and all four Worker tool totals.

## Interpretation limits

The pool has three distinct weight artifacts, two architecture families and
five resident instances, not five model-quality tiers. The unchanged anonymous
static contract merges equivalent declared modality/context/capability envelopes;
model size alone does not create a justified quality class.

All methods use the same locality scheduler, not a load balancer or model-quality
optimizer. Prompt-only synthesis, artifact locations, input sizes, output budgets
and visual versus text work differ. GPU0's short accumulated workload is not a
matched version of A28's work: dividing these totals by counts does not measure
hardware speedup, routing optimality or model-quality superiority. Changing model
selection can also change the selected weight artifact; pure-device quality
invariance is therefore not established.

Fresh Worker stores/processes do not imply cold model/cache state. Constant
runner/server identity validation and dedicated resident processes control model
loading; ordinary prefill, image processing, queuing and generation remain service
cost. No guessed warmup subtraction, TTFT inference or utilization percentage is
introduced. Registered artifact traffic is not all prompt/control communication.

This evidence supports honest environment/use reporting for the final
characterization, not a cost-guidance winner or the final Q1–Q10 conclusions.
The held-out block remains live; no supporting/corpus/store-body audit occurred.

## Immutable owner-local receipts

Root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.

| Artifact | SHA256 |
| --- | --- |
| resident-returned-model-utilization-full168-001.json | `dde73546792e0861d6e75a14d51a9ae5d092ef6d035d59d33eecc01b49f761e8` |
| resident-returned-model-utilization-full168-provenance-001.json | `14b2f89de0acc6d1f2bf33fc4764668c26733945ca5e9a8d434429f01440a087` |
| Preserved analysis source | `e5199e3970544c44a809f9a5960799eacd10a91ec4a4592fdbf88f76a872b3ec` |
| Historical first109 receipt | `e3656e46de7da5e12f0e8e95d0d67f769eea7572b856fb830bd07e64129c7bb0` |

Zero new model/Planner calls; no full trace, API output, dataset or model payload
passed through the development PC. See [pool calibration](resident-model-pool-calibration-v1.md),
[comprehensive review](large-scale-resident-phase1-comprehensive-audit-v1.md) and
[quality-conditioned footprint](large-scale-resident-phase1-quality-footprint-v1.md).
