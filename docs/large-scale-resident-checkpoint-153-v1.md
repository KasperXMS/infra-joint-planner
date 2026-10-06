# Resident checkpoint153: completed, format-valid, wrong answer

2026-10-06. MultiHop representative1 (`29e45040dce39dae`), Qwen/Fast/A,
attempt1. Normal execution completion and valid terminal; original evaluator
score **0.0**. This is a valid quality-failure sample, not a reason to replace
the task, retry, tune the prompt or change the frozen Verifier.

## Actual execution

Aggregate artifacts → two BM25 retrieval actions → one A28 physical model
inference. Two read_artifact calls were returned as phase-restricted logical
observations rather than executed Worker reads. No specialist was created.
The frozen phase behavior is recorded, not repaired to rescue this answer.

| Metric | Observed |
|---|---:|
| Manager / Verifier / specialist calls |4 /4 /0|
| Physical actions / successful tools / model inference |4 /3 /1|
| Model input/output tokens |7,476 /236|
| E2E |229.788926s|
| Complete action movement |5,204,596bytes /2.651685s|
| Fixed initial placement |7,696,522bytes /1.041034s|
| Model service / tool work |195.587714s /2.875623s|
| Manager / Verifier work |16.317825s /11.390339s|
| Frozen list-price API estimate |USD0.052624262879|
| Graph nodes / information-flow edges / snapshots |4 /4 /13|
| Actual SDK recipient contexts |8|

API price receipts were complete. Work sums are not an additive wall-time
decomposition; setup traffic is not Agent-controlled traffic. Supporting-evidence
retrieval, selection, retention and synthesis causality remain for the full
post168-cell private audit. Score0 alone does not identify the primary semantic
failure. No gold/supporting-evidence body was read during this settlement audit.

## Integrity

Independent original admission reconstruction matched the original receipt and
canonical journal settlement. Four empty Worker stores, verified Worker exit,
five unchanged resident model identities, full recipient/privacy checks and tc
cleanup passed. No new execution epoch, model reload or semantic tuning.

Remote proof:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/resident-source004-cell153-settlement-audit-001.json`.
SHA256 `5249909a07d3c2995106e0dc3e138e40b2858975babf15af3650910478ce4056`.

At the following cell154, Queue021 stopped for exact compound field/policy
review. This document records153 only; it does not claim168 completion, method
pruning or actual held-out PhaseII. Old42 remain a separate historical block.
