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
