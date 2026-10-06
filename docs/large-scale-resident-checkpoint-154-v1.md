# Resident checkpoint154: compound input-policy and record-field failure

2026-10-06. MultiHop representative1 (`29e45040dce39dae`), DeepSeek/Slow/B1,
attempt1. Queue021 stopped at14:25:57Z. No evaluated answer was produced:
completionfalse, scoreunknown, formatunknown. Missing evaluation is not0.

## Exact failure classification

Primary: **provider input-policy refusal**. A DeepSeek specialist request and
the terminal fixed Qwen3.8-Max Blind Verifier request each returned HTTP400,
`data_inspection_failed`, `Input text data may contain inappropriate content.`
The other17API requests returned HTTP200. Actual response timestamps and the
terminal AgentLoopError independently match the persisted API and trace.
This is not provider outage, balance exhaustion, timeout or model-service OOM.
No input censorship, prompt repair, model substitution or replacement is allowed.

Secondary: **workflow composition: absent record-field misuse**. Specialist
`hn-analyst` issued three BM25 requests with `text_field="text"` over actual
derived artifacts `hn-epoch-shard1`, `hn-epoch-shard3`, `hn-epoch-shard2`.
Each had10records, string `body` in every record, and no `text` field. Actual
sizes were29,951,28,450,27,426bytes. Whole-record-preserving source/producer
provenance was reproduced; the original semantic source schema declared `body`.
The runtime correctly rejected `document field must be text: text`.
Whether that specialist itself received sufficient schema is not asserted by
this shape proof; full recipient/semantic attribution remains separately required.

The existing unchanged compound reviewer reproduced both findings. Original
result, trace, admission and raw journal remain immutable. A separately
source/evidence-bound sidecar admits this as a nominal failure, prohibits retry
and keeps evaluation unknown. It does not declare execution success.

## Actual telemetry

| Metric | Observed |
|---|---:|
| Root Manager attempts / completed |4 /4|
| Specialist attempts / HTTP200 |11 /10|
| Verifier attempts / HTTP200 |4 /3|
| Created specialists |2|
| Physical actions |21|
| Tool actions / successful receipts |19 /16|
| Model attempts / context rejects / inference |2 /2 /0|
| Phase-restricted logical observations |6|
| Absent-field execution failures |3|
| E2E |149.871834s|
| Successful action movement subtotal |55,037bytes /0.296605s|
| **Complete** action movement |**unknown** (3unmeasured execution failures)|
| Fixed initial placement |7,696,522bytes /22.362490s|
| Successful tool work subtotal |5.150288s|
| **Complete** tool work |**unknown**|
| Completed Manager / specialist / Verifier work |53.876819 /65.080100 /8.672093s|
| Known API estimate subtotal |USD0.202916570776 (17known,2unknown calls)|
| **Complete** API estimate |**unknown**|
| Graph nodes / information-flow edges / snapshots |21 /22 /64|
| Actual SDK recipient contexts |19|

Prepared operators: BM259, read_artifact6, aggregate1, filter3, invoke_model2.
Both model attempts failed before physical selection/inference on context; zero
physical inference is proven, not inferred from an absent result. The run-level
returned usage isnull, so counts above come from actual API/events. Failed cloud
reasoning intervals are not silently included in completed-work subtotals.
Work sums overlap and are not an additive E2E decomposition.

Both requests matched anonymous static `model-class-01`: text modality,
required capability `model`, reserved output2048, no quality-class override.
Root requested min_context8192 and specialist4096; both static requirement
matches were true. Their actual action context preflight still rejected the
invocations before physical selection. This does not demonstrate deployment
unavailability, a network-induced failure or an impossible capability-class
request. It must not be labeled an infra-awareness benefit. Exact context/input
attribution remains a separate semantic audit, without changing the requests.

Four empty Worker stores, verified Worker exits, five unchanged resident model
identities, recipient/privacy checks and tc cleanup passed. No benchmark/API
body was exported; shape inspection occurred on owning devices after shutdown,
without reading supporting-evidence/gold bodies.

## Append-only evidence

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Proof | SHA256 |
|---|---|
| `analysis/resident-source004-cell154-compound-field-policy-diagnosis-001.json` | `be444a5266cbb7c3b39c6696eb01c0b8e161900b09af71c4c7cf789b6460d9ca` |
| `compound-record-policy-adjudications/<run154>.json` | `0b1797d2eb6f47a0754c748d877a1abda852e2598651ab921424e8a3bb8f3ade` |
| Reviewed admission canonical hash | `7ce19dd060d692f4b12e49211df83a4a0d14b352dc8ec73b7c2ae2206da7fdf7` |
| `analysis/resident-source004-cell154-settlement-audit-001.json` | `bc12ae34cfd53ad23500871f8ad1c54639bfafb8d7dcd430631381acf132081c` |
| `analysis/resident-source004-cell154-model-preflight-audit-001.json` | `e7b6cb214ceb945002a97ced50a453f6ad83367570bc55a8027247e885955a7d` |

This is valid failure evidence, not evidence of cost optimization. B1 exposure
does not establish adoption. Current complete-coverage projection and renewed
queue dispatch require their own verification. Full168/private semantic audit,
method pruning, held-out PhaseII and final research conclusions are not complete.
