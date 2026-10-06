# Resident Phase I checkpoint140: D attempts comparison but exhausts horizon

2026-10-06. `phase1-longbench_v2-2-1458aa227ea0348b-p1-fast-D`, attempt1.
Reserved11:23:09.599888Z; valid settlement11:26:21.401491Z.
Execution did not complete: `AgentLoopError: manager turn budget exhausted`.
Terminal/evaluation are absent; score and format remain **unknown**, not zero.

| Metric | Actual value |
| --- | --- |
| Completed Manager / specialist / Verifier cloud calls | 20 / 0 / 2 |
| Prepared physical actions | 2 BM25 |
| Actual model inference | 0; no model action prepared |
| Quote creations / commit authorizations / discards | 7 / 2 / 5 |
| Quote rejections | 12, phase_restricted; separate from 1 logical phase_restricted observation |
| Actual comparison calls / submitted candidate count | 1 / 3 |
| Returned valid quote cards / feasible comparisons / selected quotes | 0 / 0 / 0 |
| Actual root requests exposing comparison | 20 / 20 |
| E2E reconstructed from failed-run trace | 156.823s |
| Fixed initial distribution | 2,119,778bytes / 0.854s |
| Recorded action movement | 0bytes / 0ms; subtotal alone does not establish completeness |
| Successful tool / Manager / Verifier work | 0.789s / 148.288s / 6.015s; non-additive wall time |
| Frozen API list-price estimate | USD0.140225768347; all22 calls known |
| Graph snapshots / nodes / edges | 7 / 2 / 0 |
| Maximum concurrent actions / overlap | 2 / 0.601s |

D **was attempted**: one real SDK tool call submitted three candidates. All
three returned typed failures, not created cost cards. The returned comparison
result is exactly present in eight subsequent recorded root SDK inputs; no
member quote was selected or executed. Thus one submitted multi-candidate set
is not one usable multi-consequence or multi-feasible comparison. This differs
from previous D cells with no comparison call at all.

Observed terminal cause is20-turn Manager-horizon exhaustion, not64-call
exhaustion or unavailable inference. The detailed stopping/phase/quote behavior
remains for the comprehensive post168 private audit. No budget or protocol is
changed to rescue this cell. A requested specialist did not create a specialist.

## Independent evidence and diagnostic correction

Original admission independently reconstructed and exactly matched: valid,
no problems or operational incidents. Original reserve/settle bind attempt1
and execution004. Four empty stores, Worker exit, residency, tc cleanup and
all22 actual SDK recipient contexts pass. Result preserves `loop=null` and
`telemetry=null`; the complete trace supplies timing/graph/physical counts.

The first metadata proof used a lexical event-name filter for `compare` or
`comparison`; the actual event name is `logical.cost_candidates.returned`.
Its lexical event count is **not an adoption metric**. An append-only independent
proof applies the existing exact-card/exposure adoption auditor and records
the correct one returned set, three typed failures and zero valid comparisons.
The original proof/result/trace remain unchanged. This is a read-only diagnostic
correction, not an execution defect or reason to repeat the cell.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA256: `efa44541f192788292c8e219f25a28267de766148cbbbe262572e6ea2ad85e55`.
- Settlement SHA256: `f08a921d6c53b867760bf05befcfc3ee6fd0fcf12b6f5111c3f2bf3384c8e934`.
- Original admission canonical SHA256: `f151c4c85ca2e393f370b9be9b87a0f84578c2984740cf28c2b9d8e037801b01`.
- Cost/admission proof `analysis/resident-source004-cell140-longbench-D-settlement-audit-001.json`,
  SHA256 `b59de04c65a057f0700d5184f9da637f8038343fcc34d6a30de30d49ab9c30cf`.
- Correct interface/adoption proof `analysis/resident-source004-cell140-D-interface-adoption-002.json`,
  SHA256 `8d1cfb4d241235268eb10fa9f79893d8926c976ec05a6d68f6a6ca633488fc37`.
- Existing offline adoption auditor source SHA256:
  `6327d3ed5864011f670850bce08bacb1818fff7853b6af8298a440a9ec2a35d4`.

140/168 effective cells, no premature method selection. Complete audits,
frozen pruning, actual PhaseII and finalQ1–Q10 remain outstanding.
