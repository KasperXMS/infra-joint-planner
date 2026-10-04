# Phase I results — incomplete checkpoint

2026-10-05. **15 / 168 nominal samples admitted at this checkpoint.** One original
confounded attempt remains separately preserved. This is not the completed Phase I
report, not a method ranking, and does not authorize pruning or Phase II.

Execution revision: 94c9bac62daa30d70ed319d741a17c54e6ec96cd;
execution-freeze-002 canonical SHA-256:
50e2fbcac51693695e551f0b09bd83f332891a1e4c2e6a48b393fd3874d569d8.
Task/placement/order/model/Verifier/method freezes are unchanged.

| Task | Planner | Network | Method | Attempt | Complete / format / score | E2E s | Initial bytes / s | Action bytes / transfer work s | Manager / specialist / Verifier turns | Cloud HTTP | API USD |
|---|---|---|---|---:|---|---:|---|---|---|---:|---:|
| Video 602-2 | Qwen3.8-Max | Fast | B1 | 2 | yes / valid / 1.0 | 229.841 | 213,739,837 / 18.605 | 772,094 / 0.907 | 5 / 0 / 5 | 10 | 0.227857 |
| Video 602-2 | DeepSeek V4 Pro | Slow | B0 | 1 | yes / valid / 1.0 | 808.533 | 213,739,837 / 596.688 | 718,415 / 2.755 | 5 / 0 / 5 | 10 | 0.133623 |
| Video 602-2 | Qwen3.8-Max | Slow | E | 1 | yes / valid / 1.0 | 867.962 | 213,739,837 / 596.699 | 1,402,620 / 4.482 | 3 / 0 / 3 | 6 | 0.154932 |
| Video 602-2 | DeepSeek V4 Pro | Fast | D | 1 | yes / valid / 1.0 | 326.551 | 213,739,837 / 18.602 | 1,633,728 / 0.349 | 8 / 0 / 2 | 10 | 0.114748 |
| LongBench 66f94f9ebb02136c067c4fde | DeepSeek V4 Pro | Fast | B0 | 1 | yes / valid / 0.0 | 203.930 | 2,119,778 / 0.228 | 25,538 / 0.389 | 8 / 0 / 8 | 16 | 0.107196 |
| LongBench 66f94f9ebb02136c067c4fde | Qwen3.8-Max | Slow | B1 | 1 | yes / valid / 0.0 | 80.051 | 2,119,778 / 5.983 | 0 / 0 | 7 / 0 / 7 | 14 | 0.243392 |
| LongBench 66f94f9ebb02136c067c4fde | DeepSeek V4 Pro | Slow | A | 1 | yes / valid / 0.0 | 180.078 | 2,119,778 / 5.989 | 15,904 / 0.139 | 10 / 0 / 10 | 20 | 0.146186 |
| LongBench 66f94f9ebb02136c067c4fde | Qwen3.8-Max | Fast | B | 1 | yes / valid / 0.0 | 188.625 | 2,119,778 / 0.481 | 25,392 / 0.150 | 10 / 0 / 10 | 20 | 0.184718 |
| LongBench 66f2c44e821e116aacb2b826 | Qwen3.8-Max | Fast | A | 1 | yes / valid / 1.0 | 123.583 | 514,789 / 0.205 | 18,852 / 1.016 | 7 / 0 / 7 | 14 | 0.082493 |
| LongBench 66f2c44e821e116aacb2b826 | DeepSeek V4 Pro | Slow | B1 | 1 | yes / valid / 1.0 | 343.549 | 514,789 / 1.570 | 28,379 / 0.910 | 13 / 16 / 13 | 42 | 0.827349 |
| LongBench 66f2c44e821e116aacb2b826 | Qwen3.8-Max | Slow | B0 | 1 | yes / valid / 1.0 | 218.928 | 514,789 / 1.552 | 88,537 / 1.835 | 10 / 8 / 10 | 28 | 0.297327 |
| LongBench 66f2c44e821e116aacb2b826 | DeepSeek V4 Pro | Fast | E | 1 | yes / valid / 1.0 | 755.092 | 514,789 / 0.201 | 18,934 / 0.289 | 11 / 9 / 11 | 31 | 0.340510 |
| MultiHop 4b6de4acbde051fee1f727f3 | Qwen3.8-Max | Fast | B | 1 | yes / valid / 1.0 | 138.709 | 7,696,522 / 1.004 | 12,185 / 0.593 | 6 / 0 / 6 | 12 | 0.163738 |
| MultiHop 4b6de4acbde051fee1f727f3 | DeepSeek V4 Pro | Slow | A | 1 | yes / valid / 0.0 | 985.729 | 7,696,522 / 22.035 | 67,507 / 1.474 | 14 / 0 / 14 | 28 | 0.492382 |
| MultiHop 4b6de4acbde051fee1f727f3 | Qwen3.8-Max | Slow | B1 | 1 | yes / valid / 0.0 | 319.257 | 7,696,522 / 22.249 | 5,204,596 / 14.943 | 9 / 0 / 9 | 18 | 0.120485 |

All fifteen effective admissions have no unresolved findings. Original private evaluators ran.
The latest E cell has a separately audited admission sidecar; its original
validation gate rejection remains intact. It was not repeated or repaired.
Qwen/Fast/B1 attempt1's score 1.0 is excluded: repeated missing H.264 decoder
failures and an order-dependent accounting aggregate. It is not in this table.
Full exclusion/repair provenance is in the failure audit.

The second row's E2E contains almost 597 seconds of fixed video initial placement
before Manager reasoning. Do not attribute that setup delay to Blind decisions.
These rows differ in Planner, method and network; **they are not a matched effect
estimate**. There is no current cross-workload or method-level conclusion.

## Observed mechanism use (not screening/pruning)

- E: the optional query interface was present in all three actual Manager API
  requests; zero query attempts/cards. Frozen rules were visible in all three
  predecision inputs. One physical inference took 189.672 s. Rule visibility does
  not demonstrate internal use, quality-preserving reduction or a matched benefit.
- D: three quotes, two authorized/observed executions, one discarded quote; final
  states consumed=2/discarded=1. No comparison call or multi-candidate comparison.
  Two phase-restricted proposal rejections are retained as ordinary control
  behavior. Quote protocol took 0.530 s of measured gateway control work, while
  Manager reasoning used 67.371 s and physical inference 189.852 s. These work
  counters are not an additive E2E decomposition. Discard is not automatically a
  proven cost-induced workflow revision.

The first nine admitted trajectories used no created specialist. Academic /
DeepSeek / Slow / B1 then created two specialists with peak active count two;
their combined reasoning-turn count is 16. Legal single-agent execution remains
accepted; requested specialist/tool calls and actual creation/execution are
recorded separately. This is not evidence that B1 causes MAS topology.

## First observed quality failures: retained

Both LongBench position-2 runs complete normally and reach the original evaluator
but score 0.0. DeepSeek/Fast/B0 has two context rejects plus phase/semantic typed
failures; Qwen/Slow/B1 has one context and one semantic reject. Each subsequently
reaches one successful physical inference, terminal extraction and evaluation.
They are valid wrong-answer samples, not replacements or reasons for prompt tuning.
Fine-grained primary semantic/evidence/stopping causes await comprehensive
post-run private/trace audit; score 0 alone does not distinguish them.

The 80-second Qwen/Slow/B1 wrong completion is not an optimization success; zero
artifact-localization transfer does not mean zero RPC/cloud-information traffic
or prove preserved evidence. These rows again change Planner/method/network and
are not a matched method comparison. Scores are not pooled across benchmarks.

Government / DeepSeek / Slow / A and Qwen / Fast / B also complete with score 0.0.
Each has two context rejects plus other typed semantic/phase failures, and one
successful inference. B's query interface was present in all ten actual Manager
requests, but zero optional queries/cards were generated across nine observed
selected-ready decisions. These are retained quality failures, not tuning targets.

## First admitted Academic cases

Qwen / Fast / A completes with score 1.0 after six prepared physical actions,
including two model attempts and one successful inference (89.215 s).
DeepSeek / Slow / B1 completes with score 1.0 after 62 physical calls: 57 prepared
tools (55 successful) and five model attempts (one reached inference, 128.766 s).
The latter has two artifact-too-large rejects, four context rejects, and other
semantic/phase failures. Its graph has 62 action nodes / 59 information-flow edges
and two explicit handoffs. Graph status snapshots are not 187 distinct structures.

Its frozen-list-price API USD 0.827349 includes Manager 0.085935, specialists
0.220818, and the fixed Blind Verifier 0.520596. This is substantial control-plane
work in a successful trajectory, not an invoice or a matched B1 overhead effect.
Do not infer the benefit of subagents or network awareness from these two rows,
which change Planner, method and network together. No inference cache was reset.

Academic / Qwen / Slow / B0 subsequently completes with score 1.0. It creates one
specialist (eight turns), uses 22 physical calls including five model attempts
and one inference (114.581 s), and records one handoff. Four context failures plus
phase/semantic rejects are preserved. Blind also naturally creates specialists;
MAS topology is neither forced nor evidence of awareness by itself.

The next original cell is Academic / DeepSeek / Fast / E, attempt1. Queue PID
1344958 and owned child PID 1561358 were verified live at this checkpoint. No
task is replaced, and no semantic tuning is performed.

Remote read-only checkpoint: analysis/settled-snapshot-008.json, file SHA-256
2997b29dedbeab09e8fe2bfdd85a53d6d257e07371994e703910a85eab455dab.
There are eleven valid, one original confounded and one pending attempts; no
operational exclusions. No score aggregation, screening or Phase II is authorized.

## Offline structure/parallelism checkpoint

All eleven settled valid traces pass append-only graph/integrity and complete
interval checks with no dependency-order violations. Academic / DeepSeek / Slow /
B1 has 187 status snapshots but **62** actual structural growth events and three
owners with actions. Actual physical-action peak is eight, overlap wall time
9.665 s; its artifact/control-edge path is 130.790 s, **not** full E2E 343.549 s.
Academic / Qwen / Slow / B0 has 67 snapshots / 22 additions / two owners, peak
four physical actions and 1.338 s overlap. Different task/Planner/method inputs
and unrecorded reasoning dependencies prevent a causal parallelism benefit claim.

Remote analysis/settled-graph-audit-001.json, file SHA-256
f5fc0a27eb38873e58755c0ee7f6fc22ab787a7b51ea03a64ce3b83b8c95951d;
offline helper SHA-256 46a65142801f09faaf8cf47e4b8ffe1d1a77800e426d165cbd3021d569ca147f.
The helper is outside the 94c9bac app; no execution component changed. Twelve new
offline regression cases bring the full suite to **737 passed**; Ruff, strict
Pyright and diff check pass. Missing timing stays unknown; descriptors never
export artifact IDs/bodies, prompts, questions or private evaluation metadata.

## Exact post-inference JSON failure: preserved and adjudicated

Academic / DeepSeek / Fast / E completes correctly after six physical model
attempts: two context rejects, three successful inference telemetry receipts
(375.323 s service subtotal) and one post-inference JSON-output parse failure.
Thus at least four calls reached inference, not three. Failed inference tokens
and model service time are unknown; the known subtotal is **not** complete work.
The Worker rejected invalid JSON before materializing its requested JSON artifact;
no hidden correction or malformed artifact was passed as successful evidence.
Two specialists were created (peak active one), with nine combined turns;
the graph has 22 action nodes / 12 edges. Rules and query interface were visible
in all eleven Manager requests; zero optional queries across six selected-ready
decisions. Completion and low action movement do not demonstrate an E benefit.

The queue stopped on the conservative validation_failed gate. Independent full
re-audit confirmed only this model-output behavior, with no other findings.
A sidecar binds all 147 original evidence hashes and frozen Worker code. Original
journal/admission/result/trace stay intact; there is no rerun or output repair.

- Sidecar canonical SHA-256: 2937c8c41ebd486e1b3ea0417bc6a51db6f5c1270504d3f712e003c305faa996.
- Snapshot-009 file SHA-256: cd527a9da8c3db8172f330db85cc92e3a2786a9489a20d2df958ef28cd142339.
- Supplemental queue-control freeze-002 canonical SHA-256:
  932ad827c2d7c89991480356a576ce1e762b3d4c7df7f4aecf71d660a4e0ae14.

Only an offline admission-view adapter (316400f) is new. Agent/Worker/scheduler/
operator/benchmark/model/instructions and execution-freeze-002 remain exactly
94c9bac. Full pytest **758 passed**, Ruff/strict Pyright/diff pass. Parent1660678
and child1661081 were verified live on the next original MultiHop-1 / Qwen / Fast /
B attempt1. No Phase II or pruning. Earlier progress paragraphs are checkpoints.

## First settled MultiHop condition

MultiHop position 1 / Qwen / Fast / B completes with original score 1.0, valid
terminal format and clean admission. Twelve successful BM25 executions and two
physical model attempts form a 14-node / 12-edge graph. The first model attempt
has a context reject; a later inference succeeds (4,920 input / 2 output tokens,
finish_reason=stop, 85.969 s service work). The run has no created specialist.
Phase/semantic typed failures are preserved, without changing tool or prompt.

The optional query interface is visible in all six actual Manager requests,
but zero queries/cards are generated across four observed selected-ready
decisions. Its successful score alone does not demonstrate a cost-query benefit.
The twelve cloud HTTP calls comprise six Manager and six fixed Blind Verifier
requests, estimated USD 0.075002 / 0.088736 respectively. These are frozen-list-price
estimates, not invoices; physical service and cloud inference are separate.

Remote snapshot-010 file SHA-256:
b9df34a5eaa55b0ca6e2719ea8b21bac2c8b15fa4ec149523a088af727c491e7.
It contains thirteen effective valid / one confounded / one pending attempts
(fifteen total), with one immutable adjudication and no operational exclusions.
Offline collector v1-6 source SHA-256:
9278026ce0846445c752963ae048ea2e6a149a61dd42ed80d288c7f433571849.
It checks the same evidence once per membership calculation and derives all
counts from one verified population, avoiding repeated proof checks per cell.
Full pytest **760 passed**, Ruff/strict Pyright/diff pass; the execution app and
queue-control freeze remain unchanged. Parent1660678 and child1671569 were
verified live on MultiHop-1 / DeepSeek / Slow / A. No Phase II or pruning.

## Second settled MultiHop condition: valid wrong completion

MultiHop-1 / DeepSeek / Slow / A subsequently completes with format validity,
original score 0.0 and no admission findings. Its fourteen Manager / fourteen
Verifier turns, zero specialists and 26 physical actions remain below the frozen
ceilings. Twenty-one tools succeed; five physical model attempts comprise two
context rejects and three successful inferences, all finish_reason=stop. Recorded
model service work is 789.002 s, versus 1.474 s action transfer work; these are
work counters, not an additive E2E partition. No timeout, backend incident or
budget exhaustion is recorded. The graph has 26 nodes / 30 information edges.

The 28 cloud calls cost an estimated USD 0.492382: Manager 0.115300, fixed Blind
Verifier 0.377083. Wrong completion and repeated inference are retained research
outcomes, not reasons to modify stopping, models, prompts or retry the cell.
Primary retrieval/evidence/reasoning/stopping attribution awaits the complete
post-run private audit. This cell and Qwen / Fast / B vary Planner, method and
network simultaneously; neither establishes a matched quality/cost effect.

Snapshot-011 file SHA-256:
8d85ee4bf47a3ae884d4a8804c5c0af4a4e351f1d68e67ee6762fefdadcb1761.
Fourteen effective valid, one original confounded and one pending attempts
(sixteen total); one independently adjudicated original rejection remains intact.
Parent1660678 is still live; the next owned child1725706 is MultiHop-1 / Qwen /
Slow / B1, attempt1. No unresolved admission issue, method pruning or Phase II.

## Third settled MultiHop condition: raw-profile wrong completion

MultiHop-1 / Qwen / Slow / B1 completes with valid terminal format, original score
0.0 and clean admission. Nine Manager / nine Verifier turns, no specialists and
seven prepared physical actions remain within the frozen horizon. Five tools
succeed; two model attempts comprise one context rejection and one successful
inference (7,527 input / 325 output tokens, normal stop, 226.378 s service work).
Phase/semantic rejects remain recorded. Graph: seven nodes / eight information
edges. E2E is 319.257 s, with 5,204,596 action-transfer bytes / 14.943 s work and
7,696,522 fixed initial-placement bytes / 22.249 s. Raw infra visibility does not
by itself demonstrate correct evidence selection or efficient information flow.

Eighteen cloud requests estimate USD 0.120485 (Manager 0.055717 / fixed Blind
Verifier 0.064768), not invoice cost. The wrong score is retained, not a harness
bug, a retry target or a reason to tune prompts. Primary semantic attribution
and quality-conditioned matched comparisons await the complete Phase I audit.

Snapshot-012 file SHA-256:
eff3cd1bf29165e8c8dac0da0abef4bbe50fb4836a797b3b6a813a38b2c24c79.
Fifteen valid / one confounded / one pending attempts (seventeen total), one
immutable adjudication, zero operational exclusions. Original frozen schedule
continues to MultiHop-1 / DeepSeek / Fast / B0 attempt1, child1745464; parent
1660678 remains live. Formal execution 94c9bac is unchanged; no pruning/Phase II.

Analysis is remote-only and read-only, exports bounded telemetry and structural
metadata, and does not feed observations back to Agents. See the offline analysis
definitions for query denominator, last-turn accounting and unknown-value rules.
