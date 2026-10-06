# Cell110 mixed gate: genuine input-schema defect and separate provider refusals

2026-10-06. This is a preserved diagnosis and tested local generic repair, **not**
an activated new execution freeze, completed affected rerun or queue resumption.
Measured app002/revision955fe8f, historical freezes and evidence remain unchanged.

## Authoritative stopped state

Queue010PID3755889 exited1 at03:54:42Z after cell110
`phase1-multihop_rag-1-29e45040dce39dae-p1-slow-E-attempt1`.
Atomic3896528 exited0; every owned Worker was verified exited and residency passed.
The journal's229records through sequence228 are preserved; settlement SHA
`73a4be5b78ed6ce39db6409475d24c77c9e6ccb371ae5ec928ce54777fc25997`.
Current membership is109effective cells/112settled attempts, zero pending, with
two retained resolved Quote-confounded originals and one unresolved110finding.
No new benchmark call, shaping or ordinary retry followed the gate.

110did not complete; original evaluator was not invoked. Score and format validity
are **missing**, not0. The original admission contains both exact gates:

- `typed_action_failure_requires_audit:validation_failed`
- `unclassified_API_failure_requires_audit`

Independent full admission reproduction matches the original receipt. All134
original evidence files are hash-bound, not overwritten. Actual SDK recipient
contexts26were scanned; no additional privacy/cleanup/residency finding appeared.

## Separate the three observed mechanisms

Nine `bm25_retrieve(text_field="text")` actions failed over actual record arrays
with string `body` and no `text` field. Six source-shard calls and three specialist
derived-artifact calls have exact logical/physical failure receipts. Owning-node
hash/metadata-checked shape inspection covers three original arrays
(1,030/898/919records) and three derived10-record arrays. Bodies stayed on their
owning nodes; only field names, counts and hashes returned. These requests are
field misuse, not a reason to add an alias or tune retrieval.

One specialist `filter_records` action supplied three materialized artifacts.
The **actual provider-request function schema** says `minItems=1`, without
`maxItems`; its description supplies no single-input constraint. Worker execution
calls `_single_input` and rejects anything except one input. Thus the public
system-owned action contract admitted a request that the implementation cannot
execute. This is a genuine harness/operator-schema defect, not just an Agent's
illegal choice. Existing exact field reviewers correctly refuse to waive this
different failure or the extra API gate.

Two raw HTTP400responses separately report exact `data_inspection_failed` input
policy refusals: DeepSeek V4 Pro specialist and Qwen3.8-Max Verifier. The latter
terminates the loop as `logical_loop_failed`/`AgentLoopError`; the earlier specialist
failure is distinct. These are not provider outages, account-balance evidence or
authorized operational replacements. No censorship, provider retry, model change
or claim that the schema defect caused the refusals is made.

The original110trajectory therefore remains a system-confounded attempt, with
separate field-misuse and provider-policy factors. It cannot become a semantic
wrong-answer sample by a blanket validation/API waiver.

## Original telemetry, including missing measurements

Trace E2E199.195s; fixed initial7,696,522bytes/22.048s. Thirty-seven prepared
physical actions include24successful tools, ten execution validation failures
and three model context-selection rejects. **Zero returned model inferences**;
context rejects are not inference. Seven additional semantic-validation and nine
phase-restricted observations may overlap SDK/physical populations and are not
summed as independent additional executions.

Successful tool-work subtotal6.389s and successful action-transfer subtotal0are
not complete totals: ten failed executions lack complete receipts, so complete
tool/action-transfer work and bytes remainUNKNOWN. Root87.758s, specialist53.719s
and completed Verifier29.541s are measured separate work, not an E2E partition.
Failed result has no serialized loop usage; do not invent a completed usage record.

Twenty-six actual HTTPcalls include24known list-price receipts and two refused
calls with unknown usage. Known subtotalUSD0.47265; complete API USD isUNKNOWN,
not that subtotal or0. Graph37nodes/33edges/112snapshots; observed maximum
concurrency6/overlap5.636s. No inference success or benchmark quality is inferred.

## Minimal generic correction, local only

Commit `f633e55` adds one catalog construction line: `maxItems=1` for the five
existing single-input structured primitives (`filter_records`, `select_fields`,
`derive_fields`, `aggregate_records`, `top_k_records`). All already call the same
single-input runtime check. `aggregate_artifacts` remains multi-input. No handler,
argument schema, vocabulary, prompt, Verifier, budget, model, scheduler or evaluator
semantics change. Native function schemas and anonymous static capabilities inherit
this same registry constraint; ordinary semantic validation rejects invalid input
cardinality before physical execution rather than silently splitting/serializing.

Sixteen new tests cover all five primitives' valid/invalid registry inputs,
actual SDK schema and anonymous static contract, semantic pre-execution rejection,
and preserved multi-input aggregation. Before correction:15failed/1passed;
after correction:16passed. Fullpytest **1,195passed in67.18s**, Ruff passed,
strictPyright0errors/0warnings, diffcheck passed.

An independent local capability reconstruction verifies that removing only the
five new `maxItems` entries reproduces the old static contract hash exactly:
`1064a5e3446a1dbf0c99360751cc5e9604efa30cad9c548b650ac13d6963a4c0`.
The corrected hash is
`daf641106bb91e46dbcd354cc0b57f3205bfe840ba7bfcbd9cec0ddac524e013`.
Model classes, operator identities and every other contract field are unchanged.
This computed hash is preparation only; no old/new formal harness file was written.

Historical manifest files are unchanged. Historical-freeze regression assertions
now explicitly require rejection of the corrected capability hash, rather than
silently updating their hashes. The first full run exposed precisely these old
expectations (5failed/1,190passed); the final full run passes with stricter explicit
historical rejection. No new measured harness is claimed ready by these tests.

An exact source/hash-bound scan of all109effective earlier traces found **zero**
prepared multi-input actions for these single-input primitives. Only110is currently
proved behaviorally affected; earlier otherwise-valid/wrong samples must not be
repeated to improve their answers. The corrected exposed schema is nevertheless
a new source/capability boundary and must be reported transparently.

## Immutable remote proofs

| Artifact under resident root | File SHA256 |
| --- | --- |
| `analysis/resident-cell110-mixed-gate-diagnosis-001.json` | `a03af848086dd78c8cb91522340ee3b80d6e016695785993f2d6366b8287c984` |
| `analysis/resident-cell110-confounded-telemetry-001.json` | `c3b8089c7b8bbe59b33b029bbdc550d534a0ffe488eb5e07bbb1c0eb65d516a4` |

Diagnosis binds all original files, actual request schema, exact ten validation
receipts, owning-node shapes, two raw refusal receipts and the unchanged first109
source projections. One preliminary stdin audit used the wrong YAML-helper alias
and stopped before proof writes; corrected independent reproduction succeeded.
This was preparation, not a new formal attempt, replacement or evidence change.

## Required next step, not permission to restart old control009

Prepare a separate immutable execution003/harness capability receipt, actual
Linux/Worker surface validation and an exact110genuine-bug repair lineage.
Inherited Quote repairs4/84must keep their execution002authorizations; do not
rewrite old sidecars/configs/freezes or convert policy refusal into an outage retry.
Then allow only the specifically authorized affected repair and never-started
cells, with the new source boundary reflected in controller, collector and final
audit. No run may begin merely because local tests are green.

At04:11:02Z both Queue010 and cell110atomic handles were confirmed missing;
`queue-exit-010.json` confirms exit1. The unchanged229-record journal file SHA is
`fe7249cca15c2dcddb26fcc438b9ccfde596b9090714c5ddf5b1bc8645b97bf3`.
`execution-freeze-003.json` does not yet exist. This is a verified terminal gate,
not an observation timeout that would justify restarting the same controller.

Complete168effective PhaseI outcomes/private/failure/adoption audit, frozen pruning,
actual PhaseII within420cap and final Q1–Q10remain required. The goal is active;
this stopped queue is an audit/repair gate, not completion or an autonomous pause.

## Later activation, without rewriting this original preparation checkpoint

Execution003/control010and exact affected-only110authorization were frozen after
local/Linux1,213passing tests,34actual-archive regressions and four fresh Worker
surface/residency/exit validation. Queue011was launched04:34:07Z, with no ordinary
samples repeated. [Activation and immutable hashes](large-scale-resident-cardinality-repair-activated-v1.md)
supersede the earlier unactivated status; the mixed original110remains preserved.
