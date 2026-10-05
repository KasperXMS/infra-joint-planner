# Resident-block checkpoint 045–049

2026-10-06. At `2026-10-05T20:39:45Z`, 48 of the 168 new nominal
outcomes had settled. This is not a completion/correctness aggregate or a
comprehensive private semantic audit. Old 42 outcomes remain closed/unpooled;
four original reviewed rejections remain immutable with their exact sidecars.
No retry, replacement, semantic tuning, early pruning or Phase II launch.

## Three fully projected LongBench representative-2 outcomes

Original task `66f94f9ebb02136c067c4fde`, Governmental two-document input,
2,119,778 source bytes initially on A4. Fixed independent Blind Qwen Verifier,
same operators/scheduler, five resident models, context 32K/output 2048,
unchanged execution freeze and queue control freeze 004.

| Measurement | 45: P2 / Fast / C | 46: P1 / Slow / B | 47: P2 / Slow / A |
| --- | --- | --- | --- |
| Completed / canonical terminal / original score | yes / valid / 0.0 | yes / valid / 0.0 | yes / valid / 0.0 |
| Manager / Verifier turns | 18 / 3 | 10 / 10 | 6 / 6 |
| Created specialists | 0 | 0 | 0 |
| Physical actions / actual inference | 2 / 1 | 10 / 1 | 6 / 1 |
| Submitted context rejects | 0 | 2 | 0 |
| E2E, seconds | 118.399 | 136.311 | 71.062 |
| Fixed initial placement, bytes / seconds | 2,119,778 / 0.235 | 2,119,778 / 5.976 | 2,119,778 / 5.978 |
| Complete action transfer, bytes / seconds | 0 / 0 | unknown / unknown | unknown / unknown |
| Successful action transfer receipts | 0 / 0 | 0 / 0 | 0 / 0 |
| Complete tool-only work, seconds | 0.286 | unknown | unknown |
| Successful tool-only work, seconds | 0.286 | 2.939 | 1.491 |
| Complete backend work, seconds | 0.479 | 14.585 | 0.521 |
| Physical model input / output / finish | 284 / 2 / stop | 5,181 / 2 / stop | 452 / 2 / stop |
| Manager / Verifier work, seconds | 107.512 / 7.205 | 80.931 / 29.530 | 34.957 / 25.051 |
| Frozen-list-price API USD | 0.1443829216 | 0.1573943103 | 0.2583245991 |
| Actual SDK recipient contexts audited | 21 | 20 | 12 |
| Graph nodes / declared artifact edges / snapshots | 2 / 0 / 7 | 10 / 6 / 31 | 6 / 2 / 19 |
| Actual simultaneous action maximum / overlap seconds | 1 / 0 | 2 / 2.639 | 1 / 0 |

All three original admissions have no unresolved problems; original evaluator,
actual recipient privacy/method inputs, Worker exits, tc cleanup and resident
model checks passed. API usage is known for every listed call. Failed reads in
46/47 lack complete transfer/operator receipts: returned zero successful
movement is **not** proof of a complete zero total. Backend work is complete here
because there are no unmeasured failed inferences. Inclusive Worker work must
not be added to backend work. Work sums/graph action paths are not E2E
decompositions, and fixed initial placement is not Agent-controlled movement.

### Cell 45: mandatory protocol, wrong answer

Actual execution: BM25 on A4 → model inference on strong GPU0 resident 27B.
Six quotes: two consumed/authorized, four discarded, zero stale. Quote-control
work 2.253 s. Quote-level phase-restricted rejections: five; logical observation:
one. Raw SDK contexts expose at least six corresponding failed function results;
these are not extra physical model inferences. Eighteen Manager turns did not
reach the twenty-turn ceiling. Quote-induced causal revision rate remains
unknown: four discarded quotes are not four proven cost-induced revisions.

The low physical-model input and zero declared artifact edges do not establish
missing decisive evidence: SDK context/prompt information flow also matters.
The answer is valid but wrong. Its primary semantic cause awaits complete
post-hoc private audit. Cheap wrong execution is not an optimization success;
neither this run nor unmatched neighboring cells authorize a method winner.

### Cell 46: legal continuation, still wrong

Execution: oversized read failure → two BM25 calls → context rejection → two
BM25 calls → context rejection → two BM25 calls → successful A4 resident VL4B
inference. Six successful retrievals, one inference and three failed physical
nodes. Two independent retrieval actions overlapped; frontier width seven did
not imply seven concurrent actions. Optional queries/cards: zero, with seven
observed ready schema-valid opportunities. The B interface was unused in this
run. Natural continuation is not a harness retry or proof of cost-driven
reduction. Wrong-answer cause remains pending private evidence audit.

### Cell 47: read/retrieve continuation, still wrong

Execution: oversized read failure → BM25 → bounded read → BM25 → bounded read
→ strong GPU0 resident 27B inference. Five successful nodes, one failed node;
no context rejection or actual parallelism. Read results entering SDK context
are not represented solely by the model-action input-artifact edge count.
Primary semantic failure cause remains unknown pending post-hoc audit.

## Durable provenance

| Cell | Original admission canonical SHA-256 | Append-only remote projection file SHA-256 |
| --- | --- | --- |
| 45 | `1c1924d1f315ffbc4988003a8ca8de7dbad949933ecce013c3ca18e757c2f1cd` | `3ae0b08d2080532c6aed52923ed899e20b891ee27f9358501e0579ef233b3bd0` |
| 46 | `221afee04da62374c4670200685db4ceef9d67dd67c2ea979345b3925059607a` | `892cb3793d970cd54fd3b247ab44ab1abe83cd65da842ea1fddba52da40564f2` |
| 47 | `d85bdb6f087ab6d65516d0afbd0983dc9ef1b577d713d6bc6aa82f5dc28ba8e7` | `9cdf439f758256540035b4bdedf944eafb3cb47dd0af4de1cef0f69ef87c05b1` |

Remote projections are `analysis/resident-cell-NNN-summary-001.json` under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`. They validate the
original journal hash chain, admission/result agreement, owning Worker exit and
residency, and bind trace/result/source hashes. No dataset, prompt/private
evaluator or model payload passes through the local PC. These are individual
settled-cell projections, not a new complete-block snapshot or semantic proof.

## Later boundary and unfinished work

Cell 48 / LongBench 2 / P1 / Fast / B1 settled valid at sequence 96,
`2026-10-05T20:39:12.696886Z`. Original admission canonical SHA:
`0e10fcc16c9697dc528bcae271cedfa9bbacf6b0a4759cc48638202f08348a40`.
The bounded original result records completed / valid terminal / score 0.0,
9 Manager / 9 Verifier turns, zero specialists, six charged physical calls,
E2E 111.338 s and fixed initial 2,119,778 bytes / 0.495 s. Eighteen actual SDK
contexts passed admission. Subsequent full projection:
`analysis/resident-cell-048-summary-001.json`, file SHA
`8560cfcb3bf354270ad5be5cc27aa4c2761686f7a2c08e208f7b7c2cb95aa8f7`.
Three successful BM25 calls, two submitted context preflight rejects and one
successful A4 resident VL4B inference account for the six physical nodes.
Three model proposals are not three inferences. The Manager naturally issued
later retrieval/model actions after typed feedback, without automatic retry.

Complete action movement 0 bytes / 0 s; complete tool work 1.107 s; complete
backend work 11.637 s; model input/output 4,098 / 2, stop. Manager/Verifier work
71.760 / 23.362 s; all eighteen cloud usages known, frozen list-price estimate
USD 0.1110928819. Graph 6 nodes / 3 edges / 19 snapshots, four succeeded and
two failed; actual concurrency one, no overlapping action intervals. All
owning Worker exits/residency, actual recipient/method privacy, evaluator and
source/receipt checks passed. Wrong-answer cause still awaits private evidence
audit; raw profile visibility does not establish rational adaptation or explain
the answer. This projection does not change the original admission or authorize
pruning after only a partial block.

Cell 49 / MultiHop representative 1 / P2 / Fast / D subsequently settled valid
at `2026-10-05T20:42:42.812059Z`, sequence 98. Original admission canonical SHA
`f72acc514f1a445876b99001df555760b92b72641a1f649f5876cecfca5fed71`.
Bounded original result: completed / valid terminal / original score 0.0,
8 Manager / 4 Verifier turns, zero specialists, four charged physical calls,
E2E 166.232 s. Fixed initial 7,696,522 bytes / 1.601 s; returned successful
action movement 5,204,596 bytes / 0.689 s. Twelve actual SDK contexts passed
admission. Full inference, complete-transfer and true multi-candidate-comparison
accounting still require its next per-cell projection. Four charged calls do
not establish four inferences or D comparison adoption. Private semantic cause
remains pending; this wrong answer is retained without tuning/replacement.

Queue 005 PID `1997584` remained live at `20:39:45Z`; cell 49 / MultiHop 1 /
P2 / Fast / D atomic PID `2278832` was live, reserved at sequence 97. Always
re-read actual process state rather than treating this historical PID as current.
At `20:43:48Z`, cell 50 / MultiHop 1 / P1 / Slow / C atomic PID `2293113`
was verified live, reserved at sequence 99; queue 005 remained unchanged.

Full 168-cell execution, comprehensive private semantic/recipient/failure/
adoption audit and frozen method pruning remain required. Then preregister and
execute complete Phase II method blocks within `42 + 168 + 48m <= 420`, followed
by the named final reports and Q1–Q10. No goal completion or scope reduction.
