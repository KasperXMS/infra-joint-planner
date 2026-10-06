# Resident model/Worker utilization — first109effective cells only

2026-10-06. This updates the earlier87-cell diagnostic without changing its
evidence, scheduler, model contract or sampling. It is not a full PhaseI result,
model-quality comparison or hardware speedup measurement. Old42and the two
retained Quote-confounded originals remain excluded from this population.

| Resident deployment | Returned inference receipts | Distinct effective runs | Returned backend work seconds | Input / output tokens |
| --- | ---: | ---: | ---: | --- |
| A4 Qwen3-VL4B | 79 | 62 | 2,882.275 | 391,802 / 10,130 |
| A5 Qwen3-VL8B | 9 | 7 | 435.969 | 52,582 / 1,282 |
| A28 Qwen3.5-27.3B | 33 | 24 | 4,764.916 | 200,063 / 3,981 |
| strongGPU0 Qwen3.5-27.3B | 27 | 26 | 21.819 | 9,068 / 974 |
| strongGPU1 Qwen3-VL8B | 0 | 0 | 0 in returned population | 0 / 0 in returned population |

There are148returned inference receipts, all finish-stop. Three additional
confirmed post-inference JSON failures lack returned service/token telemetry;
they are retained and explicitly unmeasured, not zero-work or part of148.
These are counts/work for a defined returned population, not universal inference
or complete failed-service-work totals. Distinct run counts overlap across models.

Successful generic tool receipts: A4=358, A5=135, A28=99. StrongWorker has actual
GPU0inference; all four Workers have real execution. All five models are resident,
but GPU1still has no returned benchmark inference in this prefix. No forced
load-balancing/routing, substitution or warmup subtraction was added to make the
utilization table look uniform. Fresh Worker/store does not mean cold inference.

Inputs, prompts, modalities, output sizes and trajectories differ substantially.
In particular, the very short GPU0calls are not matched counterparts of the A28
workload. Do not divide accumulated work by counts to assert device speedup,
quality superiority, routing optimality or a causal cost-information effect.
No new quality class is inferred from model size. The frozen pool remains three
artifacts/two model families/five instances, with declared equivalent capabilities
merged into one anonymous static class.

## New109/B0 example: service work, not a stalled queue

MultiHop1/P2/Fast/B0 completed with a valid terminal answer and original evaluator
score0. Four Manager/four Verifier turns, four physical actions, zero specialists:
`aggregate_artifacts -> two BM25retrievals -> invoke_model`. One actual A28
inference consumed two materialized evidence artifacts; there was no context
failure, backend exception, model reload or inferred retry. Two recorded
`phase_restricted` tool observations did not prevent normal completion.

E2E210.457s; returned backend179.301s/7,622input/170outputtokens/finish-stop.
Tool-only work2.938s, root reasoning14.737s, Verifier11.979s are separate measured
work, not an exact E2E partition. Fixed initial7,696,522bytes/0.856s is distinct
from complete action movement5,204,596bytes/0.915s. Frozen API list-price estimate
USD0.05066 is not an invoice.

Graph4nodes/4edges/13snapshots; observed maximum concurrency2 and overlap1.778s.
The artifact-action dependency path182.852s excludes root/Verifier/control waits;
it is not a full Manager-critical-path estimate. Actual recipient contexts8,
privacy/residency/Worker exit all passed. Execution completed wrong; evidence
selection/reasoning/stopping primary attribution remains pending private audit.
Artifact inputs alone do not prove semantic adequacy or establish quality loss.

## Immutable source-bound proofs

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Proof | File SHA256 |
| --- | --- |
| `analysis/resident-snapshot-027.json` | `0ae71b594a0d57c774fa56a898951706114e339cd1a3b594ba2e77e77c95a5b8` |
| `analysis/resident-cell109-source-bound-001.json` | `2bb12bb4b6bca9b434f9a4d3f17305f8cf149dcdfaf5d9c0665eafb0664a6b20` |
| `analysis/resident-returned-model-utilization-first109-001.json` | `e3656e46de7da5e12f0e8e95d0d67f769eea7572b856fb830bd07e64129c7bb0` |

The first108source-aware membership/trace/source hashes come from snapshot027;
109has an independent exact ledger/admission/result/trace projection. All109are
unique effective runs, with verified shutdown/residency. Selected and executed
deployment must agree and belong to the five-instance pool; returned counts must
match each run's original telemetry projection. Every shared87-cell run retains
its earlier trace hash and per-deployment receipt count. No prior proof is relabelled.

No prompt, gold, benchmark body or full trace entered the development PC. This
read-only diagnostic makes zero new model calls, no score aggregation and no
method-pruning/PhaseIIdecision. Current measured execution remains002/revision
955fe8f. At03:53:08Z Queue010PID3755889 and cell110atomic3896528 were live;110is
pending, not covered by this109-cell table. Full168/complete private audit/frozen
screening/actualPhaseII/final Q1–Q10remain required.
