# Pre-decision Raw-Aware cross-benchmark characterization v1

**Status: LONGBENCH COMPLETE; VIDEO RUNNING; overall scope incomplete.**
Updated 2026-10-03 (Asia/Hong_Kong). Twelve LongBench cells, all four Video
795-3 cells and the first three 848-1 cells are clean effective results (19/24). The two old
Financial confounded attempts remain preserved/excluded. Video 848-1 Slow-Aware is active.

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

All current dataset access/materialization/distribution and new raw evidence remain
on remote nodes, with 4090 owning the sources. Development PC obtains bounded
telemetry/metadata. The deployment Git archive also included already-tracked
historical results; see the packaging audit below. Do not call that source-only;
future bundles must exclude old result/trace evidence explicitly.

The user authorized a transport-only mitigation after the stopping-boundary audit:
Worker client idle keepalive expiry 5 s → 4 s, no retry and unchanged 100/20
connection limits. Full pytest **440 passed**, Ruff passed, strict Pyright **0 errors**.
Implementation commit `7823cdc`; separate patch freeze/execution commit
`d43c3b37bdade20464d00e630e4f61973c7ab5ad`. New harness SHA-256
`232a017188e4b779215c9a92f4df7ee0766f3892bbea596c5f81548e8fb8248e`.
The logical runtime, Manager/Verifier instructions, budgets, models, static
capability contract, tasks, representation, scheduler and observer semantics
are unchanged. Six task freeze records match the original byte-for-byte as
structured values. This is a transport revision difference, not a new method;
retain the three clean old cells rather than rerun unaffected results.

## Authoritative evidence and continuation

Remote root: `/home/super/xiaoming/predecision-crossbenchmark-v1-90cea32`.
`protocol-freeze.json` covers all six task bundles/source files/capabilities before
any Manager call. Per-cell evidence:
`evidence/<task>-<condition>/primary/{freeze,private,runs,tc-attestation.json,...}`.
All four fresh Worker roots are independently namespaced per attempt.

Initial queue PID: **358408** (`queue-launch.json`); it exited at the fourth
cell's operational audit gate. The authorized identical replacement PID **453741**
and suffix-controller PID **476338** also exited at the replacement audit gate.
The eight Slow-Aware Worker PIDs and all three queue/controller PIDs were checked
inactive. Never infer liveness from launch records: verify `/proc/<pid>/cmdline`
and `queue.jsonl` before waiting or restarting.
The queue stops at the first operational audit gate; no automatic semantic retry,
replacement, prompt change or budget expansion. See exception policy in protocol.

Read-only audit snapshot `audit-progress-006.json` retains all five attempts,
separates three effective clean records, and lists twenty unexecuted primary cells
plus the unresolved Slow-Aware cell. `persistent-operational-stop-v1.json` records
the stop boundary. No third automatic attempt or later cell was launched.
Audit tool revision does not change frozen runtime/code/config or cell results.

Authorized patch evidence root:
`/home/super/xiaoming/predecision-crossbenchmark-v1-d43c3b3`.
`patch-authorization-and-identity.json` and `patch-launch.json` record the scope,
identity checks and user approval. Affected-cell PID **2709635**; gated suffix
controller PID **2709636**. Both must be checked for actual liveness, not assumed
active from their launch record. The controller requires a clean full audit of
`transport-patch-1` before starting the exact twenty unexecuted cells and stops
at any new operational gate. New evidence never overwrites either old attempt.

Patched boundary audit passed: 132/132 probes, 11/11 actual pre-decision Aware
profiles and Manager input hashes, 11 Blind Verifier input hashes, terminal-agent
answer provenance, 12 expected persisted artifacts, trace parent chain, Worker
shutdown and tc restore. `audit-progress-001.json` merges six attempts from both
roots into four effective cells; `financial-four-cell-audit-001.json` records the
completed task comparison. The fixed suffix began with Academic Fast-Blind.

## Partial result

| Task | Condition | Completed / evaluated | Answer / score | E2E s | Action bytes | Model inferences | Manager / Verifier |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| Financial `66f7c780bb02136c067c35e8` | Fast-Blind | yes / yes | A / 0.0 | 406.653 | 265,938 | 2 | 20 / 20 |
| Same task | Fast-Aware | yes / yes | A / 0.0 | 318.058 | 486,264 | 2 | 10 / 10 |
| Same task | Slow-Blind | yes / yes | A / 0.0 | 278.919 | 141,047 | 1 | 14 / 14 |
| Same task | Slow-Aware transport patch, **clean** | yes / yes | A / 0.0 | 251.831 | 486,432 | 1 | 11 / 11 |
| Same task | Slow-Aware primary, **excluded/confounded** | yes / yes | A / 0.0 | 311.743 | 486,420 | 2 | 10 / 10 |
| Same task | Slow-Aware replacement, **excluded/confounded** | yes / yes | A / 0.0 | 412.727 | 58,287 | 2 | 10 / 10 |
| Academic `66f2c44e821e116aacb2b826` | Fast-Blind, clean | yes / yes | C / 1.0 | 126.426 | 63,102 | 1 | 9 / 9 |
| Same task | Fast-Aware, clean | yes / yes | C / 1.0 | 175.840 | 243,055 | 1 | 6 / 6 |
| Same task | Slow-Blind, clean | yes / yes | C / 1.0 | 176.759 | 25,132 | 1 | 11 / 11 |
| Same task | Slow-Aware, clean | yes / yes | C / 1.0 | 156.410 | 18,921 | 1 | 11 / 11 |
| News `66faa8efbb02136c067c7357` | Fast-Blind, clean | yes / yes | C / 1.0 | 600.051 | 107,471 | 5 | 14 / 14 |
| Same task | Fast-Aware, clean | yes / yes | A / 0.0 | 74.828 | 0 | 1 | 8 / 8 |
| Same task | Slow-Blind, clean | yes / yes | C / 1.0 | 507.576 | 191,727 | 4 | 13 / 13 |
| Same task | Slow-Aware, clean | yes / yes | A / 0.0 | 189.024 | 19,112 | 1 | 9 / 9 |
| Video `795-3` | Fast-Blind, clean | yes / yes | B / 0.0 | 185.443 | 581,538 | 1 | 5 / 5 |
| Same task | Fast-Aware, clean | yes / yes | A / 1.0 | 252.371 | 1,230,240 | 1 | 3 / 3 |
| Same task | Slow-Blind, clean | yes / yes | A / 1.0 | 1069.965 | 1,562,096 | 1 | 3 / 3 |
| Same task | Slow-Aware, clean | yes / yes | A / 1.0 | 1071.594 | 1,471,756 | 1 | 3 / 3 |
| Video `848-1` | Fast-Blind, clean | yes / yes | B / 0.0 | 442.512 | 798,787 | 1 | 6 / 6 |
| Same task | Fast-Aware, clean | yes / yes | A / 0.0 | 226.982 | 380,788 | 1 | 6 / 6 |
| Same task | Slow-Blind, clean | yes / yes | A / 0.0 | 871.266 | 981,232 | 1 | 4 / 4 |

All four effective Financial conditions are clean retained semantic quality failures. Fourth primary
is preserved but excluded: one A4 observer transport disconnect changed the actual
turn-6 Aware profile candidate count from four to three. The replacement suffered
the same transport error on A5/A28, marking three sources HOST_UNREACHABLE and
rejecting its first action before selection. Do not compare either as a clean Aware result.
See [exception audit](predecision-crossbenchmark-failure-audit-v1.md).

First cell passed profile isolation, input/Verifier hash reconstruction, terminal
answer provenance, all 320 Worker probes, artifact persistence and tc restoration.
It is a retained **valid semantic quality failure**, not a reason to tune the harness.
Trace: 40 graph nodes / 63 edges; one specialist / 8 specialist turns; peak four
overlapping actions. Four conservative context preflight rejections are recorded,
not counted as inference. Physical model service work 113.943 s, action transfer
work 3.760 s, Manager work 163.616 s, Verifier work 88.344 s; sums are non-additive.
Initial placement separately moved 1,081,150 representation bytes in 0.387 s.

Fast-Aware independently passed 10/10 pre-decision profile/input hashes and 216
Worker probes; Slow-Blind passed 14 Manager input hashes and 208 probes. Their
terminal provenance, persistence, privacy and tc restoration checks pass.
No complete task/family aggregate, stability, cost-rationality or cross-benchmark
claim yet. At the historical stopping boundary, the old suffix controller correctly
refused continuation and all twenty suffix cells were unexecuted. A third identical
operational replacement remains forbidden. The authorized transport patch above is
a separately frozen affected-cell rerun; it does not retroactively validate either
old attempt. Historical transport root cause remains unproven.
A synthetic loopback diagnostic reproduces the same disconnect on a reused
connection at the equal five-second client/server expiry boundary; a four-second
client-expiry control opens a new connection and passes. The control was originally
diagnostic-only; after explicit approval, the same limits helper passed the remote
production-client diagnostic and was frozen in the new deployment. This does not
establish historical root cause. All 20 **old-attempt** Worker PIDs were inactive
at the boundary and original deployment hashes remain unchanged. The original
24-clean-cell objective has not been achieved.

## Pending final analysis

Task-level four-condition tables, workload properties, operator/reduction/sampling
paths, evidence preservation, physical/cloud work, infra-response and quality
will be reported after auditing all attempts. Do not pool incompatible benchmark
scores or interpret single trajectories as stochastic stability. Existing MultiHop
analysis remains [separate](infra-aware-predecision-qwen-v1.md).

Final goal requires all 24 cells executed or validly failed, operational incidents
resolved or explicitly hard-stopped, final reports, evidence and repository audit.
This report does not claim completion of the unattended goal.

Financial task preliminary interpretation: both Aware conditions aggregate first,
including the constrained network. Slow-Aware sends **244.9% more action bytes**
than Slow-Blind while taking 9.7% less E2E in this single trajectory; Fast-Aware
sends 82.8% more bytes while taking 21.8% less E2E. All four original evaluator
scores are zero. Lower E2E is not evidence of network-efficient, quality-preserving
adaptation: Manager/Verifier/model work differs, n=1 does not exclude stochastic
trajectory variation, and the one transport-only revision difference is disclosed.
No method or prompt is tuned to correct these results.

`audit-progress-002.json` retains seven attempts and selects five effective cells.
Academic Fast-Blind passed 112/112 probes, 9 Manager and 9 Verifier input hashes,
terminal provenance, persistence, privacy, shutdown and tc restore. It retrieved
first, used one specialist / 8 turns, 14 nodes / 13 edges, one context-preflight
rejection and one actual model inference. This is a correct individual result,
not a complete Academic task comparison or a family-level quality claim.

Later `audit-progress-005.json` and `academic-four-cell-audit-001.json` complete
the Academic task comparison: all four trace chains/terminal provenance, hashes,
privacy, persistence, shutdown and tc restoration pass; 364/364 Worker probes.
Aware changes aggregate-first in Fast to BM25-first in Slow. Slow-Aware has
24.7% fewer action bytes and 11.5% lower E2E than Slow-Blind with equal correct
quality; Fast-Aware is 39.1% slower than Fast-Blind. This is one observed
workload-dependent response, not stochastic stability or causality. Model service
work (10.947 / 126.845 / 103.752 / 83.875 s) dominates the transfer differences.
See the detailed [LongBench task tables](predecision-longbench-v1.md).

### LongBench family completion

All twelve effective cells completed/evaluated with no unresolved system confounder;
14 historical attempts retained. Family audits verify 48 unique empty stores,
1844 successful probes, 136 Manager / 136 Blind Verifier hashes, 55 fresh Aware
inputs, all trace chains/terminal provenance/persistence/privacy/tc restore,
32768/2048 deployment surfaces, 21 normal-stop inferences and 48 exited Worker PIDs.
Selected-task scores: Financial 0/4, Academic 4/4, News 2/4. See
`longbench-family-completion-audit-001.json`, `longbench-family-runtime-integrity-001.json`
and the [family report](predecision-longbench-v1.md), including zero-score source audits.
No cross-benchmark quality pooling or broad benchmark-accuracy claim.

News Aware is cheaper but wrong in both networks. Fast-Aware eventually synthesizes
from a short prompt after specialist reads; Slow-Aware retains bounded chunks from
both documents and still answers incorrectly. Source hashes and original evaluator
are intact; classify semantic selection/synthesis and readiness, not runtime repair.

Video begins with real A4 AV1 sampling and image transfer to A28, not a smoke
MJPEG substitute. The first two 795-3 trajectories both sample 32 frames at 5 s
cadence; Blind rejects 16-image input then answers wrongly from four images,
Aware answers correctly from eight images with higher model/transfer cost. This
is a quality/cost trade-off, not uniform Aware efficiency improvement. Slow-Blind
also completed/evaluated correctly: one inference, no context failures, 16 successful
probes, E2E 1069.965 s. Fixed initial source materialization is 788.892 s (~74% of E2E),
separate from 1,562,096 action bytes / 5.508 s transfer and 236.090 s model service.
Slow-Aware also completes/evaluates correctly: 28 probes pass, E2E 1071.594 s,
1,471,756 action bytes, 788.481 s fixed initial placement. Sampling cadence changes
5→10 s, with terminal selected frames 8→10 versus Fast-Aware; both still sample
32 frames locally, with the same two-node operator sequence. Relative to Slow-Blind,
Aware action bytes are 5.8% lower but E2E is 0.15% higher: not a clear system benefit.
The fixed 282 MB initial transfer dominates both Slow E2Es. The complete task audit
checks 96 probes, 14 Manager / 14 Blind Verifier hashes, six fresh Aware inputs,
16 empty initial states/exited Workers, trace provenance, persistence, privacy,
normal model finishes and tc cleanup. See the [Video task report](predecision-videomme-v1.md).
Eight Video conditions remain pending; current 848-1 Fast-Blind is active.
Merged `audit-progress-011.json` records 18 preserved attempts / 16 effective cells.

Later `audit-progress-012.json` adds 848-1 Fast-Blind: B/0, completed/evaluated,
24 successful probes, six reconstructed Manager/Blind-Verifier inputs, terminal
provenance, privacy/persistence and cleanup pass. It samples 31 frames at 64 s
cadence, recovers a rejected 16-image request into 11 distributed input frames,
then answers incorrectly. E2E 442.512 s is chiefly model (259.739 s), cloud Manager
(72.368 s) and decode/operator (73.009 s) work, not action transfer (1.429 s).
No semantic retry or tuning; seven Video conditions remain, Fast-Aware is active.

`audit-progress-013.json` adds clean 848-1 Fast-Aware: A/0, six fresh profile/input
hashes / Blind Verifier hashes, 56 successful probes, all provenance/privacy,
persistence/cleanup checks pass. It naturally recovers a 31-image context rejection
by constructing a 31-frame contact sheet and using it in actual A28 inference.
This is a genuine extra reduction node, with 52.3% fewer action bytes / 48.7% lower
E2E than Fast-Blind, **but both wrong**, not a solved quality-preserving benefit.
Remote image checks verify readable identical 2560×720 JPEG sheet copies on A4/A28,
all 31 inputs, declared thumbnail/JPEG reduction; no PC image payload transfer.
Current progress: 20 preserved attempts / 18 effective cells / six pending;
848-1 Slow-Blind is active, not restarted during long initial materialization.

`audit-progress-014.json` adds clean 848-1 Slow-Blind: A/0, 16 probes and four
Manager/Blind-Verifier hashes, original evaluator and provenance/privacy/persistence/
cleanup pass. It directly consumes 12 distributed frames and reaches actual inference
without context failures. Only four turns / two charged physical calls are used;
this is a temporal evidence-selection/synthesis zero, not a budget or feasibility
failure. E2E 871.266 s includes 446.971 s fixed initial placement, 283.732 s model
service and 73.003 s decode. Current: 21 attempts / 19 effective cells / five pending,
Slow-Aware active; no semantic retry/tuning or new runtime incident.

## Historical completion audit at the blocking boundary (before authorization)

The original objective remains **24 clean formal cells**, not three successful
executions or an operational-stop report. Remote `blocking-boundary-audit-v1.json`
independently rechecks all five trace parent chains/run identities/single terminal
events, frozen entry/protocol/native-runtime/component hashes and all 20 owned
Worker PIDs. These checks pass; no process is still running.

| Requirement | Historical status before authorized transport patch |
| --- | --- |
| Three original LongBench and three distinct Video tasks, frozen before calls | Frozen protocol/task/source metadata exist; Video questions use two original videos, limitation declared |
| LongBench 12 clean formal cells | 3 clean; 1 cell has two confounded attempts; 8 other cells unexecuted |
| Video 12 clean formal cells | 0 executed; all 12 unexecuted |
| Shared frozen Manager/Verifier/tools/budgets/profile timing/physical substrate | Integrity/provenance checks pass for retained attempts; no experimental-path change |
| Per-attempt trace/result/config/hash/stores/observer/evaluator evidence | All five attempts retained; all five trace chains reconstruct; all completed/evaluated |
| No unresolved observer/runtime confounder | **Not satisfied:** persistent Slow-Aware observer disconnect |
| Privacy, artifact persistence, tc restoration and owned-process cleanup | Checks pass for all retained attempts; current roots mq/mq/mq/noqueue |
| Task-level clean four-condition comparisons and cross-family interpretation | **Incomplete:** no task has four eligible cells; no cross-family claim |
| No third identical operational attempt | Preserved; suffix never started |
| Reports/git | Partial reports and exception diagnosis committed/pushed; final scientific deliverables remain incomplete |

The manual operational replacement is explicitly recorded by attempt directory,
run ID, CLI launch and audit authorization. The inherited freeze field
`replacement: false` is a harness execution-policy flag; it must **not** be used
to infer that this explicitly named manual attempt is a primary. The read-only
auditor reports attempt identity separately. Original evidence is not overwritten
to change that policy field.

At that boundary, continuing required review and authorization for any subsequent
affected experimental run. The user subsequently authorized the transport-only
patch and the gated suffix recorded above. Preserve the boundary as history; do
not interpret it as the current queue state or as achievement of the goal.

## Offline verification

Cross-benchmark admission, continuation and audit/diagnostic tooling: full pytest **434 passed**,
Ruff passed, strict Pyright **0 errors / 0 warnings**, `git diff --check` passed.
Strict Pyright explicitly uses `.venv/Scripts/python.exe` on this workstation;
unqualified invocation selected an unrelated interpreter and could not find installed
LangGraph/Pillow typing dependencies. No runtime code change was needed.
The deployed execution commit's initial suite had 424 passing tests; subsequent
tests cover audit provenance, contract aliases, replacement eligibility and fail-closed
suffix continuation.
No running cell's frozen code or semantic behavior was changed by audit tooling.
