# B/D/E cost-guidance follow-up v1

2026-10-04. **18/18 primary cells completed, format-valid and evaluated; all
retained after admission and private coverage audit.** No additional cells are
scheduled. B/D's novel interfaces were largely unused; E reproduced a concrete
evidence-selection/quality-cost failure. No route is promoted as a proven method.

## What was implemented and frozen

This follows the user's request to test B/D/E, rather than treating their absence
from the earlier A/C study as evidence against them. The prospective protocol is
[cost-guidance-bde-protocol-v1.md](cost-guidance-bde-protocol-v1.md).

- **B:** optional `estimate_<operator>` ready-action consequence cards; ordinary
  execution remains direct, with no mandatory quote/commit turn.
- **D:** single-use quotes plus `compare_ready_actions` for 1–3 Agent-proposed
  ready alternatives. Costs are advisory; the system does not select an optimum.
- **E:** B plus six advisory rules distilled in one offline meta-agent call from
  independently audited cost-only historical traces. No training or weight update.

All three retain A's measured spent-cost ledger in effective Manager input. Zero
optional queries therefore means B exercised **ledger feedback without querying
prospective costs**, not that it received no cost feedback at all. D retains C's
mandatory single-action quote/commit path alongside optional comparison.

Execution revision: `17b8bf048ced8a03358c55ef143b34712d8ea99c`. Audit/resumption
code was added in `d275d8c`, without changing frozen execution components. Original
SDK-native runtime SHA-256 remains
`b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985`.

The new matrix is **3 existing tasks × Fast/Slow × B/D/E = 18 cells**, n=1,
no retry/replacement/prompt tuning. Fixed order: MultiHop, Academic, Video; for each
task Fast B/D/E, then Slow B/D/E. Earlier A/C 16 cells remain historical controls;
the combined reservation count is 34/36, with no remaining slots scheduled.

All methods share the unchanged native Manager/specialists, Blind Verifier,
benchmark/evaluator/representation/placement, finite operators, B0 minimum-input-
movement scheduler, Worker/runtime, 32K/2048 deployments and 1200s service timeout.
Manager is `qwen3.8-max`. Budgets: 20 Manager turns, 64 physical calls, 20 Verifier
calls; 8 specialist turns, 4 created/2 active specialists. Only the root Manager
receives method feedback; specialists and Verifier remain Blind. These cost-guided
variants are not the original resource-blind baseline.

Four fresh isolated Worker stores are used for every cell. Devices are A4/A5/A28
Jetsons and strong-4090. Fast is 100 Mbps/configured added delay 5 ms; Slow is
3 Mbps/configured added delay 50 ms. Existing tc implementation is reused:
Jetsons support HTB but not netem; 4090 applies HTB+netem. The delay setting is
not a guarantee of measured symmetric RTT. Neither scheduler nor physical placement
policy was tuned. Experiment cells execute serially because tc, Workers and models
are shared. Code/test work runs independently on the development PC.

Datasets, artifact bodies, raw traces and evaluator-private annotations never pass
through the development PC. Evidence root on 4090:
`/home/super/xiaoming/cost-guidance-exploration-v1-bde-17b8bf0`.

## E provenance and limits

The single meta-agent call used `qwen3.8-max`: 42.818 s, 18,718 input and 2,011
output tokens. Sources were historical Financial/News LongBench and Video 795-3,
excluding all three evaluation tasks. Input contained only allowlisted numeric
costs, operator sequence/cardinality and typed failures: no query, artifact text,
answer, gold, evaluator score or physical identity. Quality was explicitly unknown.

Rules content SHA-256:
`6b2152aaf9c3e1ba90deacd4031bddc8870e0ac01e32c72be68fb24dc0b43be9`.
History SHA-256:
`693f26bc8855f1712e22607e98ca4bc0571027e51d9db247dfe8f0012d3c392b`.

The six principles advise avoiding large pre-reduction aggregation, redundant
retrieval, very large inference inputs, wasted high-cardinality sampling and
cascading failures, and considering field filtering before aggregation. They retain
support/counterexample IDs, scope and overfit warnings. These receipts establish
provenance, **not causal or semantic validity** of a rule. In particular, a cited
counterexample can still contain context failures; cost-only traces cannot certify
quality-preserving reduction. This is an Enum/GRPO-related in-context heuristic
variant, not novel RL or a learned quality-constrained policy.

## Primary-cell results

E2E includes initial materialization/placement. `Bytes` and `Xfer s` below are
action-induced transfer only. `M/S` counts metered Manager/specialist reasoning
calls. `P/I` counts prepared physical actions / completed physical model inferences;
preflight-rejected model attempts are not inference. Service/operator times are
work sums, not additive E2E components. All shown cells completed normally with
valid terminal format and the original evaluator invoked.

| Task | H | Method | Score | E2E s | Bytes | Xfer s | Model s | Operator s | M/S | P/I |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MultiHop | Fast | B | 1 | 180.825 | 5,204,596 | 1.714 | 107.668 | 4.066 | 9/0 | 7/1 |
| MultiHop | Fast | D | 1 | 167.195 | 5,204,596 | 1.619 | 125.550 | 2.119 | 9/0 | 4/1 |
| MultiHop | Fast | E | 1 | 112.256 | 57,351 | 0.200 | 5.531 | 2.819 | 7/8 | 16/1 |
| MultiHop | Slow | B | 1 | 92.751 | 5,204,596 | 14.776 | 7.649 | 3.921 | 5/0 | 6/1 |
| MultiHop | Slow | D | 1 | 1,076.493 | 5,204,596 | 15.454 | 943.976 | 2.152 | 17/0 | 6/3 |
| MultiHop | Slow | E | 0 | 204.181 | 27,774 | 0.545 | 125.370 | 2.410 | 5/0 | 8/1 |
| Academic | Fast | B | 1 | 183.716 | 243,116 | 0.481 | 117.804 | 0.335 | 9/0 | 7/1 |
| Academic | Fast | D | 1 | 122.420 | 217,558 | 0.068 | 6.092 | 0.101 | 14/0 | 3/1 |
| Academic | Fast | E | 1 | 168.496 | 226,963 | 1.314 | 44.362 | 1.894 | 9/4 | 15/1 |
| Academic | Slow | B | 1 | 136.573 | 226,984 | 0.836 | 44.437 | 0.755 | 10/0 | 9/1 |
| Academic | Slow | D | 1 | 132.298 | 0 | 0.000 | 5.660 | 0.219 | 20/0 | 3/1 |
| Academic | Slow | E | 1 | 164.601 | 25,439 | 0.811 | 118.741 | 0.521 | 4/0 | 6/1 |
| Video 848-1 | Fast | B | 0 | 731.159 | 983,606 | 1.440 | 508.761 | 141.481 | 5/0 | 4/1 |
| Video 848-1 | Fast | D | 0 | 355.125 | 585,789 | 0.291 | 191.786 | 70.841 | 8/0 | 2/1 |
| Video 848-1 | Fast | E | 0 | 418.404 | 761,039 | 0.389 | 262.414 | 71.458 | 4/0 | 3/1 |
| Video 848-1 | Slow | B | 0 | 852.065 | 761,039 | 3.767 | 264.321 | 70.953 | 4/0 | 3/1 |
| Video 848-1 | Slow | D | 0 | 819.053 | 585,789 | 2.864 | 191.476 | 70.843 | 9/0 | 2/1 |
| Video 848-1 | Slow | E | 0 | 799.874 | 604,893 | 2.958 | 213.541 | 70.133 | 5/0 | 3/1 |

Initial bytes are fixed per task: MultiHop **7,696,522**, Academic **514,789**,
Video **160,083,738**. Video Slow B alone spends **446.976 s** on initial movement;
that occurs before the Manager can adapt. An action-byte reduction must not be
reported as a corresponding reduction of total experiment traffic.

Additional telemetry: `V` is Verifier calls, `MA` prepared model attempts, tokens
are from completed physical inference only, `N/E` action nodes/information-flow
edges, and overlap is the union of simultaneous physical-action intervals.
All **20 completed physical inferences** have `finish_reason=stop`. Manager/
specialist provider usage and latency are separately retained in the full audit;
absent provider usage remains unknown, not a measured zero.

| Task / H / method | V | MA | Model input/output tokens | N/E | Max physical parallelism | Overlap s |
|---|---:|---:|---:|---:|---:|---:|
| MultiHop Fast B | 9 | 2 | 4853/2 | 7/8 | 1 | 0 |
| MultiHop Fast D | 4 | 1 | 7255/2 | 4/4 | 1 | 0 |
| MultiHop Fast E | 7 | 4 | 134/2 | 16/20 | 6 | 0.765 |
| MultiHop Slow B | 5 | 1 | 272/2 | 6/4 | 2 | 1.304 |
| MultiHop Slow D | 7 | 3 | 17425/1925 | 6/6 | 1 | 0 |
| MultiHop Slow E | 5 | 2 | 7260/2 | 8/8 | 3 | 2.141 |
| Academic Fast B | 8 | 3 | 6793/2 | 7/6 | 1 | 0 |
| Academic Fast D | 4 | 1 | 194/2 | 3/1 | 1 | 0 |
| Academic Fast E | 9 | 3 | 2475/2 | 15/20 | 4 | 1.015 |
| Academic Slow B | 10 | 3 | 2478/2 | 9/11 | 3 | 1.455 |
| Academic Slow D | 4 | 1 | 152/2 | 3/0 | 1 | 0 |
| Academic Slow E | 4 | 2 | 6839/2 | 6/4 | 2 | 0.946 |
| Video Fast B | 5 | 2 | 12262/540 | 4/45 | 1 | 0 |
| Video Fast D | 3 | 1 | 7674/3 | 2/8 | 1 | 0 |
| Video Fast E | 4 | 2 | 10493/2 | 3/43 | 1 | 0 |
| Video Slow B | 4 | 2 | 10587/2 | 3/43 | 1 | 0 |
| Video Slow D | 3 | 1 | 7707/2 | 2/8 | 1 | 0 |
| Video Slow E | 5 | 2 | 8559/2 | 3/25 | 1 | 0 |

## Observations, not promotion claims

**Interface use.** Across all 18 cells, B/E returned zero valid optional
cards. B Academic Fast attempted `estimate_invoke_model` once, but semantic
validation rejected it. Query attempts are counted separately from valid cards
and matched execution. Exact SDK call receipts are deduplicated across replayed
effective inputs and are a lower bound if a final call has no later model input.
D created **30** quotes across its six finished cells: all 30 are present in exact
effective Manager input; **20** were visible before selection and matched actual
execution. Only one
`compare_ready_actions` call occurred, with **one candidate**, not a real comparison.
Thus B's optional-query and D's multi-candidate selection mechanisms have integration
coverage, but essentially no live adoption yet. Under-use is retained, not repaired
with prompt tuning. The frozen Manager instructions do not explicitly define a
cost-minimization objective, which limits interpretation of optional tool adoption.

**Control overhead and repeated work.** D MultiHop Slow used three successful
inferences of 479.152, 424.391 and 40.434 s, all normal `stop`, not timeout/OOM.
Model service sums to 943.976 s of 1,076.493 s E2E. D Academic Slow uses 20 Manager
calls and about 107.301 s Manager work for 5.660 s model service. A cost interface
can leave excessive analysis intact and/or shift cost into the control plane.

**Quality-cost conflict.** E MultiHop Slow reduces action movement from B's
5,204,596 to 27,774 bytes (99.47%) but score drops from 1 to 0, and E2E rises from
92.751 to 204.181 s. The post-queue private audit confirms both supporting documents
were retrieved on shard 3, but after an all-six-artifact context reject the terminal
model consumes only the shard-1 pair, which contains neither supporting document.
Primary cause: **workflow composition/evidence selection**, with static-context
misuse/recovery and premature acceptance as contributing factors. This reproduces
the old C pattern; the physical substrate did not lose the retrieved artifacts.
No private audit findings are fed into an Agent.

E MultiHop Fast's score 1 and 57,351 action bytes are interesting single-run numbers,
but its successful terminal inference has no artifact inputs and only 134 actual
input tokens. Its trajectory also
has three context failures and an eight-turn specialist, so E does not universally
eliminate wasted work. Earlier retrieval/read activity can inform a Manager's
prompt: absence of direct terminal artifact inputs or literal fact matches is not
proof that no paraphrased evidence reached it. It does mean this cell is not a clean
demonstration of a quality-preserving evidence-reduction artifact handoff.

**Grounding caveat.** D Academic Fast/Slow terminal model actions have no artifact
inputs, with actual input token counts 194/152. Score 1 therefore does not establish
that the terminal model consumed a reduced evidence artifact. Evidence embedded
in a prompt must be distinguished from an explicit artifact handoff.

**Video.** Each completed Video cell has valid format but score 0. Costs and
sampling/model inputs differ; shorter execution does not resolve visual/evidence
quality. Do not infer the exact missed video segment from a gold choice label.

**Profiles.** Unknown model profiles remain unknown. On D MultiHop Slow the
large-context empirical bucket predicts p50 177.817 s/p90 320.140 s, while the two
large inferences take 479.152/424.391 s. The model/service bucket is too coarse to
predict repeated-work cost accurately; current cache/queue effects are not modeled.
Configured transfer serialization is not measured transfer latency. Artifact DAG
critical paths/overlap are not full reasoning/Verifier/control-plane critical paths.
The ready-action estimator does not predict a complete future-workflow critical
path or total cost; those forecasts remain unknown, not a reconstructed hindsight
forecast. Actual E2E and action/control intervals remain reconstructable in trace.

D's 20 matched execution receipts have exact transfer-byte predictions (all byte
errors zero). Eight matched model receipts include six empirically supported
profiles and two unknowns. Examples of model p50 prediction versus actual service:

| Action class / run | Predicted p50 s | Actual s |
|---|---:|---:|
| MultiHop Fast D terminal | 177.817 | 125.550 |
| MultiHop Slow D analysis 1 | 177.817 | 479.152 |
| MultiHop Slow D analysis 2 | 177.817 | 424.391 |
| MultiHop Slow D terminal | 87.217 | 40.434 |
| Academic Fast D terminal | unknown | 6.092 |
| Academic Slow D terminal | unknown | 5.660 |
| Video Fast D terminal | 274.468 | 191.786 |
| Video Slow D terminal | 274.468 | 191.476 |

These are contemporaneously quoted predictions, not a hindsight refit. Exact byte
accounting does not establish accurate latency or quality prediction.

## Workflow/failure trace summary

Semantic/readiness/phase/preflight failures are returned to the Agent and retained,
not counted as actual inference. No successful context-rejected action is fabricated.
`aggregate`/`retrieve` below denote the existing generic operators, not a new recipe.

| Task / H / route | Observed trajectory | Principal limitation |
|---|---|---|
| MultiHop Fast B | union aggregate → retrieve → context reject → smaller retrieve → model | Static envelope recovery; optional card unused |
| MultiHop Fast D | union aggregate → two retrievals → terminal model | Correct, but full-corpus movement; no alternative comparison |
| MultiHop Fast E | six cross-shard retrievals → context reject → specialist aggregates/schema recovery → prompt-only terminal | More composition/recovery work; correct score does not prove a grounded reduction handoff |
| MultiHop Slow B | union aggregate → retrieve/read evidence → terminal model | Correct but high action movement; no prospective cost query |
| MultiHop Slow D | union aggregate → retrieve → two analysis models → terminal model | Repeated expensive reasoning despite quotes; no timeout |
| MultiHop Slow E | six cross-shard retrievals → context reject → shard-1-only terminal inputs | Both supporting documents discarded despite successful shard-3 retrieval |
| Academic Fast B | aggregate → retrieve → repeated context-reject/retrieve → model | Trial-and-error feasibility; one invalid optional query |
| Academic Fast D | aggregate → retrieve → prompt-only terminal model | Correct score is not explicit artifact-grounded reasoning; quote-turn overhead |
| Academic Fast E | aggregate/retrieval → context reject → specialist/read/retrieval → model | 15 actions and context recovery; rules did not eliminate expansion |
| Academic Slow B | aggregate → context reject → retrieval reductions → model | Static capability/size misuse and subsequent recovery |
| Academic Slow D | retrieve/retrieve → prompt-only model; one single-candidate comparison | 20 Manager calls; unused true alternative comparison |
| Academic Slow E | two retrievals → context reject → two smaller retrievals → model | Low movement but expensive inference; one-run quality success |
| Video Fast B | sample → context reject → resample → model | Visual/evidence quality failure; repeated sampling cost |
| Video Fast D | sample → model on eight frames | Visual/evidence quality failure; no true candidate comparison |
| Video Fast E | sample → context reject → model on eleven frames | Visual/evidence quality failure; input reduction alone insufficient |
| Video Slow B | sample → context reject → model on eleven frames | Visual/evidence quality failure plus fixed initial-transfer cost |
| Video Slow D | sample → model on eight frames | Visual/evidence quality failure plus quote/control overhead |
| Video Slow E | sample → context reject → model on a smaller frame subset | Visual/evidence quality failure; cost rules do not repair temporal evidence |

Observed same-owner physical parallelism is genuine but small: e.g. six-way
MultiHop Fast E retrieval has 0.765 s overlap, MultiHop Slow E 2.141 s, and Academic
Fast E 1.015 s. All six D cells execute physical actions serially. Parallelism
availability is not evidence of large E2E benefit, particularly with long model
service and initial movement. Graph snapshots retain real action nodes and artifact
information-flow edges; they are execution-grown, not a frozen future DAG.

### Post-queue private MultiHop evidence audit

Run only after every experimental controller exited. Artifacts were scanned on
owning nodes; annotation/body hashes were checked locally there. No inference or
private-feedback call was made. These are document/literal coverage receipts,
not a semantic evaluator or an oracle exposed to an Agent.

| Cell | Retrieved supporting documents | Terminal information path | Score |
|---|---|---|---:|
| Fast B | both | Both small retrieval artifacts retain both documents and exact fact literals | 1 |
| Fast D | both | Both retrieval artifacts retain both documents and exact fact literals | 1 |
| Fast E | both on shard 3; later reduced retrieval also retains both | Prompt-only terminal; no direct artifact inputs or exact fact literals in prompt | 1 |
| Slow B | both | Successful reads precede prompt-only terminal; no direct artifact inputs | 1 |
| Slow D | both | Two model analysis artifacts feed terminal; document identity unknown after generated prose | 1 |
| Slow E | both on shard 3 | Only shard-1 pair consumed; both documents absent | 0 |

For generated analysis prose, literal absence is not semantic absence; do not
interpret missing document IDs as a proven loss of all relevant reasoning.

## Comparison with the preserved A/C study

Each entry is **score / E2E seconds**. A is measured spent-cost Ledger; C is
mandatory single-action Quote-before-Commit. A/C are earlier runs, not concurrent
randomized controls. Financial is not added to B/D/E and has no fabricated cells.

| Task / H | A (historical) | B | C (historical) | D | E |
|---|---|---|---|---|---|
| MultiHop Fast | 1 / 250.012 | 1 / 180.825 | 0 / 203.999 | 1 / 167.195 | 1 / 112.256 |
| MultiHop Slow | 1 / 201.631 | 1 / 92.751 | 0 / 228.329 | 1 / 1,076.493 | 0 / 204.181 |
| Academic Fast | 1 / 114.371 | 1 / 183.716 | 1 / 185.066 | 1 / 122.420 | 1 / 168.496 |
| Academic Slow | 1 / 162.897 | 1 / 136.573 | 1 / 61.482 | 1 / 132.298 | 1 / 164.601 |
| Video Fast | 0 / 349.878 | 0 / 731.159 | 0 / 1,467.875 | 0 / 355.125 | 0 / 418.404 |
| Video Slow | 0 / 785.337 | 0 / 852.065 | 0 / 556.145 | 0 / 819.053 | 0 / 799.874 |

There is **no demonstrated quality-preserving Fast/Slow workflow-adaptation
reversal**. Graphs do differ across single draws, but uncontrolled trajectory,
input-size, warm-cache/service variation and fixed ordering preclude attributing
those differences to infrastructure alone. For example B MultiHop is faster on
Slow because terminal inference is prompt-only/272 tokens instead of artifact-
consuming/4,853 tokens on Fast, not because the slower link became faster.

### Updated disposition, not a performance leaderboard

| Route | What is now tested | Disposition |
|---|---|---|
| A | Eight preserved spent-only Ledger runs | Retain lean cost-feedback control; no causal improvement claim over original Blind |
| B | Six real runs, optional query attempted once/rejected; zero valid cards | Low-overhead interface is implemented; prospective-cost mechanism still unexercised, neither winner nor empirically rejected optimizer |
| C | Eight preserved mandatory-quote runs | Retain negative/control evidence; do not promote current mandatory protocol |
| D | Six real runs; 30 visible quotes; one one-candidate comparison | Repeated-model/control cost remains; true multi-candidate decision benefit untested |
| E | Six held-out-task runs with identical frozen cost rules; zero valid optional cards | No promotion: one concrete evidence-discard/quality regression; cost-only distillation and weak contrasts do not establish quality-safe learning |

The previous recommendation that B/D/E were untested is now historical. This
follow-up does not justify claiming all five alternatives failed, a statistically
ranked best method, or that RL is required. The next research-design question is
how to expose actionable uncertain costs with low control overhead **and preserve
semantic sufficiency**, including explicit treatment of unused interfaces. No new
prompt/objective, training, task, scheduler policy or experiment is authorized by
this report. A larger sweep is not warranted by these single-draw findings.

## Admission, history and next decision

A pre-call manifest-reader field mapping was corrected before any meta-agent or
live cell call; its failed deployment log was preserved. E MultiHop Fast initially
tripped the broad `validation_failed` operational gate. An independent, hash-bound
post-run audit identified an Agent's BM25 `text_field=text` misuse on aggregate
output, followed by recovery. Original result/trace/gate remain intact, with a
separate admission receipt; only never-started cells resumed. No cell was rerun.

Final admission verifies all 18 exact source/task/capability/config/harness/rule
hashes, 72 unique initially empty Worker stores, recipient isolation, trace/event
chains, original evaluator results and cleanup receipts, with **zero unresolved
findings**. One result remains independently adjudicated, rather than concealing
the original broad-gate rejection. All four nodes now have zero owned Worker
processes; actual qdisc equals the pre-experiment state. All 16 old A/C
result/trace/freeze/method-audit hashes are unchanged. Global reservations are
**34 unique run IDs**; 18 unique B/D/E starts and finishes, with no repeats.

Append-only remote audit receipts:

| File under evidence root | SHA-256 |
|---|---|
| `bde-admission-audit-001.json` | `2eee218884615b537dd757d319b04c2a794bf4dbcb3e85bdb89ea20bf4d92bca` |
| `bde-private-multihop-coverage-audit-001.json` | `3356d33f89dd8e68448b53ddb1275cf8509619bfb8e228454cd683b8bd43feeb` |
| `bde-closure-audit-001.json` | `79ebf5d8c48a500e664a580b6e010f19799f5b1239ec96fa31fd2b7a52f12439` |

Protocol file SHA-256:
`58f8a475b88144943f8085048ff166f4150ac43bedbaf64d730f5b2ffa08c72d`.
Rules manifest file SHA-256:
`36ba6e780bbf39b9509b70a98b80a8cd5478ce532420207070bdde9e7f2f0887`.

Local regression: full pytest **573 passed**; Ruff passed; strict Pyright with
the locked project interpreter **0 errors, 0 warnings**. Bare Pyright selected a
different interpreter and reported missing dependency stubs/imports; explicit
`.venv/Scripts/python.exe` resolves that environment-only issue without code changes.

All 18 cells are now audited and the queue has stopped. No extra cells,
repetitions, prompt rescue, semantic tuning, scheduler change, RL or whole-plan
DAG revival is scheduled. Historical failed evidence and progress checkpoints
remain intact; only source and bounded report metadata are committed locally.
