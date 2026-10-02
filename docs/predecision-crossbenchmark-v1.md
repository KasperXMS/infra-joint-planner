# Pre-decision Raw-Aware cross-benchmark characterization v1

**Status: IN PROGRESS, not a final report.** Updated 2026-10-03 (Asia/Hong_Kong).

## Scope and frozen system

Extend the existing audited MultiHop block without repeating it: three LongBench
multi-document tasks and three Video-MME questions, four conditions each, n=1,
24 primary cells. See [frozen protocol](predecision-crossbenchmark-v1-protocol.md).
This is raw coarse profile visibility, not cost-guided planning or a new method.

Frozen execution commit: `90cea3261c1e21f7cb528025c64729741ccc8451`.
Harness: unchanged `infra-aware-predecision-v1`, SHA-256
`cd184ee891e9227aa7f236e3361fc6d49a756a4429a8aa3e7070b286f144ba99`.
Manager/Blind Verifier `qwen3.8-max`; physical Qwen3.8-27B Q4_K_M 32K/2048;
20/64/20 budgets; 1200 s service timeout. Same native loop, instructions, tools,
scheduler, worker substrate and observer semantics. Fast 100 Mbps / configured
5 ms, Slow 3 Mbps / configured 50 ms; Jetson netem limitation is unchanged.

All dataset access/materialization/distribution and raw evidence remain on the
4090. Development PC only sends code and obtains bounded telemetry/metadata.

## Authoritative evidence and continuation

Remote root: `/home/super/xiaoming/predecision-crossbenchmark-v1-90cea32`.
`protocol-freeze.json` covers all six task bundles/source files/capabilities before
any Manager call. Per-cell evidence:
`evidence/<task>-<condition>/primary/{freeze,private,runs,tc-attestation.json,...}`.
All four fresh Worker roots are independently namespaced per attempt.

Queue PID at launch: **358408** (`queue-launch.json`). Never infer liveness from this
file: verify `/proc/358408/cmdline` and `queue.jsonl` before waiting or restarting.
The queue stops at the first operational audit gate; no automatic semantic retry,
replacement, prompt change or budget expansion. See exception policy in protocol.

Read-only scalar audit snapshots are stored remotely, e.g. `audit-progress-002.json`.
Audit tool revision does not change frozen runtime/code/config or cell results.

## Partial result

| Task | Condition | Completed / evaluated | Answer / score | E2E s | Action bytes | Model inferences | Manager / Verifier |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| Financial `66f7c780bb02136c067c35e8` | Fast-Blind | yes / yes | A / 0.0 | 406.653 | 265,938 | 2 | 20 / 20 |

First cell passed profile isolation, input/Verifier hash reconstruction, terminal
answer provenance, all 320 Worker probes, artifact persistence and tc restoration.
It is a retained **valid semantic quality failure**, not a reason to tune the harness.
Trace: 40 graph nodes / 63 edges; one specialist / 8 specialist turns; peak four
overlapping actions. Four conservative context preflight rejections are recorded,
not counted as inference. Physical model service work 113.943 s, action transfer
work 3.760 s, Manager work 163.616 s, Verifier work 88.344 s; sums are non-additive.
Initial placement separately moved 1,081,150 representation bytes in 0.387 s.

Second cell (Financial Fast-Aware) is running as of this update. No remaining-cell
outcome, family aggregate, stability, cost-rationality or cross-benchmark claim yet.

## Pending final analysis

Task-level four-condition tables, workload properties, operator/reduction/sampling
paths, evidence preservation, physical/cloud work, infra-response and quality
will be reported after auditing all attempts. Do not pool incompatible benchmark
scores or interpret single trajectories as stochastic stability. Existing MultiHop
analysis remains [separate](infra-aware-predecision-qwen-v1.md).

Final goal requires all 24 cells executed or validly failed, operational incidents
resolved or explicitly hard-stopped, final reports, evidence and repository audit.
The unattended goal remains active.

## Offline verification

Cross-benchmark admission and queue instrumentation: full pytest **426 passed**,
Ruff passed, strict Pyright **0 errors / 0 warnings**, `git diff --check` passed.
The deployed execution commit's initial suite had 424 passing tests; the two
additional tests cover read-only audit provenance and the contract alias round-trip.
No running cell's frozen code or semantic behavior was changed by audit tooling.
