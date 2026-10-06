# Offline projection schema repair: no measured execution change

2026-10-07, Asia/Hong_Kong. Code commit
`2c0e6403814647f97903dced3f0a4942bb6d926c`.

## Actual defect and preserved failure

The first actual mixed-provider metadata collection reached the retained156
operational exclusion, then raised `KeyError: 'reason'` in the new collector.
The canonical `large_scale_snapshot_v1.read_attempt()` emits `admission_reason`,
not `reason`. The earlier synthetic fixture used the latter and masked the
integration mismatch. No output snapshot was written. Neither a benchmark run
nor the active queue was failed, restarted or changed by this offline command.

The old collector remains immutable in
`audit-tools/resident-rate-audit-control-001`. Failure diagnostic
`analysis/resident-offline-projection-schema-failure-001.json`, SHA256
`ea351b3db376edfbeaa1b40ac6733b6c0130d71eb49107aaa6361a414a69a8d5`,
binds its actual source hash, the canonical reader hash and snapshot051's173
actual settled-attempt field shapes. The original SSH stderr is preserved in
the tool record, not claimed to exist as a separate remote stderr artifact.

## Minimal fix and tests

Read `attempt.get("admission_reason")` and continue checking its exact equality
to the independently verified review reason. Missing, wrong or legacy-only
`reason` records fail closed. No fallback, classification waiver, exclusion
change or evidence rewrite is introduced. Update the fixture to the actual
canonical schema and add missing-field/legacy-alias rejection cases.

The revised tests failed on the original implementation, then passed with the
one-line fix. Full local pytest:1,681passed /7Windows symlink skips,1,688
collected. Ruff passes; configured strict Pyright reports0errors /0warnings;
diff check passes. Actual4090:8specialized tests pass in1.01s. Frozen APP004
archive preflight passes; the actual live-queue private-body guard rejects
before any benchmark body read. Actual Manager/runtime imports remain APP004
only, revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`.

| Append-only artifact | SHA256 |
|---|---|
| `resident-rate-audit-code-only-002.tar` | `7036bf374b3ed5263b92f7620f9c52c570a9098b347df3327b04a8c4516bf92a` |
| `audit-tools/resident-rate-audit-control-002/validation-001.json` | `0fb80b18167cfe8d5abaf552533c89d141a03048cf5f9f98e872db0dc01c6311` |
| New collector file | `1b48d3efb9977869d23ab02de28e12aa5314013dcc2515d1425171fcda54c227` |

Only code/test bytes traveled from the development PC. No Planner/model calls,
Worker launches, tc writes, evaluator calls or private gold-body scans were
performed by this repair validation. Future offline imports must prepend the002
collector namespace before001 and use the existing003rate controller/reviewer
namespace; old outputs and both namespaces remain intact. Actual full metadata
collection and the post168 private/comprehensive audit are separate next steps,
not implied by passing these tests.

## Live execution boundary

At16:36:11Z cell158 Video1/DeepSeek/Slow/E/attempt1, PID1417611, was
independently owned/live and had entered the actual SDK loop. Its four initial
stores were empty; all five resident model identities matched157after-state.
Actual child PYTHONPATH was execution-only and explicit archive revision0ff0e9b
matched. Result remained pending. Proof
`analysis/resident-source004-cell158-live-start-audit-001.json`, SHA256
`3a54e429c3b394375db0885f15f0fd100ec6fb90929bd9b8eb9f81a406bd2404`.

Count remains157/168. No Agent, model, prompt, budget, scheduler, method,
benchmark, evaluator, task or network configuration changed. Full168,
post-block semantic/failure/recipient/adoption audit, frozen pruning, actual
held-out PhaseII and finalQ1–Q10 remain required.
