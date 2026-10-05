# Resident-block private evidence audit

This is an offline audit protocol, not a method, Verifier, prompt change or
new runtime feature. Execution app revision remains `90fd30c`; the independent
auditor is committed at `3d7d2808fb5be07f6178536f16c73de7bdf88cc9` and deployed
outside that app at `audit-tools/private-evidence-001` on4090. No experiment
cell, artifact body scan, Planner/model invocation or gold-bearing API request
was introduced during this preparation.

## Gate and evidence boundary

`large_scale_resident_private_evidence_v1.py` rejects actual live processes
recorded by the new block's queue lease, queue-process receipts and per-attempt
atomic process receipts. It does not reuse the historical auditor's different
controller/queue filenames. PID reuse by an unrelated process is not counted
as a live experimental action. The phase-wide body scan additionally requires
all168 new cells resolved/admitted, no pending/confounded attempt, and verified
Worker exits. The gate is checked again before each cell and at the end.

The scan will run **only after Phase I has ended**. Preparation includes an
actual remote rejection test against the currently live queue; it returned
`live_queue_body_scan_rejected=true`, without opening benchmark artifact bodies.
This avoids adding corpus I/O/remote load to measured trajectories.

Only the new resident block is audited. Old42 samples remain nonpooled, and
task selection/original corpus/privacy/execution hashes are independently
bound. Artifact requests must address the exact frozen run/owning-node store,
with existing generic hash/size verification. Replica metadata disagreement,
missing successful information artifacts, wrong scanner membership or returned
hash/size fails the audit instead of producing a zero/guessed metric.

The original prepared private JSON includes a trailing newline, whereas the
runtime copy uses a different writer. The auditor verifies the **original file
hash** and then parsed-value equivalence of its copy; it does not confuse a
canonical JSON hash with a formatted file hash. A regression covers this exact
serialization distinction.

## Evidence diagnostics, not a semantic oracle

MultiHop's private supporting annotations are mapped to original corpus document
identities. Bodies are scanned on their owning nodes, after execution is idle;
only bounded document-ID/literal coverage receipts return to4090. These receipts
are never injected into a Manager, specialist, Verifier, cost card or history.

Per action, the report identifies successful inputs/outputs, failures, terminal
source ownership and model-prompt literal cues. It excludes raw corpus text,
query, support facts, prompts and gold. Actual terminal provenance comes from
the persisted loop-end receipt, not an inferred future candidate.

Exact document-ID presence does **not** prove complete fact preservation. Missing
literal text in a paraphrase does **not** prove semantic loss. Therefore
automatically computed semantic evidence retention and primary semantic causes
remain unknown. Required-evidence retention needs a subsequent private semantic
audit of the evidence path, with explicit confidence/unknowns. LongBench and
Video lack the needed supporting-reference annotation in this setting; their
coverage remains unknown, not zero or pseudo-annotated from evaluator gold.

This helper alone cannot mark the comprehensive audit complete, prune methods,
authorize Phase II or select a winner—even after168 cells. Complete recipient
context/privacy, failure taxonomy, quality and method-adoption analysis remain
separate required steps.

## Verification and provenance

1023 full pytest pass (32.75s); Ruff pass; strict Pyright0 errors with the project
interpreter; diff check pass. Tests cover new live-process filenames, unrelated
PID reuse, incomplete-block rejection, exact run/owner scope, original/copy JSON
equivalence, corpus/private/result drift, replica/scanner membership drift,
bounded exports and unknown retention/quality. Frozen execution hash was
reverified after deployment:
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.
All four nodes/five model instances remain resident.

Deployment receipt's initial commit field was descriptive rather than an exact
source revision. Its original bytes are preserved; an append-only correction
binds the exact `3d7d2808...` commit and original receipt hash. This audit-only
metadata correction did not alter any formal configuration/result or frozen app.

## Current evidence checkpoint, not pruning

2026-10-06 01:28 Hong Kong:13/168 valid cells,1 pending,0 confounders or
operational exclusions. The queue and current atomic run are verified live on
MultiHop representative1/P1/Slow/A. Snapshot003:

- Remote path: `analysis/resident-snapshot-003.json`.
- Captured UTC: `2026-10-05T17:28:27.952529+00:00`.
- SHA-256: `70a1012c7323ee7a07d434a1eb4477708480d7d88933b4ae0e4802705ff7726c`.
- No aggregation/pruning/PhaseII authorization.

The additional seven cells since snapshot002 all completed with valid terminal
format and original evaluator invocation. These are per-cell observations, not
matched method comparisons or a benchmark-wide accuracy estimate.

| Task representative | Planner / network / method | Score | Manager turns | Physical actions / inference | Context rejects | E2E s | Action-artifact transfer bytes |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| LongBench2 | P1 /Slow /A | 0.0 | 7 | 13 /1 | 2 | 120.812 | unknown |
| LongBench2 | P2 /Fast /B | 0.0 | 9 | 7 /1 | 2 | 86.655 | 0 |
| LongBench1 | P2 /Fast /A | 1.0 | 11 | 16 /1 | 2 | 102.246 | 217,558 |
| LongBench1 | P1 /Slow /B1 | 0.0 | 9 | 12 /1 | 2 | 117.808 | 9,427 |
| LongBench1 | P2 /Slow /B0 | 1.0 | 9 | 14 /1 | 4 | 110.204 | 15,861 |
| LongBench1 | P1 /Fast /E | 0.0 | 10 | 24 /1 | 3 | 159.341 | unknown |
| MultiHop1 | P2 /Fast /B | 0.0 | 4 | 4 /1 | 0 | 181.955 | 5,204,596 |

Unknown action-transfer totals follow `read_artifact` size-limit execution
failures lacking complete transfer receipts; they are not filled with zero.
Their context preflight rejections remain separate from actual inference. Each
sample reached one returned inference; service work is separately persisted.
MultiHop's first sample selected A28 and reported152.812s model work; the other
new samples also exercise A4/A5/strong-4090 tool/model selections. Residency of
all five instances does not imply inference on every instance.

No optional cost query was attempted in the two newly observed B trajectories.
That is a pair of specific trace observations, not cross-Planner adoption/pruning
evidence. Quality failures are retained without replacement or tuning; primary
semantic attribution awaits the mandated complete private audit.
