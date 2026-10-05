# Resident-block checkpoint 059–063

2026-10-06. Three additional original attempt1 outcomes are settled and valid:
61/168 nominal outcomes classified, including earlier exact-reviewed failures,
not an aggregate completion/accuracy claim. Old 42 remain closed and unpooled.
No retry/replacement, semantic tuning, task/model/budget change or early pruning.

All cells use fresh isolated Worker processes/stores and per-cell tc attestation,
the same frozen native runtime/tools/scheduler/evaluators, five resident models
and 32K/2048 contracts. P1=`deepseek-v4-pro`, P2=`qwen3.8-max`; independent fixed
Blind Verifier=`qwen3.8-max`. Configured network delay is not measured symmetric
RTT. No measured-cell warmup/reload/cold-start subtraction or silent fallback.

| Measurement | 59: MultiHop2/P1/Slow/D | 60: MultiHop2/P2/Fast/E | 61: LongBench1/P2/Fast/C |
| --- | ---: | ---: | ---: |
| Completed / canonical terminal / original score | yes / valid / 1.0 | yes / valid / 1.0 | yes / valid / 1.0 |
| Manager / Verifier turns | 20 / 3 | 6 / 6 | 17 / 5 |
| Specialists / specialist turns | 0 / 0 | 0 / 0 | 0 / 0 |
| Physical actions / actual inference / context rejects | 4 / 1 / 0 | 8 / 1 / 1 | 6 / 1 / 0 |
| E2E, seconds | 148.561 | 131.629 | 98.718 |
| Fixed initial bytes / transfer work, seconds | 7,696,522 / 22.073 | 7,696,522 / 1.233 | 514,789 / 0.106 |
| Complete action bytes / transfer work, seconds | 0 / 0 | 12,084 / 0.178 | 217,558 / 0.082 |
| Complete tool-only work, seconds | 1.153 | 2.193 | 0.513 |
| Complete backend work, seconds | 0.448 | 83.909 | 0.458 |
| Actual model input / output tokens | 78 / 3 | 4,804 / 3 | 203 / 2 |
| Returned finish | stop | stop | stop |
| Manager / Verifier work, seconds | 115.907 / 6.855 | 29.204 / 15.418 | 82.784 / 13.299 |
| Frozen-list-price API USD, complete known usages | 0.1399113568 / 23 | 0.1292213636 / 12 | 0.1632476156 / 22 |
| Actual SDK recipient contexts audited | 23 | 12 | 22 |
| Graph nodes / artifact edges / snapshots | 4 / 0 / 13 | 8 / 6 / 25 | 6 / 4 / 19 |
| Actual maximum action concurrency / overlap, seconds | 3 / 0.624 | 3 / 1.212 | 3 / 0.236 |

Work sums/graph action dependency paths do not decompose E2E. Inclusive Worker /
model-wrapper work contains backend work and must not be added to it. Fixed
initial placement remains separate from Agent-controlled movement. No unmeasured
failed execution/inference appears in these receipts; known complete zero action
transfer is not a guess from successful-receipt subtotals.

## Per-cell trajectory and limits

MultiHop2 is original task `multihop-rag-train-fe71f374676e35359d12c83e`, same
three hash-nonsemantic shards whose union is complete. Cell 59 performed three
parallel BM25 actions on A4/A5/A28, then one prompt-only strong-GPU0 27B inference.
All four nodes succeeded. Twenty turns is the last allowed reasoning turn but
the run completed, not budget-failed. Eight ordinary quotes: four consumed/four
discarded/zero stale; control work 3.348 s. Four discarded model quotes had known
context-selection failures, not four actual inference/preflight executions.
Ten quote phase rejections/six deduplicated SDK phase failures overlap and must
not be added as independent physical calls. Three comparison sets `[1,3,1]`
were returned, but **no cost cards or selected alternatives** in those sets;
the [independent adoption audit](large-scale-resident-comparison-audit-059-v1.md)
clarifies the frozen collector's misleading cardinality-only label.

Cell 60 grew `3 BM25 → context-rejected model → 3 BM25 → successful A28 27B
model`, with two actual three-way retrieval batches. Seven nodes succeeded, one
failed. Both abstract model requirements are statically feasible; the first full
input request exceeded context preflight. One semantic-validation/one
phase-restricted SDK failure are also visible. E advisories appeared in six root
input envelopes, not six necessarily distinct rules or proof of internal rule
use. Structure SHA equals cell 57's creation-order descriptor, not equality of
queries/prompts/evidence or a causal rule/network effect. Evidence retention and
rule adherence require private post-run analysis.

LongBench1 is original Academic task `66f2c44e821e116aacb2b826`, two original
documents/514,789 source bytes, same lossless representation/evaluator. Cell 61
grew aggregate on A4 → four BM25 nodes on the aggregate → prompt-only
strong-GPU0 27B model. All six nodes succeeded; three BM25 nodes actually
overlapped, not all four by structural width alone. Nine quotes: six consumed /
three pending / none discarded or stale; quote control 1.580 s. Five quote
phase-rejection/six deduplicated SDK phase-failure receipts are overlapping
scopes. Attempted reads/reduction/specialist calls do not prove corresponding
physical execution or created specialists.

Short prompt-only model inputs in 59/61 do not prove private leakage, absent
semantic evidence or answer guessing: facts may be carried by the Manager into
the prompt. Correct scores do not prove every intermediate path preserved all
required evidence. Full private semantic/effective-recipient analysis remains
pending. These unmatched n=1 cells do not choose a winner or support causal
resource-optimization claims.

## Append-only provenance

Per-cell remote `analysis/resident-cell-NNN-summary-001.json` verifies the
original journal chain, canonical admission/result, Worker exits/residency and
trace/result/source bindings. No dataset, model payload, raw prompt or gold is
transferred through the PC. Comprehensive-private-audit/pruning flags remain
false; original rejected receipts/sidecars and all prior projections are retained.

| Cell | Original admission canonical SHA-256 | Projection file SHA-256 |
| --- | --- | --- |
| 59 | `dda41f024c5e13a7dc74087c38bc1292515dee98efc11f3d1f0a92ebd41e65cc` | `d9f51b597e180069304c53ffdc6d27ec43fa78eeaad8ca1bd237f1df824f511a` |
| 60 | `1b06622c4e5c1f98705a26714cd786b0acf2e2630767d46820bfb66a73bd2b67` | `ccf23bbdcd10eb8be7af5bdf2ccb3aa147b6279103b6556429f738c4232d725f` |
| 61 | `f0e40853376eb3060a0e20d8edea5c77ef3560e5416e3f34230cf03493daeca2` | `0bc1eaffca1983911b1890b53ab69f94c563ab8b6ad50278ed5b3c7d354f1053` |
| 62 | `7b2606d960c4dd7e08499f0a8a6cf86854b41247548efea99a686adb9a013275` | `75a782bfb24628c2a51c6f34b2bc019909751f0ab2baceddb0312e5bdc8c0869` |
| 63 | `41872186afd5401c25cc388fee07aa708ee95f1a82231f74e37cd1b02e1ae461` | `f7caae24a30dfd07a0743127d7b7d3493e17f8001c0ab4fdd14608ba7dba47e2` |

Original settlement sequences 118/120/122 occurred at 21:46:23.082794Z /
21:49:29.954232Z / 21:52:04.963719Z on October 5. The offline comparison auditor
is separate, versioned and tested; it changes no admission or execution source.

## Cell 62 / LongBench1 / P1 / Slow / B

Original attempt1 settled valid at sequence124, `21:55:43.689831Z`; nominal
boundary advanced to 62/168. Completed/validterminal/originalscore1.0;
10 Manager / 10 Verifier turns, two created specialists / ten total specialist
turns / peak two active specialists, 20 physical actions / one actual inference.
Three logical action owners, one InformationObject handoff, one actual
cross-owner overlapping pair; maximum action concurrency two / overlap2.495s.
Logical specialist names do not identify different foundation models: they
remain on frozen P1 DeepSeek. No forced MAS topology or model substitution.

Executed actions: seven reads (two `artifact_too_large`, five success), ten
BM25 actions, three model requests (two context rejects, one success). All three
abstract model requirements are statically feasible; context rejects do not
count as inference. Six phase-restricted SDK failures also remain. The growing
graph has20nodes/15artifactedges/61snapshots,16succeeded/4failed. Structural
frontier width nine is not nine-way execution. Final model is A4 resident VL4B,
5,248 input / 2 output tokens / stop; complete backend work14.966s. There is no
unmeasured failed model inference.

E2E161.547s; fixed initial514,789bytes/1.697s. Successful action-transfer subtotal
9,423bytes/0.117s; **complete action bytes/time UNKNOWN** because two failed
execution receipts do not provide complete movement telemetry. Successful
tool-only work2.274s; complete tool workUNKNOWN for the same reason. Measured
failed physical execution work0.182s does not establish missing transfer cost.
Manager/specialist/Verifier work70.772/68.221/32.852s overlaps and is not an E2E
decomposition. All30APIusages known, complete list-priceUSD0.4590116518.

B optional interface was visible in all ten actual Manager requests; query/card
counts remain0 despite seven observed ready root opportunities. All30actualSDK
recipient contexts passed original admission/privacy checks, including both
specialists, along with Worker exits/residency, original evaluator/artifact
integrity and tc cleanup. This demonstrates natural valid continuation and MAS
execution, not that the unused optional cost mechanism caused recovery or
reduced resource use. Private semantic sufficiency/retention and matched causal
comparisons remain pending; no primary evidence-loss cause is inferred.

## Cell 63 / LongBench1 / P2 / Slow / A

Original attempt1 settled valid at sequence126, `22:00:37.202312Z`; nominal
boundary advanced to63/168. Completed/validterminal/originalscore1.0;
15Manager/15Verifier turns, one specialist/eight specialist turns,23physical
actions: one failed oversized read,12BM25,8model requests (5context rejects,
3actual successful inferences),2top-k-record reductions. All eight abstract
model requirements are statically feasible; five full input requests still
exceeded preflight. One phase-restricted/two semantic-validation SDK failures
also remain. No preflight rejection is counted as inference or repaired by the
harness. Later retrieval/reduction/model continuation is actual Agent behavior,
not proof of a causal Ledger effect.

Models: A5residentVL8B once, A4residentVL4B twice; summed actual12,962input/
296outputtokens,three stop finishes, complete backend86.931s. Graph23nodes/
21artifactedges/70snapshots,17succeeded/6failed; two logical action owners/one
InformationObject handoff. Actualmaxconcurrency3/overlap0.844s,zero cross-owner
overlap; structural frontier12 is not twelve-way execution or concurrent MAS.

E2E239.212s; fixedinitial514,789bytes/1.559s. Successful action-transfer subtotal
0bytes/0s but **complete action movement UNKNOWN**, not zero, because the failed
read lacks full transfer receipts. Successful tool-only work1.574s, complete
tool workUNKNOWN. Measured failed execution0.093s does not recover those missing
costs. Manager/specialist/Verifier work60.721/22.937/57.615s;38actualSDKcontexts
passed original admission/privacy checks,all38APIusages known,USD0.4731351147.
Worker exit/residency,evaluator/artifact integrity andtc cleanup passed; no
unmeasured failed model inference. Full private semantic audit remains pending;
same task/Slow but different Planner/method versus62 is not a causal matched
treatment comparison. No quality aggregation, winner or pruning.

## Actual continuation / full scope

Queue007 PID `2437975` and cell64 atomic PID `2591226` were verified live at
`2026-10-05T22:02:18.257338Z`: LongBench1/P1/Fast/B1, attempt1, reserved seq127
at 22:00:39.634919Z. It is still executing; no final outcome is
inferred before settlement. Check real process/journal before acting on these
historical handles. Execution freeze001 and control freeze006 are unchanged.

Only offline audit code was added (18 new tests; full1095 pytest/Ruff/strict
Pyright/diff passed). Finish all168 new primary outcomes and comprehensive
private/recipient/failure/adoption audit, then frozen screening/pruning, actual
preregistered PhaseII within `42 + 168 + 48m <= 420`, all named reports and
Q1–Q10. No survivor selection, reduced objective or goal completion is claimed.
