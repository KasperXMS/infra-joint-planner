# Cross-benchmark exception audit v1

## Authorized isolation repair addendum (2026-10-03)

User-authorized recipient-boundary repair `4a81081`, separately frozen/pushed as
`3c3bd95`, prevents specialist tool-result profiles and checks actual accumulated
SDK context. Full 479 tests, Ruff and strict Pyright pass. Only Financial FA,
News FA and 795-2 SA get one affected-cell attempt each, with fresh stores and
unchanged semantics. Historical exclusions and the external hard-stop result
remain intact; existing MultiHop is not rerun. See the
[patch audit](predecision-specialist-profile-isolation-patch-v1.md).

## Historical audit snapshots

Latest clean semantic boundary: 795-2 Fast-Aware completes/evaluates B/0 with two
successful backend requests, one explicitly output-limited intermediate inference
and one normal-stop terminal inference. After observing the first output it widens
sampling from 10 s to 77 s cadence and continues. No timeout, hidden retry, missing
artifact, profile leak, invalid evaluator mapping or store collision is observed.
The wrong terminal temporal-order answer is retained as an evidence interpretation /
synthesis result, not repaired as a runtime defect. Ten turns / 13 physical calls
remain below the frozen budget; expensive recovery did not restore quality.
See `video-795-2-fast-aware-cell-audit-001.json` under the final patch root.

User-reported Qwen balance exhaustion/recharge check (2026-10-03 10:27 UTC):
26 cross-benchmark trace files and recent controller/driver logs were inspected
read-only, with no extra provider/Planner probe. No billing/arrearage/balance/quota
error was found in failure events or recent logs. The last successful cloud event
is Fast-Aware's Blind Verifier verdict at 10:16:35.999829 UTC, followed by run end.
Slow-Blind is still in initial video transfer, before its first Manager call;
there is therefore no observed billing-confounded attempt to replace. This does
not independently attest account balance or future availability. The next existing
scheduled call will test actual service access. Preserve
`qwen-billing-interruption-audit-001.json` under the final patch root.

Append-only follow-up: the next **already-scheduled** Slow-Blind Manager call
completed successfully at 10:30:37.666347 UTC, then submitted `sample_frames`.
No extra API probe/retry/replacement was made. Service access is demonstrated by
that actual reasoning completion, not by assuming the recharge propagated.
`qwen-billing-interruption-followup-001.json`, SHA-256
`c219a45c890d957e1ac967b81d526a674aa8d42145323f5bfc4c23b7f5125d44`.

## Pre-run JSONL diagnostic regression

Before formal runs, the source pool was audited on the 4090. A diagnostic using
`read_text().splitlines()` falsely appeared to show malformed JSONL. Physical-line
iteration verified **all 208 records parse**: embedded Unicode U+2028/U+2029 is legal
inside a JSON string but Python `splitlines()` splits it. Source bytes were neither
modified nor discarded. This was a diagnostic/parser defect, not dataset corruption.

The same concrete defect existed in the lightweight queue's trace parser. A synthetic
regression puts U+2028/U+2029 inside an observation and proves the old parser fails on
valid JSONL. The generic queue parser now splits only LF, and the new cross-benchmark
summary uses existing `JsonlTraceWriter.read_all()` (physical file iteration).
Native runtime, prompts, evaluator, actions and physical execution are unchanged.
Frozen MultiHop component sources/manifest and completed evidence are preserved.

No formal cell had started; no experimental retry or historical MultiHop rerun is
needed. The fix is an instrumentation correctness fix, not semantic tuning.

## Formal attempts

Financial Fast-Blind, Fast-Aware and Slow-Blind completed with canonical A,
format-valid/evaluated score 0.0. Their operational, independent provenance and
persistence gates pass. They are retained semantic/model quality failures, not
implementation defects. No repair/retry/replacement is authorized for those scores.
The [partial family audit](predecision-longbench-v1.md) records narrow terminal
evidence, conservative context recovery and frozen Verifier readiness behavior.

## Financial Slow-Aware primary: observer transport confounder

Primary completed/evaluated A / 0.0 but is **excluded from clean comparison**.
One of 264 probes failed: A4 `/state`, 2026-10-02T19:07:16.121615Z to
19:07:16.595027Z, `RemoteProtocolError: Server disconnected without sending a
response.` Diagnostic observation ID `cd049211-a87f-49de-8823-3adbf61694ed`.
The actual `manager:native-turn:6` pre-decision input received candidate_count=3
instead of the normal 4. Thus the failure changed experimental Aware input even
though it caused neither lost artifacts nor a failed physical action.

All artifacts remained PRESENT (the source on A4 also had a replica on A5), and
the next A4 probe succeeded at 19:07:34.410352Z. All four Worker logs have zero
Python tracebacks and graceful shutdown; all owned PIDs are inactive. tc restoration
matches original mq/mq/mq/noqueue, cleanup_error=null, artifact persistence passes.
The queue exited rather than starting the next cell. Exact underlying transport
cause remains unknown; no invented keep-alive explanation or observer-policy change.

Audit authorization is durable at remote root
`operational-audit-financial-slow-aware-v1.json`. Frozen protocol permits one
identical replacement for a connection reset/disconnect. New attempt
`operational-replacement-1` uses unchanged execution revision 90cea32, new run ID
and four fresh namespaces. Primary evidence and score are untouched.

### Replacement: same-class persistent incident, continuation stopped

Replacement completed/evaluated A / 0.0, E2E 412.727 s, 58,287 action bytes,
10 Manager/Verifier turns, 14 tool attempts, six model attempts/two actual
inferences, graph 20/17. This is **not an eligible clean result**.

At 2026-10-02T19:14:07.247524Z/19:14:07.247616Z, A5/A28 state probes again
failed `RemoteProtocolError` (~52 ms). Private diagnostic observation ID
`a4964bf2-7c52-435a-b60e-e61633d8c098`, affected action
`manager:call_c4e9e522bd13427f9baaac7b`. Three input sources were marked
HOST_UNREACHABLE and the first action returned missing_input with no physical
selection. The next observation recovered both workers. All 10 pre-decision
profile events subsequently show four candidates; this does **not** erase the
physical-action confounder between those inputs.

Replacement privacy/provenance/persistence/tc checks pass, but two of 200 probes
fail. All four logs have zero Python tracebacks and graceful shutdown; owned PIDs
are inactive. The suffix controller stopped at its clean-boundary check and no
academic/news/Video cell started. No third identical replacement is authorized.

Idle gaps between last successful probes and disconnecting probes were 4.539 s
for the primary and 4.966 s for both replacement failures. Installed HTTPX 0.28.1
and Uvicorn 0.53.0 expose default five-second keep-alive settings, and the frozen
clients/server do not override them. A stale keep-alive timing race is a plausible
**hypothesis**, not a proven root cause. There is no packet/connection-lifecycle
trace proving it, and no transport or observer-semantics change was made.

Remote `persistent-operational-stop-v1.json` records the unresolved gate; full
`audit-progress-006.json` retains all five attempts, not just selected clean scores.
Twenty scheduled cells remain unexecuted. The 24-run goal is incomplete and no
cross-family scientific conclusion can be drawn from this partial block.

### Transport-only diagnostic, no new formal attempt

`scripts/diagnose_http_keepalive_v1.py` ran once on the 4090 with a synthetic
loopback HTTP endpoint. It uses no dataset, benchmark adaptation, Worker namespace,
model/provider call or tc operation. This is a mechanism counterexample, **not**
a reproduction of the historical network/connection lifecycle.

The endpoint returns only `{healthy: true}`. Uvicorn timeout_keep_alive=5 s;
after the first successful response, wait 4.8 s and explicitly inject a 0.4 s
header-write delay **after** connection checkout. The request trace shows:

| Client idle expiry | Second-request TCP connects | Second request |
| --- | ---: | --- |
| 5 s (current default) | 0 (reused connection) | RemoteProtocolError: Server disconnected without sending a response |
| 4 s (diagnostic control only) | 1 (fresh connection) | HTTP 200 |

The production config is **not** changed to 4 s. Exact remote diagnostic artifact:
`transport-counterexample-v1.json`, SHA-256
`7a0cee459d372c949ab3b2aa00d204faed965c59c329d9c172623097b94507b2`.
All three actual Jetson Worker virtualenvs report Uvicorn 0.53.0 with the same
default five-second server keep-alive, independently checked without starting Workers.

Across all five preserved attempts, 1,208 state probes include 25 probe gaps in
[4.5,5.0) s: 22 successes and all three disconnects. The other 1,183 probes
succeed. Remote `transport-probe-gap-audit-v1.json` records this distribution.
These are intervals between `/state` probes, **not** authoritative connection idle
durations: other HTTP requests can intervene. Association plus the synthetic
counterexample strengthens the hypothesis, but neither proves historical cause.

All 20 Worker PIDs across the five attempts and all three queue/controller PIDs
are inactive. Frozen entry/protocol hashes still match the original preparation.
No third experiment attempt was launched. This preserves the persistent-cell
operational stop required by the protocol; the next decision needs review rather
than treating this cell as a Planner failure or silently applying a speculative fix.

Diagnostic tooling verification: full pytest **434 passed**, Ruff passed, strict
Pyright (explicit project interpreter) **0 errors / 0 warnings**. Three new tests
cover the fixed non-private payload, evidence no-overwrite guard and explicit
synthetic/not-historical/not-formal classification; they do not claim to cover
production connection timing or provide a validated runtime fix.

The final read-only stopping-boundary audit is remote
`blocking-boundary-audit-v1.json`: five valid trace parent chains and terminal
events, unchanged frozen runtime/component/entry/protocol hashes, all 20 owned
Worker PIDs inactive, three clean cells, twenty untouched primary cells and one
unresolved cell. It records the named manual replacement separately from the
inherited `replacement:false` automatic-execution policy field. No historical
freeze/result/trace was edited or rewritten.

The read-only auditor now retains all attempts and distinguishes effective clean
records from excluded/confounded primary records. It does not select by quality
or E2E. A separate suffix controller invokes the **same frozen cell entry point**
for only twenty unexecuted cells after a clean boundary; it refuses existing cells
and stops on any operational gate. Neither tool changes logical/physical execution.

## Read-only audit contract alias

The first post-run audit invocation incorrectly reparsed a frozen `OutputContract`
field-name dump using aliases only (`schema_definition` vs `schema`). This affected
only the new read-only audit tool; the live run, answer/evaluator and tc restoration
were already complete and unchanged. Use explicit `by_name=True`, with a round-trip
regression. The corrected audit snapshot independently verified Manager/Verifier
hashes and terminal provenance. No affected experimental cell needs rerunning.

Preserve all primary and authorized operational replacement evidence.

## Authorized transport patch (2026-10-03)

After reviewing the stopping boundary, the user authorized continuing with the
transport-only mitigation. The shared SDK-native Worker HTTP client now expires
idle pooled connections after **4 s**, below the verified Uvicorn 5 s server
timeout. Connection limits remain HTTPX defaults (100 total / 20 idle); model
controller-to-Worker timeout remains 1200 s. There is no Worker HTTP retry, new failure classification,
fallback, observer relaxation, prompt change, budget change, or scheduler change.
The mechanism remains a hypothesis for historical incidents, not proven root cause.

Regression coverage checks production client construction, unchanged concurrency,
single-attempt failure propagation, and real-Uvicorn idle expiry. Additional
tests cover the unchanged logical/protocol freeze and cross-revision audit merging
without discarding either excluded attempt. Full pytest: **440 passed**; Ruff and
strict Pyright pass after style cleanup.

New manifests use the `*-transport-patch1.yaml` suffix; original manifests and the
original deployment/evidence stay untouched. The Financial Slow-Aware rerun is
named `transport-patch-1`, with an explicit bug-fix attempt provenance sidecar.
It is a new-patch affected-cell rerun, **not** a third identical operational
replacement. Only a clean audited boundary permits the twenty-cell fixed suffix.
No corrected formal result has been claimed at the time of this patch freeze.

### Affected-cell result after patch freeze

Financial Slow-Aware `transport-patch-1` completed and evaluated: terminal `A`,
score 0.0, E2E 251.831 s, action bytes 486432. All 132 state probes pass; all
11 Manager/pre-decision profile and 11 Blind Verifier input hashes reconstruct.
Terminal provenance, trace parent chain, twelve expected artifacts, Worker
shutdown and tc restoration pass. This establishes a clean affected sample,
not historical proof of the disconnect mechanism or guaranteed future transport
reliability. The two old excluded attempts are preserved. The gated suffix
continued to Academic Fast-Blind without retry or logical behavior changes.

### Deployment archive scope audit

The transport-patch deployment used `git archive HEAD`, 36669440 bytes. It includes
669 already-tracked historical `results/` files despite ignore rules for new
results; the earlier "code-only archive" shorthand was inaccurate. No current
benchmark dataset was downloaded/materialized/distributed through the development
PC: all six sources are the frozen external 4090 paths; execution uses new isolated
Worker stores, not historical archived results. Current logical privacy checks
pass. No API-key/device-info file is tracked. Preserve the existing copies and
running freeze; future bundles must explicitly exclude historical result/trace
evidence, with any needed immutable profile metadata allowlisted separately.
This is an avoidable packaging/transfer issue, not grounds to replace clean
semantic outcomes or modify the experiment path.

### Frozen source and backend client policy audit

Read-only `execution-source-integrity-audit-001.json` verifies all 141 tracked
`src/` and `scripts/` files against Git blob hashes from `d43c3b3` on all four
nodes: no missing files or mismatches. Controller/driver use that frozen source
and revision environment. This does not attest dependency or model blob hashes.

The 1200 s timeout is the **controller -> Worker** request limit, not the
Worker -> Ollama SDK timeout. Frozen `build_model_backend()` creates AsyncOpenAI
without overrides: its effective defaults are **max_retries=2**, timeout
connect=5 / read=600 / write=600 / pool=600 s. Cloud Manager/Verifier clients
explicitly use max_retries=0 and timeout=180 s. No settings are changed here;
the earlier unqualified "no HTTP retry" statement applies only to Worker HTTP
transport and explicit cell/semantic repetition, not every client layer.

`backend-client-policy-and-request-count-audit-001.json` maps 21 completed
attempt windows (19 effective plus two excluded) to A28 Ollama access logs,
accounting for its UTC+8 clock. All **32 traced actual inferences match exactly
32 completed server requests, each HTTP 200**, with no observed duplicates.
The two historical HTTP 500 entries are outside these windows. This supports
one accepted inference per action in the checked scope; connection attempts
that never reached server logging remain unobservable. Do not claim SDK retries
were disabled or silently alter the ongoing freeze. Extend request-count
coverage after the remaining cells, preserving this audit unchanged.

Append-only audit `backend-client-policy-and-request-count-audit-002.json`
extends coverage to 20 effective crossbenchmark cells, both exclusions and all
12 existing MultiHop runs: **34 preserved attempts, 47 traced inferences,
47 completed HTTP-200 requests**, one match per action. No rerun or network/model
configuration change. SHA-256
`4cfdf7686883aafef5bfe315b2d71be209d5dbbbc39752dfe6ddba435eed63f3`.
This still excludes unfinished 795-2 cells and retains the pre-server limitation.

Worker inference max output is the deployment's reserved 2048 tokens. The
inherited harness annotation `terminal_canonical_labels=[Yes,No]` is not the
multiple-choice task contract: per-task A-D labels and original evaluator wiring
remain authoritative and validated. Do not alter the frozen manifest in-flight.

### 795-2 Fast-Blind: newly observed backend timeout / hidden retry

At 2026-10-03 09:28:48 UTC, A28 Ollama recorded HTTP 500 after exactly 10 minutes
for the pending visual model request (server task 334), cancellation with
`truncated=0`, then a second request (task 837) without any new logical action.
The Worker client inherits max_retries=2 and read timeout=600 s, while the cell's
declared service timeout is 1200 s. The exact server-versus-client cancellation
origin is not established solely by the access log; the **additional backend
request under one logical action is directly observed**.

This is a genuine no-hidden-retry / timeout-propagation contract defect and an
invalid baseline attempt, not a Planner reasoning failure. It does not retroactively
invalidate the earlier scopes with one matched HTTP-200 request per inference.
The suffix controller PID 2709636 was ownership-verified and SIGSTOP-held before
any later condition; atomic driver PID 3197880 continues to preserve/cleanup its
attempt. Original results/traces/configs remain untouched. Append-only evidence:
`backend-timeout-hidden-retry-incident-001.json` and affected attempt's
`private/execution-incidents.json`. Do not resume the old controller.

Minimal fix implementation `3c3d3c8`: backend factory explicitly disables SDK
retries; configurable read timeout retains the legacy 600 s default, while formal
Worker preparation propagates the already-declared 1200 s service timeout.
Connect 5 / write 600 / pool 600 s stay unchanged. No reasoning-effort, temperature,
model, context, output budget, Manager/Verifier instructions, tools, scheduler or
network change. Read-only auditor incorporates run-bound external incidents into
derived eligibility without overwriting historical validation/result files.

Four initial regression tests fail against the old factory: max_retries=2 and
three actual requests for a simulated 500, timeout or disconnect. All pass after
the fix, with exactly one request and typed error propagation. Full implementation
suite: **449 passed**, Ruff passed, strict Pyright **0 errors / 0 warnings**.
New patch manifests use `*-backend-client-patch1.yaml`; frozen semantics and
task/network matrices are unchanged. Affected-only bug-fix rerun and exact three-cell
suffix require a separate patch freeze, clean current-attempt cleanup and audit.
No corrected 795-2 outcome is claimed yet.

Atomic attempt subsequently ended at the outer 1200 s timeout: result
control_plane_failed / UserError, no terminal/evaluator. Actual typed observation
is physical_execution_failed / ReadTimeout. First and second server requests
return HTTP 500 at 600 s; third SDK request starts before owned Worker shutdown.
Append-only incident addendum preserves these logs and process identity. The
held controller was ownership-verified and terminated without starting another
cell; the lingering owned A28 Worker received a second shutdown signal. Ollama
server was not killed/restarted. All four old Worker ports are closed; tc matches
its original state. 52 state probes, persistence and privacy still pass; none
makes this a valid result. Failed-inference/transfer cost must not be inferred
from successful-only service counters; external request evidence is authoritative.

Additional generic admission defect: SDK UserError wrapper drops the timeout
text, so old failure-string matching allowed this system failure through. Two
red regression cases reproduce the missed physical/unknown typed failure gate;
five semantic/readiness/context cases continue to pass. Fix `a5d1e80` checks typed
observations, not just wrapped strings, and enumerates backend-patch attempts in
cross-revision audit. This is an audit gate, not an Agent behavior change.

Final execution freeze `5dafc43327a057f6a66df29d112a4e56820a65a2`; full 459 tests,
Ruff and strict Pyright pass. New deployment/task/source checks pass on all nodes.
Only affected Fast-Blind is launched anew, then the three-cell suffix is
audit-gated. Source bundle excludes historical results and benchmark bodies.
Earlier `66a6016` staging is diagnostics-only; no formal cells executed there.
See [freeze note](predecision-backend-client-patch1-freeze.md). Existing 20 effective
cells remain unchanged; the new excluded attempt is preserved, not replaced
in-place. Historical repair-boundary ledger: 23 attempts / 20 effective / four unresolved.

### Clean affected-cell boundary after backend patch

795-2 Fast-Blind / backend-client-patch-1 completed/evaluated C/1.0, format valid,
E2E 692.487 s. All 56 probes, eight Manager / Blind Verifier hashes, trace/terminal
provenance, privacy/persistence, four empty initial stores / exited owned Workers
and tc restoration pass. Ollama window contains exactly one HTTP-200 request;
service 441.516 s, finish stop. The no-hidden-retry incident is absent in this
new sample. Old failed attempt is retained/excluded via incident sidecar.

Do not claim timeout expansion caused correct reasoning: new native sampling
75 s versus prior 30 s differs stochastically, and the successful service call
finishes below 600 s. This is a clean corrected execution boundary, not a paired
mechanistic quality comparison. Only the exact remaining three cells continue.
Latest `5dafc43/audit-progress-002.json`: 24 attempts / 21 effective / three pending.

## Recipient-context profile leakage: hard-stop, superseding prior clean counts

At 2026-10-03 11:19:45.791355 UTC, the last 795-2 Slow-Aware attempt was stopped
for specialist dynamic-profile leakage. Gateway exposure used run-level AWARE
visibility, and the wrapper returned full observations to specialists. SDK tool
outputs therefore supplied network/transfer/queue ranges even with the direct
specialist profile field null. This is a genuine isolation implementation defect,
not inefficiency, reasoning failure or an operational replacement candidate.

Full 39-trace scan invalidates previously admitted Financial Fast-Aware and News
Fast-Aware, three existing MultiHop Aware repetitions, and the interrupted Video
cell. Two already excluded old Financial Slow-Aware attempts also have the defect.
New coverage is **21/24**, not 23/24; existing MultiHop is not a clean balanced n=3
block. Detailed affected-run IDs, input hashes, source mechanism and durable
evidence are in the [hard-stop report](predecision-specialist-profile-isolation-hard-stop-v1.md).

Driver/controller and all four owned Workers are inactive; tc restoration passes
with cleanup_error null. No evidence was overwritten/deleted. Interrupted trace
ends at Verifier input before the stop record, after six completed inferences;
no normal result/run.end exists, so a separately typed external hard-stop result
preserves failure/cleanup facts without pretending benchmark completion.

The previous direct-field-only isolation audit was too weak. Full 459 tests/Ruff/
strict Pyright remain green but do not cover this live recipient-context invariant.
No automatic code fix/resume is made under the explicit privacy hard-stop.
