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

## Offline traversal repair (separate from benchmark execution)

The first offline proof process2360076 repeatedly rehashes all existing sidecars
once for each scheduled cell during ledger replay. A regression proves the
defect: four scheduled cells require four full proof passes despite identical
membership; a single complete pass is sufficient. The live process consumes a
CPU and rereads about288 GB of already cached, node-local evidence files;
it has not written a compound sidecar. This is a confirmed offline traversal
defect, not an expired observation or failed benchmark action.

Only that exact, ownership-checked audit process is terminated after recording
its PID/source/IO/proof status. No benchmark/Worker/model process is restarted.
The incomplete audit source folder remains unchanged. Stop receipt SHA-256:
`ec8b516fa6f2ece7cf075d3249bffd6d1a0e95eea67e58a3b93ebe7651377239`.
Its stale lease is explicitly reconciled only after actual process absence and
all owned queue/attempt absence are confirmed; the single lease file is moved
to readiness/compound-review-001/stale-audit-lease-001.json, not discarded.
Reconciliation receipt SHA-256:
`55188750328e37f9071979c8c21eed426e6e177dfbf143cebc663a8b7bf03e94`.

Commit533105f16ad7bb3fdf89cdc78483d854e5ec0f63 adds one membership-set calculation
to the new offline ledger. Each query still fully revalidates every proof/file;
there is no persistent unverified cache and no validator or finding change.
The regression now observes one full pass and the same admitted cells.
Full pytest **885 passed in23.43 s**, Ruff / strict Pyright / diff check pass.
The corrected reviewer deploys in a new readiness/compound-review-002 folder;
old folders, freezes, validators and all attempt evidence are untouched.
New source SHA-256:
`7e71edfe5e985a18bedfb7f8182f520fe0918658c7a5a374f5787dbdafd56ebf`.
Test-provenance file SHA-256:
`1483930fe26203d2131aee896d29f87f3f3641f71093822a74312d107e794006`.
Corrected audit process2418654 is verified live; no classification or experiment
resume is asserted before its full proof completes.

Additional structural audit of all28 already-admitted snapshot024 cases passes:
all actions close, all intervals are available and dependency order has zero
violations. This includes the terminal-choice failure and provider-policy
failure; graph closure does not imply semantic completion. Remote
analysis/settled-graph-audit-004.json file SHA-256:
`732615f5af5a366ab7b482016c1ffaa9710af017757647db496a4095f48f62f7`.
It is source/result/trace/admission-hash bound and performs no supporting-body
coverage audit, no pooled score calculation and no method pruning.

## Exact compound proof completed; no rerun

The corrected audit completes and reproduces the full original admission. The
new sidecar binds all115 original files, one exact post-inference JSON failure
and two exact HTTP400 policy refusals. It preserves the original rejected
admission/journal/result/trace and all previous reviewers, sidecars and freezes.
It authorizes no replacement, prompt change, censorship or model-output repair.

Compound sidecar canonical SHA-256:
`128c5815eaba6b8d947e0c3237a9c6e35b7acbfbbbe09afdcb4071fdd476cf69`.
File SHA-256:
`92929d1f68c462a4949522c28e1bd26ae97e2b086cf9682b2038ccbe8216214c`.
Effective reviewed-admission canonical SHA-256:
`13b3c02451e8f5535bbaf5b32eb4f5b70b7f9c510335f75386d230a402a016b0`.
The original rejection remains
`6e5e7b41b1a8cade0bba26f01ca929ec4c6a7e7984e888dcafb588fa8b212eb0`.

The run is a classified nominal mixed model-output/provider-policy failure,
with provider refusal primary. Incomplete execution/unevaluated quality and all
unknown failed service/token/API totals remain unknown. It is the29th classified
Phase I condition, not a successful completion or a score0. No benchmark run
is repeated during this offline proof correction.

New queue-control-freeze-006 independently reproduces immutable parent005,
all unchanged old reviewer/control sources and the unchanged execution003.
It additionally binds the new compound review set and offline controller.
Canonical SHA-256:
`80129a3427d32f2026e1c6259460f58b3cf1d1ec1607ad32990d78042bbe41f3`.
File SHA-256:
`1e807e5aedcae4a274ee71a84d1d54aa0702b6a0b0099b2075e93d8e79a7ce42`.
It does not authorize repeated valid/failed nominal cells, semantic tuning,
changed schedule or a new execution freeze. The original next unstarted cell is
MultiHop-1 / Qwen / Slow / A; queue resume is not asserted until actual launch
and owned-process verification.

Snapshot025 completes:29 classified /31 attempts /0 pending /2 effective
confounders /6 original confounded journal records /2 exact JSON reviews /
1 exact policy review /1 compound review /0 operational exclusions. File SHA:
`3c396e9b7764df5337c268aa867a0b350538a1a6b00ea01145ed13944d5ad90b`.
Its projection pins the base collector and compound reviewer/projection sources,
retains unknown failed inference work/API totals and does not pool scores.
It is generated before the experimental queue resumes.

Queue007 is then actually launched, recording queue-process-007.json and new log;
parent2448151 and original next-cell child2450537 are verified owned/live.
The child reserves only MultiHop-1 / Qwen / Slow / A attempt1; all four before
states have zero artifacts. Latest journal now has32 attempts /1 pending;
the classified failed cell is not repeated. This is not Phase I completion,
method pruning, a new semantic strategy or Phase II authorization. Full168-cell
classification/audit and the remaining frozen study still have to complete.
