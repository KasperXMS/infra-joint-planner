# Resident Phase I checkpoint 138: Blind valid wrong completion

2026-10-06. `phase1-longbench_v2-2-1458aa227ea0348b-p1-slow-B0`, original attempt 1.
Reserved 11:14:41.340990Z; valid settlement 11:18:29.376516Z.
Completed, terminal format valid, original evaluator score **0.0**.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier calls | 8 / 2 / 8 |
| Created / peak active specialists | 1 / 1 |
| Prepared physical actions | 13: 5 read_artifact, 5 BM25, 1 select_fields, 2 model attempts |
| Actual model inference | 1, resident A4 Qwen3-VL-4B |
| Model input / output tokens | 6,302 / 2 |
| Typed observations | 1 artifact_too_large, 1 context_limit_exceeded, 1 phase_restricted |
| E2E | 173.794 s |
| Fixed initial distribution | 2,119,778 bytes / 5.981 s |
| Recorded action movement | 0 bytes / 0 ms; subtotal alone does not establish completeness |
| Model service / successful tool work | 18.023 s / 5.885 s |
| Manager / specialist / Verifier work | 69.824 s / 38.551 s / 35.765 s; non-additive wall-time work |
| API frozen list-price estimate | USD 0.583198254029; all 18 calls known |
| Graph snapshots / nodes / edges | 40 / 13 / 10 |
| Maximum concurrent actions / overlap wall time | 4 / 2.397 s |

The context rejection did not reach inference. The Blind trajectory continued,
then produced a legal but wrong answer; there is no terminal backend or budget
failure. Primary semantic/retrieval/evidence-selection/stopping cause remains
pending the comprehensive post-168 private audit. Cell137 is not a matched
comparison: its Planner, method and network all differ. Neither cheap wrong
completion nor repeated wrong scores establish a resource-optimization claim.

Original admission independently reconstructed and matched exactly: valid,
no problems or operational incidents. Both original journal records bind
attempt1 and execution004. Four stores started empty; Worker exit, residency
and tc cleanup passed. All18 actual SDK recipient contexts passed admission
scanning. No retry, tuning, budget increase or measured source modification.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA256: `fdef45cf35bc78fc9441742c399d2f9de415268eb107042a0c90f7a7f8917b08`.
- Settlement SHA256: `c8ca7ec8d9ffd5a780fdc36a14ee09b3e3b148fbcaf2ae0f86f55a7be35714e6`.
- Admission canonical SHA256: `f6b98df19179bf80a49c21c413e91c61fd2311ab556b4ea8d6d3db2f0439e4e0`.
- Independent proof `analysis/resident-source004-cell138-longbench-blind-settlement-audit-001.json`,
  SHA256 `79b62e96f2daa01c24a1349a59b9258cd49f30c55da6f3b6c4a632b3c9a9267b`.

Current progress138/168. Full private/failure/recipient/adoption audit, frozen
pruning, actual held-out PhaseII and finalQ1–Q10 remain required.
