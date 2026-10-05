# Resident-block exact validation review

This records offline admission audits, not a new method or semantic repair.
The active block is `large-scale-cost-guidance-resident-v1`; the old42 samples
remain immutable, separate and unpooled. The execution app remains revision
`90fd30c531f3ad879dcaf5394b7633bcf7b07c3b`, canonical freeze
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.
No Manager/Verifier prompt, operator, scheduler, budget, task, evaluator, model
or measured execution code changed in these reviews. No semantic retry occurred.

## Why the queue stopped twice

The frozen gate deliberately does not classify arbitrary `validation_failed`
errors as Planner failures. It stopped at cells14 and15 for independent review.
Both attempts already completed, produced canonical-valid terminal answers,
invoked the original evaluator, exited their fresh Workers and passed residency
and full effective-recipient privacy audits. Independent complete admission
reproduction matched each original rejected receipt. The original rejection,
hash-linked journal, result, traces and other evidence were not overwritten.

| Cell / MultiHop representative1 | Original finding | Exact evidence | Effective disposition | Original score |
| --- | --- | --- | --- | ---: |
| P1 /Slow /A | `validation_failed` | One model action requested JSON; selected backend completed before the frozen Worker raised `model output is not valid JSON` | Valid post-inference model-format failure, then continued successfully | 1.0 |
| P2 /Slow /B1 | `validation_failed` | Four specialist tool calls requested absent `text`, `content` or `description` fields from a materialized JSON record array | Valid workflow-composition/argument failures, then completed with wrong answer | 0.0 |

Cell14's exact model-JSON sidecar binds78 original files; canonical sidecar hash:
`372ddb783d4c4f205012a678e5ed7d06bbf3b66db6028fa8c98fd16e67617d2d`.
Cell15's exact record-field sidecar binds158 original files; canonical hash:
`b2174a35dd742c453cc9626c391f2d13bfab882fb83c92e8aa3900e0bad5cc28`.
Sidecars remain on4090 under `adjudications/` and
`record-field-adjudications/`, respectively. No replacement was authorized.

## Cell15 record proof and limitations

The root received the correct corpus schema (`body` is a declared string field).
Six successful root BM25 actions used `body` over all three original hash shards.
The specialist concatenated three retrieved arrays into `techcrunch-all`, a
30-record,86,803-byte JSON artifact, using the unchanged whole-record-preserving
`aggregate_artifacts`. Its actual hash is
`aec546934a271ae299c0989749b64847572944817e69084f40f1621150bf76bb`.

While all execution was inactive, a hash/size/metadata-checked shape inspection
ran on the artifact's owning A28 store. Only field names, counts and hash receipts
returned to4090; no record values, private evidence or dataset payload traversed
the PC. Actual record fields do not contain any of the rejected fields. The
successful information-flow producer chain, actual replicas and exact logical /
physical failure messages are bound to the proof. Only `bm25_retrieve` and
`select_fields` absent-field errors matching that proof are admissible; a
different validation, privacy, availability or transfer failure still stops.

The specialist subsequently projected `title/body` successfully. Its initial
assignment had artifact IDs rather than their semantic field schemas. Do not
claim that it received the root's complete artifact schema. This frozen delegated
information-flow limitation is kept explicit, not silently repaired. The
workflow's final wrong answer still requires the phase-wide private evidence /
semantic audit; these four exact errors alone do not establish its primary
semantic root cause or prove that raw profile visibility caused the wrong answer.

Other observed cell15 outcomes: two model requests were rejected before inference
with conservative inputs175,138 and58,024tokens against32K/2048. One read exceeded
the65,536-byte read limit. The terminal model action reached strong-4090 GPU0
inference successfully, with232input/180outputtokens, `finish_reason=stop`.
There was no model-JSON parse failure in this cell. Output and score remain
unchanged; no task-specific recovery or schema alias was introduced.

## Per-cell resource receipts

Work sums can overlap and are not an E2E decomposition. Failed execution lacks
complete transfer/service measurements; unknown values are not replaced with0.
USD below uses the frozen regional list prices, not a provider invoice.

| Metric | Cell14 P1 /Slow /A | Cell15 P2 /Slow /B1 |
| --- | ---: | ---: |
| Manager /specialist /Verifier turns | 6 /0 /6 | 12 /8 /12 |
| Budget-counted physical actions | 15 | 19 |
| Returned successful inference telemetry | 7 | 1 |
| Additional confirmed post-inference parse failure | 1 | 0 |
| Actual inference count | at least8 | 1 |
| Returned model-service work ms | 593,687.787 | 2,009.005 |
| Complete model-service work ms | unknown | 2,009.005 |
| E2E ms | 575,573.220 | 168,441.812 |
| Fixed initial placement bytes | 7,696,522 | 7,696,522 |
| Fixed initial placement receipt work ms | 22,071.459 | 22,034.552 |
| Successful action-transfer receipt bytes | 0 | 57,006 |
| Successful action-transfer receipt work ms | 0 | 406.943 |
| Complete action-transfer bytes /time | unknown /unknown | unknown /unknown |
| API estimated USD | 0.1585326353 | 0.4981514171 |

Cell14's online ledger already kept failed inference work and complete transfer
totals unknown. It was checked against the original root contexts, not corrected
post hoc. The original result telemetry is preserved even where its successful
receipt subtotal is incomplete.

## External audit implementation and continuation

All new code is under the block's `audit-tools/`, outside its389-file frozen app.
Record review implementation: `edf642f`; audited-journal replay regression:
`fd3f65b`; auditor-lock guard: `5d69def`; dependency-source freeze: `0ab3241`.
The failed offline review tool launches are retained in separate directories;
they made zero model calls, zero experiment reservations and zero evidence edits.
The guard skips only its own audit lease, never a live queue/atomic process.
The continuation view verifies sidecars while retaining the original journal.

Verification:1050 full pytest pass (33.47s), Ruff pass, strict Pyright0 errors with
the project interpreter, `git diff --check` pass. Added tests cover derived
whole-record provenance, exact absent fields, source/hash/replica drift,
unexpected failures, original-history preservation, successive adjudicated
journal replay, and rejection of real live queue processes despite an audit lock.

New immutable `queue-control-freeze-002.json` binds all ledger dependency sources,
both sidecar sets and the original atomic entrypoint. Canonical SHA:
`1f1e38d4967d3547358a0716ffbeb7c9a765113e8df48ed996499daf7f0a58a0`.
Its file SHA is
`f1d4ec42c68edbab7836d6687052d1bb256315d50692e42394a8c517b39465e9`.
Continuation permits only never-started scheduled cells; no attempt2, replacement,
model repair or import-path monkeypatch. Measured children import exactly the
frozen app, not the offline audit tools. A new unresolved finding stops again.

## Checkpoint, not a completed study

`analysis/resident-snapshot-005.json`, captured2026-10-05T18:14:45.805945Z,
has15/168 effective admissions,0pending,0unresolved confounders. Two original
rejections remain preserved, with the two independent classifications above.
Snapshot file SHA:
`055653e81c5c7058f1b5135e8eabe983fd53a44da4979ca9c33994e9d481ff2a`.

The queue was relaunched with new process receipt003 at18:15:41UTC, PID1716829;
later liveness and journal state must be re-read. All168 primary cells remain
required before comprehensive audit and method pruning. No accuracy pooling,
method winner, PhaseII authorization or final research conclusion is claimed.
