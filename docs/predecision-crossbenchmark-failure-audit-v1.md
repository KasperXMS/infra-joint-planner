# Cross-benchmark exception audit v1

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
