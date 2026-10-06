# Resident Phase I checkpoint 137: valid Raw-Aware wrong answer

2026-10-06. Cell `phase1-longbench_v2-2-1458aa227ea0348b-p2-fast-B1`, attempt 1.
Reserved 11:10:40.878923Z; valid settlement 11:13:49.485808Z.
Execution completed, terminal format valid, original evaluator score **0.0**.
This is a retained nominal wrong answer, not a retry or tuning candidate.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier calls | 7 / 6 / 7 |
| Created / peak active specialists | 1 / 1 |
| Prepared physical actions | 11: 4 BM25, 4 read_artifact, 3 model attempts |
| Actual model inference | 1, resident 4090 GPU0 Qwen3.5-27B |
| Model input / output tokens | 661 / 2 |
| Typed observations | 2 context_limit_exceeded, 1 semantic_validation_failed, 1 phase_restricted |
| E2E | 152.458 s |
| Fixed initial distribution | 2,119,778 bytes / 0.338 s |
| Recorded action transfer | 0 bytes / 0 ms; subtotal alone does not establish completeness |
| Model service / successful tool work | 0.666 s / 2.091 s |
| Manager / specialist / Verifier work | 61.346 s / 49.646 s / 35.121 s; non-additive wall-time work |
| Frozen API list-price estimate | USD 0.519677572118; all 20 calls known |
| Graph snapshots / nodes / edges | 34 / 11 / 12 |
| Maximum concurrent actions / overlap wall time | 3 / 0.874 s |

Only one physical model attempt reached inference; the two context failures
remain separate. No budget exhaustion or backend outage terminated the run.
The wrong result's underlying retrieval, evidence-selection, reasoning and
stopping causes remain pending the comprehensive private post-168 audit.
Neither the small model input nor low action-transfer subtotal proves evidence
loss by itself. A cheap wrong answer is not optimization success.

## Independent checks and immutable evidence

Original admission independently reconstructed and exactly matched: valid,
no problems or operational incidents. Two original journal records bind
attempt 1 and execution freeze 004. All four Worker stores started empty;
Worker exit, five-instance residency and tc cleanup passed. All 20 actual SDK
recipient contexts passed admission scanning. Full bodies remain on the 4090.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA-256: `8a14b7c61681a45b7b4e438a5f9c67588573ef65fd05266fa587711c6505b375`.
- Settlement SHA-256: `eb7843f2c60ee501e64998dbfd9597799bdc0b5c15113cbf3efcdb26293f0777`.
- Admission canonical SHA-256: `fbdf7915cbb5a42063283f120ad0df86a3781c50ea12d143759f01c63a63c280`.
- Independent cost/concurrency/admission proof:
  `analysis/resident-source004-cell137-longbench-rawaware-settlement-audit-001.json`,
  SHA-256 `274a925dcab4576061e3fa14b3615d227d6f8cc29563e84c21b8d39c0f10faed`.

No execution, Agent, protocol or model change. Current effective progress is
137/168; complete audits and frozen pruning are still required before Phase II.
