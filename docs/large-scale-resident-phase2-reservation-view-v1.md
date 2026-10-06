# External reservation-view correction

2026-10-07 HKT. This correction changes external bookkeeping only, not the
frozen Agent/runtime/scheduler/model/method/benchmark contract.

## Reproduced problem and minimal correction

In a synthetic192-cell ledger, one original `_check_reservation` reads the
verified attempt view196times. Its remaining-cell list repeatedly asks for
`completed_cells`; each access correctly revalidates the immutable model-JSON
sidecar, but does so again for every scheduled cell. The startup of actual
controller003 therefore spent substantial time checking hashes/FFmpeg before
cell17. Controller/SSH liveness was verified; no restart was inferred from a
timeout or slow observation. Cell17 subsequently executed normally and ended.

The read-once external adapter now obtains **one freshly verified tuple for one
pure reservation invariant check**, derives pending/completed membership and a
copy of repair authorizations, then invokes the **unchanged original validator
body** against that local view. No validation is cached across checks or later
property accesses. The next check revalidates again. Original ordering, errors,
pending/unresolved rejection, no nominal retry and one operational replacement
rules are unchanged. Full original gates still run at execution boundaries.

A separate copied-function entrypoint reuses the original exact `create_review`
with this reviewed ledger, permitting raw journal replay after an earlier
preserved review. The original raw-only entrypoint rejects such later
reservations. The original strict inactivity guard and exact source/evidence/
JSON failure proof still run; unrelated findings are not waived. It does not
rewrite journal/admission/evidence, repair a model answer or authorize a retry.

## Tests and source binding

Thirteen additional tests cover one-read/fresh-next-check,10original invariant
cases and exact error equality, second known review after a prior raw rejection,
immutable journal/no global mutation/no nominal retry and original live guard
before parent reads. Full local1774passed/7Windows skips,1781collected; Ruff,
strict Pyright with the project interpreter and diff check pass.

Actual Linux135passed. Log SHA256:
`02f1470eef21d6489749b4dcec5d35768be591a99ba339bb8f77b6b372d5249b`.
New namespace: `audit-tools/resident-phase2-read-once-control-003`.
Code-only archive SHA256:
`cac4fa8b8d9dad4fbe6536ec3c3c7206dcd4ab157d8725bb048577cd13d058fb`.
Adapter source SHA256:
`ec67c84c6aff4c9e3b93aa51890de9c31b84bfafcc0c11f9634203e9992081af`.
Namespaces001/002, old controller receipts and all model outputs remain immutable.
No new semantic/model calls were made by these diagnostics/tests.

## Actual cell17, not a retry candidate

Cell `phase2-multihop_rag-4-fffab28c23fbdeaf-p1-fast-E`, attempt1,
completed with valid terminal format and original evaluator score0.
Controller003 exited1 at22:53:05Z because original admission conservatively
flags the two exact known post-backend JSON failures. Journal35records:
15raw valid/2raw confounders/no pending. Only cell16 has a review sidecar at
this preparation checkpoint; the effective settled count is still16.

The actual17th run's full original admission and journal settlement reproduce;
four empty stores, five unchanged resident identities, Worker exit, tc cleanup,
direct successful terminal model text and12actual SDKcontexts pass. Receipt:
`22f2fe0b1d72b5b956d9fd20047d767633fe1fcfc5167fa6673c5542ab20cd2a`.
Exact Worker003/atomic004 source agreement proves both JSON failures followed
backend completion; partial diagnostic:
`fb302da3beebc37aed22c57cd229b8c4e27457f0b8f2e1809577affbe327f54f`.
Do not interpret their negative original inference flags as preflight rejection.

Run17:6Manager/6Verifier/13physical=6BM25+7model requests,4returned successful
model receipts plus2source-proven backend completions;1context rejection and
3logical phase restrictions. No specialist. Graph13nodes/6edges/40snapshots,
peak concurrency3. E2E352.579s; initial7,696,522B/1.108s; returned model
tokens22,619input/1,060output/4stop; complete model work/tokens remain unknown.
Successful tool work2.045s and inclusive successful model-action work190.220s
are not an E2E decomposition or an extra backend-work component. Complete
artifact movement is unknown despite successful transfer subtotal0. API frozen
list-priceUSD0.150308, not a bill. Terminal model has0artifact inputs, which alone
does not establish evidence loss or the causal semantic error.

Next: independently freeze the exact second review and reviewed control, bind
this new adapter receipt, then resume the **next** frozen cell only. Do not
rerun17 or tune its workflow. No full private evidence scan has occurred;
semantic cause/retention and full192/Q1–Q10 obligations remain outstanding.

## Actual second review and source-bound continuation004

The exclusive creator finished normally; journal bytes stayed unchanged.
Second sidecarSHA256:
`7509ddddc81e2fb04bbde3df76175176ead5b362b3048b8809f70999cf461c66`.
It proves exactly2known post-backend model-JSON failures, supplies effective
valid disposition, retains score0 and explicitly forbids replacement. Both raw
rejections and the older sidecar/control/adapter/controller receipts are intact.

Reviewed control002SHA256:
`5754b173e2373853a5eabaa933c818f39013fc85c502f79240dff12a7f53cb52`.
Adapter freeze003SHA256:
`621d76202565e66843bea923b06f24f3b1dccb32e1adc8ad57306c2b116f1f58`.
Validation003SHA256:
`ba9e540ae0698ddd76a90d3a7748992b62e70fc48d65e78a2025d6086fcbbd5c`.
Snapshot016ef36035b6960d0ca502b48e0eb9a47a008c7a78eb5ad5fa144b1b10805de18d9
confirms17effective/17attempts/0pending/2original confounders/0exclusions.

Supervisor2229556/controller2229557 are owned/live23:08:43Z, no exit, original
revision0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd. Supervisor004SHA256:
`458d203c4821ba7bdcf3cf57e2faea5e719faf8f5e409eaf420a6ea4b90db33a`.
They are revalidating the original full gate, not claiming another completion.
Next frozen cell18=MultiHop4/Qwen/Slow/B0;175remaining. No17rerun or new
semantic tuning. The original strict private guard actually rejects this live
controller before body reads (receiptSHA256
`7a49714ec6485ff1c1b1f7e47e6a6a2b8b032c30731477655705e713766650b7`).

The prepared post-block private audit remains inactive-only. When the entire
resolved block is stopped, load its unchanged auditor from private-control001,
this adapter from read-once-control003 and the original frozen dependencies;
pass **reviewed control002 and ledger adapter freeze003** explicitly, not the
older receipt paths in the historical preparation. No private audit is claimed
now. Feedback012checks264actual SDKcontexts; visibility does not prove adoption.
