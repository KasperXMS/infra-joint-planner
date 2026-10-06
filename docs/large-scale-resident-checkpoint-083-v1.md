# Resident cells83–85: valid outcomes and one Quote confounder

2026-10-06 08:34 Hong Kong. Partial evidence only; no accuracy aggregation,
method ranking/pruning or Phase II permission. All three original outcomes are
preserved. Cell84 is not a clean comparative sample despite score1.

| Cell / condition | Completion / format / original score | Manager / Verifier / physical | Actual model inference | E2E | Complete action transfer |
| --- | --- | --- | ---: | ---: | --- |
| 83 Video602-2 / P1 / Slow / B | true / true / 1 | 5 / 5 / 3 | 1 | 720.883s | 0bytes / 0s |
| 84 Video602-2 / P2 / Fast / C | true / true / 1; runtime-confounded | 19 / 4 / 3 | 1 | 178.701s | UNKNOWN: failed read lacks complete receipt |
| 85 MultiHop1 / P1 / Fast / B | true / true / 0 | 16 / 16 / 29 | 5 | 950.202s | 30312bytes / 0.099122s |

Initial setup is separate: Video cells83/84 each move213739837bytes, taking
596.790s/18.609s respectively. MultiHop85's three complete source shards move
7696522bytes in1.159520s. These fixed costs precede Agent-controlled movement.
Cloud API/SSH communication is not counted as Worker artifact traffic.

## Cell83: normal continuation after context rejection

`sample_frames(every_seconds=176,max_frames=16)` -> eight-image model request
rejected by context preflight -> three-image request executed on resident A4
VL4B. Actual inference has3427input/2output tokens, finish_reasonstop,
18.938322s backend work. Decode/tool work45.354551s. One other model-function
request fails semantic validation before preparation; it is not inference.
The contact-sheet request was phase-restricted, not executed.

No specialists were created; graph3nodes/10snapshots/11edges, two succeeded,
one failed. Observed maximum action concurrency1/overlap0. All five actual
Manager requests had B's optional interface; there were0queries/0cards and
three observed schema-valid ready-action opportunities. This is exposure,
not evidence that the model internally used or rejected cost information.

Ten actual SDK/API recipient contexts pass original privacy checks. Frozen
regional list-price accounting totalsUSD0.1199471172882977. All five inference
instances remained resident; Worker exit/tc cleanup passed. Correct score does
not prove full temporal coverage, and differences from cell82 confound Planner,
method, network and generated trajectory, not a matched causal contrast.

## Cell84: correct answer does not remove the runtime confounder

Oversized `read_artifact` fails -> `sample_frames(every_seconds=100,max_frames=16)`
-> four images reach resident A4 VL4B. Returned inference has4444input/2output
tokens, finish_reasonstop,24.803589s backend work. Graph3nodes/10snapshots/4edges,
two succeeded/one failed, max concurrency1/overlap0. Twenty-three actual
SDK/API contexts pass original privacy checks, frozen list-price
USD0.2180554578189984. Successful transfer subtotal0 is not a complete total.

Eight quotes end as consumed3/rejected4/pending1. Four model quote commits hit
the false `quoted_action_mutated` guard, before physical execution. They are
an implementation defect, not Planner modification or bad cost reasoning.
The old projection's pending5 mislabels the four rejected quotes; its immutable
trace/result are retained with the exact correction and repair audit linked
below. Correct evaluator score does not validate the resulting control overhead.

## Cell85: valid expensive trajectory, wrong benchmark answer

Six cross-shard BM25 operations -> two context-rejected model actions ->
six `select_fields` and eight `filter_records` operations -> two aggregates ->
five actual model calls. All seven prepared model requests satisfy abstract
static requirements; only five reached inference. Actual returned totals are
17680input/2314output tokens, all five finish_reasonstop. Requests rejected in
preflight are not actual inference or zero-cost successful calls.

Inference placements: A4 VL4B once, A28 27B three times, strong-4090 GPU0 27B
once. Model service work732.805167s, tool-only work2.371804s, Manager work
157.231728s and Verifier work54.765990s are separate non-additive measurements,
not an E2E decomposition. A28 residency/loading remains verified; service work
is not a guessed cold-start term. Final evaluator score0 is valid task quality,
not an environment/runtime defect. Its primary semantic failure still requires
the full private evidence-path audit; no strategy/prompt is repaired.

No specialist was created despite two specialist-function requests. One
unprepared semantic-invalid model request is additional to the seven prepared
requests. Actual raw Manager invoke_model requests8 therefore must not be
equated with eight inference calls. There are two phase-restricted failures.

Graph29nodes/88snapshots/29edges:27successful/two failed. All physical actions
have one logical owner, no cross-agent handoff; maximum observed concurrent
actions6 and overlap2.141237s. Dependency-frontier width8 is not observed
concurrency. Dependency-path latency278.370798s excludes Manager, Verifier,
decision waits and other SDK information flow; it is not actual run critical path.

B's optional interface is present in all16actual Manager requests,0queries/
0cards;14observed ready-action opportunities. Thirty-two actual API recipient
contexts pass original privacy checks; frozen list-priceUSD0.5988651377243918.
No provider outage, post-inference JSON failure or measured model reload was
reported. All five resident instances, Worker exit and tc cleanup pass original
admission. There was no retry/replacement.

## Exact evidence and queue state

Remote `analysis` single-cell projection fileSHAs:

- 83: `d201793c1451fb71f141d6c6846e43d1fd28361c8d89347007a69bee0516312e`.
- 84: `7a6efca7e57d5d71259b78d839165dbf6e958f2f60839965ba68d08922e28496`;
  original projection is superseded for validity/lifecycle by the exact runtime audit.
- 85: `6ed7bdb22216da433be5ab35a3564406bde0713c36e41b268e4e4c882d2ff6b1`.

At00:33:51Z,85attempts are settled; cells4/84 have newly identified runtime
confounders, not clean comparisons. Queue008/atomic85 have exited; no86is
reserved. Exact [Quote integrity audit/repair](large-scale-resident-quote-integrity-repair-v1.md)
preserves the safe drain, patch/full tests and pending new-freeze/affected-rerun
gate. No new execution freeze or formal cell is claimed here. The full user goal
remains active; operational queue containment is not a completed experiment.
