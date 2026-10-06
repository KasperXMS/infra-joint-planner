# Resident Phase I checkpoint 135: correct E completion with extensive search

2026-10-06. Cell `phase1-longbench_v2-1-233652563a5a9ff2-p1-slow-E`, original attempt 1.
Reserved 11:00:52.106525Z; valid settlement 11:06:28.885653Z.
Execution completed, terminal format valid, original evaluator score 1.0.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier reasoning calls | 16 / 8 / 16 |
| Created / peak active specialists | 1 / 1 |
| Prepared physical actions | 53: 12 read_artifact, 33 BM25, 4 select_fields, 4 model attempts |
| Actual model inference | 1, resident A4 Qwen3-VL-4B |
| Model input / output tokens | 3,194 / 2 |
| Typed observations | 2 artifact_too_large, 3 context_limit_exceeded, 1 semantic_validation_failed, 2 phase_restricted |
| E2E | 297.201 s |
| Fixed initial distribution | 514,789 bytes / 1.566 s |
| Recorded action movement | 0 bytes / 0 ms; subtotal alone does not prove completeness |
| Model service / successful pure tool work | 9.175 s / 5.027 s |
| Manager / specialist / Verifier work | 146.656 s / 52.482 s / 75.967 s; non-additive wall-time work |
| API frozen list-price estimate | USD 0.968749761490; all 40 calls known |
| Manager / specialist / Verifier API estimate | USD 0.167304 / 0.097846 / 0.703599 |
| Graph snapshots / nodes / edges | 160 / 53 / 45 |
| Maximum concurrent actions / overlap wall time | 4 / 8.343 s |
| Reasoning turns with actual parallel execution | 16; 48 actions overlap |

The three context failures did not reach model inference. Their failed attempts
remain in the 53-action count, not the actual inference count. The Manager
continued after typed failures and eventually completed; success does not imply
efficient stopping or good resource use. The observed trajectory contains
extensive retrieval, a bounded specialist, and substantial Verifier API cost.
Primary semantic/retention/stopping causes require the post-168 private audit.

E's actual tool space independently passes the frozen no-query isolation check.
Sixteen cost-rule predecision events are present. Visibility is not proof that
any particular advisory rule caused an action; no internal adoption is claimed.
This result is not a matched comparison with cell 134 (different Planner/method).
No efficiency claim or method pruning is made from these two correct samples.

## Independent preservation checks

Original admission independently reconstructed and matched exactly: valid,
no problems or operational incidents. Original reserve/settle records bind
attempt 1, execution freeze 004 and the canonical admission hash. All four
stores started empty; all Workers exited; residency and tc cleanup passed.
All 40 actual SDK recipient contexts passed admission checks. Full bodies,
private evaluation and traces remain on the 4090; only bounded metadata is
reported locally. No retry, prompt tuning, budget change or execution edit.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA-256: `b6f261a464b26e99af35c154fad0d63f2b820bc9849ced92002889e7ee3b80e1`.
- Settlement SHA-256: `77fe076b01dc169ccfc0de28f4970980dc95d4a00e5425a93bc6e91b569532f4`.
- Admission canonical SHA-256: `f537a8a065ea957b497a26e11a3630af29bad862324666f397bbe07a2deb7176`.
- Independent cost/concurrency/admission proof:
  `analysis/resident-source004-cell135-longbench-E-settlement-audit-001.json`,
  SHA-256 `ba6a490c1ca22d12fcb1d76067d7cba17d75416e68016b66a930ea7c5ca961e9`.

Phase I remains incomplete. Queue018 follows the original balanced schedule;
complete private audits, frozen pruning, the real Phase II gate and final
cross-Planner analysis remain required.
