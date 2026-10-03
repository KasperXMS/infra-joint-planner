# Pre-decision Raw-Aware cross-benchmark characterization v1

**Status: AUTHORIZED TRANSPORT-PATCH RERUN IN PROGRESS; scope incomplete.**
Updated 2026-10-03 (Asia/Hong_Kong). Three clean cells retained; Financial Slow-Aware
is being rerun under a separate, tested transport patch. Its two old confounded
attempts are preserved; twenty primary cells wait for the clean boundary.

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

## Partial result

| Task | Condition | Completed / evaluated | Answer / score | E2E s | Action bytes | Model inferences | Manager / Verifier |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| Financial `66f7c780bb02136c067c35e8` | Fast-Blind | yes / yes | A / 0.0 | 406.653 | 265,938 | 2 | 20 / 20 |
| Same task | Fast-Aware | yes / yes | A / 0.0 | 318.058 | 486,264 | 2 | 10 / 10 |
| Same task | Slow-Blind | yes / yes | A / 0.0 | 278.919 | 141,047 | 1 | 14 / 14 |
| Same task | Slow-Aware primary, **excluded/confounded** | yes / yes | A / 0.0 | 311.743 | 486,420 | 2 | 10 / 10 |
| Same task | Slow-Aware replacement, **excluded/confounded** | yes / yes | A / 0.0 | 412.727 | 58,287 | 2 | 10 / 10 |

The first three are clean retained semantic quality failures. Fourth primary
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
claim yet. The suffix controller correctly refused continuation; its twenty-cell
schedule remains unexecuted. A third identical operational replacement is forbidden.
Transport root cause remains unproven; no speculative runtime repair is applied.
A synthetic loopback diagnostic reproduces the same disconnect on a reused
connection at the equal five-second client/server expiry boundary; a four-second
client-expiry control opens a new connection and passes. This control is not
deployed and does not establish historical root cause. All 20 owned Worker PIDs
are inactive and the frozen protocol/entry hashes remain unchanged.
Review is needed before separately versioned bug-fix/rerun work or closing at this
operational stop. The original 24-clean-cell objective has not been achieved.

## Pending final analysis

Task-level four-condition tables, workload properties, operator/reduction/sampling
paths, evidence preservation, physical/cloud work, infra-response and quality
will be reported after auditing all attempts. Do not pool incompatible benchmark
scores or interpret single trajectories as stochastic stability. Existing MultiHop
analysis remains [separate](infra-aware-predecision-qwen-v1.md).

Final goal requires all 24 cells executed or validly failed, operational incidents
resolved or explicitly hard-stopped, final reports, evidence and repository audit.
This report does not claim completion of the unattended goal.

## Completion audit at the blocking boundary

The original objective remains **24 clean formal cells**, not three successful
executions or an operational-stop report. Remote `blocking-boundary-audit-v1.json`
independently rechecks all five trace parent chains/run identities/single terminal
events, frozen entry/protocol/native-runtime/component hashes and all 20 owned
Worker PIDs. These checks pass; no process is still running.

| Requirement | Current authoritative status |
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

Continuing requires review of the persistent operational cell and authorization
for any subsequent affected experimental run. No demonstrated historical runtime
root cause or validated production patch currently permits an automatic bug-fix
rerun. This is an unresolved protocol/operational gate, not proof of the user's
permanent scientific hard-stop conditions and not achievement of the goal.

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
