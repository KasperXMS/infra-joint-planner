# Resident checkpoint088–092: recovery, optional adoption and stopping

2026-10-06. Five individual, first-attempt outcomes, not a matched method ranking
or the final168-cell/private semantic audit. Runtime/source/configuration stay
frozen. Wrong answers and the unevaluated stopping failure are retained.

| Cell / task / Planner / network / method | Completion / original quality | M/V / physical actions | Returned inferences | E2E | APIUSD list price |
| --- | --- | ---: | ---: | ---: | ---: |
| 88 /MultiHop1 /Qwen /Fast /E | completed /format-valid /0 | 8/8 /14 | 1 | 249.640s | 0.21677216 |
| 89 /LongBench1 /DeepSeek /Fast /A | completed /format-valid /0 | 11/11 /21 | 1 | 148.266s | 0.28970132 |
| 90 /LongBench1 /Qwen /Slow /B | completed /format-valid /1 | 8/7 /5 | 1 | 70.098s | 0.09125035 |
| 91 /LongBench1 /DeepSeek /Slow /C | not completed /not evaluated, NOT score0 | 20/2 /2 | 0 | 139.680s | 0.11325976 |
| 92 /LongBench1 /Qwen /Fast /D | completed /format-valid /1 | 10/3 /2 | 1 | 102.942s | 0.10675555 |

No specialists were created in these five cells. M/V are actual Manager/Verifier
reasoning starts, including failed cell91whose original result has no loop_usage
or telemetry object. Its E2E comes from the persisted run.failed receipt; do not
guess other missing fields or write inferred usage into the original result.
Every actual Cloud call here has a known frozen list-price receipt, not an invoice.

| Cell | Fixed initial bytes /time | Complete action-artifact bytes /time | Tool-only work | Returned model backend work | Model input/output tokens |
| --- | --- | --- | ---: | ---: | ---: |
| 88 | 7,696,522 /1.446s | 12,155 /0.909s | 4.538s | 159.576s | 4,808 /254 |
| 89 | 514,789 /0.108s | 217,558 /0.439s | 2.946s | 19.839s | 6,877 /2 |
| 90 | 514,789 /1.555s | 217,558 /0.722s | 0.373s | 11.781s | 4,171 /2 |
| 91 | 514,789 /1.561s | 0 /0s | 0.249s | 0 actual inference work | 0 /0 |
| 92 | 514,789 /0.129s | 217,558 /0.078s | 0.029s | 0.525s | 256 /2 |

Each returned inference finished-stop. Context/preparation failures are not
inference. Worker model-wrapper/backend work overlap, not an E2E decomposition.
Initial placement is fixed setup, separate from Agent-controlled movement.
Configured Fast/Slow delay is not a measured symmetric RTT. Each selected
admission has no system problems, with actual SDK recipient/residency/Worker
exit checks passed. Fresh stores are not cold model cache.

## Observed semantic continuation, not causal optimization claims

88/E first issued six top-k5retrievals across three shards. A model request failed
context preflight; it then issued six top-k1retrievals and one actual A28model
consuming those six reduced artifacts. The12successful retrievals/1inference
complete a14node graph with one failed node; actual concurrency5/overlap1.820s.
Frozen rules were visible in8Manager inputs. Reduction and rules visibility do
not prove internal rule use, evidence retention, or that E caused the wrong answer.
Quality0 means the smaller footprint is not an optimization success by itself.

89/A aggregated the two natural documents onA4, then performed four query branches
at top-k15->5->3->2. Three model preparations failed context limits; the final
A4model consumed four bounded evidence artifacts and returned a canonical but
wrong choice. It has21nodes/32information edges/64snapshots, concurrency4 and
1.608s overlapping wall interval. Recovery occurred naturally; the Worker did
not silently truncate/summarize. Root cloud87.902s plus Verifier37.085s dominate
the20s backend work in this trajectory, but their sums are not asserted as a
formal E2E partition or a cross-method result.

91/C only committed two BM25retrievals onA4/A5. Nine quotes ended consumed2/
discarded6/pending1, with10Quote-stage phase rejections and no mutation error.
Twenty Manager turns, two Verifier calls and repeated stage/quote attempts ended
in AgentLoopError for the turn budget; no physical inference or evaluator ran.
This is a valid stopping/composition/budget failure, not provider outage, wrong
answer score0 or reason to increase budget/retry. Exact semantic primary and
Verifier adequacy still need private review. Control11timed calls/3.688s excludes
associated API/turn cost. Two nodes succeeded, actual concurrency2.

92/D aggregated source artifacts onA4 then ran a prompt-only terminal model on
strongGPU0. Its two nodes have0explicit artifact-dependency edges/concurrency1.
The1,129byte terminal prompt and0artifact inputs do not prove evidence discard
or prior-knowledge provenance. One comparison submitted one candidate and
returned a typed failure, with0created cost cards; it did not exercise a genuine
alternatives comparison despite completed/correct quality. Four phase-rejected
quote attempts remain. Quotes ended consumed2/pending1; no mutation rejection.

## First observed resident B adoption: actual card and execution chain

90/B called `estimate_aggregate_artifacts` once on Manager turn1. All8actual root
request schemas exposed estimate tools; raw provider responses confirm the call,
and the exact structured returned card reached Manager turn2 before execution.
The subsequent ordinary aggregate action matches every semantic field of the
proposal except its new SDK action ID; the explicit cost_card.matched event joins
the card/proposal to the actual physical receipt. This is1valid query/card/match
among6observed eligible selected ready-action opportunities, not a global rate.

The estimate correctly bounded217,558transfer bytes; actual movement was exactly
217,558bytes/721.654ms. Configured serialization arithmetic580.155ms is **not**
an empirical wall-latency prediction. Matching transfer/operator profiles each
had sample_count1below minimum_support3: p50/p90 and output-size upper bound
remainUNKNOWN. No answer-quality estimate or scalar/predicted E2E was supplied.

After one context rejection, the root queried smaller evidence and invoked A4
with one materialized artifact, yielding correct canonical quality. Adoption and
correct completion are proven; a counterfactual workflow improvement, cost-induced
revision, benefit over a matched baseline or stable adoption across both Planners
is not. Earlier85-cell optional-query zero remains its old scope, not a conclusion
that B will be unused in the complete matrix.

For B, legacy cost_quote.observed.action_id identifies the proposed estimate;
cost_card.matched.action_id identifies the later execution. Their different SDK
IDs are expected: semantic fingerprint equality plus the explicit match joins
the trace without changing any event or runtime. The C-specific quote visibility
helper is not a B-card visibility proof; this audit compares the actual card_id
tool output exactly instead. No missing trace information or repair is inferred.

## Durable source/projection hashes

All evidence below stays under the new resident remote root. No body/prompt/gold
was exported to the development PC. Standalone projections and the new global
snapshot preserve source identities, physical receipts and admission membership.

| Artifact | FileSHA256 |
| --- | --- |
| `analysis/resident-cell088-source-aware-projection-001.json` | `ccb5fd19112dd7ce241a66ccabdeaaab9a43261d0f374b53d33991f4874f5b55` |
| `analysis/resident-cell089-source-aware-projection-001.json` | `4539282452b283dd533026327fdbd6c78d7d43ced258833f8e2f4ebe8a82403f` |
| `analysis/resident-cell090-source-aware-projection-001.json` | `4ece4ba3766492f9764ff61ace8780c805c0de15dde46f55986629c52f20e6f5` |
| `analysis/resident-cell090-first-optional-card-proof-001.json` | `d46d77f8a2ee99102ae557b798e41391bdf9caa9ac4e26490f66094086be0979` |
| `analysis/resident-snapshot-024.json` | `6d04900709b1c21ee38d19d838afed6af359386a547868421f30d0f8b8e01005` |

Snapshot024captured02:54:02Z with an unchanged journal during collection:
SHA `79a1386215ef4c1ea2d889211161258f3e4423fd6ea77044cd62f601214f22dd`.
It verifies92effective cells/94settled attempts/1pending/2retained confounded
originals, both frozen execution sources and all exact sidecars/tasks. Cells91/92
are bound in its full rows; no separate isolated projection is falsely claimed.
Old42are separate/unpooled. No accuracy aggregation, complete private semantics,
method screening/pruning, PhaseII permission or final recommendation.
