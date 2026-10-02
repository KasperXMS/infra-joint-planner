# Infra-Aware Pre-decision Qwen v1

Date: 2026-10-02. Status: **completed and audited; experiments stopped**.
Twelve primary runs completed/evaluated; original score 1 in 11 runs, score 0 in
Slow-Blind r2. No replacements, retries or execution-path changes during the block.
Pre-decision timing is verified, but the desired Slow-local-first behavior is not.

## Frozen protocol

Experiment commit: `91f11ff2ccf60e1b4d00a89155c8a2ae0a458096`, branch
`open-ended-mas-preliminary-v1`. Harness: `infra-aware-predecision-v1`.
Manifest SHA-256: `cd184ee891e9227aa7f236e3361fc6d49a756a4429a8aa3e7070b286f144ba99`.
See [preregistered protocol](infra-aware-predecision-v1-protocol.md).

One unchanged MultiHop task: `multihop-multisource`, query
`multihop-rag-train-9bae0079038050a37a1ae583`; complete 609-document corpus, three
non-semantic hash partitions initially on A4/A5/A28. Corpus/query content hashes
and original private evaluator are recorded in the protocol and per-cell freeze.
Only the prospective task-declared terminal serialization requires exact `Yes`/`No`.
Historical evaluation objects and evidence remain untouched.

Cloud Manager and always-Blind Verifier: `qwen3.8-max`. SDK-native persistent loop,
bounded specialists-as-tools, same instructions/tools/operator semantics/scheduler.
Budgets: Manager 20; physical calls 64; Verifier 20; specialists 8 turns, 4 created,
2 active. Physical inference: Qwen3.8-27B Q4_K_M Ollama on A28/strong-4090,
32768 context / 2048 reserved output, 1200 s client timeout. A4/A5 operator-only.

Fast = 100 Mbps + 5 ms added RTT; Slow = 3 Mbps + 50 ms. Existing transactional
tc mechanism is unchanged, including Jetson netem support limitations. These are
shaper settings, not measured symmetric end-to-end RTT guarantees. Model devices,
initial placement, tool vocabulary and physical scheduler are identical across cells.
Specifically, A4/A5/A28 applied HTB without netem; strong-4090 applied HTB plus
5/50 ms netem. Jetson-to-Jetson artifact routes therefore have bandwidth shaping,
not the advertised added delay on both ends. This inherited, preregistered support
limitation prevents interpreting the block as a fully symmetric RTT experiment.

Order: each of r1/r2/r3 runs Fast-Blind, Fast-Aware, Slow-Blind, Slow-Aware.
Twelve primary runs, fresh processes and 48 distinct initially empty Worker stores.
No semantic retry/replacement, prompt tuning, cost guidance or whole-plan compiler.
All dataset reading/materialization/distribution occurs on strong-4090; the
development PC receives no dataset/artifact bodies.

## Implementation changes

Opt-in SDK input filter fetches the existing anonymous `PhysicalProfileView` before
every Aware Manager call, including H0. Actual sanitized model inputs, profile
event/order, selected/effective action arguments, exact sanitized Verifier input,
lineage and per-action intervals are recorded. Blind fetches/injects no profile;
Verifier stays Blind. Provider-private reasoning is excluded.

Prospective canonical terminal contract rejects punctuation/Markdown/prose without
semantic guessing or changing the original evaluator. Existing stopping/synthesis
states remain unchanged. See [implementation audit](infra-aware-predecision-implementation-v1.md).

## Tests

Before experiment freeze: full pytest 412 passed; Ruff passed; strict Pyright
0 errors/0 warnings. Additional read-only audit tooling has two synthetic tests;
it is outside the deployed frozen execution path. Final full pytest: **414 passed**;
Ruff passed; strict Pyright 0 errors/0 warnings; `git diff --check` passed.
Analysis tooling is separately committed/pushed as `5b2bcde`.

## Evidence

Remote root: `/home/super/xiaoming/infra-aware-predecision-v1-91f11ff`.
Each `evidence/matrix-rN/condition` contains result, JSONL trace, private observer
diagnostics, original evaluation, freeze/source manifest, run configuration,
empty pre-run Worker states, Worker PIDs, tc restoration attestation
and lightweight validation. Source/model/profile unknowns are not imputed.
Generated Worker configs reside in `<root>/worker-configs`; strong-4090 Worker logs
in `<root>/logs`; Jetson Worker logs in their corresponding deployment roots on
each node. Cell/repetition filenames link these logs to retained PID records.

Read-only full audit: `predecision-audit-v1.json` under the remote root;
SHA-256 `40aa08d5cdc23ec64f642f75b411424a8297af6bb91906d59a2ee1780a7fde3c`.
It contains raw-event references, input lineage, exact Verifier contexts, profile
history, physical selection/telemetry, concurrency and input evidence hashes.
Reproduce to a **new** output path on strong-4090 with
`scripts/predecision_trace_audit_v1.py --root <root> --output <new-audit.json>`.
Do not copy the dataset-bearing audit/trace through the development PC.

## Formal matrix / final clean matrix

Run IDs are `predecision-qwen-multihop-<condition>-rN` in the exact order below.
All completion/format/evaluator gates pass. Bytes/time below are **action traffic**;
initial placement is separately 7,696,522 bytes per run (Fast 1.255–1.669 s,
Slow 21.987–22.539 s), included in E2E. Inference counts exclude preflight failures.

| Order / run suffix | Answer / score | E2E s | Action bytes | Transfer s | Inferences / model service s | Manager / Verifier turns | Physical calls |
|---|---|---:|---:|---:|---:|---:|---:|
| fast-blind-r1 | Yes / 1 | 156.210 | 5,204,596 | 1.121 | 1 / 107.131 | 7 / 7 | 7 |
| fast-aware-r1 | Yes / 1 | 156.766 | 5,204,596 | 1.530 | 1 / 84.109 | 7 / 7 | 7 |
| slow-blind-r1 | Yes / 1 | 132.646 | 5,204,596 | 14.830 | 1 / 6.936 | 6 / 6 | 11 |
| slow-aware-r1 | Yes / 1 | 121.426 | 5,204,596 | 14.775 | 1 / 8.267 | 8 / 8 | 7 |
| fast-blind-r2 | Yes / 1 | 671.796 | 5,204,596 | 1.630 | 3 / 588.661 | 9 / 9 | 8 |
| fast-aware-r2 | Yes / 1 | 138.353 | 57,445 | 0.443 | 1 / 5.940 | 7 / 7 | 13 |
| slow-blind-r2 | No / 0 | 270.295 | 42,446 | 0.602 | 1 / 125.554 | 8 / 8 | 15 |
| slow-aware-r2 | Yes / 1 | 188.718 | 5,204,596 | 14.771 | 1 / 80.962 | 7 / 7 | 7 |
| fast-blind-r3 | Yes / 1 | 145.748 | 5,204,596 | 2.133 | 1 / 82.015 | 9 / 9 | 7 |
| fast-aware-r3 | Yes / 1 | 171.831 | 112,712 | 0.288 | 1 / 6.961 | 9 / 9 | 30 |
| slow-blind-r3 | Yes / 1 | 207.437 | 57,351 | 0.953 | 1 / 11.009 | 8 / 8 | 20 |
| slow-aware-r3 | Yes / 1 | 193.687 | 5,204,596 | 15.047 | 1 / 83.843 | 9 / 9 | 7 |

### Completion / quality and system aggregates

| Condition (n=3) | Completed / evaluated | Mean original score | E2E mean / median s | Action bytes mean / median | Transfer mean / median s | Inferences mean | Model service mean / median s |
|---|---|---:|---:|---:|---:|---:|---:|
| Fast-Blind | 3 / 3 | 1.000 | 324.585 / 156.210 | 5,204,596 / 5,204,596 | 1.628 / 1.630 | 1.667 | 259.269 / 107.131 |
| Fast-Aware | 3 / 3 | 1.000 | 155.650 / 156.766 | 1,791,584 / 112,712 | 0.754 / 0.443 | 1.000 | 32.337 / 6.961 |
| Slow-Blind | 3 / 3 | 0.667 | 203.460 / 207.437 | 1,768,131 / 57,351 | 5.461 / 0.953 | 1.000 | 47.833 / 11.009 |
| Slow-Aware | 3 / 3 | 1.000 | 167.944 / 188.718 | 5,204,596 / 5,204,596 | 14.864 / 14.775 | 1.000 | 57.691 / 80.962 |

Overall completion/evaluation 12/12, score 11/12; new scores are the unchanged
original evaluator on prospective canonical outputs, not post-hoc canonical rescoring.
All 12 terminal outputs are exactly `Yes` or `No`; the sole zero is a real wrong
direction, not serialization. No formal cell is discarded for being incorrect.

## Operational and provenance audit

All 12 freeze manifests identify the same deployed commit, harness hash, static
capability hash and task bundle hash
`059cbc033c1e8610b2322ba4d57d5f49be67fa3ddeb08d9b3495e1c5f3787815`.
There are 12 unique config hashes, 48 unique storage roots, four empty pre-run
Worker states per cell, `retry=false`, `replacement=false`, `repetitions=1`.
Frozen runtime/component hashes were rechecked on the deployed code after completion.
Recorded Manager-input and Verifier-context hashes were independently recomputed
using the frozen serialization function; all match. Each result's terminal action ID
matches its last successful manager-owned model action. All 24 pre-run A28/4090
deployment states expose the unchanged 32768/2048 text+image contract.

- 12/12 privacy scans cover all `logical.*` events, including actual model input
  provenance. No physical/private identity findings; Blind has no profile.
- Aware has **47/47** Manager calls with a matching fresh profile event before the
  actual input event; 94 total Manager input events across the block. Verifier is
  Blind in both conditions; its saved sanitized contexts exclude physical profiles.
- All six Aware H0 snapshots precede the first action. Fast reports `network_class=fast`,
  Slow `constrained`; candidate count 4, queue envelope [0,0]. Overview input bytes 0,
  remote count [0,0], transfer/service estimates null. These are empty-input overview
  values, not marginal cost estimates for the selected aggregate action.
- All **1,300 Worker probes succeeded**. No `missing_input` or persisted-artifact
  disappearance. Selected/retrieved artifact read-only checks on A28 match stored
  content hashes in all 12 runs; relevant guides were retrieved in every run.
- 12/12 tc restoration attestations match original/restored qdisc; no cleanup errors.
  The queue has a terminal `completed: 12` journal record, its process has exited,
  and all 48 created Worker PIDs were checked inactive across four nodes. Ollama
  deployments and historical stores/evidence were left intact.

## Failure audit / bugs / affected reruns

See [exception audit with trace IDs and confidence](infra-aware-predecision-qwen-v1-failure-audit.md).
All score-zero runs, the top E2E outlier, equal maximum-traffic runs and unusual
high-call/reduction trajectories were audited from raw provenance and retained blobs.

The only incorrect terminal is **Slow-Blind r2**: relevant shard-3 guides survived,
the specialist and Verifier saw the simplified-build evidence, but terminal synthesis
consumed two irrelevant shard-1 results. Verifier subsequently accepted `No` despite
its earlier affirmative evidence assessment. Primary evidence-selection failure;
secondary Verifier semantic failure, high confidence. No operational confounder.

Every run encountered conservative context preflight; Fast-Aware r3 encountered two.
Thus 27 prepared model actions include 13 context rejections and **14 actual completed
inferences**. These are byte-upper-bound preflight rejections, not proof of actual
tokenizer overflow/OOM. All completed model calls finish `stop`. Raw evidence is
not automatically summarized/truncated; successful reduction/reasoning is explicit.

No genuine deployed harness/runtime/evaluator/observer defect was discovered in this
block, so **affected reruns/replacements = 0**. Legal-tool argument errors, phase
restrictions, within-run output-ID reuse and Verifier semantic errors remain recorded
Agent behavior; none was tuned away. Analysis-only handling of model-action schema,
null failed selection and unknown token usage was tested without formal reruns.

## Workflow comparison

Counts below include prepared physical attempts, not only successes. `M` is model
actions / actual inferences; `Ctx` preflight context rejections; `Red` generic
filter/select/top-k/derive attempts. Cross-agent handoffs are explicit traced events.

| Suffix | First operators | Graph nodes/edges | BM25 / aggregate / read / Red | M / Ctx | Specialists / turns | Handoffs | Peak actions / overlap pairs / parallel turns |
|---|---|---:|---:|---:|---:|---:|---:|
| FB r1 | aggregate | 7/8 | 4/1/0/0 | 2:1 / 1 | 0/0 | 0 | 2/1/1 |
| FA r1 | aggregate | 7/8 | 4/1/0/0 | 2:1 / 1 | 0/0 | 0 | 2/2/2 |
| SB r1 | aggregate | 11/10 | 5/1/3/0 | 2:1 / 1 | 2/9 | 1 | 2/2/1 |
| SA r1 | aggregate | 7/6 | 2/1/2/0 | 2:1 / 1 | 2/4 | 0 | 1/0/0 |
| FB r2 | aggregate | 8/9 | 2/1/0/1 | 4:3 / 1 | 0/0 | 0 | 1/0/0 |
| FA r2 | BM25 ×1 | 13/15 | 7/2/2/0 | 2:1 / 1 | 1/6 | 1 | 5/10/1 |
| SB r2 | BM25 ×3 | 15/17 | 9/1/3/0 | 2:1 / 1 | 1/8 | 1 | 3/6/2 |
| SA r2 | aggregate | 7/8 | 4/1/0/0 | 2:1 / 1 | 0/0 | 0 | 2/1/1 |
| FB r3 | aggregate | 7/8 | 4/1/0/0 | 2:1 / 1 | 0/0 | 0 | 1/0/0 |
| FA r3 | BM25 ×6 | 30/35 | 11/3/8/5 | 3:1 / 2 | 3/24 | 3 | 6/17/1 |
| SB r3 | BM25 ×1 | 20/22 | 11/2/5/0 | 2:1 / 1 | 2/14 | 2 | 5/10/1 |
| SA r3 | aggregate | 7/8 | 4/1/0/0 | 2:1 / 1 | 0/0 | 0 | 1/0/0 |

Eight runs have real overlapping action intervals (peak 2–6); singleton gateway
batches do not imply sequential execution. No incomplete/unknown action intervals.
Information is reduced either through explicit BM25/reduction artifacts, physical
model summaries, or observed evidence incorporated into the terminal prompt. Five
terminal calls have no artifact inputs but carry evidence facts from prior tool/read
observations in the selected prompt; they are not hidden finalizer calls.

| Condition | Mean Manager turns | Mean physical calls | Mean successful tools | Mean BM25 attempts | Graph node counts r1/r2/r3 | First aggregate / local |
|---|---:|---:|---:|---:|---|---|
| Fast-Blind | 8.33 | 7.33 | 4.33 | 3.33 | 7/8/7 | 3 / 0 |
| Fast-Aware | 7.67 | 16.67 | 11.00 | 7.33 | 7/13/30 | 1 / 2 |
| Slow-Blind | 7.33 | 15.33 | 11.67 | 8.33 | 11/15/20 | 1 / 2 |
| Slow-Aware | 8.00 | 7.00 | 5.00 | 3.33 | 7/7/7 | 3 / 0 |

## Cost decomposition

Seconds of service work; **do not add columns as a wall-time partition**. Operator
column excludes model service. Model operator-wrapper work is separately retained
in the audit. Deployment choice for all 14 successful inferences is A28; tools use
A4/A5/A28. The unchanged scheduler minimizes input movement, not newly calibrated
model latency. strong-4090 remains available but is not substituted to rescue cells.

| Suffix | Manager | Specialists | Verifier | Tool/operator | Physical model | Action transfer |
|---|---:|---:|---:|---:|---:|---:|
| FB r1 | 22.012 | 0 | 18.867 | 4.980 | 107.131 | 1.121 |
| FA r1 | 36.869 | 0 | 25.967 | 5.712 | 84.109 | 1.530 |
| SB r1 | 31.868 | 37.552 | 26.445 | 4.018 | 6.936 | 14.830 |
| SA r1 | 31.130 | 15.345 | 22.389 | 2.870 | 8.267 | 14.775 |
| FB r2 | 48.229 | 0 | 27.622 | 2.033 | 588.661 | 1.630 |
| FA r2 | 38.006 | 23.499 | 65.323 | 2.899 | 5.940 | 0.443 |
| SB r2 | 40.974 | 23.033 | 52.664 | 3.264 | 125.554 | 0.602 |
| SA r2 | 36.879 | 0 | 25.692 | 5.160 | 80.962 | 14.771 |
| FB r3 | 28.600 | 0 | 25.317 | 3.843 | 82.015 | 2.133 |
| FA r3 | 62.355 | 81.403 | 43.537 | 3.204 | 6.961 | 0.288 |
| SB r3 | 56.699 | 67.269 | 41.397 | 4.138 | 11.009 | 0.953 |
| SA r3 | 33.549 | 0 | 30.213 | 4.375 | 83.843 | 15.047 |

| Condition | Mean Manager / specialist / Verifier s | Mean tool/operator s |
|---|---:|---:|
| Fast-Blind | 32.947 / 0 / 23.935 | 3.619 |
| Fast-Aware | 45.744 / 34.968 / 44.943 | 3.938 |
| Slow-Blind | 43.180 / 42.618 / 40.169 | 3.807 |
| Slow-Aware | 33.853 / 5.115 / 26.098 | 4.135 |

Fast-Blind r2 is the dominant E2E outlier: two raw-evidence summary inferences plus
terminal inference account for 588.661 s versus 1.630 s transfer. The five thin-prompt
terminal runs use 181–501 input tokens and roughly 5.9–11.0 s model service, whereas
the ordinary reduced-artifact terminal calls consume roughly 4.7–4.8K tokens and
81–107 s. Workflow/evidence representation strongly changes model service cost.
Cloud Manager/specialist token counts were not persisted by the SDK hooks and remain
**unknown**, not zero; Verifier/physical token counts are retained where measured.

## Infra-response analysis

- **Blind Fast vs Slow:** aggregate-first 3/3 versus 1/3 despite no network visibility;
  this warns that condition-associated workflow differences alone are not causal evidence.
- **Aware Fast vs Slow:** aggregate-first 1/3 versus **3/3**. All Slow decisions saw
  `constrained` H0 beforehand. The hypothesized Slow-local-first / Fast-move-data
  pattern is **not supported**; this is not a late-profile implementation defect.
- **Fast Blind vs Aware:** Aware mean E2E 155.650 versus 324.585 s, but medians
  156.766 versus 156.210 s are essentially equal; the mean gap is dominated by one
  expensive Blind summary trajectory. Aware moves fewer bytes on two trials, but
  performs more physical calls and far more variable workflow composition.
- **Slow Blind vs Aware:** Aware mean/median 167.944/188.718 versus 203.460/207.437 s,
  with quality 3/3 versus 2/3. However Aware transfers **2.94× the mean bytes** and
  about 90.75× the median bytes. It has higher physical model service work and lower
  cloud/specialist expansion. This is a quality/traffic/reasoning trade-off, not uniform
  infrastructure efficiency improvement.

E2E sample CVs: FB .927, FA .108, SB .339, SA .240. Small E2E CV does not imply stable
workflow: Fast-Aware node counts 7/13/30 and calls 7/13/30 differ substantially.
Slow-Aware topology is stable but consistently moves the full corpus under Slow.
No significance test, causal counterfactual or general benchmark claim is warranted
from one task and n=3 with provider-default Manager sampling and fixed run order.

## Comparison with historical Reactive-Aware

Historical audited block stays separate; no pooled samples or rewritten scores.
Its source archive hash remains
`6f1114d1dc2f530a8f2de04aa312ac5da161e3d2eb50b93bbeaf59144044f8af`.
See [historical raw-trace audit](qwen-multihop-trace-audit-v1.md).

| Condition | Old completion | Old E2E mean / median s | Old mean action bytes | Old mean inference count | Old graph nodes | Old first aggregate / local |
|---|---|---:|---:|---:|---|---|
| Fast-Blind | 3/3 | 168.579 / 166.909 | 5,204,596 | 1.000 | 27/4/10 | 2 / 1 |
| Fast-Aware | 3/3 | 182.073 / 194.482 | 1,791,553 | 1.000 | 21/4/16 | 1 / 2 |
| Slow-Blind | 3/3 | 501.279 / 310.232 | 3,496,281 | 2.667 | 30/10/9 | 2 / 1 |
| Slow-Aware | 2/3 | 360.055 / 232.591 | 3,526,759 | 2.000 | 7/39/4 | 2 / 1 |

Old Aware had no H0; new Aware has 47 fresh pre-decision inputs. Slow-Aware is now
less topologically variable (7/7/7), but stable aggregate-first does not support the
local-first hypothesis. Fast-Aware remains variable. The old block includes two
observer-confounded trajectories and nine affirmative serialization/evaluator zeros.
New prospective canonical output handling, instrumentation and different stochastic
trajectories are additional between-block changes. Therefore new completion/quality
and E2E differences cannot be attributed solely to H0; old secondary semantic audit
scores are not substituted for its original scores.

## Cost-accounting limitations

Service/transfer/operator/cloud sums are non-additive work, not a critical-path
partition. `invoke_model` operator latency includes service: never add them twice.
Initial placement traffic is reported separately from action traffic and is inside
the runner E2E. Idle/recovery/overhead cannot be uniquely inferred from residual
wall time; these remain unknown. Parallelism is computed from actual action interval
overlap, not singleton gateway batch counts. Provider tokens and physical model
tokens are distinct. Preflight rejection does not count as physical inference.

The existing overview profile is coarse: H0 includes anonymous network class and
queue ranges, but lacks measured action-marginal/model-service estimates. Its
`input_bytes=0` describes the empty-input overview query, not zero task data.
Unknown service/transfer estimates remain unknown. No new cost estimator is added.

## What is established

The minimal timing/serialization repair works in real SDK/cloud/Worker execution,
with reconstructable action graphs, real transfers/inferences, private observer
diagnostics, exact terminal labels and unchanged original evaluation. The complete
block has no observed operational confounder; the wrong answer is trace-explainable
evidence selection plus Verifier semantic behavior. Real model/cloud/recovery costs
often dominate action transport, and low traffic alone does not guarantee quality.

## What is not established / next-method implication

Raw pre-decision visibility of this **coarse existing profile** is insufficient to
reliably obtain the desired cost-sensible Slow-local-first adaptation. It does not
establish that all infrastructure information is useless: this profile has no
action-specific marginal transfer/model costs or useful service profiles. Neither
consistent latency/traffic superiority nor a rational adaptation reversal is proven.

Explicit, verifiable marginal-cost guidance is a reasonable **next research question**,
not an implemented result or authorized continuation of this goal. No cost-guided
planner, RL, new benchmark, further matrix, semantic tuning or budget expansion was
added. Stop after committing/pushing this report and exception audit.
