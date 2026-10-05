# Resident cell 64 — exact post-inference JSON-output audit

2026-10-06, Hong Kong. This is one-cell progress evidence, not a completed
168-cell study, method pruning or authorization for Phase II.

## Preserved original finding

Cell `phase1-longbench_v2-1-233652563a5a9ff2-p1-fast-B1`, attempt1, settled at
`2026-10-05T22:07:31.661411Z`, sequence128. The original admission and journal
remain unchanged: disposition `confounder`, sole problem
`typed_action_failure_requires_audit:validation_failed`.

Original admission canonical SHA-256:
`ff23c987d1351628a1961d60e455dd5421faa0d55d33c9676aec9167f20d1876`.
Original settlement entry SHA-256:
`7b6d47508f6c0de5e4d851a5b951a6ce66c161cf48bd171f6d33ef886f9c592a`.

The task itself completed with a canonical terminal answer, format validity
true and original LongBench evaluator score1.0. A failed intermediate action
does not imply failed task completion or authorize replacement.

## Exact classification, not a validation allowlist

The existing independent reviewer reproduced the full admission, verified
Worker exit/residency, bound all218 original evidence files, and confirmed
exactly two model-output parsing failures:

| Action | Action canonical SHA-256 |
| --- | --- |
| `specialist-b:call_6f643aeaf0fc4b44bffd3ebf` | `865d14f514ae2030a4e3b8895ec7f6b16d011f315984b7f814523e349c061e0a` |
| `manager:call_f127c70f35db4bcdbc8100dc` | `71000f8b80356648e41f3a1ef8bde0a5274bee8ca065267cc2ddd7e4ed114c7e` |

Both requested exactly one materialized `application/json` output. Both had a
concrete strong-4090 GPU0 resident27B selection and matching logical/physical
`model output is not valid JSON` failures at execution stage. The hash-bound
frozen Worker source awaits backend completion before raising that exact
parsing error. These actions **reached inference**; they are model-output
contract failures, not context rejection, unavailable deployment, missing
operator or a runtime defect. Their service time/token totals remain unknown.

The effective admission is valid with reason
`audited_post_inference_model_json_failure`. The original rejection is not
rewritten. The review authorizes neither rerun nor model/prompt repair.

Remote append-only sidecar under
`large-scale-cost-guidance-resident-v1/adjudications/`:

- Canonical sidecar SHA-256: `9f4e6e36575cf56300529dd398a6b91e43cf500ffbc818aba1f1349e15cb4ff4`.
- Sidecar file SHA-256: `263f93bb34078167e29b7959efaa0cb26495c4d57e63972ab93349ba7322784c`.
- Effective admission SHA-256: `fa56e12b8a5041b8bf8d617c7eea71cb1779d43cd50b12c2d5a555cc23e1e86b`.
- Independent per-cell projection file SHA-256: `dbbf3d200ba639c0f1ef3eedf54989014159bcf7ea4dccd772c3bbfa044c2ce1`.

## Actual trajectory and cost boundaries

| Measure | Cell64 observed value |
| --- | --- |
| Manager / Verifier turns | 13 / 13 |
| Specialists created / total reasoning turns / peak active | 3 / 21 / 2 |
| Physical actions | 42:32tools,10model requests |
| Successful tools / successful models | 30 / 3 |
| Confirmed inference count | At least5:3successful +2exact post-inference parse failures |
| Context rejects / oversized reads | 5 / 2 |
| Other logical validation failures | 3; not silently repaired |
| Recorded graph | 42nodes,34artifactedges,127snapshots;33succeeded,9failed |
| Logical action owners / InformationObject handoffs | 4 / 3 |
| Actual action concurrency / overlap | max4 / 3.088s;one cross-owner overlapping pair |
| E2E | 365.188s |
| Fixed initial placement | 514,789bytes / 0.287s |
| Successful action-transfer subtotal | 15,966bytes / 0.504s |
| Complete action-transfer bytes/time | UNKNOWN:four failed execution receipts lack complete measurement |
| Successful tool work / complete tool work | 1.341s / UNKNOWN |
| Returned successful backend work / complete backend work | 98.017s / UNKNOWN |
| Returned successful model input/output tokens | 4,132 / 740;three stop finishes;failed-inference tokensUNKNOWN |
| Actual SDK recipient contexts audited | 47,allpassed original admission/privacy checks |
| Cloud API list-price cost | All47usages known,USD0.7803408682;not an invoice |

Executed tools include13reads,16BM25retrievals,oneaggregate,onefieldselection
andone top-k reduction. There are ten model actions:one abstract requirement
classified statically impossible andnine statically feasible; five actual
context rejects remain preflight failures, not inference. A static-feasible
requirement is not proof that the supplied artifacts fit the context envelope.
One active-specialist-budget rejection is visible in SDK observations; it is
not a deployment failure or evidence of changed budgets.

Manager/specialist/Verifier measured work111.352/144.137/53.863s overlaps and
must not be summed as an E2E decomposition. Failed execution work4.942s does
not recover missing backend/transfer metrics. The frozen returned-inference
flag's false value must not be interpreted as proof of no inference for these
two parsing failures. Structural frontier16 is not sixteen-way execution.

This B1 cell demonstrates natural continuation after typed failures and
successful MAS execution. It does not establish that raw profile visibility
caused recovery, quality preservation or resource reduction. Full private
semantic/evidence-retention and matched causal audit remain pending.

## Frozen continuation gate

No source/prompt/model/scheduler/budget/benchmark changes were needed. Full
pytest1095passed, Ruffpassed, strictPyright0errors/0warnings anddiffcheckpassed
before creating the new separate offline control freeze007:

- Canonical SHA-256: `114c0d391c1229701d746275707053434a11a77b02174d487f30b288457089c1`.
- File SHA-256: `d000e831aceaccbd023214841aa26ad27271a3453810245cd9764c63bb391b6d`.

Execution freeze001 remains
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.
Old42results remain closed/unpooled. Only never-started scheduled cells may
continue after actual ledger verification; no automatic attempt2. All168
primary outcomes, comprehensive audit, frozen pruning, actual PhaseII and final
reports/Q1–Q10 are still required. No completed-goal claim is made here.

## Stable full-block boundary and actual continuation

Read-only snapshot020 completed at `2026-10-05T22:24:25.299832Z`, proving
64effectivevalid admissions /64attempts /0pending /0unresolvedconfounders.
Allseven original confounded receipts remain:two exact JSON-output reviews,
one exact materialized-record-field review andfour provider-policy reviews.
No operational exclusion/replacement, score pooling, comprehensive-private-audit
completion or pruning permission is inferred.

- Snapshot file SHA-256: `8dc0c5a77259f809b4b992c5e1e923965699391abf1592a5be19af44550512d1`.
- Stable journal file SHA-256: `6e47652714442981a164df233a51637372d2868959578f235a7f0482f76440d0`.

Queue008 actually launched at `2026-10-05T22:25:25.110720Z`, PID2678456, with
new exclusive `queue-process-008.json` / `queue-console-008.log` andcontrol007.
Its real `/proc` command line was verified. Startup revalidates the ledger;
no new cell is claimed before its reservation. The launcher bound snapshot020,
unchanged journal, exactcontrol and executionfreeze. Measured children retain
only frozen app imports; offline reviewer imports do not enter Agent execution.
Check current process/journal before relying on these historical handles.
