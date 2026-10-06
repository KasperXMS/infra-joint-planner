# Resident model/Worker utilization — first87effective cells only

2026-10-06. Actual returned-inference telemetry, not complete PhaseI/model-quality
comparison, a routing change or a claim that every resident instance was used.
Two original Quote-confounded attempts are excluded; repaired counterparts count
once. Closed predecessor42are not pooled.

| Resident deployment | Returned inference receipts | Distinct effective runs | Returned backend work | Input /output tokens |
| --- | ---: | ---: | ---: | ---: |
| A4 VL4B | 66 | 51 | 2,546.093s | 329,489 /9,098 |
| A5 VL8B | 8 | 6 | 415.821s | 48,202 /1,280 |
| A28 Qwen3.5-27.3B | 30 | 21 | 4,304.611s | 180,611 /3,554 |
| strongGPU0 Qwen3.5-27.3B | 21 | 20 | 18.944s | 7,591 /961 |
| strongGPU1 VL8B | 0 | 0 | 0s in returned population | 0 /0 in returned population |

There are125returned inference receipts, allfinish-stop. Three additional
post-inference model JSON failures have no returned service/token telemetry;
they are retained/proven by exact scoped reviews, **not** counted as zero-work
or included in the125returned population. The table therefore is not a universal
total inference/service/token-work accounting. Empty returned populations are
observed zero receipts, not a claim about unknown failed work or model capacity.

A4/A5/A28 have286/110/85successful generic tool receipts. StrongWorker has actual
GPU0inference. Thus all four Workers have real execution, while the five model
instances are not equally used. All87selected residency checks passed. Resident/
warm does not imply invocation; no scheduler tuning, forced balancing, model
substitution or cold-start subtraction was performed. Later cells may differ.

Model work is heterogeneous: different prompts, image/text inputs, context sizes,
output lengths, schedules and Planner trajectories. Do not divide these totals
to claim hardware speedup, model superiority or cost-rational placement. No
validated quality tier is introduced; the pool still has3artifacts/5instances
and the anonymous capability signature merges equivalent declared capabilities.
Task/evaluator quality must be reported separately in the complete audit.

## Source proof

Remote exclusive receipt:
`analysis/resident-returned-model-utilization-first087-001.json`, fileSHA
`78f0799b29e92b0c18a70f173a2931f2d4fa0d9bd31422dcfcdaa3c549bc4e47`.
It verifies snapshot023and the exact cell086/087isolated projection hashes,
87unique effective cells matching the frozen schedule prefix, all trace hashes
and per-action unique physical receipts. Selection deployment must equal the
execution deployment and belong to the five-instance pool; returned counts must
equal each original telemetry projection's successful inference receipt count.
Journal prefix183recordsSHA:
`c663e222e5076bc622aff07048251600e1acfba13a862db65c1928bb022216b4`.

No benchmark artifact body/private annotation/model prompt is exported. This is
0new inference calls/0scheduler mutations and no score aggregation or pruning.
All168/complete private audit/pruning/actualPhaseII/finalcharacterization remain
required. This updates the earlier64-cell utilization scope, not its old files.
