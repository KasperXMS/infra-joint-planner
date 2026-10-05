# Resident-block checkpoint 040

2026-10-06. Forty of 168 new Phase I nominal outcomes are classified; the
full study is not complete. Cell 40 settled valid at journal sequence 80,
`2026-10-05T20:16:16.298046Z`. The original four rejected admissions remain
preserved with their exact offline sidecars; no new attempt was repeated,
replaced or semantically repaired. The old 42 results remain closed and unpooled.

## Newly inspected Video-MME receipts

All four rows below concern the same frozen Video-MME task `131-3` and original
full-timeline source, but their Planner, method and/or network differ. P1 is
`deepseek-v4-pro`, P2 is `qwen3.8-max`; the independent Blind Verifier is fixed
`qwen3.8-max`. Each row is one scheduled attempt, not a repetition.

| Ordinal | Planner / network / method | Completion / format / original score | Manager / Verifier | Physical actions / actual inference / context rejects | E2E s | Initial bytes / work s | Complete action bytes / work s | Tool-only work s | Backend work s | API estimated USD |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| 37 | P2 / Fast / B | yes / valid / 1.0 | 3 / 3 | 2 / 1 / 0 | 47.011 | 7,037,220 / 0.652 | 0 / 0 | 1.313 | 24.844 | 0.0736689565 |
| 38 | P1 / Slow / A | yes / valid / 1.0 | 6 / 6 | 3 / 1 / 1 | 104.447 | 7,037,220 / 19.713 | 0 / 0 | 1.635 | 18.901 | 0.1267842265 |
| 39 | P2 / Slow / B1 | yes / valid / 1.0 | 4 / 4 | 2 / 1 / 0 | 86.303 | 7,037,220 / 19.706 | 0 / 0 | 1.632 | 37.510 | 0.0776280365 |
| 40 | P1 / Fast / B0 | yes / valid / 1.0 | 6 / 6 | 4 / 2 / 1 | 116.955 | 7,037,220 / 0.979 | 0 / 0 | 1.313 | 49.471 | 0.1456709948 |

All rows have zero created specialists and maximum one observed simultaneous
physical action. Actual SDK recipient context counts are respectively 6, 12, 8
and 12. Original evaluator, full recipient privacy/method input checks, Worker
exit, tc cleanup and all five resident-instance checks passed. Physical inference
selected the existing local A4 4B visual model; neither explicit device routing
nor model startup subtraction was introduced.

Each completed physical path begins with `sample_frames`. Cell 37 and 39 each
have one successful `invoke_model`. Cell 38 has a rejected context request followed
by one successful inference; cell 40 has one rejected context request and two
successful inferences. Context rejection does not count as backend inference.
Semantic argument-validation / phase-restricted function errors remain in the
recorded trajectories; legal later Agent actions are not harness retries.

Model input/output totals: 37 = 4,456/2; 38 = 3,409/2; 39 = 6,661/2;
40 = 8,928/4. All returned inference finish reasons are `stop`. Graph node/edge
counts: 2/4, 3/18, 2/6, 4/24. Cell 40's dependency frontier width is three, but
actual action concurrency is one; graph width is not realized parallelism.

Cell 37 backfills the previously bounded receipt in
[checkpoint 035](large-scale-resident-checkpoint-035-v1.md): raw Manager responses
confirm zero optional cost queries, zero cards and two observed schema-valid
ready action opportunities. The optional interface was present in all three
Manager requests. Interface availability is not adoption; this one trajectory
does not establish a cross-Planner pruning conclusion.

## Provenance

New append-only remote projections bind journal reservation/settlement entries,
original admission/result/trace, Worker shutdown/process exit/residency and
collector source hashes. They verify the actual journal digest algorithm and
result/admission consistency. No benchmark body or private evaluator material
was transferred through the local PC.

| Remote projection under the resident root | File SHA-256 |
| --- | --- |
| `analysis/resident-cells-037-038-summary-001.json` | `bffc9bf55232f48e53bd22e083094997f7374fe9f158d48eadf9154b107fe74f` |
| `analysis/resident-cell-039-summary-001.json` | `5b6352413a7f9e39f5f8fdacf33809155a79b8fa503b9591fa70a3194d0a133d` |
| `analysis/resident-cell-040-summary-001.json` | `4c803ca6b97c7e302c2cb0bcbc27f0226aa6fc2e6fe59546dab07c03334d72d2` |

Original admission canonical hashes for cells 38, 39 and 40 respectively:

- `94509eb76bd9003e0c92aa9ed65c5277060928ca3f742a04c281c88ab693990d`;
- `ae229773028fa441e05b8c5115d375a68e065b3a12ac5f36887d46b4facf79a1`;
- `85d5d158b8527a2b2516bc18d2a78226f567f46c53804d5f36ae60ab0d3a9f7c`.

Reported transfer/work scopes are complete here only because their persisted
receipts have no unmeasured execution-stage failures; this is not a universal
zero-imputation rule. Inclusive Worker operator work already includes model
actions and is not additive with backend work. API costs are frozen regional
list-price estimates, not invoices. E2E includes fixed setup; no online predicted
E2E or scalar objective was exposed.

## Continuation / completion limits

At `2026-10-05T20:17:00Z`, cell 41 atomic PID `2183138` was verified live on
MultiHop representative 2 / P2 / Fast / D, reserved at sequence 81. Queue 005
PID `1997584` remains the unchanged external continuation controller. Re-read
actual processes later; a stale receipt or observation timeout is not a terminal
condition or retry authority.

The measured execution and external control freeze 004 remain unchanged. No
prompt, Verifier, budget, benchmark, finite tool vocabulary, scheduler, model
contract or method changed. This checkpoint is not a causal method comparison,
score aggregate, complete private evidence audit or pruning manifest. In
particular, lower bytes or E2E in a different stochastic trajectory cannot be
attributed to infrastructure guidance from this table alone.

Continue all 168 primary outcomes, then complete private semantic/recipient/
failure/adoption auditing, freeze screening/pruning, preregister and execute
remaining Phase II tasks under `42 + 168 + 48m <= 420`, and finish the named
reports plus Q1–Q10. No final goal completion is claimed; the
[full-scope audit](large-scale-completion-audit-v1.md) remains applicable.

## Later settlement: cell 41 / MultiHop 2 / P2 / Fast / D

Cell 41 settled valid at sequence 82, `2026-10-05T20:18:16.898465Z`, raising
the classified-outcome count to 41. Completed / valid terminal / original score
1.0; Manager 10 / Verifier 2; zero specialists; four physical actions:
three BM25 retrievals and one actual model inference, no context rejects.
All twelve SDK recipient contexts, original evaluator, Worker exit, tc cleanup
and five resident-instance gates passed. Original admission canonical SHA:
`188adb0ab4b4dca0ba8cbd1b944b39b5d05c152954703ff91777f60ab34ccf9d`.
Append-only `analysis/resident-cell-041-summary-001.json` file SHA:
`6a3d94f46b01d6e46d5fe7bfa80594952ad5272e30980456188edb5572ff2bfe`.

Task identity is `multihop-rag-train-fe71f374676e35359d12c83e`.
E2E 74.151 s; initial 7,696,522 bytes / 1.505 s; complete action artifact
transfer 0 bytes / 0 s. Tool-only work 1.133 s; backend model work 11.371 s;
Manager / Verifier reasoning work 55.302 / 4.715 s. Physical model usage
3,987 input / 3 output tokens, stop. Frozen-list-price API estimate
USD 0.1116954544, all twelve calls with known usage.

Graph 4 nodes / 1 edge / 13 snapshots, all nodes succeeded. The three
independent ready BM25 actions ran on A5/A4/A28 with maximum three simultaneous
actions and 0.508 s observed overlapping wall time. The model ran on A4's
existing 4B deployment. This is actual same-owner ready-action parallelism,
not three agents or proof of an E2E improvement over a counterfactual.

D issued five quotes: four consumed/authorized, one discarded, none stale;
measured quote control work 0.842 s. **Zero real multi-candidate comparisons**
were observed. Eight phase-restricted function receipts remain in the actual
trajectory and are not physical inference calls. Quote count is not candidate
count, and a discarded quote is not proof of cost-induced semantic revision.
The complete matrix and later private evidence audit remain necessary before
assigning a method-level mechanism/failure explanation.

Read-only snapshot attempt 018 produced no projection: the journal advanced
during collection, so the collector failed closed. Preserve its
`audit-tools/resident-policy-control-003/snapshot-console-018.log`; do not
overwrite or label it a successful snapshot. This observation failure did not
stop, restart or invalidate a measured cell. Snapshot 017 retains its earlier
34-outcome boundary; later counts rely on immutable subsequent settlements and
their bound per-cell projections, not a fabricated full snapshot.

The next atomic process, PID `2192132`, was verified live on cell 42 / MultiHop 2 /
P1 / Slow / C while the queue 005 continuation remained unchanged. No new freeze,
method tuning, retry, pruning or Phase II authorization occurred. All remaining
full-study requirements are unchanged.

## Later settlement: cell 42

Cell 42 / MultiHop representative 2 / P1 / Slow / C settled valid at
`2026-10-05T20:21:23.623092Z`, sequence 84. Completed / valid terminal /
original score 1.0; no admission problems. Original admission canonical SHA:
`e00b9af2b05d4a6fa76288024a2c8e3be033217958f70dde94e0c5d9a32668a8`.
Admission-bound result canonical SHA:
`20bd42236463b71d93aed16e8afe63e771cf758d65dd85f991c9413290ff75c5`.

The bounded result receipt reports Manager 14 / Verifier 3, zero specialists,
four charged tool/model calls, E2E 123.066 s, initial 7,696,522 bytes / 22.115 s
and returned action transfer 0 bytes / 0 s. Inclusive operator work is 1.849 s;
Manager reasoning work 89.776 s. Separate inference/preflight accounting, quote
adoption, API cost and complete failed-action movement need the later full
per-cell projection; this receipt does not infer those quantities from total
calls or inclusive work.

There are now 42 classified new nominal outcomes, not a resumed/pool of the old
closed 42-outcome block. At `2026-10-05T20:21:54Z`, cell 43 atomic PID
`2205076` was verified live on MultiHop representative 2 / P2 / Slow / B,
reserved at sequence 85. Queue 005 remains unchanged. No pruning, Phase II or
full-study completion is authorized by this checkpoint.

## Cell 42 accounting backfill

`analysis/resident-cell-042-summary-001.json` now separately binds the original
admission/result/trace, journal entries, process exit, Worker shutdown/residency
and the existing collector sources. File SHA:
`626c3dd6414a67207f4fa181bf445c6fd487c4abe873b8b6969662efc3c25a6d`.
It does not overwrite the earlier bounded receipt or change execution behavior.

Four physical actions were three successful BM25 retrievals and one successful
model inference; zero physical context rejects. BM25 ran on A5/A28/A4 with
maximum three simultaneous actions and 0.817 s overlapping wall time. Tool-only
work 1.437 s. The terminal model action had **no artifact inputs**, a 329-byte
prompt, and ran on the existing strong GPU0 27B deployment: actual 77 input /
3 output tokens, stop, 0.407 s backend work. Complete action artifact transfer
remains 0 bytes / 0 s, not an estimate inferred from missing measurements.
Seventeen actual SDK recipient contexts passed the original admission audit.
Frozen-list-price API estimate: USD 0.1029014762, all seventeen calls known.

The quote trace records six proposals: four consumed/authorized, two discarded,
none stale. Measured quote control work 2.673 s; Manager reasoning work remains
89.776 s and is not omitted from method overhead. The two discarded model
proposals had artifact inputs and explicit quoted `context_limit_exceeded`
selection consequences. Both consequence cards were present in actual Manager
inputs before their discard decisions. Neither proposal was committed or reached
physical inference. Do not count these as two inference calls or two submitted
physical context rejects; quote-level feasibility feedback is a distinct scope.

The terminal prompt-only proposal subsequently quoted feasible and was committed.
This proves an observed change of proposal/input structure after feasibility
feedback, **not** a counterfactual causal cost benefit or a demonstrated network
trade-off. It does not prove required evidence was preserved after this change;
that remains a post-run private semantic audit question. Context feasibility is
not interchangeable with infrastructure bandwidth sensitivity.

Graph: four nodes / zero declared artifact edges / thirteen snapshots; all nodes
succeeded. Zero declared edges does not mean no information reached the Manager:
native tool observations return to its SDK context, whereas the final model action
specified no artifact-ID dependencies. Nine quote-level phase-restricted rejects
and one other logical phase-restricted call remain recorded; none is a backend
inference. The quote-induced **causal** revision rate remains unknown, not inferred
from the discarded-quote count. No new semantic policy, prompt or routing rule
has been introduced to explain or improve this trajectory.
