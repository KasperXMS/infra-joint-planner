# Resident Phase I checkpoint 136: Blind completion after context failures

2026-10-06. Cell `phase1-longbench_v2-1-233652563a5a9ff2-p2-fast-B0`, original attempt 1.
Reserved 11:07:18.199886Z; valid settlement 11:09:50.080620Z.
Execution completed, terminal format valid, original evaluator score 1.0.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier calls | 13 / 0 / 13 |
| Prepared physical actions | 11: 8 BM25, 3 model attempts |
| Actual model inference | 1, resident A4 Qwen3-VL-4B |
| Model input / output tokens | 5,131 / 2 |
| Typed observations | 2 context_limit_exceeded, 1 semantic_validation_failed, 1 phase_restricted |
| E2E | 115.929 s |
| Fixed initial distribution | 514,789 bytes / 0.110 s |
| Recorded action transfer | 6,294 bytes / 0.507 s |
| Model service / successful tool work | 14.617 s / 0.383 s |
| Manager / Verifier work | 52.778 s / 43.838 s; non-additive wall-time work |
| API frozen list-price estimate | USD 0.203672471067; all 26 calls known |
| Graph snapshots / nodes / edges | 34 / 11 / 8 |
| Maximum concurrent actions / overlap | 1 / 0 |

The two context failures are preserved and do not count as model inference.
The resource-blind Manager continued and reached a valid terminal answer without
a retry, changed budget, prompt tuning or hidden recovery. Semantic evidence
coverage still requires the complete post-168 private audit. Comparisons with
nearby cells involving different networks, methods or Planners are not causal
claims of efficiency or correctness advantage.

## Independent preservation checks

Original admission independently reconstructed and matched exactly: valid,
no problems or operational incidents. Both original journal records bind
attempt 1 and frozen execution 004; all four stores started empty, all Workers
exited, residency and tc cleanup passed. All 26 actual SDK recipient contexts
passed admission scanning. Full private bodies remain on the 4090.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA-256: `c1cedfad2797a164d9042346e2bd8932c80d4c8e3e5a1dc319653c660372ad5f`.
- Settlement SHA-256: `f386d34e23cfaa98df63d05a40e9f25c7f427ac835117d8685a8e2da3b873f92`.
- Admission canonical SHA-256: `e96b03ecb8c94a57655c276688d88ece5bb2bf5b37b7607ca3596440cc3653a6`.
- Independent cost/concurrency/admission proof:
  `analysis/resident-source004-cell136-longbench-blind-settlement-audit-001.json`,
  SHA-256 `45a959ce8a11ff0fecf44e24ff64ba539af9bbcd7da7488e358d381987fc834c`.

No runtime, Agent, model, scheduler or protocol changes. Current progress is
136 admitted cells; Phase I completion/private audits/pruning/Phase II remain
outstanding. Queue018 continues the original balanced schedule.
