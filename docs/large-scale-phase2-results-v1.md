# Resident Phase II results — in progress

Checkpoint: 2026-10-06T19:11:40Z / 2026-10-07 03:11 HKT. Five of 192 nominal
held-out cells settled. These are actual original evaluator results, not final
method estimates. Same frozen 18-task manifest, execution004, resident diversified
pool, B0/B1/A/E methods, deterministic schedule and n1 discipline. Old42 and
Phase I results are not pooled into this held-out table.

The first four cells are the same frozen LongBench-v2 position6 task hash
`612be14c898ffdda`, attempt1. Canonical choice came from successful terminal model
output; evaluator ran without a semantic finalizer. Original admissions were
independently reproduced exactly and matched journal settlements. Empty initial
stores, Worker exit, five-instance residency and tc restoration passed. Existing
actual SDK recipient scans found no issues; complete post-block semantic/adoption
audits remain pending. The fifth is frozen Video-MME position5 task hash
`332db0bfa03dd109`, also attempt1, with valid completion but original score0.

| Task | Planner / network / method | Completion / format / score | Manager / Verifier | Physical / returned inference | Context rejects | E2E s | Initial bytes / s | Artifact movement bytes | API list-price USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LongBench6 | DeepSeek / Fast / E | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 61.338 | 2,032,683 / 0.215 | 0 | 0.076829 |
| LongBench6 | Qwen / Slow / B0 | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 57.405 | 2,032,683 / 5.737 | 0 | 0.066510 |
| LongBench6 | DeepSeek / Slow / B1 | true / valid / 1 | 17 / 17 | 24 / 11 | 2 | 392.753 | 2,032,683 / 5.739 | 0 | 0.468597 |
| LongBench6 | Qwen / Fast / A | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 53.779 | 2,032,683 / 0.204 | 0 | 0.065860 |
| Video5 | Qwen / Fast / E | true / valid / 0 | 8 / 8 | 7 / 1 | 1 | 136.761 | 2,076,341 / 0.209 | 0 | 0.486185 |

Fast100Mbps/configured5ms and Slow3Mbps/configured50ms retain the existing
Jetson HTB/no-netem caveat: configured delay is not measured symmetric RTT.
Initial materialization is separate from Agent-controlled registered artifact
transfers. Zero artifact movement does not mean zero HTTP prompt/control traffic.
The price estimate is based on frozen usage/pricing, not the provider invoice.
Worker operator receipts include invoke_model and must not be added again to
backend service work as an E2E decomposition.

Observed paths:

- E, B0 and A: two BM25 attempts, two model requests, one context preflight rejection
  followed by successful smaller-input inference. Six Manager/Verifier turns,
  four graph nodes. No specialists; single-agent completion is valid.
- B1: ten BM25 actions, one aggregate_artifacts action and thirteen model requests,
  with eleven returned inference telemetry receipts and two context rejections.
  24 graph nodes/14 edges, 73 snapshots, zero specialists. Physical model input/
  output totals42,324/729; all eleven finish reasons stop. Backend service work
 260.379s. Most successful model selections were A4; the terminal prompt-only
  choice synthesis selected the4090GPU0Qwen3.5-27B instance,290input/2output tokens.
 34actual SDK contexts (17Manager/17Verifier) scanned without findings.
- Video5/E: sample_frames, an infeasible model request, four make_contact_sheet
  actions, then successful visual model invocation consuming all four sheets.
  A4VL4B returned4,620input/2output tokens, finish stop; service25.118s. Seven
  graph nodes/64 artifact-flow edges/22snapshots; max actual concurrency1,
  no specialists. The terminal model choice was format-valid but wrong under
  the original evaluator. Actual original admission/settlement, four empty stores,
  unchanged five resident identities, tc restoration, Worker exit and16SDK
  recipient contexts passed. This is retained without retry/tuning; visual
  reasoning versus evidence selection/coverage remains unidentified pending
  post-block private audit. Source-bound first-video audit SHA256
  `07edea55b8d8a80ae3e5927d943c95c5197bf6a656b755b0f9cb2e924c2d322b`.

These unmatched Planner/method/network cells cannot establish an E or B1 causal
effect, a matched speedup, stable infrastructure adaptation or statistical
significance. B1's longer successful trajectory is retained unchanged, not
treated as a bug to tune away. Evidence coverage/semantic sufficiency and causal
profile adoption remain separate questions for the full audit.

Authoritative owner-local snapshot004 SHA256:
`cbfc4ee0a97a7d1c8cb11c172140e14cb2b01d7816a17362fef4daf68adde2e5`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`4cfc30a5cb72954293d5670ceb1cc5677d6e56adabe3a237972095bc959cd8e7`.
Earlier snapshot002, covering the first three cells, remains preserved:
`0cb9a56a44ed0707482c237958a8ef9a760d2c27e85ab06a42ad01b54230bc9c`.
At snapshot003, the fifth cell was pending; its reservation is not completion.
Snapshot003 SHA256 remains preserved:
`7b9bdfa4d7d3f0b969cea7eec7a0324be366a513e605386123aa54366e82db8e`.
No complete-table aggregation, private-body scan, new method, retry, prompt
tuning or replacement was performed. The remaining frozen schedule continues.
See [first-cell audit](large-scale-resident-phase2-first-cell-v1.md) and
[collector validation](large-scale-resident-phase2-projection-v1.md).
