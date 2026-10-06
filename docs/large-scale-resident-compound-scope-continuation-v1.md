# Exact compound admission continuation, execution unchanged

2026-10-06. This is external experiment admission/control bookkeeping, not a
new method, Agent implementation or measured execution epoch.

Cell154 produced three absent-field BM25 requests and two HTTP400 input-policy
refusals, including the terminal fixed Blind Verifier refusal. The existing
unchanged compound reviewer independently reproduced both findings from actual
artifact record shapes, source provenance, HTTP requests/responses and the
terminal trace. No outage, retry, prompt repair or evaluation imputation is
authorized. Original admissions, results, traces and journal remain immutable.

## Scope change

`scripts/large_scale_resident_compound_scope_queue_v1.py` preserves the exact
parent021 control receipt and all its source-bound historical proofs, including
the SDK argument failure147. It additionally binds the complete current
compound-policy sidecar set, verifies each original/effective admission and
fails closed on missing, changed, unproved or non-nominal membership.

It executes the unchanged launch implementation in a copied function namespace;
only the external ledger factory and control verifier are supplied. Historical
module globals and source files are not mutated. Child imports remain archived
execution004 `src:scripts`, with revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`.
The new audit module is not an Agent/Worker import. No scheduler, schema,
semantic recovery, SDK parsing, model, task, budget or tool-space change occurs.

## Verification

New `tests/test_resident_compound_scope_queue.py` covers historical proof
preservation, both exact nominal proofs, raw settlement preservation, unchanged
execution identity, absent/drifting/unproved scopes, copied-global isolation and
control drift rejection before reservation or physical execution.

| Check | Result |
|---|---|
| Full local pytest |1616 passed,7 skipped (Windows symlink availability)|
| Ruff |passed|
| Strict Pyright with explicit project interpreter |0 errors,0 warnings|
| `git diff --check` |passed|
| Actual4090 targeted regression suite |120 passed,1.43s|
| Actual execution004 archive preflight |passed|
| Additional Planner/inference/Worker/tc actions during validation |0|

The initial remote test collection lacked a shared test fixture. That failed
collection was retained in `validation-collection-failed-001.json`; a separate
code-only fixture archive was added, without overwriting the initial archive or
changing execution source. It was not a benchmark attempt or model failure.

Remote namespace:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/audit-tools/resident-compound-scope-control-001`.

| Receipt | SHA256 |
|---|---|
| Code-only archive | `685815be726a8ea0b1fab7ca6b55476baec67e3c052282862f4ad3fbc504d3b7` |
| Separate fixture archive002 | `7aa4c71a9b69474fbb1208d13f8d29f7fd3309a27e8ab0290a5c18ffc1a755b8` |
| Remote validation001 | `4f9b6a920d7e0ea0b41e5a17a4378a11184f859441f89a60de5e510c1bde0f67` |

This establishes tested continuation bookkeeping only. It does not prove a
running queue, completed168-cell screening, semantic evidence retention, method
pruning or actual held-out PhaseII. No source/benchmark/API body was exported.
