# Held-out Phase II: first settled cell audit

2026-10-07, Asia/Hong_Kong. This is one actual held-out result, not a completed
Phase II report or an optimization claim. Phase I's 168 nominal outcomes remain
closed; historical 42 are not pooled. The preregistered Phase II has 192 cells.

Cell: `phase2-longbench_v2-6-612be14c898ffdda-p1-fast-E`, attempt1. It uses the
unchanged execution004 revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`,
resident model pool, native SDK loop, fixed Blind Verifier, and frozen E rules.

| Recorded outcome/work | Value |
| --- | --- |
| Completion / terminal format / original LongBench score | true / valid / 1.0 |
| Manager / specialist / Verifier turns | 6 / 0 / 6 |
| Prepared physical actions | 4: two BM25, two model requests |
| Successful model inference / context preflight reject | 1 / 1 |
| Actual model selection | A4, `resident-a4-vl4b-v1` |
| Model input/output tokens / finish reason | 5,130 / 2 / stop |
| Model service work | 14.756 s |
| E2E | 61.338 s |
| Agent-controlled transfer bytes/time | 0 / 0 s |
| Initial materialization, separately recorded | 2,032,683 bytes / 0.215 s |
| Frozen list-price API estimate | USD 0.07682918; not an invoice |
| Graph | 13 snapshots; 4 nodes, 2 edges; 3 succeeded, 1 failed |
| Actual action concurrency / overlap | 1 / 0 s |

The first model request failed context preflight without inference. The Manager
then performed another BM25 reduction and invoked the model successfully. A
successful model output supplied the terminal canonical choice; no new semantic
finalizer generated the evaluated answer. Phase restrictions and semantic schema
rejections are also recorded, not erased. This is observed continuation, not proof
that E caused the reduction or improved cost. Single-agent execution is valid.

Original admission was independently reproduced exactly; its canonical receipt
matches journal settlement. Four Worker stores started empty, Workers exited,
and five model runner/server identities matched before/after. Residency validation
passed without startup subtraction. tc restored original qdiscs without error.
All 12 actual SDK contexts (6 Manager, 6 Verifier) had no findings in the existing
recipient scan. E tool isolation was independently checked; six rules-visibility
events do not prove internal adoption. Private gold/supporting-body scans remain
deferred until the entire queue is inactive.

Append-only owner-local audit:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/resident-phase2-first-cell-audit-001.json`

SHA256: `6435a277f031f0da61df026e9bedda53668d30284cfc58a6488fa09869fa2def`.
It binds actual config, trace, result, admission, Worker exit, attempt freeze,
tc, empty-store state and residency receipts. No artifact or API bodies were
exported through the development PC; the diagnostic itself made zero model calls.

The activated controller remains separate from execution004. Further held-out
cells continue unchanged; ordinary failures are retained without semantic retries.
The full Phase II audit and final Q1–Q10 remain outstanding.
