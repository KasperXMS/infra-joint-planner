# Stage 2 failure attribution

The frozen H1 experiment has 14 incomplete cells among 36. This analysis inspected each original receipt, event trace and saved Verifier response **on the experiment controller**. The machine-readable [diagnostic export](../../results/harness-v2-baseline-stabilization/failure-diagnostics-public.json) gives, per cell, the private trace-relative path and response SHA256; it contains no raw prompt, candidate answer or response body. Original outcomes remain unchanged. A successful semantic action count is not an evaluator success.

| Cell | Immediate stopping cause | Successful / settled semantic actions | Manager model outputs | Physical calls | E2E s | Cloud USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| S2-fast-1-1-AWARE | raw Verifier schema | 6 / 9 | 0 | 0 | 39.6 | .0336 |
| S2-fast-2-1-AWARE | raw Verifier schema | 13 / 16 | 1 | 1 | 116.9 | .1173 |
| S2-fast-2-1-BLIND | raw Verifier schema | 17 / 31 | 1 | 1 | 163.0 | .2806 |
| S2-fast-2-1-LEDGER | raw Verifier schema | 9 / 15 | 1 | 1 | 86.5 | .0717 |
| S2-fast-2-2-BLIND | Manager turn budget | 6 / 65 | 0 | 0 | 158.8 | .1453 |
| S2-fast-2-2-LEDGER | raw Verifier schema | 13 / 17 | 1 | 1 | 119.8 | .1207 |
| S2-slow-1-1-BLIND | raw Verifier schema | 13 / 16 | 1 | 1 | 179.9 | .0867 |
| S2-slow-1-1-LEDGER | Verifier semantic validation | 6 / 8 | 0 | 0 | 55.9 | .0274 |
| S2-slow-1-2-LEDGER | raw Verifier schema | 6 / 8 | 0 | 0 | 59.2 | .0288 |
| S2-slow-2-1-AWARE | raw Verifier schema | 13 / 17 | 1 | 1 | 129.1 | .1277 |
| S2-slow-2-1-BLIND | terminal choice contract | 14 / 23 | 1 | 1 | 166.0 | .1588 |
| S2-slow-2-2-AWARE | raw Verifier schema | 13 / 16 | 1 | 1 | 111.9 | .1147 |
| S2-slow-2-2-BLIND | raw Verifier schema | 14 / 25 | 1 | 1 | 153.5 | .1763 |
| S2-slow-2-2-LEDGER | raw Verifier schema | 13 / 16 | 1 | 1 | 115.0 | .1177 |

**Trace-supported observation.** Every one of the 11 schema failures is a single `submit_verification` call with parseable JSON and a string-valued `evidence_state_version`, where the raw schema requires integer or null. Nine declare `complete`; two declare `continue` while binding a terminal candidate, and also fail semantic validation. The separate semantic-only failure is a schema-valid `continue` carrying `candidate_action_id`. These are model-generated protocol errors; no evidence indicates a wrong provider tool name, missing `arguments`, or JSON corruption. The strict boundary correctly rejected them. The immediate stop after rejection is a separate Harness recovery limitation.

**Trace-supported observation.** All 11 schema failures had 4–17 Manager/Verifier turns left. This makes bounded recovery feasible at the protocol level, but does **not** imply that a retry would yield a correct task answer. The two MultiHop Ledger failures stopped before any physical model inference or nonempty Manager model output. LongBench often performed substantial retrieval and inference before failure, so those costs are real wasted work. In the budget-exhausted cell the remaining Manager/Verifier turns were zero; it is a valid capability/budget outcome, not a Harness defect.

**Reproduced defect.** In slow LongBench trial 1 Blind, the saved successful Manager candidate satisfied the early leading-choice check, but the later deterministic terminal parser raised `AgentLoopError` on the same text. The in-place probe exports only booleans and length. This is an inconsistent Harness transition; candidate correctness against hidden gold was not evaluated. See [protocol analysis](verifier-protocol-analysis.md).

Failure labels show where execution stopped, not a complete counterfactual explanation of TSR. Nine malformed `complete` calls followed nonempty candidate model outputs, but neither the protocol metadata nor hidden evaluator establishes that any was correct. Likewise, the 63 explicit physical `context_limit_exceeded` rejections across all 36 cells are observable capability failures, not silent truncation and not automatically the proximate cause of these 14 stops.
