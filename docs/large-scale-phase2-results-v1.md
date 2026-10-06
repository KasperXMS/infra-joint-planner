# Resident Phase II results — in progress

Checkpoint: 2026-10-06T18:58:26Z / 2026-10-07 02:58 HKT. Three of 192 nominal
held-out cells settled. These are actual original evaluator results, not final
method estimates. Same frozen 18-task manifest, execution004, resident diversified
pool, B0/B1/A/E methods, deterministic schedule and n1 discipline. Old42 and
Phase I results are not pooled into this held-out table.

All three cells are the same frozen LongBench-v2 position6 task hash
`612be14c898ffdda`, attempt1. Canonical choice came from successful terminal model
output; evaluator ran without a semantic finalizer. Original admissions were
independently reproduced exactly and matched journal settlements. Empty initial
stores, Worker exit, five-instance residency and tc restoration passed. Existing
actual SDK recipient scans found no issues; complete post-block semantic/adoption
audits remain pending.

| Planner / network / method | Completion / format / score | Manager / Verifier | Physical / returned inference | Context rejects | E2E s | Initial bytes / s | Artifact movement bytes | API list-price USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSeek / Fast / E | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 61.338 | 2,032,683 / 0.215 | 0 | 0.076829 |
| Qwen / Slow / B0 | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 57.405 | 2,032,683 / 5.737 | 0 | 0.066510 |
| DeepSeek / Slow / B1 | true / valid / 1 | 17 / 17 | 24 / 11 | 2 | 392.753 | 2,032,683 / 5.739 | 0 | 0.468597 |

Fast100Mbps/configured5ms and Slow3Mbps/configured50ms retain the existing
Jetson HTB/no-netem caveat: configured delay is not measured symmetric RTT.
Initial materialization is separate from Agent-controlled registered artifact
transfers. Zero artifact movement does not mean zero HTTP prompt/control traffic.
The price estimate is based on frozen usage/pricing, not the provider invoice.
Worker operator receipts include invoke_model and must not be added again to
backend service work as an E2E decomposition.

Observed paths:

- E and B0: two BM25 attempts, two model requests, one context preflight rejection
  followed by successful smaller-input inference. Six Manager/Verifier turns,
  four graph nodes. No specialists; single-agent completion is valid.
- B1: ten BM25 actions, one aggregate_artifacts action and thirteen model requests,
  with eleven returned inference telemetry receipts and two context rejections.
  24 graph nodes/14 edges, 73 snapshots, zero specialists. Physical model input/
  output totals42,324/729; all eleven finish reasons stop. Backend service work
 260.379s. Most successful model selections were A4; the terminal prompt-only
  choice synthesis selected the4090GPU0Qwen3.5-27B instance,290input/2output tokens.
 34actual SDK contexts (17Manager/17Verifier) scanned without findings.

These unmatched Planner/method/network cells cannot establish an E or B1 causal
effect, a matched speedup, stable infrastructure adaptation or statistical
significance. B1's longer successful trajectory is retained unchanged, not
treated as a bug to tune away. Evidence coverage/semantic sufficiency and causal
profile adoption remain separate questions for the full audit.

Authoritative owner-local snapshot002 SHA256:
`0cb9a56a44ed0707482c237958a8ef9a760d2c27e85ab06a42ad01b54230bc9c`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`2f26394340da9ee15b37e049b1cde6d7cd0d0948a943eeb55396b8c4d636a3d1`.
No complete-table aggregation, private-body scan, new method, retry, prompt
tuning or replacement was performed. The remaining frozen schedule continues.
See [first-cell audit](large-scale-resident-phase2-first-cell-v1.md) and
[collector validation](large-scale-resident-phase2-projection-v1.md).
