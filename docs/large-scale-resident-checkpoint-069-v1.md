# Resident checkpoint: LongBench representative2, cell69

2026-10-06. Partial new-block evidence; not method screening/pruning or final
semantic diagnosis. Old42results remain immutable, closed and unpooled.

## Original valid quality failure

LongBench-v2 representative2/task66f94f9ebb02136c067c4fde/P1/Fast/A, attempt1,
settled valid2026-10-05T23:07:31.291791Z, sequence138. Execution completed,
terminal format valid, original evaluator score **0.0**. Keep the wrong answer;
do not retry, substitute a task, tune prompts or classify it as a budget failure.

Observed trajectory: oversize read rejection -> repeated BM25 retrieval and
bounded artifact reads -> two context-preflight rejections -> later successful
model inference -> terminal answer -> original evaluator. The selected sequence
has additional rejected logical calls; only prepared actions belong to the
executed physical graph. No automatic truncation or hidden semantic finalizer.

| Measure | Original observed value |
| --- | --- |
| Manager /Verifier turns | 11 /11 |
| Specialists /specialist turns | 0 /0 |
| Prepared physical /tool /model actions | 14 /11 /3 |
| Successful tool executions /successful inference | 10 /1 |
| Prepared operator counts | read_artifact3,bm25_retrieve8,invoke_model3 |
| Context rejects | 2;not actual inference |
| Other failure receipts | artifact_too_large1,phase_restricted2,semantic_validation_failed1 |
| Model requirements | 3static-feasible;complete input preflight remains independent |
| Successful inference | A4residentVL4B;6,553input /2outputtokens;stop |
| E2E | 145.554s |
| Fixed initial placement | 2,119,778bytes /0.570s |
| Successful action-transfer subtotal | 0bytes /0s |
| Complete action transfer | UNKNOWN;onefailedexecutionhasincompleteworkreceipts |
| Successful tool work /complete tool work | 3.431s /UNKNOWN |
| Complete model backend work | 18.565s;oneactualinference,nomissingmodeloutcome |
| Failed physical execution work | 0.0266s;not a substitute for missing transfer/tool breakdown |
| Manager /Verifier work | 83.326s /37.954s;not additive E2E components |
| Cloud API | All22usages known;USD0.2996133405971379,frozen list-price not invoice |
| SDKrecipient contexts checked | 22;originaladmissionprivacycheckspass |
| Graph | 14nodes /8artifactedges /43snapshots;11succeeded,3failed |
| Action owners /InformationObject handoffs | 1 /0 |
| Actual concurrency /overlap | max2 /3.177s;sameowner,0crossownerpairs |
| Dependency path | 2nodes /19.867s;not E2E prediction |

Root raw responses contain10BM25calls and4invoke_modelcalls, while the prepared
physical graph contains8and3respectively. Counts differ because rejected
SDK/logical calls are not executed physical actions. Failure counters can overlap
different receipt layers; do not add them into a fictitious total inference count.
Ledger exposure is not proof that it caused these choices or reduced resources.

Allfive model instances resident, fresh Worker processes/stores, verified exits
and successful tc cleanup. No source/operator/evaluator/prompt/budget/scheduler
change, warm-start subtraction, retry or operational replacement.

The agent recovered from typed read/context failures and reached real inference,
but its final answer was wrong. Neither20turns nor64physicalcalls was exhausted.
Repeated retrieval/reduction is observed; the primary semantic/evidence/Verifier
failure cause remains **pending complete private audit**. Do not infer evidence
loss from token/byte counts alone or treat lower resource usage plus score0 as
an optimization success. No matched method/network causal claim is established.

## Append-only provenance

Original admission canonical SHA-256:
`f8fa2b09cd01e62c11f431ff27eb4d5b8c0a8f2b42e07c29cecaa144a29dde42`.
Original settlement journal SHA-256:
`ea8d3d1a012b62adf2af2a43961288b15eaba253c6bddbd2c932fc06e322445a`.
Exclusive remote `analysis/resident-cell-069-summary-001.json` file SHA-256:
`64de57272701c0b77cd84227d89c6c328bb917b4224e2dac8ce5294e01d1647b`.
Original trace/result/source/admission bindings and hash-linked journal checked.
Only bounded metadata returns to this PC, never datasets/models/artifact bodies/
raw prompts/gold. Original evidence is not rewritten to fill missing telemetry.

At2026-10-05T23:08:28.500175Z queue008PID2678456/cell70atomicPID2835022 were
verified live onLongBench representative2/P2/Slow/B, reservedseq139at23:07:33Z.
Execution001/control007 unchanged,69classified primary outcomes; all168 and
comprehensive private/recipient/failure/adoption audit, frozen pruning, actual
PhaseII and finalreports/Q1–Q10 remain unfinished. No early pruning or new method.

## Cell70 append: P2 /Slow /B

Attempt1 settled valid2026-10-05T23:11:03.426177Z,sequence140. Completed,
canonical terminal valid, original LongBench-v2 score0.0. This is another valid
quality failure, not authorization to tune or retry. Primary semantic cause
remains pending complete private evidence/Verifier audit.

| Measure | Cell70 observed value |
| --- | --- |
| Manager /Verifier turns | 11 /11 |
| Created specialists /specialist turns | 1 /8;peakactive1 |
| Physical actions /model requests /successful inference | 16 /4 /1 |
| Prepared operators | read_artifact3,bm25_retrieve8,aggregate_artifacts1,invoke_model4 |
| Successful tools /context rejects | 11 /3;rejectsnotinference |
| Other failure receipts | artifact_too_large1,phase_restricted1,semantic_validation_failed1 |
| Successful actual inference | strongGPU0residentQwen3.5-27B;579input /2outputtokens;stop |
| E2E /fixed initial transfer | 150.826s /2,119,778bytes,5.978s |
| Successful action-transfer subtotal /complete action transfer | 0bytes,0s /UNKNOWN |
| Successful tool work /complete tool work | 2.085s /UNKNOWN |
| Complete backend service work | 0.701s;nomissingmodeloutcome |
| Manager /specialist /Verifier work | 69.081s /31.744s /34.889s;not additive E2E |
| Cloud API | All30usagesknown,USD0.3322638182808701,list-price not invoice |
| Actual SDKrecipient contexts checked | 30;originalprivacyadmissionpassed |
| Graph | 16nodes/14artifactedges/49snapshots;12succeeded,4failed |
| Logical owners /InformationObject handoffs | 2 /1 |
| Actual concurrency /overlap | max1 /0s;nominalMASdoesnotimplyparallelbenefit |

Trajectory includes specialist retrieval/aggregation and oneexplicit handoff.
Four requests are static-feasible; three complete-input preflights rejected
context. The final real model call is prompt-only in the graph (no artifact
dependency edge). Low input tokens alone do not prove evidence discard: inline
prompt facts and specialist-to-root information need private semantic audit.
Do not infer27Bspeed superiority over cell69's different6,553token/4Brequest or
optimization from an incorrect answer. Failed read leaves complete transfer/
tool workUNKNOWN; measured failed-action walltime0.101s does not fill breakdown.

Optional query tools visible in all11rootinputs,0queries/cards,8observed eligible
ready decisions. Unused interface cannot explain a claimed benefit. Specialist
context separately audited; root response counts are not all physical calls.
Allfive instances resident;Workerexit/tccleanuppass,no source/prompt/budget change.

Original admission canonical SHA-256:
`d60ebacc4c36bbb6e2193a66440bb498ec7e174ca309e792ee95635661d502bf`.
Original settlement journal SHA-256:
`9bce3e6f36d7486c3cb54a775098cf86460f5d7ef3416871b3f5195772fceae7`.
Exclusive remote `analysis/resident-cell-070-summary-001.json` file SHA-256:
`663325d3f397a6649495ae5294cf7107949232e94622e8fce9ac1927ee14458a`.

Queue008PID2678456/cell71atomicPID2849294 command-verified live23:12:06.514970Z
onLongBench2/P1/Slow/C, reservedseq141at23:11:06Z. ActualQuotecreated/authorized/
executed receipts are present; no final71outcome inferred.70classified of168,
control007/execution001unchanged;fullstudy/audits/pruning/PhaseIIunfinished.
