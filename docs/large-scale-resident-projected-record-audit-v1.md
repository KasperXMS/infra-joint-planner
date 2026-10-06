# Resident projected-record audit: no semantic repair or replacement

## External replay repair validated and frozen

Code-only commit`7ca9725` introduces the separate v2controller, leaving all
v1sources, controls, proofs, runtime and completed evidence immutable. Actual
expanded308record replay reproduces the original parent freeze. Fullpytest
1411passed; Ruff/configured strictPyright/explicit controller strictcheck passed;
actual4090offline193tests passed. Regression includes a later successful cell
after the reviewed raw confounder: the historical ledger refuses it, the new
ledger admits the same immutable journal, without any semantic replacement.

New control-freeze013 fileSHA
`a06073aefa13d0363ec403ab7ffa9756ed62b20d7eec8ea0f5ed00cde674d8a5`,
canonicalSHA
`a676dae4108630aa1b21eef39876214ab6d626a3403ea53f6ae466ce7ad88bf5`.
Readiness003 records actual source equivalence and unchanged execution004.
Queue014 has been launched from this new receipt to continue only remaining
scheduled cells. A live PID/first-dispatch check is still required before claiming
actual atomic execution; Queue013 remains terminal, not retrospectively resumed.

## Controller-only replay defect:Queue013 halted08:08:23Z

The completed ninth E sample remains valid. Before dispatching another cell,
the old parent controller tried to replay the expanded journal with its historical
ledger, which cannot interpret the new projection proof. It correctly failed
closed on the apparent unresolved confounder. No new reservation or failed
benchmark cell resulted;120valid settlements remain. The defect is in external
control-version compatibility, not measured Agent/Worker execution. Exact stop
receipt:`analysis/resident-projection-parent-replay-defect-001.json`; original
console/exit/source/control receipts remain unchanged.

A new external v2controller is under regression/full validation: it reconstructs
the original parent source/evidence/authorization freeze but uses only the
projection-aware ledger for expanded-journal replay. It does not weaken the old
controller, authorize semantic reruns, or touch execution004. This is a pending
repair, not a claim that Queue013 is still live.

## First continued atomic settlement:08:07:43Z

MultiHop2/P2/Slow/E/attempt2 has settled valid, completed/format-valid/score1.0.
Effective count is now120/168. All four pre-materialization Worker stores were
empty; all four owned Worker processes exited and5resident models passed.
Every actual Manager request remains E no-query;8SDK recipient contexts audited.
Full application trace and request bodies remain remote. Admission canonicalSHA
`30c7519fecd41da19219fadb96a80d6450b80c3002434b9938e621b5d59f92ec`;
append-only bounded run audit fileSHA
`839bb02078fbe176ca37924bb90d32e513248a22b5bc6dabd85b176fd9e87ac5`.

Actual sequence:3shard-local BM25 actions; model over3results rejected before
transfer at44,039estimated input +2,048reserved versus32,768; then terminal
model uses only shard1retrieval onA4/Qwen3-VL4B. One inference,3successful tools,
4Manager/4Verifier,5physical calls,0specialists,16graphs/5nodes/4edges. Model
3,995input/3output tokens,stop,11.629sservice;1.193stool work. One SDK
phase-restricted aggregation attempt is not an extra physical execution.

E2E75.550s; fixed corpus placement7,696,522bytes/22.246s stays separate. Complete
action movement0is supported by the receipt: the failed action stopped before
movement and the successful terminal artifact was already onA4. This is **not**
quality-preserving optimization evidence: required-support retention is still
unaudited, and using only one shard can discard previously retrieved evidence.
Score1does not establish semantic sufficiency or causal method benefit.

## Actual continuation:08:05:51Z

Queue013 has reserved the next still-unfinished, previously authorized E repair:
MultiHop2/P2/Slow/attempt2. Actual journal sequence306, reservation SHA
`c82328a36dbe3b965509e933dff2f6564de03f4ebf02a405511b0254716dfb3c`.
It uses exactly execution004. Snapshot041 remains the immutable pre-dispatch
119/136/17/0 view; the live journal now additionally contains this reservation,
not a120th settled sample. No audited valid cell was repeated.

## Exact review reproduced:2026-10-06

The actual remote sidecar reproduces the full successful projection ancestry
and passes source/evidence/replica checks. SHA256
`cde11f3bf66ab13a29b4775a84046dfc554a1b352162233633401a74582b8c38`.
The new read-only view admits **119/168** cells from136retained attempts, with
17historical excluded confounders and0pending. The journal remains exactly its
original306records/hash below; no benchmark cell was rerun to obtain this view.
The score1sample is retained as successful completion with a recoverable
composition/absent-field misuse, not classified from score alone.

Snapshot041 at08:00:43Z binds this exact119/136/17/0 scope, SHA256
`bb3fb9206eda65d537c4c6136bfb754c2ccf07f03bbd9b5f9a6d44dc30f89e99`.
New control-freeze012 fileSHA
`cbf9ec7293db55bd0c1a9fb8d4eda98ca58ab3ab853d0e10bc59ac9f0a23ead6`,
canonicalSHA
`40f8bf3d77bdda5d21edfadc04814744daf0eefbd18ab93a5264794d47dd0b03`.
It binds the old control011 without altering it, new exact sidecars, sources,
same17 affected-only genuine repair authorizations and measured execution004.

Queue013 controllerPID422310 was launched08:02:11Z and verified live08:04:06Z.
At that check it was still revalidating control; no new atomic dispatch was yet
claimed. The original balanced schedule, no ordinary retries and fresh Worker
stores remain. The actual private-body/gate/PhaseII guards all reject before
input while this controller is live. Passed guard receipt003 SHA
`b4fd10349caad0132644b5305612001667bad9d508b4a794b859be31bec4a856`.

## Preserved stop

Queue012 stopped normally at2026-10-06T07:36:48Z after its eighth execution004
E attempt settled. This is an exact admission audit, not a new method, runtime
change, result-dependent prompt change or permission to retry a correct answer.

Run:`large-scale-cost-guidance-resident-v1-phase1-multihop_rag-1-29e45040dce39dae-p2-fast-E-attempt2`.
Raw admission is a confounder pending the prescribed validation-failure review;
the task actually completed, format-valid, original evaluator score1.0.
Journal306records SHA256
`9b95cd814a75e73ea88c12209efd869477f351f57cc302b205ce1ff4a1ed511d`.
Original canonical admission SHA
`e32422cbed6d0867bc23bc83eef93bc5d9a5e5995dd8755033a74ec0a7522fbe`.

All failed and successful actions remain in their original trace. No field
alias, retry, injected schema, strategy hint or replacement run was performed.
E Manager request tools are no-query/quote/comparison;18 actual recipient contexts
passed the frozen admission audit. The Planner-created specialist`tc-verifier`
is not the fixed infrastructure-blind Verifier.

## Exact failure and evidence path

```text
3 original corpus shards (record-array schema; body:string)
  -> BM25(text_field=body, top_k=5) on each shard
  -> select_fields(title, body, source) on each result
  -> aggregate_artifacts:15 records,36,027 bytes
  -> specialist BM25(text_field=text, top_k=10)
  -> typed validation_failed: document field must be text: text
```

Actual materialized input has only`body/source/title`, all bodies are strings.
Artifact SHA256
`dfa713f502d1a13f278234002994b502e5f2947c7fd9d226772aba115d89a46e`.
Inspection remained onA28; only shape/hash metadata reached the development PC.
The successful generic projection preserves the original body values. The
requested`text`field does not exist; silently aliasing it would change execution.
One other model request was rejected before movement/inference at85,400estimated
input tokens plus2,048reserved versus32,768context. That reject is not inference.

Root initial schema is established. Whether the specialist received sufficient
derived-artifact schema is not asserted by this provenance proof and remains
explicitly unknown; post-block recipient/semantic attribution remains required.

## Historical reviewer rejection is retained

The original whole-record reviewer correctly refuses to infer preservation
through an operator outside its whitelist. Its rejection was reproduced and
preserved, not overwritten:
`analysis/resident-projected-record-review-stop-001.json`, SHA256
`56998989d1646c8f0b0ef158f9f861e9c00bcaf7674a2696ffd3972efa73ced3`.

The new reviewer accepts only successful, source-bound body-preserving
`select_fields`ancestry, actual input shape and exact paired logical/physical
absent-field failure. It rejects body removal, unknown/failed/unexecuted
producers, source/evidence/schema/replica drift, extra failures and privacy or
provider findings. Historical reviewers/controllers/sidecars stay immutable.

## Validation and scope

Code-only commit:`23f2fea`. Full localpytest1402passed; Ruff, configured strict
Pyright, explicit strict checks of6audit/controller scripts and diffcheck passed.
Actual4090 offline184tests passed in a separate validation namespace; no Agent
call or measured runtime change. The initial archive-deployment check without
the exact frozen revision environment failed closed before any newcell/proof.
Measured application remains execution004/revision`0ff0e9b`, not this audit commit.

The new external ledger/controller/collector and future private/gate consumers
share the same precise audit view. Only a reproduced sidecar permits effective
admission and continuation of unfinished scheduled cells. Raw journal/admission
and all historical evidence stay untouched; this sample cannot be repeated.

Two diagnostic import-path failures for offline private dependencies are retained
as guard receipts001/002, distinct from actual benchmark evidence. The successful
check used the existing immutable`resident-four-epoch-audit-001/scripts`closure
after the new namespace and archived dependencies. No live controller file or
its child environment was edited, and neither failed check reached body reads.

This is not full168-cell screening, quality aggregation, private semantic audit,
method pruning, PhaseIIexecution, or goal completion. All remain required.
