# Resident-block checkpoint 053–056

2026-10-06. Four more original attempt1 outcomes are settled and classified;
56/168 is a nominal-outcome count, not a completion rate or pooled accuracy.
The six earlier original rejection receipts and their exact proof sidecars
remain immutable. No retry/replacement, semantic tuning, source change or
early method pruning. Historical 42 are closed and unpooled.

## Video representative 2: 131-3

All three cells use the same original full-timeline video representation,
7,037,220 source bytes initially on A4, original task/evaluator, frozen finite
tools/budgets, independent fixed Blind Qwen Verifier and five resident physical
model instances. P1 is `deepseek-v4-pro`; P2 is `qwen3.8-max`. Each cell has fresh
Worker processes/stores and its own network attestation. Fast is nominal
100 Mbps/configured 5 ms; Slow is 3 Mbps/configured 50 ms, not measured symmetric
RTT. No measured-cell model reload, cold-start subtraction or substitution.

| Measurement | 53: P1/Fast/B1 | 54: P2/Slow/A | 55: P1/Slow/B |
| --- | ---: | ---: | ---: |
| Completed / canonical terminal / original score | yes / valid / 1.0 | yes / valid / 1.0 | yes / valid / 1.0 |
| Manager / Verifier turns | 6 / 6 | 6 / 6 | 5 / 5 |
| Specialists created / specialist turns | 0 / 0 | 0 / 0 | 0 / 0 |
| Physical actions / actual inferences | 3 / 1 | 4 / 2 | 3 / 1 |
| Context rejects / static-impossible binding rejects | 0 / 1 | 1 / 0 | 1 / 0 |
| E2E, seconds | 80.210 | 97.999 | 128.689 |
| Fixed initial placement, bytes / seconds | 7,037,220 / 0.637 | 7,037,220 / 19.707 | 7,037,220 / 19.710 |
| Complete action transfer, bytes / seconds | 0 / 0 | 0 / 0 | 0 / 0 |
| Complete tool-only work, seconds | 1.514 | 1.325 | 1.628 |
| Complete physical backend work, seconds | 19.137 | 25.819 | 44.235 |
| Physical model input / output tokens | 3,403 / 2 | 4,651 / 4 | 7,775 / 2 |
| Returned finish reasons | 1 × stop | 2 × stop | 1 × stop |
| Manager / Verifier work, seconds | 41.774 / 15.533 | 31.639 / 17.380 | 47.160 / 14.121 |
| Frozen-list-price API USD estimate | 0.1189985131 | 0.1514688157 | 0.1185438991 |
| Actual SDK contexts audited / known API usages | 12 / 12 | 12 / 12 | 10 / 10 |
| Graph nodes / artifact edges / snapshots | 3 / 9 / 10 | 4 / 13 / 13 | 3 / 23 / 10 |
| Actual maximum action concurrency / overlap | 1 / 0 s | 1 / 0 s | 1 / 0 s |

All successful tool/model actions selected A4; actual inference used its
resident Qwen3-VL 4B deployment. Selection-stage rejects do not count as
inference. There are no unmeasured failed executions/inferences in these
receipts. Inclusive Worker/model-wrapper work contains backend time and must
not be added to it. Work sums and action dependency-path timings do not
decompose E2E; initial placement is fixed setup, not Agent-controlled movement.

### Observed continuation and method interfaces

Cell 53 grew `sample_frames → rejected invoke_model → successful invoke_model`.
The rejected request is classified **static impossible**, not dynamic deployment
unavailability. The later legal request used three frame artifact inputs rather
than six declared edges at the rejected node. This establishes visible
continuation, not that raw profile feedback caused it, nor semantic adequacy of
each individual frame. Two semantic-validation and two phase-restricted SDK
failures also remain recorded. Actual raw Manager responses contain three
`invoke_model`, two `sample_frames` and two `make_contact_sheet` calls; only one
sampling and two model actions reached the physical graph. **No contact sheet
execution is established.** Raw response counts and replay-history lower bounds
are different scopes, not interchangeable executed-call totals.

Cell 54 grew `sample_frames → context-rejected model → visual inference →
terminal model inference`. Declared artifact edges at those model nodes are
8, 4 and 1, respectively. All three requested abstract model requirements are
statically feasible; the first full request still exceeded input-context
preflight. This is evidence of request-size recovery, not proof of dynamic
infrastructure infeasibility. One semantic-validation and one phase-restricted
SDK failure are separately recorded. No extra tool is credited merely because
the Manager attempted it.

Cell 55 grew `sample_frames → context-rejected model → successful model`, with
16 then 7 declared frame input edges. Both model requirements are statically
feasible. One semantic-validation and one phase-restricted SDK failure also
remain visible. B's optional interface appeared in all five actual Manager
requests, but **zero query attempts/cards**, despite three observed ready
schema-valid action opportunities. No absent cost card is credited with
changing this trajectory.

All 34 actual SDK recipient contexts passed original admission checks, as did
evaluator integrity, Worker exits, residency, method/privacy checks and tc
cleanup. The graph's maximum frontier width of two in each run is not executed
parallelism. A single action owner and zero specialists are legal, not a
failure to meet a forced MAS gate. These n=1 cells vary method/Planner/network;
their timings do not isolate a treatment effect or justify choosing a winner.

### Cell 56: P2 / Fast / C

Cell 56 also completed with valid canonical terminal and original score 1.0.
Five Manager turns, two Verifier calls, zero specialists, two physical actions:
one `sample_frames` and one A4 resident VL4B inference. No physical context or
binding rejects. One quote-proposal semantic validation rejection remains a
typed SDK failure, not an inference. Two quotes were consumed, zero discarded /
stale; quote-control work 0.436 s. This exercises mandatory quoting but does not
establish quote-induced revision or optimization benefit.

E2E 60.117 s; fixed initial 7,037,220 bytes / 0.678 s; complete action transfer
0 bytes / 0 s; complete tool-only work 1.276 s; complete backend work 38.088 s.
Actual model usage 6,632 input / 4 output tokens, `stop`. Manager / Verifier
work 14.529 / 4.822 s; all seven API usages known, list-price estimate
USD 0.0825679374. All seven actual SDK contexts passed admission. Graph 2 nodes,
6 edges, 7 snapshots; both nodes succeeded, maximum concurrency 1 / overlap 0.
No absent failed-execution measurement is replaced by zero.

## Immutable provenance

Remote projections reside under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
They verify hash-linked original journal entries, canonical admission/result
agreement, exited Workers and residency, and bind trace/result/source file
hashes. Only bounded metadata/telemetry are exported; no dataset body, gold,
raw effective prompt or model payload is moved through the local PC.

| Cell | Original admission canonical SHA-256 | Append-only projection file SHA-256 |
| --- | --- | --- |
| 53 | `652f5d4d0e665febc739bf45b8a49a0ec13c4dd08bc84c65d95100b9c081508a` | `0213ff583d66d222a1c62433075410fd0543ee01157943cb37ec7d0c6595ba68` |
| 54 | `be39ca53668cfb091e50f5d0cdfd0fe4924ff049bbb34959586f36aaaf19f74a` | `3940d267034aa997363e2d662cbec87b4b890573b38ac65607c4404a47b655a5` |
| 55 | `2a895fa1967f47ac560088096ca76c552c765abcf0e12347528f88451cccc8ab` | `f5b24ce2891eccc67208ff5dc064160d94b68918319305fbe2ac86da36a1fb28` |
| 56 | `fde0a3216e267abafaa648cef2752973b404b0ef06433bf15294a3e63d5e65a8` | `f03877ba9eb40900a6027aa91c3299d501ba9c8fd397a98fe0726d58dbaa89bc` |

Projection names are `resident-cell-053-summary-001.json`,
`resident-cell-054-summary-001.json`, `resident-cell-055-summary-001.json`,
`resident-cell-056-summary-001.json`.
Original settlement sequences 106/108/110 occurred at
21:29:34.785582Z / 21:32:01.620932Z / 21:34:57.620817Z on October 5.
Their comprehensive-private-audit and pruning-authorization flags remain false.
Cell 56 settled at sequence 112, 21:36:45.776000Z, original settlement SHA
`414f481d68976f5f0ba01fd071968876a19392e13088f5c04adc6acbecba1dfd`.
An initial read-only 54/55 projection probe used the wrong initial previous-hash
sentinel and failed before any write; corrected verification used the journal's
documented 64-zero sentinel. No measured cell or original evidence was rerun.

## Continuation and remaining obligations

Queue 007 PID `2437975` and cell 57 atomic PID `2494581` were verified live at
21:37:59.950280Z: MultiHop representative 2 / P1 / Fast / B, original attempt1.
It was reserved at sequence 113, 21:36:48.136138Z. These are historical observations,
not restart authority; check actual process/journal before acting.

Frozen execution source, execution freeze 001 and queue control freeze 006
remain unchanged. This checkpoint changes documentation only; full tests last
passed before that control freeze (1077 pytest, Ruff, strict Pyright, diff
check). All 168 new primary outcomes and comprehensive semantic/recipient/
failure/adoption audit remain required before screening/pruning, then actual
preregistered Phase II within `42 + 168 + 48m <= 420`, and final reports/Q1–Q10.
No survivor set, reduced objective, early aggregate accuracy or completed-goal
claim follows from this checkpoint.
