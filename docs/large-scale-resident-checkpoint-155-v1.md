# Resident checkpoint155: Blind completion with evaluated quality failure

2026-10-06. MultiHop representative1 (`29e45040dce39dae`), Qwen/Slow/B0,
attempt1. Normal execution, valid terminal, original evaluator score **0.0**.
Retain this as a nominal quality failure; no retry, replacement, prompt tuning,
model/budget change, stopping repair or new method.

## Actual path and parallelism

Full aggregation → two BM25 actions → one A28 physical inference. Two attempted
read_artifact calls returned phase-restricted logical observations, not Worker
reads. No specialist was created. The two independent BM25 actions actually
overlapped in Manager native-turn2: peak2,1pair,2.095677s overlap. This is
single-Manager tool parallelism, not multi-agent reasoning or a proven E2E benefit.

| Metric | Observed |
|---|---:|
| Manager / Verifier / specialist calls |4 /4 /0|
| Physical actions / successful tools / inference |4 /3 /1|
| Context rejects |0|
| Model input/output tokens |7,612 /113|
| E2E |228.529579s|
| Complete action transfer |5,204,596bytes /14.841222s|
| Fixed initial placement |7,696,522bytes /22.066470s|
| Model service / tool work |163.056691s /3.145013s|
| Manager / Verifier work |14.331597s /10.288905s|
| Frozen list-price API estimate |USD0.053307973797|
| Graph nodes / information-flow edges / snapshots |4 /4 /13|
| Actual SDK recipient contexts |8|

All8price receipts were known. Cloud cost is the frozen regional list-price
estimate, not an invoice. Initial/setup traffic is separate from action traffic.
Work sums overlap and are not an additive E2E decomposition. The full movement
receipts were complete, not zero-imputed from an absent failed receipt.

This macro operator sequence resembles153(Qwen/Fast/A), but both method and
network differ; that is not a matched causal contrast or proof of identical
semantic evidence. Retrieval, selection, retention, model reasoning and frozen
Verifier-phase attribution remain for the complete post168-cell private audit.
No supporting-evidence/gold body was read in this settlement audit. Score0 alone
does not identify a primary semantic cause.

## Validity and immutable evidence

Original admission independently reconstructed and matched the canonical raw
journal settlement. Four Worker stores were initially empty; actual exits,
recipient/privacy checks, five resident identities and tc cleanup passed.
Before execution the five runner identities also exactly matched154after-state:
no warm-up/reload introduced by continuation022. Execution remains004/revision
0ff0e9b; no measured-source or Agent behavior change.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Proof | SHA256 |
|---|---|
| `analysis/resident-source004-cell155-live-start-audit-001.json` | `c19b7781cae84ea16a6749eaec81e3d014f8d23acede32146bc6eebd4379c983` |
| `analysis/resident-source004-cell155-settlement-audit-001.json` | `9b4902f836902238f7a01421f46478cdb8989d031a59600b729f37fd6b86720b` |

At15:01:31Z Queue022 PID1228624and the next MultiHop1/DeepSeek/Fast/E
atomic1260363were owned/live, attempt1, still preparing before Worker starts.
That156th result is pending. Current count155/168comes from verified snapshot051
plus this one independently reconstructed settlement, not a relabeled snapshot.
Old42remain unpooled; all168/private failure/semantic/recipient/adoption audit,
frozen pruning, actual held-out PhaseII and finalQ1–Q10 remain required.
