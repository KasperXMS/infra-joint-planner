# Exact compound failure audit — Phase I

2026-10-05. Offline-only classification of the original MultiHop-1 / DeepSeek /
Fast / B1 attempt. No new Agent mechanism, retry, censoring, prompt/strategy/model
change or execution-app modification. Existing exact JSON and provider-policy
reviewers remain unchanged and still reject a compound finding individually.

## Original stop and evidence

Run ID:
`large-scale-cost-guidance-v1-phase1-multihop_rag-1-29e45040dce39dae-p1-fast-B1-attempt1`.
Execution fa19e0bcf27fe1e09b1596a50d2a4af120432438 / freeze003.
Actual queue parent2235001 and child2296499 exit; every Worker is verified exited.
Original admission is a confounder requiring audit, with exactly these findings:

- `typed_action_failure_requires_audit:validation_failed`;
- `unclassified_API_failure_requires_audit`.

Original admission canonical SHA-256:
`6e5e7b41b1a8cade0bba26f01ca929ec4c6a7e7984e888dcafb588fa8b212eb0`.
Original result has execution_completed=false, evaluator=null, telemetry=null.
Terminal failure is Blind Verifier HTTP400 `data_inspection_failed`, not quota,
provider outage, context overflow or physical timeout. The specialist also has
one exact HTTP400 input-policy refusal; all other cloud receipts are HTTP200.

The specialist's materialized application/json model action has a selected
deployment and execution-stage failure exactly `model output is not valid JSON`.
The frozen Worker invokes the backend before parsing JSON. It is a completed
inference with unmaterialized invalid output, not a missing executable/schema
contract or a silent JSON repair. Failure action lifetime134.663 s is measurable;
actual failed model service/tokens are unknown, not reconstructed from elapsed time.

## Cost and execution scope

| Metric | Original recorded evidence |
|---|---|
| E2E | 413.573 s from explicit run.failed |
| Manager / specialist reasoning turns started | 5 /13 |
| Verifier calls | 5; last request refused |
| Created specialists | 2 |
| Prepared physical actions | 21:18 tools /3 model attempts |
| Successful tools | 18 |
| Physical model inference | 1 successful receipt +1 proven post-inference JSON failure |
| Context preflight reject | 1; not inference |
| Successful model-service subtotal | 150.269 s; complete total unknown |
| Successful inference input/output tokens | 3,745 /307; failed inference tokens unknown |
| Initial placement | 7,696,522 bytes /0.760 s |
| Successful action-transfer subtotal | 56,806 bytes /0.715 s; full total unknown |
| Physical receipts | All21 present |
| Execution-grown graph | 64 status snapshots,21 nodes /22 edges,2 information handoffs |
| Cloud HTTP calls | 23;21 known usage /2 unknown |
| API known subtotal | USD0.231155; full estimate unknown, not invoice |
| Evaluation / quality | Not invoked /unknown, not score0 |

The original trace includes phase/context/semantic typed continuation before
the provider refusal. Do not infer evidence quality, retention or causal B1
benefit from these counters. Private supporting-body coverage analysis waits
until all168 cells have finished and no queue is active.

## Strict composition, not a gate relaxation

New offline helper `large_scale_compound_review_v1.py` accepts only the exact
two-finding set. It isolates each finding for the unchanged original validator,
requires both independent proofs, and rejects any additional finding, missing
proof, operational incident, different HTTP400, quota/outage, non-model failure,
selection-stage failure, non-JSON output, evaluated result or completed run.
The full original admission remains untouched and is independently recomputed
before a sidecar can be written. Every original file, Worker parse source,
component reviewer and compound reviewer is hash-bound and reverified.

A separate compound sidecar preserves the original rejected journal record.
The effective nominal classification is mixed model-output / provider-policy
failure, with provider-policy primary because it terminates the run. There is
no replacement authorization. The original API/private/JSON/result/trace stays
immutable; no answer is invented, filtered or sent to the evaluator.

The new offline controller binds the unchanged parent control005, all component
reviewer sources, compound sidecar set and itself. It uses the same execution003
and original168-cell schedule, skips classified failures, and launches only the
original next unstarted cell. Actual process absence is required before resume;
observation timeout is never a restart signal. Original controllers/freezes are
not overwritten. All new scripts deploy outside the frozen app.

The read-only projection preserves unknown failed model work and separately
counts proven post-inference failures; it does not label incomplete inference
telemetry as zero or turn absent evaluation into score0.

## Verification and deployment status

Offline code commit: `0b0abdc32fd8e8d8e04d517a8cc03d2075162649`.
Full pytest **884 passed in23.11 s**; Ruff passed; strict Pyright0 errors /
0 warnings; git diff --check passed. Added33 regressions cover proof composition,
rejection of unrelated failures, original-review strictness, coexistence of all
three sidecar types, no rerun/journal mutation, cache/source/evidence tamper,
process liveness, exact parent control, original-next-cell launch and unknown
cost/quality projection. A targeted cache regression caught Worker-source drift
being omitted from the new cache key; the new view now hashes that source and
reviewer sources before reusing verified membership. Historical helpers are unchanged.

The three source files are copied only to remote readiness/compound-review-001.
Execution003 independently revalidates to
`092f39fd278027eab324d4b0c5280bbd5024db9f23cc60de556c361f3901e749`;
formal app,366 source/config hashes and semantics remain unchanged. The independent
full original admission/sidecar audit is still running at this checkpoint;
classification/resume is not asserted until that actual audit completes.
