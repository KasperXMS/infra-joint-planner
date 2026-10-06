# Resident PhaseI checkpoint133: C exhausts Manager horizon

2026-10-06. Valid nominal failure, not a system confounder or a retry candidate.

Cell `phase1-longbench_v2-1-233652563a5a9ff2-p1-fast-C`, attempt1.
Reserved10:53:31.835155Z; valid settlement10:56:23.492898Z.
Execution did **not** complete; terminal failure is `logical_loop_failed`,
`AgentLoopError: manager turn budget exhausted`. Original evaluator was not
invoked: benchmark score and terminal format are **unknown**, not zero.

| Metric | Actual value |
| --- | --- |
| Completed Manager / specialist / Verifier cloud calls |20 /0 /3|
| Prepared physical actions |2read_artifact,2BM25|
| Actual model inferences |0; no physical model action was prepared|
| Typed observations |2artifact_too_large,1phase_restricted|
| Quote creations / commit authorizations / quote rejections |9 /4 /10|
| Trace-measured E2E |134.796s|
| Initial placement |514,789bytes /0.412s|
| Recorded action transfer |0bytes /0ms; no completeness claim merely from subtotal|
| Successful tool work |0.095s; failed-read latency not included|
| Model service / physical inference tokens |0 /0; verified no actual inference, not an estimate from missing usage|
| Manager / Verifier work |123.502s /9.046s; non-additive E2E work|
| API frozen list-price estimate |USD0.117260598732;23calls, known usage-cost|
| Trace-grown graph snapshots / nodes / edges |13 /4 /0|
| Full actual SDK recipient contexts |23; no admission findings|

The failed run's result has `loop=null` and `telemetry=null`. Its preserved full
JSONL contains action/graph/cost/timing events, including measured failed-run E2E;
the unchanged trace-audit implementation reconstructs the above metrics. No
result is rewritten to manufacture a successful loop or evaluation. A diagnostic
initially assumed every result had a loop; that read-only assumption was corrected
before publishing any proof, without modifying execution or rerunning the cell.

Observed terminal class: Manager-horizon/budget exhaustion. Underlying semantic,
retrieval, stopping and quote-protocol contributions await the complete post168
private trace/evidence-path audit. A20-turn ceiling with only4prepared physical
actions is not64-call exhaustion. No budget or C prompt/strategy is changed.

## Independent preservation checks

Original admission independently reconstructed and matched exactly: valid,
no problems or operational incidents. Both original reserve/settle records bind
attempt1 and frozen004; four stores started empty, all Workers exited, five-instance
residency passed, tc cleanup succeeded. Failure result and whole trace preserved.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA256:
  `c18f7bf3ad1634ced830e5f605870a35547464740c28352e9e85286f0d67c7d0`.
- Settlement SHA256:
  `974fc75fe3743db819b37ba909767ce65c899ca9da4a920cf401a864f6713c33`.
- Independent admission/result/trace/exit/tc/graph/cost proof
  `analysis/resident-source004-cell133-longbench-C-settlement-audit-001.json` SHA256:
  `cd02902cc6fbcb1aac1493b8732c9ab0724a6ea517526883eef77dfc65744c71`.

Snapshot045remains an immutable132+1pendingtimepoint, not retrospectively changed.
This exact valid settlement yields133effective cells. Original Queue018 continues;
full168/private semantic/failure/recipient/adoption audits/frozen pruning/actual
PhaseII/finalQ1–Q10remain required. Normal trajectory failures do not trigger tuning.
