# Phase I results — incomplete checkpoint

2026-10-05. **10 / 168 nominal samples admitted at this checkpoint.** One original
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

All ten admissions have no unresolved findings. Original private evaluators ran.
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

The next original cell is Academic / Qwen / Slow / B0, attempt1. Queue PID 1344958
and owned child PID 1546948 were verified live at this checkpoint. No task is
replaced, and no semantic tuning is performed.

Remote read-only checkpoint: analysis/settled-snapshot-007.json, file SHA-256
c6d8be9f3e6e2b6caaddd9b18e73c57ceb77394a4e115db6765ec55ca56576a5.
There are ten valid, one original confounded and one pending attempts; no
operational exclusions. No score aggregation, screening or Phase II is authorized.

Analysis is remote-only and read-only, exports bounded telemetry and structural
metadata, and does not feed observations back to Agents. See the offline analysis
definitions for query denominator, last-turn accounting and unknown-value rules.
