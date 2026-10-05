# Resident-pool utilization: exact first64-run scope

2026-10-06. Offline workload accounting only. Model residency, available
deployment surface and actual benchmark selection are different quantities.
No inference/warm-up, scheduling change, routing tuning or new cell was used
to produce this audit. No quality aggregation or method pruning.

Snapshot020's exact64admitted attempts were re-read on the4090. Every trace
hash matched the immutable snapshot; each successful model receipt had a
matching selected Worker/deployment andexecution deployment ID. Returned
telemetry counts matched the original collector for each run. Three separately
confirmed post-inference JSON failures were added only using exact hash-bound
adjudication proof, not a false inference flag or a preflight rejection.

| Deployment | Returned successful inferences | Confirmed JSON failures after inference | Confirmed inference lower bound | Successful input/output tokens | Successful backend work |
| --- | ---: | ---: | ---: | --- | --- |
| A4 / Qwen3-VL4B | 46 | 0 | 46 | 223,631 /1,661 | 1,223.559s |
| A5 / Qwen3-VL8B | 6 | 0 | 6 | 33,040 /1,276 | 346.088s |
| A28 / Qwen3.5-27B | 20 | 1 | 21 | 120,610 /1,829 | 2,785.598s |
| 4090 GPU0 / Qwen3.5-27B | 14 | 2 | 16 | 4,453 /651 | 12.486s |
| 4090 GPU1 / Qwen3-VL8B | 0 | 0 | 0 | 0 /0 | 0s inthisclosedpopulation |

All86returned successful inferences finished withstop. There are89confirmed
actual inferences includingthree post-inference parse failures. No additional
unreviewed missing model outcome is present in this exactsnapshot. Failed parse
service time/tokens areUNKNOWN:complete A28 andGPU0backend totals remainUNKNOWN,
not their successful subtotals. Zero GPU1observed inference is an empty measured
population, **not** proof that it was unloaded, unavailable or has zero service
latency. Synthetic calibration/warm-up outside these runs is not counted here.

Successful tool executions: A4=217,A5=97,A28=64,strong-4090=0. These are successful
tool receipts, not all requested/failed calls. The4090Worker was nevertheless
used for model inference. Allfour Workers have actual successful execution;
onlyfour ofthefive resident model instances have observed benchmark inference
inthisearlysubset. Do not claim balanced utilization or five-instance inference
use. Current surfaces andcalibration/residency checks remain unchanged.

Service work is overlapping receipt work, not E2E. The deployments saw very
different input volumes, task stages andmodel artifacts. These totals are not
a matched hardware-speed comparison, a proof of model quality equivalence or
evidence that a method caused optimization. Inparticular GPU0's low input volume
does not prove semantic evidence loss: facts may be carried inline byManager;
private information-path audit is still required. Q4_K_M/context32768/reserved2048
configuration is shared, but that is not a measured accuracy tier.

## Exact scope and provenance

Remote append-only `analysis/resident-utilization-snapshot020-audit-001.json`
file SHA-256:
`33bf860ffeccb44f09649dcd33dff19aefa234fa77d485f03a283caa33a9902d`.
Snapshot020 file SHA-256:
`8dc0c5a77259f809b4b992c5e1e923965699391abf1592a5be19af44550512d1`.
Original64-run journal prefix SHA-256:
`6e47652714442981a164df233a51637372d2868959578f235a7f0482f76440d0`.
The current append-only journal's first129physical lines matched that prefix,
so later queue advancement did not silently change the population. The frozen
environment file hash matched executionfreeze001's source binding.

Per-run trace/admission hashes, conditions andcounts are persisted with the
five deployment definitions; no prompts, artifacts, gold or model outputs were
exported tothisPC. No original result, admission, journal, app or Agent input
was rewritten. Modelcalls0 for thisaudit;fullPhaseIaudit/pruningflagsfalse.
The ongoing queue stays oncontrol007/execution001. This is the earlier64-run
scope, not the current finished count or the complete168/PhaseII characterization.
