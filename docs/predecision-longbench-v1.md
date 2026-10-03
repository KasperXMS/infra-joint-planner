# LongBench-v2 pre-decision Raw-Aware v1

Updated 2026-10-03. **Twelve effective cells completed and audited; all evaluator
contracts pass. Eight answers are correct.** Excluded attempts remain immutable;
the Video block separately ends with eleven completions and one valid budget failure.

## Frozen scope and representation

Three original multi-document tasks, Fast/Slow × Blind/Aware, n=1. Fixed original
order FB -> FA -> SB -> SA; genuine-bug reruns retain this relative order.
No semantic retry, prompt/budget tuning, task replacement or proposed method.

| Task | Source task ID | Original UTF-8 bytes | Record bytes / chunks | Documents / initial placement |
| --- | --- | ---: | --- | --- |
| Financial | 66f7c780bb02136c067c35e8 | 1033800 | 1081150 / 344 | 4 / A4, A5, A28, A5 |
| Academic | 66f2c44e821e116aacb2b826 | 494456 | 514789 / 164 | 2 / A4, A5 |
| News | 66faa8efbb02136c067c7357 | 228792 | 242295 / 77 | 2 / A4, A5 |

Natural document boundaries and ordered chunks reconstruct every original source
character; source/reconstruction SHA equality is frozen. Original question,
choices, private gold and exact-choice evaluator are unchanged. No task strategy
or supporting evidence is supplied. See the [protocol](predecision-crossbenchmark-v1-protocol.md).

Cloud Manager and always-Blind Verifier: `qwen3.8-max`; SDK-native Manager plus
bounded specialists, same B0 locality scheduler and finite generic tools.
Budgets: 20 Manager / 64 physical calls / 20 Verifier, specialists 8 turns /
4 created / 2 active. Physical context 32768, output ceiling 2048. Actual metadata
reports `qwen35`, 27.3B, Q4_K_M under alias `qwen3.8-27b-v1`, not independent
proof of release branding. **Every completed physical inference selected A28**;
the available dual-4090 device is not an observed placement reversal.

Fast: 100 Mbps + configured 5 ms; Slow: 3 Mbps + configured 50 ms. Jetsons use
HTB without netem, so configured delay is not measured symmetric RTT. Cloud/SSH
are unshaped. Data bodies stay on remote nodes; PC receives bounded metadata only.

## Effective matrix

All rows completed, format-valid, terminal-provenance-valid and evaluated.
Action bytes mean artifact payload, not measured wire bytes. Initial placement
is separately reported and included in E2E. Times are seconds; service/work sums
are non-additive and must not be added into a wall-time partition.

| Task / condition | Answer / score | E2E | Initial placement | Action bytes / transfer | Model service | Manager / Verifier / specialist turns |
| --- | --- | ---: | ---: | --- | ---: | --- |
| Financial FB | A / 0 | 406.653 | 0.387 | 265938 / 3.760 | 113.943 | 20 / 20 / 8 |
| Financial FA, isolation patch | C / 1 | 1282.028 | 0.398 | 573058 / 1.264 | 1106.980 | 14 / 14 / 8 |
| Financial SB | A / 0 | 278.919 | 3.314 | 141047 / 2.150 | 51.549 | 14 / 14 / 8 |
| Financial SA, transport patch | A / 0 | 251.831 | 3.598 | 486432 / 1.912 | 96.379 | 11 / 11 / 0 |
| Academic FB | C / 1 | 126.426 | 0.165 | 63102 / 0.818 | 10.947 | 9 / 9 / 8 |
| Academic FA | C / 1 | 175.840 | 0.422 | 243055 / 0.630 | 126.845 | 6 / 6 / 0 |
| Academic SB | C / 1 | 176.759 | 1.642 | 25132 / 0.402 | 103.752 | 11 / 11 / 0 |
| Academic SA | C / 1 | 156.410 | 1.604 | 18921 / 0.241 | 83.875 | 11 / 11 / 0 |
| News FB | C / 1 | 600.051 | 0.146 | 107471 / 1.652 | 449.079 | 14 / 14 / 8 |
| News FA, isolation patch | C / 1 | 713.826 | 0.083 | 99354 / 0.948 | 530.521 | 16 / 16 / 8 |
| News SB | C / 1 | 507.576 | 0.789 | 191727 / 0.945 | 455.067 | 13 / 13 / 15 |
| News SA | A / 0 | 189.024 | 0.827 | 19112 / 0.220 | 103.674 | 9 / 9 / 0 |

Within this selected set only: Blind 4/6 and Aware 4/6 correct; all 12 execution
completions are valid. This is not official benchmark accuracy or a significance
test. No scores are pooled with other benchmarks.

## Workflow and information movement

BM = BM25; AG = aggregation; RD = read; RED = top-k/projection. Counts describe
actual prepared actions; unsuccessful argument/phase calls need not grow a node.
Model attempts include context rejections and are **not** inference counts.

| Task / condition | First action | BM / AG / RD / RED | Model attempts / inference / context | Graph N/E | Created specialists | Peak actions / overlap s | Terminal artifact / prompt bytes |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| Financial FB | four parallel BM | 20 / 5 / 5 / 4 | 6 / 2 / 4 | 40/63 | 1 | 4 / 3.110 | 9765 / 781 |
| Financial FA | AG | 10 / 2 / 0 / 0 | 8 / 5 / 3 | 20/28 | 1 | 3 / 0.477 | 6572 / 1289 |
| Financial SB | BM | 16 / 4 / 0 / 1 | 5 / 1 / 4 | 26/29 | 1 | 4 / 1.198 | 9604 / 3076 |
| Financial SA | AG | 5 / 2 / 0 / 0 | 4 / 1 / 3 | 11/13 | 0 | 3 / 0.699 | 15938 / 1310 |
| Academic FB | BM | 7 / 1 / 4 / 0 | 2 / 1 / 1 | 14/13 | 1 | 1 / 0 | 0 / 2117 |
| Academic FA | AG | 2 / 1 / 0 / 0 | 2 / 1 / 1 | 5/4 | 0 | 1 / 0 | 25497 / 1047 |
| Academic SB | BM | 6 / 0 / 0 / 0 | 3 / 1 / 2 | 9/6 | 0 | 1 / 0 | 25132 / 933 |
| Academic SA | BM | 6 / 0 / 0 / 0 | 3 / 1 / 2 | 9/6 | 0 | 1 / 0 | 18921 / 859 |
| News FB | BM | 14 / 2 / 0 / 0 | 8 / 5 / 3 | 24/26 | 1 | 2 / 3.052 | 19 / 1865 |
| News FA | BM | 11 / 1 / 0 / 0 | 9 / 5 / 4 | 21/25 | 1 | 1 / 0 | 1174 / 1140 |
| News SB | AG | 14 / 3 / 2 / 0 | 7 / 4 / 3 | 26/31 | 4 | 4 / 111.120 | 0 / 1343 |
| News SA | RD | 6 / 0 / 1 / 0 | 3 / 1 / 2 | 10/6 | 0 | 2 / 1.355 | 19112 / 1747 |

Seven cells naturally create specialists; five remain single-Manager. No topology
is forced. Terminal artifact bytes alone are not a total-context/reduction metric:
zero-input artifact calls can carry evidence in their prompt, and upstream
analyses can contain more information than the final note size.

Financial FA: full four-document aggregation -> context rejection -> retrieval
and one Blind `verify_option_a` specialist -> four explicit per-option model
notes (669/1588/3602/713 bytes) -> terminal C. This is purposeful decomposition,
not four identical repeated verifications. All five real calls stop normally,
29605 input / 1968 output tokens. E2E is 215% greater and traffic 115% greater than
FB while quality improves from wrong to correct. About 86% of E2E is model service;
this is a quality-cost trade-off, not a system-latency win.

Academic Aware changes from Fast aggregation to Slow local BM25. Slow Aware
versus Slow Blind: 24.7% fewer action bytes, 11.5% lower E2E, same correct answer.
This is the most useful observed quality-preserving cost signal, but n=1 is not
proof of causal or stable infrastructure adaptation. Fast Aware takes 39.1%
longer than Fast Blind despite the same quality.

News FA: BM25 plus one Blind `sanofi-analyst`; context recovery and four explicit
bounded model notes (412/151/298/313 bytes), then terminal C. Five normal-stop
inferences, 23936 input / 359 output tokens. Versus FB: 7.6% fewer transferred
bytes, but 19.0% longer E2E, both correct. Slow Aware uses only one inference and
much less traffic than Slow Blind, but answers incorrectly; it is cheaper, not a
quality-preserving benefit.

## Cost decomposition

| Task / condition | Manager / specialist / Verifier work s | Operator work s | Model input / output tokens |
| --- | --- | ---: | --- |
| Financial FB | 163.616 / 31.116 / 88.344 | 1.220 | 5217 / 4 |
| Financial FA | 89.938 / 24.451 / 53.292 | 1.133 | 29605 / 1968 |
| Financial SB | 114.288 / 39.624 / 59.527 | 2.214 | 2911 / 2 |
| Financial SA | 93.553 / 0 / 47.222 | 1.750 | 4105 / 2 |
| Academic FB | 45.807 / 23.778 / 41.113 | 0.465 | 472 / 2 |
| Academic FA | 27.541 / 0 / 18.105 | 0.216 | 7335 / 2 |
| Academic SB | 35.849 / 0 / 30.455 | 0.904 | 6015 / 2 |
| Academic SA | 30.907 / 0 / 33.058 | 0.883 | 4818 / 2 |
| News FB | 60.914 / 26.026 / 54.215 | 3.059 | 25583 / 14 |
| News FA | 77.285 / 30.068 / 67.460 | 0.769 | 23936 / 359 |
| News SB | 84.473 / 50.226 / 44.655 | 2.243 | 12342 / 412 |
| News SA | 49.800 / 0 / 29.645 | 0.628 | 6014 / 2 |

The 0.24–3.76 s action-transfer work is small relative to model/cloud reasoning.
Network-class reduction alone therefore cannot predict E2E. Parallel overlap is
measured, not a proven speedup against a matched sequential workflow. Unknown
service profiles, pure operator compute, idle and other harness decomposition
remain unknown; no guessed values or predicted-critical-path claim is introduced.

## Failure audit and validity

Four effective wrong answers: Financial FB/SB/SA and News SA. Primary category is
evidence selection/interpretation and synthesis; context/argument/readiness
recovery is secondary. The available trace does not isolate evidence omission
from reasoning error. Completion at a turn ceiling does not itself imply budget
exhaustion. These valid semantic outcomes are retained without tuning.

Context rejects use the frozen conservative UTF-8-byte-as-token upper bound,
not the actual backend tokenizer. Prompt plus artifacts plus reserved2048 must
fit32768. These are static conservative-envelope refusals before transfer and
inference, not evidence of actual model-capacity/OOM or dynamic availability
failure. No estimator, capability or recovery strategy is changed in this audit.

Historical Financial SA primary and its identical operational replacement had
observer transport incidents; Financial FA and News FA originals had specialist
profile leakage. Preserve and exclude them. Transport and recipient-isolation
repairs are separately frozen; only affected cells are rerun. Original files are
not rewritten. [Failure audit](predecision-crossbenchmark-failure-audit-v1.md)
and [privacy incident](predecision-specialist-profile-isolation-hard-stop-v1.md)
retain the chronology.

All 12 effective traces have valid parent chains, terminal provenance, evaluator,
provenance/privacy gates and zero observer errors. All 48 distinct store roots
were initially empty; actual size/SHA and stored metadata now verify **256 artifact
replicas**, remotely, without sending bodies through the PC. Models' blob,
template, parameters and metadata remain identical on A28 and strong-4090.

## Authoritative evidence

Root: `/home/super/xiaoming/predecision-crossbenchmark-v1-3c3bd95`.
Execution revisions retain the original, transport and isolation provenance;
latest runtime freeze `3c3bd95`, harness SHA
`444db21f3d7aa0db13af993854e77318a29bddee1aee438f27d4a4f7c25affbf`.

- `audit-final-001.json`:24/24 effective new cells;23 completed and one budget failure.
- `longbench-twelve-effective-cell-audit-002.json`:
  `795b53345e838d7660d5f361e2523dd905d86c7342c238fda2c8c9ce06839d64`.
  Revision 002 corrects a read-only projection field name, not formal evidence.
- `longbench-actual-artifact-store-hash-audit-001.json`:
  `e1f8f8b2aeacf5b1568df49d6edf0393ea3fcfe232d86a373df98b1c8e43e2a2`.
- Financial FA deep audit:
  `757ebdfa72a5f2958057f1b35947994b4040b18227651326d72a6f2661d16371`.
- News FA deep audit:
  `eb0739f479f11a387a03e57aad083d58cb0fb30c32d21224591a98c26c6fdf07`.
- Physical model parity audit:
  `682ed9a2121d466f35edffc59b69a557aa37d4e275562242904015c9d004c4d1`.

Full trace/results, graph snapshots, requests, private evaluator/source material,
store roots and tc attestations remain on remote nodes. Historical report versions
remain in Git. No method or extra repetitions are started. Fixed order, persistent
Ollama/cache state, stochastic reasoning and n=1 limit causal/stability claims.
