# Resident source004: compound field misuse and provider-policy failure

Captured 2026-10-06. This is an offline admission audit, not a semantic repair,
new execution epoch, retry, quality claim or method-selection result.

## Exact attempt and disposition

Cell: `phase1-multihop_rag-1-29e45040dce39dae-p1-slow-E`, attempt4.
The preceding attempt3 ended in a fixed Blind Verifier 180s API timeout and was
operationally excluded under the existing one-identical-replacement rule.
Attempt4 is that sole replacement; it is **not** replaced again.

Actual attempt4 ended at 09:14:59Z. Queue015 and its atomic process were confirmed
exited. Its raw admission contains precisely two findings: an absent-field BM25
validation failure and unclassified API failure. Both findings are retained and
independently explained by an append-only source-bound sidecar:

- One specialist requested BM25 `text_field=text` on a successfully materialized
  whole-record aggregate. The actual artifact is 85,825bytes /30records; `body`
  is a string in every record, while `text` is absent. Three initial body-schema
  shards feed successful body-field retrievals, then aggregation, then the bad
  field request. The unchanged record reviewer proves this parameter misuse.
- Two actual HTTP400 responses, one specialist and the terminal fixed Qwen3.8-Max
  Blind Verifier, report `data_inspection_failed`: input text may contain
  inappropriate content. The unchanged provider-policy reviewer proves both.
  This is **not** a service timeout, connection failure or provider-wide outage.

Primary failure: provider input policy. Secondary: workflow composition /
absent-field misuse. The effective admission is a **valid nominal failure**,
not successful completion. Evaluation was not invoked; quality remains unknown,
not zero. No input censorship, output repair, gold lookup or hidden retry occurs.
Root body-schema receipt is established; specialist schema receipt remains
unknown rather than assumed visible or absent.

## Bounded telemetry

| Metric | Actual persisted scope |
| --- | --- |
| Execution /evaluation | incomplete /not invoked |
| Manager /specialist /Verifier calls |4 /14 /4; one specialist and one Verifier API refusal |
| Specialists /handoffs |2 /2 |
| Physical actions |22:19tool attempts,3model attempts |
| Successful tools /actual physical inference |18 /0 |
| Model context rejects |3,all before inference |
| Other typed failures |1absent-field BM25;6phase-restricted calls |
| E2E |139.727s,explicit `run.failed` receipt |
| Fixed initial distribution |7,696,522bytes /22.036s,separate setup |
| Successful action movement |112,414bytes /1.034s,4receipts |
| Complete action movement |unknown: failed execution movement is unmeasured |
| Successful pure tool work |4.548s; complete pure tool work unknown |
| Physical model work /tokens |0 /0input /0output,proven pre-inference rejects |
| Execution-grown graph |67snapshots,22nodes /24edges |
| Cloud API |22calls,20with known LIST-price usage;2unknown |
| API known subtotal |USD0.1762202248236091; complete cost unknown,not an invoice |

The API subtotal comprises Manager USD0.04944733387368953, specialist known
USD0.09386885555215987 and Verifier known USD0.03290403539775974. Missing failed-call
usage is not estimated as zero. The 22 actual SDK recipient contexts passed
privacy/method-surface audit; every E Manager request has no query tool. All four
fresh Workers exited and all five model instances remained resident.

This audit does not read private supporting-evidence bodies to assign semantic
quality or claim evidence retention. That full-block audit still waits for168.

## Immutable provenance and verification

All paths below are relative to the4090-owned root
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Receipt | SHA256 |
| --- | --- |
| Raw admission canonical |`fe4f025f9f136183bccc2dc874b390bf667ca95bba2a4fb7fb33ab666f7b2bed` |
| Seq315 original settlement |`42f528323f5f9a9d7de52e1744157c20bd67e2c96e9aaa0213cbc664df57690f` |
| Compound policy sidecar file |`02726bef51bd9d7b55f52c8fa68abbd090fceee87d281bc5e3eb59148de805a1` |
| Reviewed admission canonical |`1e573fe00c826210832d686cbc8e794595941c748bed38048655d998de4f15cc` |
| Bounded settlement audit |`8b8f063cd49abcd572a5ff48ad7e2e63f68d043a29277499732bdf7fd541efe2` |
| External control015 file |`9ff88aca201824b1d48d561198463bd4a6f433ad7f78cdb179ac5ad5c3b0fecf` |
| External control015 canonical |`31da4ec46d75eeb7aa3e651f4ab2784f62e733a353379204a4d33b600420e249` |

The original admission was independently reconstructed and matched, including
all source/evidence/actual-artifact hashes. Original journal, result, trace and
historical review files are unchanged. Effective membership is123/168,
17historical genuine confounders,1operationally excluded attempt,0pending at
this review boundary. The failed replacement is not another operational exclusion.

Audit commit `01ae1f7` adds only separate offline review/control/snapshot code and
tests. Measured execution remains source004 /`0ff0e9b`, Workers remain source003.
Full pytest1500passed (83.38s,no skips), Ruff, configured strict Pyright plus the
three new scripts and diff check passed. Actual Linux43tests passed (1.31s).
Code-only archive SHA256
`77935067a6048f859f6247633cd99f508ccbfa6a7eb2860e36c57c5459d3737d`.

## Actual continuation boundary

Readiness receipt SHA256
`e136b766fa610fb44105a6d92405605244ea06281507f37d60554da563a692d6`
binds full validation, control015 and unchanged execution004. A bootstrap import
path typo failed before ledger/reservation/model activity; its separate stop
receipt is retained. Correcting only the external process search path changed
neither measured sources nor experiment configuration.

Queue016 wrapper603029 /parent603036 started09:36:56–57Z and were verified owned
and live at09:37:54Z. At that capture they were still in pre-dispatch evidence
verification: no new reservation or atomic action yet. Process readiness is not
a completed benchmark run. Only the original schedule's unfinished cells may
continue; attempt4 above is valid and cannot be reserved again.

All168, complete private semantic/failure/recipient/adoption audits, frozen pruning,
actual held-out PhaseII and final Q1–Q10 remain required. No winner, pooled quality,
pruning or PhaseII claim is made. Dataset/model/prompt/full-trace bodies remain on
4090/edges and are not transferred through the development machine.

## Later actual first-cell completion (09:41Z)

Queue016 reserved Video-MME131-3 /P2 /Fast /E attempt2 at09:39:52Z,seq316.
This is one of the already authorized E tool-surface repairs, not repetition of
a valid cell. Atomic608533 was verified owned/live, with only execution004
`src:scripts` imports,actual revision0ff0e9b and four empty initial Worker stores.
Live proof SHA256
`dd54e03dc21af3a6f24b494578b96f17a43b3f99350de16a22bcead681d28ae3`.

The cell settled valid at09:41:05Z,seq317; completion/format-valid/score1,terminal
`A`. Workflow:8-frame sampling → contact sheet → one real A4 VL4B inference.
There were3Manager /3Verifier calls,0specialists,2tool executions /1inference,
0typed failures,10graph snapshots /3nodes /9information edges,one logical owner,
maximum actual concurrency1 and no overlap. Model input/output1258 /2tokens,
finish `stop`,backend7.211s,pure tool work1.098s. E2E37.022s. Fixed initial video
distribution7,037,220bytes /0.663s is separate; complete action-artifact movement
is provably0. Frozen API LIST cost USD0.08394788796024396,all6usage receipts known.

Raw admission was independently reconstructed, not merely trusted; original
settlement canonical9d49ac944984171d606e16b93dd6136878034df4a3f444acbc75750ea8ed2708,
all6actual SDK contexts/no-query E surface/freshness/Worker exits/five-instance
residency passed. Bounded proof
`analysis/resident-source004-thirteenth-E-repair-settlement-audit-001.json`,SHA256
`07ebb47187d32a89c26d5ba31de41bd39cb213b4721910c6745e619ee05dcd14`.

Earlier immutable snapshot043 independently verifies123effective /142attempts /
1pending at09:40:57Z (not124):SHA256
`2f8c75aecee7d9b179749cd07e114ead6adfdf4b05d8b81e39e14c29b42ab8df`.
The new source-bound unique settlement extends this prefix to124effective; the
old snapshot's scope is not rewritten. MultiHop2 /P1 /Fast /E attempt2 was then
reserved at09:41:51Z,seq318. Full semantic audit/pruning/PhaseII remain pending.
Neither score1 nor zero action movement proves E caused a resource/quality gain.

## Later second-cell completion:125effective

MultiHop2 /P1 /Fast /E attempt2 settled valid at09:46Z,seq319,after all original
E repair cells had now acquired their repaired nominal outcomes. It completed /
format-valid /score1; raw admission independently reproduced,all16actual SDK
contexts/no-query E surface,four empty stores,Worker exits and5resident instances
passed. Original14E exclusions remain excluded,not resurrected.

Actual trajectory:three-shard BM25 → model context reject → smaller three-shard
BM25 → context reject → smaller three-shard BM25 → A28 27B terminal inference.
There were8Manager /8Verifier calls,0specialists,9successful retrievals,
3model attempts /1actual inference. One readiness/semantic validation and one
phase-restricted call also returned typed failures; neither was hiddenly repaired.
Inference7055input /3output tokens,finish `stop`,backend123.149s. E2E212.753s.
Fixed setup7,696,522bytes /1.095s;complete action traffic17,961bytes /0.297s.
Pure tool work3.255s. API LIST cost USD0.1658094433888306,all16usage receipts known.
Graph37snapshots /12nodes /9edges;actual max concurrency3,overlap1.604s.

Bounded proof `analysis/resident-source004-fourteenth-E-repair-settlement-audit-001.json`,
SHA256 `50f7db2ed964550c3a83b7f40d544bb875eaaa379937a3d2b9b69c1e4a4b31f7`,
binds the earlier124-cell proof and the distinct unique settlement,not a rewritten
snapshot. Score1is not full required-evidence-retention proof or causal E benefit.
Queue016 then reserved previously unstarted MultiHop1 /P2 /Slow /E attempt1 at
09:46:55Z,seq320. This pending run is not counted as another completion.
