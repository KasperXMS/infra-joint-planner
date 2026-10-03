# Pre-decision Raw-Aware cross-benchmark characterization v1

Updated 2026-10-03. **24/24 effective cells audited: 23 normal completions and
one valid Manager-budget failure.** LongBench:12/12 evaluated; Video:11 evaluated
plus one no-answer result. No remaining cell or additional experiment.
This report supersedes historical partial/hard-stop counts; old reports remain
in Git and excluded attempts remain immutable on the remote nodes.

## Scope and frozen system

Three LongBench tasks and three Video-MME questions, Fast/Slow × Blind/Aware,
n=1, 24 nominal cells. The original MultiHop 12-attempt block is not rerun.
This is coarse raw pre-decision visibility, not a cost-guided method.
See [protocol](predecision-crossbenchmark-v1-protocol.md),
[LongBench audit](predecision-longbench-v1.md),
[Video audit](predecision-videomme-v1.md) and
[exception audit](predecision-crossbenchmark-failure-audit-v1.md).

Cloud Manager and always-Blind Verifier use `qwen3.8-max`; native Agents SDK
Manager and bounded specialists-as-tools; B0 locality-aware physical scheduler;
finite system-owned operators. Budgets: Manager 20, physical calls 64, Verifier
20; specialists 8 turns / 4 created / 2 active. Terminal answer is deterministically
extracted from a successful physical model result and passed to the original
private evaluator, with no hidden semantic finalizer.

Blind receives task, semantic state and static capability contract only. Aware
Manager additionally receives a fresh anonymous physical profile before **every**
reasoning call, including H0. Specialists and Verifier remain Blind in both
conditions. Dynamic profile does not include concrete IP/deployment identity;
gold, source_ref and evaluator-private metadata never enter logical context.

Actual local artifact metadata: `qwen35`, 27.3B, Q4_K_M, same model/projector
blobs and template on A28/strong-4090, configured alias `qwen3.8-27b-v1`.
The alias is not independent proof of official release branding. Formal context
32768 / output ceiling 2048, same quantization/runtime; metadata 262144 is not
the configured context. Modelfile `num_predict=256` is overridden by Worker
request `max_tokens=2048`. Every completed physical inference audited so far
selected A28: no observed RTX/A28 model-placement reversal.

Fast = 100 Mbps + configured 5 ms; Slow = 3 Mbps + configured 50 ms. Jetsons
have HTB without netem; 4090 has HTB+netem. These are configured regimes, **not
measured symmetric RTTs**. Peer/Worker/iperf/ICMP shaping excludes cloud443/SSH.
Initial placement, models, tasks and scheduler remain unchanged. Fresh Worker
stores/processes do not imply cold Ollama processes/caches. Fixed FB/FA/SB/SA
order, stochastic trajectories and n=1 prevent stable or causal claims.

## Workload properties

| Task | Original source / representation bytes | Initial artifacts / sources | Semantic structure |
| --- | --- | --- | --- |
| Financial | 1033800 / 1081150 | 4 documents / 3 Workers | 344 ordered chunks, cross-document comparison |
| Academic | 494456 / 514789 | 2 documents / 2 Workers | 164 chunks, GPT-4 report and Chroma |
| News | 228792 / 242295 | 2 documents / 2 Workers | 77 chunks, two Sanofi releases |
| Video 795-3 | 282442048 / intact MP4 | 1 / A4 | 2495.121 s, AV1+Opus, visual tool question |
| Video 848-1 | 160083738 / intact MP4 | 1 / A4 | 2037.781 s, AV1+Opus, visual evidence question |
| Video 795-2 | 282442048 / same intact 795 MP4 | 1 / A4 | temporal-order question; not another independent video |
| Existing MultiHop | 7696522 corpus record bytes | 3 nonsemantic hash shards / 3 Workers | 609 documents, 2847 chunks, union is complete corpus |

LongBench source characters reconstruct exactly from ordered document chunks;
question, options and private evaluator/gold are unchanged. Videos are original
full sources, not smoke MJPEG representations. Agent-generated JPEG frames and
contact sheets are explicitly lossy runtime evidence; exact decisive-pixel
coverage is not established. `sample_frames` is cadence sampling capped by
max_frames, **not uniform full-timeline coverage**. For example 32 frames at 5 s
cover a nominal prefix through 155 s, not the 2495 s video.

No current dataset/artifact bodies pass through the development PC. Dataset
materialization/distribution and content hashes are computed remotely; PC receives
bounded audit metadata. Historical archive mistakes are disclosed separately,
not reused as current data transfer.

## Task-level comparison

Each entry = answer/score; E2E seconds; action payload bytes. Twenty-three rows
complete with canonical-format valid answers and original evaluation; the final
795-2 SA is a valid no-answer budget failure, not an evaluated score of zero. Action
traffic excludes mandatory initial materialization, which is included in E2E.
Do not pool incompatible benchmark scores.

| Task | Fast Blind | Fast Aware | Slow Blind | Slow Aware |
| --- | --- | --- | --- | --- |
| Financial | A/0; 406.653; 265938 | C/1; 1282.028; 573058 | A/0; 278.919; 141047 | A/0; 251.831; 486432 |
| Academic | C/1; 126.426; 63102 | C/1; 175.840; 243055 | C/1; 176.759; 25132 | C/1; 156.410; 18921 |
| News | C/1; 600.051; 107471 | C/1; 713.826; 99354 | C/1; 507.576; 191727 | A/0; 189.024; 19112 |
| Video 795-3 | B/0; 185.443; 581538 | A/1; 252.371; 1230240 | A/1; 1069.965; 1562096 | A/1; 1071.594; 1471756 |
| Video 848-1 | B/0; 442.512; 798787 | A/0; 226.982; 380788 | A/0; 871.266; 981232 | A/0; 711.029; 409154 |
| Video 795-2 | C/1; 692.487; 391212 | B/0; 1009.582; 742651 | B/0; 1170.017; 915054 | no answer/no evaluation; 4289.335; 7012950 |

LongBench: eight correct / twelve effective completions, Blind 4/6 and Aware
4/6, descriptive selected-set counts only. Video has four correct and seven wrong
evaluated answers, plus one budget failure without an evaluator score. Blind has
two correct of six evaluated; Aware two correct of five evaluated plus one failed
attempt. Missing evaluation is **not silently scored zero**. Existing MultiHop has nine eligible of twelve,
8/9 correct, unequal condition counts FB3/FA1/SB3/SA2; **not a clean balanced
n=3 comparison**. Three historical Aware runs are excluded for specialist
profile exposure. Do not use the original full-block means as clean estimates.

## Workflow response and quality-cost trade-offs

Financial Aware starts with aggregation in both Fast and Slow. Fast then retrieves,
uses one Blind specialist and performs four explicit per-option model analyses
plus terminal synthesis: five inferences, correct answer, 215% longer E2E and
115% more bytes than Fast Blind. Slow's 486432 action bytes exceed Slow Blind's
141047 and both are wrong. Neither supports a universal Slow -> Reduce policy.

Academic Aware switches Fast aggregation to Slow per-document retrieval.
Slow Aware versus Slow Blind: 24.7% fewer action bytes, 11.5% lower E2E, both
correct. This is the clearest quality-preserving **single-pair observation**,
not proof of stable infrastructure adaptation. Fast Aware is 39.1% slower.

News Fast Aware produces four explicit bounded model notes and a correct terminal
answer: 7.6% fewer bytes but 19.0% longer E2E than Fast Blind. Slow Aware is much
cheaper and wrong, while Slow Blind is correct. Reduction can lose task quality.

Video 795-3: all sample locally, differing cadence/frame selection; Slow Aware
has 5.8% fewer action bytes but virtually identical E2E to Slow Blind, both
correct. Mandatory 282 MB initial placement consumes about 789 s in each Slow
cell, not an Agent-controlled traffic saving.

Video 848-1: Aware converts many frames into compact sheets. Fast Aware reduces
bytes 52.3% and E2E 48.7%; Slow Aware reduces bytes 58.3% and E2E 18.4%.
All four answers are wrong, so these are not demonstrated quality-qualified
benefits. Sheet organization changes visual model work much more than the few
seconds of measured action transfer.

Video 795-2 Fast Aware explicitly widens sampling after a length-ended intermediate
analysis, but returns the wrong temporal answer. Compared with correct Fast Blind,
it is 45.8% slower and transfers 89.8% more bytes. Recovery and parallelism can
occur without recovered quality. Slow Aware expands to94 sampled frames across
the prefix and four clips, consumes88 images in11 inferences, but uses all20
Manager turns while still collecting evidence. No terminal synthesis/answer;
4289.335s,7012950 action bytes. Compared with Slow Blind this is3.67x E2E and
7.66x traffic, with no quality-qualified benefit. No retry or budget increase.

Existing eligible MultiHop Aware trajectories still aggregate the shards; moving
5204596 remote bytes onto A28 is co-location, **not compression**. Unequal retained
repetitions and broad Blind timing variation forbid a clean balanced speedup claim.

Eligible existing MultiHop results only (times seconds; no reruns):

| Condition / repetition | Answer / score | E2E | Action bytes / transfer | Model service |
| --- | --- | ---: | --- | ---: |
| FB1 | Yes/1 | 156.210 | 5204596 / 1.121 | 107.131 |
| FB2 | Yes/1 | 671.796 | 5204596 / 1.630 | 588.661 |
| FB3 | Yes/1 | 145.748 | 5204596 / 2.133 | 82.015 |
| FA1 | Yes/1 | 156.766 | 5204596 / 1.530 | 84.109 |
| SB1 | Yes/1 | 132.646 | 5204596 / 14.830 | 6.936 |
| SB2 | No/0 | 270.295 | 42446 / 0.602 | 125.554 |
| SB3 | Yes/1 | 207.437 | 57351 / 0.953 | 11.009 |
| SA2 | Yes/1 | 188.718 | 5204596 / 14.771 | 80.962 |
| SA3 | Yes/1 | 193.687 | 5204596 / 15.047 | 83.843 |

Slow Blind sometimes reduces locally (one correct, one wrong); eligible Aware
still moves the complete remote shards. Cost differences also reflect model/cloud
work, not a consistent network-class policy. Unequal retained repetitions limit
comparison; excluded FA2/FA3/SA1 are not put back into averages.

## Cost interpretation and limitations

LongBench action-transfer work is 0.24–3.76 s, much smaller than model/cloud work.
Financial Fast Aware spends 1106.980 s in real physical inference; News Fast Aware
530.521 s. More reduction branches can add expensive analysis, even with smaller
terminal artifacts. Prompt-carried evidence matters: zero artifact inputs do not
mean zero model input or evidence consumption.

For Slow videos, fixed initial placement is a major floor; decode and model work
remain substantial. Model/profile/operator/service work sums are non-additive
under parallelism; they are not an additive E2E partition. Measured action overlap
is not a matched sequential speedup. Unknown profiles and predicted critical-path
values remain unknown; no retrospective guessed values are inserted.

Final Slow Video Aware model service3120.961s, initial placement788.484s,
Manager142.812s, Verifier128.870s, operator74.033s and action transfer33.226s.
Its795.187s unclassified wall residual includes the separately measured initial
placement: the activity-union counter covers reasoning/actions, not materialization.
It must not be described as795s of idle/recovery or a timeout.

Context errors here are fail-closed **conservative envelope** refusals, not proof
of actual tokenizer/OOM capacity failure. The frozen text guard counts UTF-8 bytes
as a token upper bound; images have a static 2048-token cost. Prompt + artifacts
+ reserved output must fit 32768. Preflight-rejected requests did not reach
inference and must not be counted as model-service calls. This guard is unchanged,
not tuned for task completion or labeled dynamic deployment unavailability.

## Bugs, exclusions and provenance

See [failure audit](predecision-crossbenchmark-failure-audit-v1.md).
Repairs are generic and separately frozen: JSONL physical-line parsing; observer
transport idle-expiry mitigation; physical backend explicit no-retry/1200 s read
timeout; actual-recipient profile isolation. No instructions, Verifier, tool
semantics, task, budget, scheduler or model requirements were tuned.

Execution revisions are preserved per row: original `90cea32`, transport
`d43c3b3`, backend `5dafc43`, isolation `3c3bd95`. Current manifest SHA:
`444db21f3d7aa0db13af993854e77318a29bddee1aee438f27d4a4f7c25affbf`.
Only genuine affected cells were rerun; prior invalid attempts were never erased.
The privacy hard-stop and authorized repair chronology are preserved in
[incident](predecision-specialist-profile-isolation-hard-stop-v1.md) and
[repair](predecision-specialist-profile-isolation-patch-v1.md) audits.

Authoritative merged root:
`/home/super/xiaoming/predecision-crossbenchmark-v1-3c3bd95`.
`audit-final-001.json` with `--require-complete` admits24/24, no missing/unresolved
cells. Twenty-three successful terminal/evaluator provenances and one explicit
budget-failure record; zero observer errors in effective cells. All96 store roots
were initially empty;256 LongBench plus702 Video replicas pass actual size/SHA.
All24 traces/284 prepared actions have derived inputs ready before consuming
reasoning input. All51 completed A28 inferences match HTTP200/zero-truncation
records. All owned Workers/controllers are inactive; live qdiscs match originals.
Thirty preserved attempts =24 effective + five excluded finalized + one aborted.
Existing MultiHop's72 files and the original new block's156 hashed files are
unchanged. See [completion audit](predecision-crossbenchmark-completion-audit-v1.md)
for requirement-by-requirement proof and exact evidence hashes.

## Research questions Q1–Q6

1. **Different workloads change workflows?** Observed differences include
   aggregation/retrieval, specialist use, per-option analysis, sampling cadence,
   frame selection and sheets. No universal adaptation direction is demonstrated.
2. **Stable dependence on infrastructure?** Not established: n=1, stochastic
   loops, fixed order and persistent inference state. Blind also changes across
   Fast/Slow despite not seeing infrastructure.
3. **Reasonable natural adaptation?** Academic Slow is a quality-preserving
   cost signal; Video 848 sheets reduce work but all answers remain wrong.
   These should not be conflated.
4. **Counterexamples?** Financial Aware aggregates even in Slow and moves more
   than Blind; eligible MultiHop Slow Aware aggregates too. Fast can expand into
   costly retrieval/model decomposition. Slow -> Reduce is not a general rule.
5. **Dominant costs?** LongBench model/cloud reasoning and expansion; Slow Video
   initial placement plus visual model/decode. Action network time alone is small
   and insufficient to explain E2E.
6. **Simple network-class heuristic?** Not supported by this evidence; action
   consequence, evidence preservation and model work need consideration. That is
   a motivation for later research, not a method implemented or validated here.

## Claim boundary and stop

Current evidence supports workload-dependent, inconsistent quality-cost outcomes
under raw profile visibility. It does not establish that raw visibility is
universally insufficient, that Aware is causally better/worse, a crossover,
statistical stability, a cost-guided method's superiority, or scheduler placement
reversal. Final audits and cleanup pass. Stop here: no additional task, repetition,
sweep, semantic tuning or proposed method is started.
