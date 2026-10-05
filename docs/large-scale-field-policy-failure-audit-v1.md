# Initial-corpus field misuse and provider-policy audit

2026-10-05. Original cell: MultiHop-1 / DeepSeek / Slow / B, attempt1,
`phase1-multihop_rag-1-29e45040dce39dae-p1-slow-B`.
The queue stopped; parent2448151 and atomic child2471034 are verified absent.
Worker shutdown reports all owned processes exited, zero cleanup errors.
This is not a retry or a new semantic experiment. The formal app remains
fa19e0b / execution-freeze-003; all historical evidence remains immutable.

## Original outcome and costs

No terminal answer or evaluation: result score/format are null, not zero.
E2E125.127 s is recorded by explicit run.failed. Initial materialization is
7,696,522 bytes /22.189 s; recorded successful action-transfer subtotal is
70,251 bytes /0.406 s. Full action transfer is unknown because execution-stage
failures lack complete movement receipts; the subtotal is not savings evidence.
Successful operator work7.200 s overlaps other work and is not an E2E component sum.

Five Manager turns,16 specialist turns across two created specialists and five
Verifier starts occur. There are33 prepared actions:31 tools and two model
actions. Nineteen tools succeed. Both model actions fail context preflight
before physical selection/inference; physical model-service work is measured zero
for this empty inference population, not an assumption about failed backend work
or cloud API charges. There are zero missing prepared-action physical receipts.
Graph:100 snapshots,33 action nodes,8 information-flow edges, two handoffs.

Logical failures:8 validation_failed,4 artifact_too_large,2 context_limit_exceeded,
5 semantic_validation_failed,3 phase_restricted and1 artifact_not_materialized.
Those counts may include pre-physical failures; they must not all be interpreted
as physical executions. B has two observed root ready-action decision opportunities,
zero optional cost-query attempts and zero valid cards. Under-use is retained.

The terminal failure includes provider HTTP400 data_inspection_failed. Actual
specialist DeepSeek and fixed Qwen Verifier responses both carry exactly
`Input text data may contain inappropriate content.` This is not quota depletion,
timeout, context overflow at the cloud endpoint or a confirmed provider outage.
Missing refused-call usage and total API monetary cost remain unknown.

## The validation finding is not the preceding invalid-JSON case

All eight validation failures are `bm25_retrieve` on initial corpus shards:
six requests use text_field=text, then one content and one article.
The operator's exact message is `document field must be text: <requested field>`.
No failed call has an invoke_model JSON parse, so the old JSON/policy compound
reviewer correctly refuses to classify this cell.

Frozen input payloads are independently hashed and parsed on4090. Shards contain
1,030 /898 /919 records; every record has its declared string body field.
Text/content/article are absent in every record. The payloads match the task
content_schema and final Worker metadata. This is not corruption, schema/data
mismatch, a missing primitive or historical artifact-store collision.

The root Manager's actual first input contains the correct artifact schemas.
The actual specialist inputs contain assignment + static operator/model capability
contract, not the root task. The assignments contain artifact handles, roles,
objectives and instructions, but do not forward the body-field schema. The frozen
specialist interface follows the Manager's assignment; it has never promised an
automatic copy of the global task. Consequently, distinguish delegated information
flow/composition and ensuing field misuse from a missing primitive or a physical
feasibility signal. **Do not claim that specialists received the root's schema.**
This is an important limitation of the frozen delegation contract, not evidence
that infrastructure-aware information would remedy the failure. No automatic
schema injection, guessed field remapping, prompt tuning or Agent repair is added.
No previous stored trace has this same BM25 field failure, based on a read-only
structural scan; private supporting-reference/body coverage is not audited yet.

## Narrow offline proof and tests

New independent readiness modules, outside the frozen execution app:

- large_scale_field_policy_review_v1.py: exact full finding union, frozen initial
  source ownership/hash/record-shape check, actual Worker metadata, root input
  schema, prepared action, selected Worker, exact execution failure, closed failed
  action and exact raw provider request/response proof. All findings must match.
- large_scale_field_policy_queue_v1.py: immutable parent control006, new sidecar
  namespace and full source/evidence verification; only original unstarted cells.
- large_scale_field_policy_snapshot_v1.py: compose all old reviews and the new
  field/policy view, preserve unknown quality/cost and restore base collector globals.

Every original evidence file and the operator/delegation source are bound by SHA-256.
The original admission/journal/result/trace are not rewritten. No replacement is
authorized. A sidecar may classify this nominal failure only after independent
complete admission reproduces the original rejection and both exact proofs pass.

New31 tests cover missing root schema, actual source/schema/hash mismatch, wrong
operator/model/message/stage, duplicate observations, absent selection/closure,
unrelated policy/quota failures, path escape/symlink, source/evidence/proof/cache
tampering, coexistence of all four review types and original-next-cell execution.
Full pytest916 passed in29.38 s; Ruff / strict Pyright / diff check pass.
Offline code commit532f40db931faed2631cb7c2f0b23755a3ac1067.

Bound cost-only audit on4090:
`analysis/field-policy-cost-audit-001.json`, file SHA-256
`1af2010100479bb70c2a0f68b874ca60fe0e2b650c35c7aedd5c53b168ad443a`.
No dataset payload, private supporting evidence, raw API contexts or complete trace
passes through the development PC. Nothing is fed back into online agents.

## Current gate

Independent full proof completes successfully; offline PID2571271 has exited.
It binds127 original files, all eight field failures and both exact provider
refusals. The same nominal failed attempt is classified; no repeated task.
Original journal/admission are intact. Classified progress is31/168, with27
completed/evaluated and four unevaluated nominal failures. Complete snapshot026
verifies31 admissions /33 attempts /0 pending /2 preserved implementation-confounded
attempts, with zero operational exclusions. No private evidence quality audit,
screening/pruning or Phase II is authorized at this point.

Field sidecar canonical SHA-256:
`3323b245bd02c1e2c4602dec5f890f0e635382f367134596e2127ffb2d6a0fb5`;
file SHA-256:
`a9e6c735fda2ffc057c442a850c3c8c97e59a48558ec8b5ea86ed7da4acfcf4a`.
Original admission canonical:
`8bf81e64166918389c19e5e5e28d6766fc4e67193c527e68c366c1166842d46a`;
reviewed admission canonical:
`85642fc4a1d83172956545ff2d5c3a1cd1d36e036981d46faea6cfbc9276ac25`.
New queue-control-freeze-007 canonical:
`06862ee7f45fe55520ba7fcc89edd208d3bdd7f986d36ec7b1c3b6cfa0a84fbb`.
Its complete immutable control006 parent reproduces unchanged, as does formal
execution-freeze-003. No prior controller/reviewer/freeze is edited. Private
coverage, method pruning and Phase II remain gated by the full168-cell audit.

Snapshot026 file SHA-256:
`b64f153546be7f99ae5928a9c87a6818a181d220af60c89bf63b83debbcb0981`.
The independent graph audit closes all33 actions (19 successes /14 failures),
has zero dependency-order/interval/closure findings,33 structural growth events
and three logical action owners. Peak physical concurrency6 /overlap5.855 s is
not six logical agents or proven E2E benefit. Action-only dependency path1.637 s
excludes SDK reasoning, Verifier and control overhead, so it is not full critical
path or E2E. Bound graph audit file SHA-256:
`facad9b00cdc6c883aa093f6e17010d1d8e5bd0206321d62e0caaa79fb251f52`.

Both offline audit and snapshot processes are confirmed exited before launch.
Queue008 parent2599603 is actually verified live, using control007 and unchanged
execution003; original next cell is MultiHop-1 / Qwen / Fast / C. No failed or
wrong-answer cell is repeated. All old controllers, freezes and evidence remain.
