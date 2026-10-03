# Video-MME pre-decision Raw-Aware v1

Updated 2026-10-03. **Eleven effective cells admitted; 795-2 Slow-Aware
isolation-patch-1 is live.** Do not count the interrupted original as a semantic
failure. Current report supersedes older progress snapshots; Git and remote
evidence retain the entire chronology.

## Scope and benchmark-faithful representation

Three distinct original questions on **two**, not three, independent videos.
Fast/Slow × Blind/Aware, n=1; original questions, choices and private gold/evaluator.
No smoke MJPEG, offline question-conditioned sampling or strategy hints.
Initial artifact is one intact original AV1+Opus 1280×720 MP4 on A4 per cell.

| Questions | Video / duration | Original bytes | SHA-256 |
| --- | --- | ---: | --- |
| 795-3 / 795-2 | D97vMwfWxvI / 2495.121 s | 282442048 | 78c7158b4ea8a29a418f84cabe77caf0a35fb0f5416c8c1592fe781b5783a4b9 |
| 848-1 | gHXaUDx7P0Y / 2037.781 s | 160083738 | 41e26da8531c00b4ec39f03333b3f94637ec8b3ff94bc46ed2e1d01c1a38b641 |

Runtime sampling/sheet outputs are lossy evidence, explicitly not information-
equivalent substitutes for the original video. The Agent chooses cadence,
selection and sheets. FFmpeg fps sampling with max_frames is capped cadence,
**not uniform full-timeline coverage**. Thirty-two frames at 5 s span a nominal
155 s prefix; 10 s spans 310 s. Original source PTS and decisive evidence-pixel
presence are not independently established by these traces.

Cloud Manager/always-Blind Verifier `qwen3.8-max`; SDK-native loop, bounded
specialists-as-tools; same finite tools and B0 physical locality scheduler.
20/64/20 budgets; local model metadata `qwen35`, 27.3B Q4_K_M, alias
`qwen3.8-27b-v1`, context32768/output2048. All completed physical inference is
A28, sample/sheet execution A4: no model-device reversal. Resource-Blind logical
recipients see static capability only; Aware root Manager receives a fresh
anonymous profile per reasoning call. Specialists and Verifier remain Blind.

Fast100Mbps/config5ms; Slow3Mbps/config50ms. Jetsons HTB without netem,
4090 HTB+netem; configured delay is not measured symmetric RTT. Cloud/SSH
unshaped. Fresh Worker processes and stores, native model servers reused.
No data bodies through development PC. See [protocol](predecision-crossbenchmark-v1-protocol.md).

## Effective matrix

Every admitted row completes with canonical terminal choice, valid successful-
model provenance and original evaluator. Action bytes exclude mandatory initial
materialization, which is included in E2E. Times seconds. No quality pooling.

| Task / condition | Answer / score | E2E | Initial placement | Action bytes / transfer | Manager / Verifier | Model attempts / inference / context | Graph N/E |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| 795-3 FB | B / 0 | 185.443 | 26.066 | 581538 / 0.813 | 5 / 5 | 2 / 1 / 1 | 3/20 |
| 795-3 FA | A / 1 | 252.371 | 24.539 | 1230240 / 1.908 | 3 / 3 | 1 / 1 / 0 | 2/8 |
| 795-3 SB | A / 1 | 1069.965 | 788.892 | 1562096 / 5.508 | 3 / 3 | 1 / 1 / 0 | 2/10 |
| 795-3 SA | A / 1 | 1071.594 | 788.481 | 1471756 / 5.507 | 3 / 3 | 1 / 1 / 0 | 2/10 |
| 848-1 FB | B / 0 | 442.512 | 13.921 | 798787 / 1.429 | 6 / 6 | 2 / 1 / 1 | 3/27 |
| 848-1 FA | A / 0 | 226.982 | 13.973 | 380788 / 0.287 | 6 / 6 | 2 / 1 / 1 | 4/63 |
| 848-1 SB | A / 0 | 871.266 | 446.971 | 981232 / 3.885 | 4 / 4 | 1 / 1 / 0 | 2/12 |
| 848-1 SA | A / 0 | 711.029 | 446.992 | 409154 / 2.031 | 6 / 6 | 2 / 1 / 1 | 7/68 |
| 795-2 FB, backend patch | C / 1 | 692.487 | 25.471 | 391212 / 0.170 | 8 / 8 | 2 / 1 / 1 | 7/68 |
| 795-2 FA | B / 0 | 1009.582 | 24.504 | 742651 / 0.982 | 10 / 10 | 3 / 2 / 1 | 13/104 |
| 795-2 SB | B / 0 | 1170.017 | 788.482 | 915054 / 4.172 | 5 / 5 | 2 / 1 / 1 | 3/43 |
| 795-2 SA, isolation patch | pending | pending | pending | pending | pending | pending | pending |

## Real workflow differences

| Task / condition | Sampling | Successful model evidence / information flow | Ready-action parallelism |
| --- | --- | --- | --- |
| 795-3 FB | 32 at 5 s | 16-image request rejected -> first four images | none |
| 795-3 FA | 32 at 5 s | first eight images | none |
| 795-3 SB | 32 at 5 s | first ten images | none |
| 795-3 SA | 32 at 10 s | first ten images | none |
| 848-1 FB | 31 at 64 s | 16 selected images rejected -> eleven spread frames | none |
| 848-1 FA | 31 at 65 s | 31-image request rejected -> one sheet of all31 | none |
| 848-1 SB | 31 at 64 s | twelve spread frames | none |
| 848-1 SA | 32 at 60 s | 32-image request rejected -> four eight-frame sheets | peak4 / 1.421 s overlap |
| 795-2 FB | 32 at 75 s | 32-image request rejected -> four eight-frame sheets | peak3 / 0.428 s |
| 795-2 FA | 32 at 10 s, then32 at 77 s | four sheets -> length-ended analysis -> four later sheets -> wrong choice | peak4 / 0.940 s |
| 795-2 SB | 32 at 30 s | 32-image request rejected -> eleven individual frames | none |
| 795-2 SA | live: 32 at 10 s | 16-image rejection -> four sequential eight-image analyses; final pending | pending |

All eleven admitted workflows are single-Manager; no forced multi-agent topology.
Handoffs and graph edges are execution-grown artifact information flow, not a
predicted whole-plan DAG. Many fan-out edges are frame producer-consumer lineage,
not parallel reasoning agents. Same-owner ready independent sheets truly overlap;
no implicit same-turn dependency reordering is observed.

795-3 Slow Aware reduces action bytes 5.8% versus Slow Blind but E2E is essentially
equal, both correct. Roughly 789 s fixed initial placement dominates both Slow
cells; this is not a savings achieved by the Agent. Fast Aware improves wrong
to correct but adds model work and traffic. No universal cost/quality win.

848-1 Aware's compact sheets reduce Fast bytes52.3%/E2E48.7% and Slow
bytes58.3%/E2E18.4% versus matched Blind. **All answers are wrong**; quality-qualified
benefit is not established. Inference latency drops from about260–284 s on
individual images to58–61 s on sheets, whereas transfer time is only seconds.
Visibility is not proven to cause those representation choices with n=1.

795-2 FB is correct with four sheets, FA/SB wrong. FA's first analysis explicitly
ends at output limit2048 after664.541 s, then the Manager naturally widens cadence
10 -> 77 s and performs another inference. Recovery does not restore quality;
versus FB it adds45.8%E2E and89.8%bytes. Intermediate output-limit saturation is
visible, not silent input truncation. The trace does not prove missing decisive
evidence versus interpretation/synthesis failure. Final SA remains unclassified.

## Cost decomposition

Work sums are non-additive under parallelism, not an E2E partition. Prompt bytes
and actual image-token usage matter; JPEG byte reduction is not itself preserved
visual information or proportional token reduction.

| Task / condition | Model service | Manager / Verifier work | Decode/operator work | Actual input / output tokens | Terminal artifact / prompt bytes |
| --- | ---: | --- | ---: | --- | --- |
| 795-3 FB | 96.867 | 34.884 / 17.086 | 8.585 | 3871 / 2 | 581538 / 685 |
| 795-3 FA | 189.143 | 18.052 / 9.028 | 8.700 | 7562 / 2 | 1230240 / 585 |
| 795-3 SB | 236.090 | 20.191 / 9.130 | 8.696 | 9429 / 2 | 1562096 / 670 |
| 795-3 SA | 235.830 | 17.058 / 8.474 | 14.637 | 9402 / 2 | 1471756 / 520 |
| 848-1 FB | 259.739 | 72.368 / 20.477 | 73.009 | 10377 / 2 | 798787 / 671 |
| 848-1 FA | 57.891 | 59.144 / 19.791 | 74.411 | 2113 / 2 | 380788 / 1001 |
| 848-1 SB | 283.732 | 49.939 / 12.344 | 73.003 | 11349 / 2 | 981232 / 902 |
| 848-1 SA | 60.720 | 94.236 / 30.560 | 72.109 | 2728 / 2 | 409154 / 2402 |
| 795-2 FB | 441.516 | 94.105 / 30.850 | 99.722 | 2290 / 1208 | 391212 / 1379 |
| 795-2 FA | 717.318 | 103.154 / 43.871 | 117.729 | 4579 / 2050 | 362463 / 1361 |
| 795-2 SB | 260.527 | 57.331 / 16.422 | 40.646 | 10398 / 3 | 915054 / 778 |

Unknown service/predicted critical-path profiles stay unknown. Fixed source
transfer consumes 25–26 s Fast and~789 s Slow for795,~14/~447 s for848.
Do not hide these payloads in the much smaller action bytes or attribute them
to workflow adaptation. Pure operator compute/idle/harness partition is unknown.

## Semantic failures and system exclusions

Wrong canonical choices in admitted cells are valid visual evidence/temporal
interpretation or synthesis failures. Conservative static image context refusals
are visible recovery events, not proof of deployment unavailability/OOM.
Verifier readiness after sampling can limit further evidence expansion; it is a
frozen Agent/Verifier behavior, not a newly repaired code bug.

The original795-2 FB's hidden backend retry/read-deadline defect is excluded and
repaired once under `5dafc43`. Original795-2 SA was interrupted at privacy
hard-stop and separately recorded; no evaluator/normal result exists.
Recipient-isolation `3c3bd95` reruns only that affected Video cell once.
No task, representation, sample policy, prompt, Verifier, operator, budget,
scheduler or model requirement is tuned. See
[failure audit](predecision-crossbenchmark-failure-audit-v1.md).

Historical FA sheet integrity checks verify all eight JPEG sheets on A4/A28,
dimensions1280×360 and exact content hashes, totaling742651 transferred bytes.
This rules out observed copy corruption, not lossy evidence omission.

## Evidence and claim boundary

Remote root: `/home/super/xiaoming/predecision-crossbenchmark-v1-3c3bd95`,
merged `audit-progress-003.json`:11/12 effective Video cells.
Full traces, graph snapshots, canonical terminal/evaluator provenance, requests,
store states and tc attestations remain remote. No pixels/video bodies on PC.
Old source/request/deep audits remain under earlier roots; hashes in Git history.

Final full-family SHA/recipient-context/request-count/cleanup checks await the
one live cell. Do not declare 12/12 from a launch or analyze its quality before
its evaluator returns. No additional experiment follows family completion.
These n=1 observations cannot establish stable causal visibility benefits,
a generic Slow -> Reduce heuristic or official full-benchmark quality.
