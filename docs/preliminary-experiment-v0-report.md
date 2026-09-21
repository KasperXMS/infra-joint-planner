# Preliminary experiment v0 report

## Scope and disposition

This report closes the requested M4 preliminary experiment and stops before any M5,
method, sweep, dynamic-infrastructure, failure-injection, ablation, or 7-task baseline work.
The frozen substrate is `main@bccef0744bf9270f6d689401ad91885c7c130a28` (tag
`m4-clean-blind-substrate-bccef07`). The experiment harness was added without changing
the frozen M4 core architecture.

All 14 primary cells were attempted exactly once. There were no task retries, replacements,
or post-result prompt changes. Twelve runs completed evaluation; two runs terminated with
typed, fail-closed errors that the audit classifies as valid Planner failures rather than
system/harness confounders.

## Exact settings

The machine-readable freeze is in
[`preliminary-experiment-v0-freeze.yaml`](preliminary-experiment-v0-freeze.yaml). Important
settings are:

- Substrate: `bccef07`; harness base `c6c8333`; audited pre-run regime-key fix `a459463`.
- `n=1`; no task retry; OpenAI-compatible SDK `max_retries=0`; eight planning steps.
- A fresh, empty artifact root was used on both Workers for every primary run.
- EDGE: Jetson AGX Orin A4, `192.168.0.104`; GPU: 2×RTX 4090 workstation,
  `192.168.0.12`. Both exposed the same 12-operator M4 surface. Only GPU hosted model
  deployments.
- Text deployment: `deepseek-chat`, 64,000 context, 1,024 reserved output tokens.
- Vision deployment: local `qwen3-vl:4b-instruct` packaged as
  `qwen3-vl-prelim-32k`, temperature 0, 32,768 context, 1,024 reserved output tokens.
- `H_fast`: 100 Mbps, 0 ms added RTT. `H_constrained`: 3 Mbps, 50 ms added RTT.
  Each worker-to-worker artifact pull was held to at least
  `RTT + bytes*8/bandwidth`. Controller-to-initial-placement materialization was setup and
  excluded from task E2E and transfer totals.
- Video-MME 795-3 used a complete-timeline, question-independent derived representation:
  source AV1 SHA-256 `78c7158b...a4b9`; derived MJPEG 1 fps, 960×540, q3,
  107,430,156 bytes, SHA-256 `cbb636ce...d1f4`. It is explicitly a preliminary derived
  execution setting, not a formal Video-MME quality claim. Both scripted workflows sampled
  62 frames every 40 seconds and made one 8×8 contact sheet.
- LongBench used the M4 structured artifact unchanged: 17,071 records, 5,310,800 bytes,
  SHA-256 `008803f5...02b6`, initially on EDGE.
- MultiHop used the M4 gold-independent BM25 top-2 fixed-candidate setting, 41,221 bytes,
  SHA-256 `6749ef22...f542`, initially on EDGE. It remains a derived fixed-candidate task,
  not a full-corpus claim.
- The Blind Planner saw only logical state and emitted `AUTO`. The Naive-Aware Planner added
  only live agents/devices/capabilities, deployments, artifact locations, and link state; it
  had no estimator, routing heuristic, search, RL, dataset-specific logic, or strategy hint.
- Gold and supporting evidence remained private to the unchanged evaluators. No host,
  placement, deployment, or link state entered a `TaskContract`.

Preflight caught and resolved three issues before a benchmark attempt: the video produces
62 rather than 63 sampled frames; an 8B Qwen configuration exceeded its local GPU allocation,
so the already M4-validated 4B instruct base was frozen instead; and a hyphen/underscore
regime-key mismatch failed before run-directory creation, materialization, Worker action, or
model call. The latter is recorded in the freeze file and was fixed before A01's only task
attempt.

## Fourteen primary runs

Times are milliseconds. `P`, `W`, and `F` are Planner, Worker semantic-model, and Finalizer
model service measurements; parentheses give input/output tokens. Phase A has a deterministic
scripted Planner, so `P=0`. For the two typed failures, E2E is reconstructed from
`task.start` to `run.failed` in JSONL; no finalizer or evaluator ran.

| Run | Cell | Status | Score / format | E2E | Transfer bytes / ms | Operator ms | P ms (in/out) | W ms (in/out) | F ms (in/out) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| A01 | Video V1, fast | completed | 1 / valid | 22,143.0 | 107,430,156 / 8,603.2 | 10,523.0 | 0 | 8,221.8 (3,674/2) | 1,675.0 (6,841/1) |
| A02 | Video V1, constrained | completed | 1 / valid | 300,030.6 | 107,430,156 / 286,532.5 | 10,603.3 | 0 | 8,246.4 (3,674/2) | 1,850.4 (6,969/1) |
| A03 | Video V2, fast | completed | 1 / valid | 11,442.9 | 756,836 / 205.1 | 8,516.3 | 0 | 2,847.0 (3,674/2) | 1,636.9 (6,871/1) |
| A04 | Video V2, constrained | completed | 1 / valid | 10,992.6 | 756,836 / 2,079.4 | 6,084.7 | 0 | 461.9 (3,674/2) | 1,744.1 (6,999/1) |
| A05 | LongBench L1, fast | completed | 1 / valid | 3,374.7 | 5,310,800 / 425.5 | 912.8 | 0 | 756.1 (110/1) | 1,831.4 (1,077/1) |
| A06 | LongBench L1, constrained | completed | 1 / valid | 17,285.8 | 5,310,800 / 14,219.5 | 1,009.5 | 0 | 511.4 (111/1) | 1,367.4 (1,089/1) |
| A07 | LongBench L2, fast | completed | 1 / valid | 2,657.9 | 60 / 33.5 | 901.4 | 0 | 583.9 (110/1) | 1,370.3 (1,077/1) |
| A08 | LongBench L2, constrained | completed | 1 / valid | 2,803.8 | 60 / 59.0 | 1,052.4 | 0 | 847.7 (111/1) | 1,368.3 (1,089/1) |
| B01 | Video Blind | completed | 1 / valid | 11,670.0 | 229,455 / 663.7 | 3,656.1 | 5,243.0 (14,611/434) | 2,512.9 (1,138/173) | 856.7 (2,104/1) |
| B02 | Video Aware | valid Planner failure: `context_limit_exceeded` | — | 4,371.6 | 0 / 0 | 445.5 | 3,426.8 (8,228/340) | 0 | 0 |
| B03 | LongBench Blind | completed | 1 / valid | 9,029.4 | 304 / 92.0 | 1,208.9 | 6,306.0 (17,546/420) | 786.4 (206/69) | 718.3 (1,132/1) |
| B04 | LongBench Aware | completed | 1 / valid | 7,402.3 | 0 / 0 | 355.9 | 5,825.9 (17,213/389) | 0 | 609.1 (901/1) |
| B05 | MultiHop Blind | valid Planner failure: `validation_failed` | — | 2,685.2 | 0 / 0 | 23.0 | 2,411.6 (5,140/118) | 0 | 0 |
| B06 | MultiHop Aware | completed | 1 / valid | 6,214.9 | 41,286 / 163.9 | 1,174.9 | 4,048.4 (9,534/354) | 1,111.6 (10,741/87) | 596.7 (709/1) |

All eight Phase A answers were correct and format-valid. Every evaluated Phase B answer was
also correct and format-valid. B02 and B05 have no score because their valid Planner failures
occurred before finalization/evaluation; they are not converted to score zero and are not
silently excluded.

## Phase A: infrastructure sensitivity

| Task | Fast preference | Constrained preference | Reversal? |
|---|---|---|---|
| Video-MME 795-3 | V2: 11.443s vs V1: 22.143s (48.3% lower) | V2: 10.993s vs V1: 300.031s (96.3% lower) | No |
| LongBench structured | L2: 2.658s vs L1: 3.375s (21.2% lower) | L2: 2.804s vs L1: 17.286s (83.8% lower) | No |

The expected infrastructure effect is measurable: changing only the regime increased the
full-video transfer from 8.60s to 286.53s and the full-structured transfer from 0.43s to
14.22s, while reduced-artifact transfers remained small. Nevertheless, the minimizing
workflow did **not** change for either anchor: near-data reduction won in both regimes.
Therefore the predeclared problem-validity signal, a clear preference reversal in at least
one task, was **not established**.

No cell was expanded to `n=3`. The closest comparison, LongBench under `H_fast`, differed by
21.2%, which is outside the predeclared `<20%` trigger. The large Qwen service-latency
variation across Video cells also means the absolute Video gaps must not be treated as a
precise hardware benchmark, but it cannot reverse the constrained ordering dominated by a
286.5s transfer.

No bandwidth sweep or break-even experiment was run because no crossover was observed.

## Phase B: Blind versus Naive-Aware behavior

| Task | Blind workflow | Naive-Aware workflow | Audit |
|---|---|---|---|
| Video 795-3 | `sample_frames@AUTO(EDGE)` → `make_contact_sheet@AUTO(EDGE)` → `invoke_model@AUTO(Qwen)` → finish; 4 Planner steps, 1 Worker model call, score 1 | `sample_frames@data_local(EDGE)` → direct 16-image `invoke_model@Qwen`; 2 Planner steps, no Worker model call completed | Aware could see 32,768 context and 2,048 tokens/image but requested 16 images: estimated input 33,069 plus 1,024 reserved. Runtime correctly failed closed. |
| LongBench structured | Four reductions at EDGE → `invoke_model@AUTO(DeepSeek)` → finish; 6 steps, 1 Worker model call, score 1 | Four reductions with explicit `data_local` → finish; 5 steps, 0 Worker model calls, score 1 | Aware stopped with only artifact metadata visible; the finalizer had no artifact content. The correct D is a lucky quality outcome, not evidence of a safe stopping rule. |
| MultiHop-RAG | BM25 at EDGE → project presumed `doc_id,text,score`; 2 steps, no Worker model call completed | BM25 at EDGE (`AUTO`) → `invoke_model@DeepSeek` → finish; 3 steps, 1 Worker model call, score 1 | Blind hallucinated a nonexistent `doc_id` field and added an unnecessary projection. Aware used a viable path, although it left retrieval placement to `AUTO` rather than expressing a fully explicit joint choice. |

Physical state visibility alone did not reliably produce sensible joint planning. It helped
the Aware planner choose data-local reduction on the two media/structured tasks and enabled a
valid MultiHop path, but it did not prevent context oversubscription or metadata-only early
stopping.

## Failure-mode taxonomy

| Failure mode | Evidence | Classification |
|---|---|---|
| Wrong resource/context reasoning | B02 selected all 16 images although the visible deployment contract made the request infeasible | Clear Naive-Aware Planner failure; runtime behaved correctly |
| Premature finish | B04 finished after `select_fields` without invoking a model or exposing the 60-byte artifact content to Planner/finalizer | Clear Naive-Aware stopping failure; score 1 is not robust evidence |
| Unnecessary reduction / wrong field assumption | B05 added `select_fields` with nonexistent `doc_id` after successful BM25 | Clear Blind planning/search failure |
| Quality-cost conflict | B04 saved one model call and all transfer bytes but discarded semantic grounding | Clear behavior, outcome happened to be correct |
| Infra ignored | B06 used `AUTO` for retrieval despite visibility, but AUTO resolved data-local and caused no observed harm | Weak signal only; not counted as a clear failure |
| Wrong placement | None observed | Not supported |
| Myopic local decision | No harmful local placement observed | Not supported |
| Over-reduction | B05's projection was unnecessary and invalid | Supported through the wrong-field failure |
| Repeated verification | None observed | Not supported |

The three clear failures are non-harness failures. Operators and deployments existed;
surfaces matched; artifacts were present; bindings were explicit or deterministically
resolved; and there was no silent truncation, fallback, evaluator mismatch, finalization
defect, transfer bug, or infra/gold leakage.

## What this supports for method design

The observations support considering a method that jointly enforces:

1. hard feasibility accounting before a Planner commits to artifact sets or deployments;
2. typed artifact-schema/provenance propagation so downstream field choices are grounded;
3. evidence-sufficiency checks before finish, rather than treating produced-artifact metadata
   as semantic evidence; and
4. explicit optimization over transfer size, local operator cost, and model/context cost.

They do **not** establish that the proposed research problem already has a regime-dependent
optimal-workflow reversal, nor that an aware method improves accuracy, latency, or cost.
There is no statistical claim at `n=1`; the Video setting is derived; MultiHop is fixed-candidate;
only three development tasks and two static regimes were examined; two Phase B runs have no
quality observation; and B04's correct result may be chance. Method design should treat these
as hypotheses and failure constraints, not as final effectiveness evidence.

## Trace audit and reproducibility

Each run directory under `runs/preliminary-experiment-v0/<run_id>/` contains `setup.json`,
`trace.jsonl`, and `result.json`. The audit verified all 14 JSONL files parse, step indexes are
contiguous, parent links reconstruct one chain, the final event is `run.end` or `run.failed`,
all Blind model actions use `AUTO`, and no setup contains evaluator gold or supporting
evidence. Full SHA-256 digests are in
[`preliminary-experiment-v0-run-sha256.txt`](preliminary-experiment-v0-run-sha256.txt);
abbreviated `setup / trace / result` digests are shown below:

| Run | SHA-256 digests |
|---|---|
| A01 | `4a3c9b38...a29c4 / f0f97675...4e24f / d2feac90...c03f2` |
| A02 | `7e0f0601...98699 / 4bcd7252...2bcfd / 58574c24...d452d` |
| A03 | `641b5f7e...dd61 / 082e7665...94e13 / a258ef67...3f074` |
| A04 | `419fcd06...a99b / 361e5d34...91b5c / a36f8163...4ee5f` |
| A05 | `8f7f3662...82b0d / 4e3d4d24...63088 / 86e2b3ff...decd6` |
| A06 | `10ccf9eb...0082 / aa34cf2b...3b8e6 / 191cac68...04f5a` |
| A07 | `8ee6d0f4...7f530 / 3548ba17...b3274 / 6a272ea5...510a9` |
| A08 | `3ef916e6...05df / ac382772...bc5d6 / ab89f8ba...8bd52` |
| B01 | `d93f020c...d1297 / 6c973e21...ff38 / e1d1e049...8d847` |
| B02 | `b51aede4...2d882b / b0057343...3505 / 74868cd2...641b3` |
| B03 | `1af5814a...2dfbb / 2b206bf7...b9a99d / a299d837...f0880` |
| B04 | `a424f968...e5c13 / 8103ccbb...3c1c1 / 18cd92c9...16b2` |
| B05 | `676bce19...9499 / f93d4fa2...7ace1 / 4196b945...44b23` |
| B06 | `21ddc204...18c4 / 9609810a...272f4 / 2b860d20...0d93c` |

The experiment stops here.
