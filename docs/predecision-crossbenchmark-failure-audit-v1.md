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
and four fresh namespaces. Primary evidence and score are untouched. A second
same-class incident triggers persistent operational stop, not a third attempt.

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
