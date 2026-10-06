# Resident Phase I checkpoint 134: correct D completion without comparison

2026-10-06. Cell `phase1-longbench_v2-1-233652563a5a9ff2-p2-slow-D`, original attempt 1.
Reserved 10:57:11.565246Z; valid settlement 11:00:03.153960Z.
Execution completed, terminal format valid, original benchmark score 1.0.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier calls | 18 / 0 / 4 |
| Prepared physical actions | 2 BM25, 1 model |
| Actual model inference | 1, resident 4090 GPU0 Qwen3.5-27B |
| Model input / output tokens; finish reason | 211 / 2; stop |
| E2E | 134.232 s |
| Fixed initial distribution | 514,789 bytes / 1.563 s |
| Recorded action transfer | 0 bytes / 0 ms; subtotal alone does not prove completeness |
| Model service / successful pure tool work | 0.480 s / 0.267 s |
| Manager / Verifier work | 115.786 s / 11.370 s; non-additive wall-time work |
| Frozen API list-price estimate | USD 0.166698386904; all 22 calls known |
| Graph snapshots / nodes / edges | 10 / 3 / 0 |
| Quote creations / commit authorizations / rejections | 8 / 3 / 1 |
| Actual root requests exposing comparison | 18 / 18 |
| Actual comparison calls / events | 0 / 0 |

The preserved SDK request/response audit shows five `discard_quote` requests,
three `commit_quote` requests and one `consult_specialist` request. Requested
tools are not successful executions: no specialist was actually created.
One `phase_restricted` observation was recorded.

The correct score and tiny 211-token physical model input do not establish that
the necessary document evidence reached terminal synthesis. The complete private
semantic evidence-path audit must distinguish grounded reasoning, information
carried by the cloud Manager, and guessing. It remains deferred until all 168
cells finish; no gold-directed analysis is injected into the running experiment.
Comparison visibility is verified, but D comparison adoption is absent in this
cell. Neither fact authorizes prompt changes or premature method pruning.

## Independent preservation checks

Original admission independently reconstructed and exactly matched: valid,
no problems or operational incidents. Original reservation and settlement bind
attempt 1 and execution freeze 004. All four Worker stores started empty,
all Workers exited, five-instance residency passed, and tc cleanup passed.
All 22 actual SDK recipient contexts passed admission scanning.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA-256: `73749518f9bf7cf88a9c2ac11e6e7a3ae632331ff5ecfb7de530747c68808b69`.
- Settlement SHA-256: `50e483878746442c518b69aca0a23361a13343fc4b5ee3c9fe64642d88ef7fc0`.
- Original admission canonical SHA-256: `6dcb27ccae5aedfaadeb5e6c97512d6d6aa6381b663834e520fe628a2d29e5f0`.
- Independent cost/interface/admission proof:
  `analysis/resident-source004-cell134-longbench-D-settlement-audit-001.json`,
  SHA-256 `b75d7d16f93656223f0cd252d31a71ebf88bb927b6db55246e7b8235d3e32957`.

No execution code, prompts, models, budgets, scheduler, or representation changed.
This is a partial checkpoint, not the complete Phase I audit or Phase II gate.
