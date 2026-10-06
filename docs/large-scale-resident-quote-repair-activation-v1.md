# Source-frozen Quote repair preparation

2026-10-06. This is an operational repair amendment, not a new method, model
pool, prompt, budget, task set or Phase II gate. See the
[exact defect audit](large-scale-resident-quote-integrity-repair-v1.md).

## Immutable derivative app

Original `.../large-scale-cost-guidance-resident-v1/app` remains unchanged.
All389original frozen source/config/script paths were independently checked
before a remote code-only copy. No benchmark/model/evidence storage was copied
through the development PC. Workers continue using the original app and the
same five already-resident inference instances.

New control-side app:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/app-quote-integrity-repair-002`.
It has392bound paths, with exactly five source deltas:

| Path | Scope |
| --- | --- |
| `src/infra_joint/control/quote.py` | Sort the two unordered requirement sets for action integrity only |
| `scripts/large_scale_resident_queue_v1.py` | Admit the explicit derivative app/execution freeze, without altering Worker/execution behavior |
| `scripts/large_scale_resident_quote_patch_v1.py` | Verify exact delta, prior immutable freeze, tests, task/order, prices, calibration and decoder |
| `scripts/large_scale_quote_repair_ledger_v1.py` | Exact retrospective confounder proof and append-only invalidation, not semantic retries |
| `scripts/large_scale_resident_quote_repair_queue_v1.py` | Authorize affected-only repair plus never-started continuation; stop on new guard defects |

Every other tracked source/config is byte-identical. Core runtime/SDK loop,
operators, scheduler, evaluator, prompts, model pool, network regimes, task
representation and physical transfer implementation are unchanged.
Code/operational amendment commit: `955fe8fc4900586b8c77b2a766702656818a1caa`.

## Tests and frozen provenance

Full project pytest1122passed in53.60s; Ruff passed; strict Pyright0errors/
0warnings; diffcheck passed. This adds20accounting/boundary tests to the1102
hash-repair regression population. On4090,27tests passed in8.09s against the
actual derivative source: the seven hash tests plus twenty retrospective-ledger/
boundary tests, with0benchmark/model calls and no Worker/tc startup.

`readiness/quote-repair-validation-001.json` fileSHA:
`cc3fe582119fdbd7ee25fb4f2d370f4fc297615114f6d0221c24aa767ee4a196`.
It binds the actual source delta and remote regression-source hashes.

`execution-freeze-002.json` canonicalSHA:
`9dd761f7d4022ae262ada59e8f810b4ab2cac7106e50f0817093916861977198`.
FileSHA:
`9153d795bc8898f55b2620f40357dfa22ab5bcb075ab7de780b650430f9deb07`.
It retains execution001as immutable parent and explicitly records the original
Worker app, exact Quote repair, and unchanged conditions.

## Explicit ancillary preparation reconciliation

The `--freeze` command created the source-bound execution002receipt successfully,
but its inherited final ancillary writer still addressed the already-existing
`readiness/residency-at-freeze-001.json`. Exclusive creation raisedFileExistsError;
the command exited1. This is a preparation defect, not a formal cell or model
failure. The old readiness record was not overwritten.

The already-produced execution002was independently recomputed and matched.
A separate read-only attestation then recorded all four nodes/five resident
instances in `readiness/residency-at-freeze-002.json`, fileSHA
`e21aaaa8c0203490e81dd756f21a5ab81c20ab8bed873fd6b90533b59728f028`.
No source/freeze changed during reconciliation, no models were reloaded, and no
Worker, Planner, benchmark or tc action was started. The inherited `--freeze`
command is not claimed to have exited0 and must not be replayed over either
immutable receipt.

Explicit reconciliation receipt fileSHA:
`9e80666b0667836ccbd488574f84390c7f71abb9c2cfc28d8a7b0ca98b5af718`.
Path: `readiness/quote-repair-freeze-reconciliation-001.json`.

## Remaining activation gate

At00:59:30Z, exact authorization processPID3239812 was verified running with
CPU progress while revalidating the original85-attempt journal and historical
scoped sidecars. No retrospective invalidation/repair reservation was yet
committed at that observation; no new formal run had started. Do not infer
completion or restart this process from a timeout/slow poll.

Only the two proven original attempts (cells4/84) may receive append-only
`quote_integrity_confounded` events, followed by existing generic-repair
authorization bound to execution002. Their original records/evidence stay
immutable. Then freeze the exact new controller and run repaired missing cells
in the inherited schedule order, followed by only never-started cells. Ordinary
wrong answers, semantic failures and unaffected nominal cells remain non-retryable.

All168effective cells, complete private semantic/recipient/failure/adoption audit,
frozen pruning and actual PhaseII remain unfinished. The full user goal stays
active; this preparation is not experiment completion or a formal pause.

## Subsequent exact offline-review repair

The first authorization process exited before writing any retrospective sidecar,
authorization or new formal reservation. Its reviewer mistakenly used the
receipt-provenance JSON encoding (with whitespace) to replay the original action
hash, whose frozen encoding uses compact separators. The actual ten source-bound
Quote rejections were independently rechecked with compact encoding: six in
original cell4 and four in original cell84. No Agent changed the quoted action.

Commit `43591e3` fixes only that offline replay and adds a whitespace/Unicode
regression. Its separately preserved remote audit directory004 does not modify
the immutable measured app002 or execution-freeze002. That review passed all
ten actual proof checks and28remote regressions. A subsequent preparation was
explicitly interrupted before any sidecar/journal mutation because its inherited
membership calculation revalidated the same full effective view once for every
scheduled cell. The interruption released its lease and retained the original
171-line journal exactly; it did not interrupt/repeat a benchmark cell.

Commit `aad3192` uses the existing snapshot-ledger pattern: independently validate
the effective admission view once per membership calculation, then select admitted
IDs in the frozen order. It introduces no cross-call cache, discarded proof or
changed admission/retry rule. The new regression checks that later state changes
are revalidated. It also adds a read-only source-aware collector which accepts
only the original85-attempt prefix under execution001 and later authorized
attempts under the exact repaired execution002. Confounded originals remain
visible, but are explicitly ineligible for comparative samples; no scores are
pooled or pruning authorized.

Latest validation: full pytest1132passed in52.60s, Ruff passed, strict Pyright
0errors/0warnings, diffcheck passed. Actual4090tests37passed in7.82s, including
the original hash tests, exact-ledger/boundary tests and source-aware projection
identity tests. The actual reviewer in separate remote directory005 hasSHA
`4c4f698a886a5014a1d5f1020b3a8acaa7164669bb9daf8089f289b133c10c28`.
Receipt `readiness/quote-review-encoding-validation-002.json` fileSHA:
`e111d765d41b565719c675718bd95272553f0f60bd94fc5f9efc36974bbedee8`.

New authorization preparationPID3365000started01:31:48Z with directory005first
on its offline import path. Measured children still import only immutable app002;
Worker code remains original. Formal execution revision remains955fe8f and
execution002canonicalSHA remains9dd761f7d4022ae262ada59e8f810b4ab2cac7106e50f0817093916861977198.
Do not infer its completion from these tests or from source deployment alone.
