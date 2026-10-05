# Resident-block checkpoint 035

2026-10-06. The study remains unfinished: 35 of 168 new Phase I nominal
outcomes are classified; cell 36 is running. Admission is not synonymous with
successful completion or correctness. The old 42 outcomes remain closed and
unpooled, while counting toward the cumulative 420-cell cap.

## Evidence boundary

Read-only snapshot 017 captured 34 admissions / one pending / zero unresolved
confounders at `2026-10-05T20:03:05.258146Z`, file SHA-256
`9feaa8a807563f8f8abe019382b617f332a501c76c6ce1a312241858469bd973`.
It retains the four original rejection receipts and exact offline sidecars:
one model-output JSON error, one record-field misuse and two provider input-policy
refusals. No original receipt or historical result was overwritten.

Cell 35 subsequently settled as valid at `2026-10-05T20:03:58.222344Z`, journal
sequence 70. Its original admission canonical SHA is
`43e524aed30b7a91249f12bb85bb7625e83d1aad5cc751e8679e0de15cd54956`;
the hash-linked settlement entry SHA is
`4ca86859e1b0a2c5ff55899fa9ca64b9b3b941f8aa74eb2d7347cc7efb4d05f3`.
Thus the later 35-outcome count is not falsely attributed to snapshot 017.

The separate read-only projection `analysis/resident-cell-035-summary-001.json`
binds this reservation/settlement, admission, result, trace, process exit,
Worker shutdown, residency receipt and collector source hashes. File SHA:
`0e64f027f8ae16e3edaaabe03f4bb8b60598e376a28e781ab80001d0a0725f5d`.
It verifies the journal chain using the actual journal digest implementation and
checks result/admission consistency; it is not a full private semantic audit or
a replacement admission. Only bounded metadata was returned to the local PC.

## Cell 35 result

Task: Video-MME `602-2`, the frozen original full-timeline video representation.
Condition: P1 (`deepseek-v4-pro`) / Slow / B1 raw pre-decision awareness, with the
same independent infrastructure-blind Qwen Verifier. Run ID:
`large-scale-cost-guidance-resident-v1-phase1-video_mme-1-7ea6434bc064f69c-p1-slow-B1-attempt1`.

| Measurement | Observed value |
| --- | --- |
| Execution / terminal format / original evaluator | completed / valid / 1.0 |
| Manager / Verifier turns | 3 / 3 |
| Created specialists / specialist turns | 0 / 0 |
| Physical actions / actual model inference | 2 / 1 |
| Context preflight rejects | 0 |
| Tool sequence | `sample_frames -> invoke_model` |
| Actual physical selections | both A4; model `resident-a4-vl4b-v1` |
| E2E | 716.105 s |
| Fixed initial placement | 213,739,837 bytes / 596.782 s |
| Complete action artifact transfers | 0 bytes / 0 s |
| Tool-only execution work | 45.563 s |
| Backend model service work | 37.710 s |
| Physical model tokens / finish reason | 6,690 input / 2 output / stop |
| Manager / Verifier reasoning work | 25.998 s / 8.251 s |
| Frozen-list-price API estimate | USD 0.0734726730, six calls with known usage |
| Actual SDK recipient contexts audited | 6 |
| Execution graph | 2 nodes / 6 edges / 7 snapshots; both nodes succeeded |
| Observed parallel action width | 1; zero overlapping action wall time |

The recovered `phase_restricted` function failure remains in the trajectory.
It is not a context reject, physical inference, automatic retry or replacement.
All actual recipient, original-evaluator, tc cleanup, Worker exit and five-model
residency gates passed. Fresh stores are not cold inference caches; there was no
model reload/warmup or startup subtraction in this measured cell.

Raw inclusive Worker operator work is 83.439 s, including the model action.
Do not add backend service work to that inclusive total. Initial placement is
fixed setup before Agent reasoning, not an Agent-controlled information movement
decision. Zero action artifact bytes does not mean zero SDK/API/RPC traffic.
The graph's six edges include information dependencies, not six physical actions
or a parallel MAS trajectory.

## Live continuation and unfinished scope

At `2026-10-05T20:06:06Z`, queue 005 PID `1997584` and cell 36 atomic PID
`2129949` were verified live by their actual `/proc` command lines. Cell 36 is
Video `602-2` / P2 / Fast / A, reserved at journal sequence 71. Re-read those
handles before relying on them; an observation timeout is not a stopped run.

Measured app execution freeze and external continuation freeze 004 are unchanged:

- execution: `4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`;
- control: `dbbc9d0a4752e31e07b0428cf911da3bcafccbf0d20b65c8f69a8af8e5bac6e4`.

No methods, prompts, budgets, model contracts, scheduler, tasks or measured code
were changed. No early method pruning, cross-benchmark score pooling, Phase II
selection or causal method claim is made. Finish all 168 cells, then complete
private evidence/recipient/failure/adoption auditing and freeze pruning before
preregistering and executing Phase II within `42 + 168 + 48m <= 420`.
The final reports and Q1–Q10 characterization remain required; see the
[full completion audit](large-scale-completion-audit-v1.md).

## Later settlement: cell 36

Cell 36 / Video `602-2` / P2 / Fast / A settled valid at
`2026-10-05T20:07:15.827600Z`, journal sequence 72, giving 36 classified nominal
outcomes. Original admission canonical SHA:
`2b0455449900a6559040909d516c1795bc814b6a13e4e5239c52099d225f9c6b`.
The separate `analysis/resident-cell-036-summary-001.json` applies the same
hash-linked single-cell checks, file SHA:
`2e10e046b42a34f68c7f403a68f709c7d8d3c6b543633f8481a67989c70dd73e`.
Neither this addition nor the 35-cell projection changes snapshot 017.

Completed / valid terminal / original score 1.0; Manager 6 / Verifier 6;
zero specialists; three physical actions with only one actual model inference,
one explicit context preflight reject. Two semantic validation failures and one
phase-restricted function call also remain recorded. The Agent continued legally
to successful inference without a harness retry or replacement. All twelve
actual SDK contexts, residency, Worker exit and tc cleanup passed.

E2E 145.626 s; fixed initial 213,739,837 bytes / 18.610 s; complete action
artifact movement 0 bytes / 0 s; tool-only work 45.046 s; backend service work
25.158 s. Model usage: 4,504 input / 2 output tokens, stop. Frozen-list-price API
estimate USD 0.1427094407. Graph: three nodes / twenty information edges / ten
snapshots, two succeeded and one failed node, max one concurrent action. Its
dependency frontier width of two did not produce observed parallel execution.

Cell 35 and cell 36 differ in both Planner/method and network. Their large E2E
difference is dominated by the separately recorded fixed initial transfer; it
does not demonstrate a method-controlled resource improvement. No winner,
causal adaptation, aggregate quality or pruning claim follows.

At `2026-10-05T20:07:49Z`, cell 37 atomic PID `2143489` was verified live on
Video `131-3` / P2 / Fast / B, reserved at journal sequence 73. Queue 005
continues unchanged. Re-read actual process state at the next continuation.
