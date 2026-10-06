# Resident checkpoint 105–108: completed wrong answers, not runtime failures

2026-10-06. Four first executions on the unchanged resident execution002
(revision955fe8f), control009/external006, task freeze and model pool. All completed,
produced canonical-valid terminal answers and reached the original evaluator,
with score0. No retry, replacement, prompt change or semantic correction occurred.
Actual recipient privacy, model residency and Worker exit checks passed.

## Individual outcomes

All four concern frozen LongBench2 (`1458aa227ea0348b`, Government pattern,
2,119,778 initial bytes). M/S/V means Manager/specialist/Verifier calls.
The conditions differ in Planner, network and method: this is not a matched
single-factor comparison, pooled quality statistic or method ranking.

| Cell | Planner / network / method | M / S / V | Physical calls | Successful tools / returned inference | E2E seconds | Frozen list-price API USD |
| --- | --- | --- | ---: | --- | ---: | ---: |
| 105 | P1 / Fast / C | 20 / 0 / 4 | 5 | 3 / 1 | 145.328 | 0.13519 |
| 106 | P2 / Slow / D | 10 / 0 / 3 | 2 | 1 / 1 | 78.654 | 0.09481 |
| 107 | P1 / Slow / E | 11 / 0 / 11 | 15 | 10 / 1 | 164.490 | 0.26071 |
| 108 | P2 / Fast / B0 | 7 / 0 / 7 | 6 | 3 / 1 | 71.580 | 0.09446 |

P1 is DeepSeek V4 Pro; P2 is Qwen3.8-Max. All use the same Blind Qwen3.8-Max
Verifier. API cost is a frozen regional list-price estimate, not an invoice.
Cell105 completed on its20th Manager turn: **this is not budget exhaustion**.
Wrong answers are retained valid executions; missing evaluation is not scored0.

| Cell | Fixed initial transfer seconds | Complete action-artifact bytes / seconds | Complete tool-only work seconds | Returned backend seconds | Input / output tokens |
| --- | ---: | --- | --- | ---: | --- |
| 105 | 0.213 | UNKNOWN / UNKNOWN | UNKNOWN | 0.514 | 385 / 2 |
| 106 | 5.977 | 0 / 0 | 0.402 | 0.495 | 331 / 2 |
| 107 | 5.979 | UNKNOWN / UNKNOWN | UNKNOWN | 13.900 | 4,878 / 2 |
| 108 | 0.217 | 0 / 0 | 0.972 | 11.467 | 3,982 / 2 |

105/107 each had one overlarge-read failure without complete execution receipts.
Their original result's successful action-transfer subtotal0 is preserved, but
does not establish complete transfer0. For107 the successful tool-only subtotal
is6.278s; complete work remains unknown. Context selection failures are not model
inference. Returned backend telemetry records one finish-stop inference per cell.
Work sums may overlap and are not an E2E decomposition; setup movement is separate
from Agent-controlled action movement. Fresh stores are not cold inference cache.

## Observed control and evidence paths

105/C:9quotes, consumed5/discarded4;14timed control calls/2.360s. Its terminal
model consumed no artifact inputs. Graph5nodes/0edges/16snapshots. Root reasoning
129.168s and Verifier11.782s are separate measured work. No successful artifact
read occurred. This does not prove evidence discard or prior-knowledge provenance.

106/D:5quotes, consumed2/pending3;7timed control calls/2.094s. The actual
comparison audit has zero returned sets/cards/selections: D's comparison
mechanism was not exercised in this trajectory. Its terminal model also consumed
no artifact inputs. Graph2nodes/0edges/7snapshots. Root60.650s/Verifier8.542s.

107/E:10successful BM25 retrievals;4prepared model actions, with3context
preflight rejects and1actual inference. An aggregation call also returned semantic
validation failure. Terminal inference actually consumed two materialized bounded
evidence artifacts. Graph15nodes/10edges/46snapshots; observed maximum concurrent
actions4 and overlap3.971s, not merely nominal graph width. Eleven actual root
requests exposed frozen E rules and optional estimate schemas, but no actual
optional query was emitted. Rule visibility does not establish internal use.
Root98.575s/Verifier39.215s. Recovery to inference did not recover correctness.

108/B0:3successful BM25 retrievals;3prepared model actions,2context rejects and
1actual inference consuming one bounded evidence artifact. A semantic validation
failure also occurred. Graph6nodes/3edges/19snapshots; maximum concurrent actions1,
overlap0. Root37.659s/Verifier19.919s. This is resource-blind continuation to a
wrong answer, not one-shot planning failure or a reason to retune the baseline.

Actual recipient contexts audited:24/13/22/14 for105/106/107/108. Private semantic
primary-cause and evidence-retention audit remains pending; artifact counts alone
do not establish evidence sufficiency, preservation or model reasoning provenance.
No quality-saving optimization or causal method effect is claimed.

## Immutable remote proofs and current scope

All paths below are under the isolated4090 evidence root
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.
Only bounded metadata entered the development PC, not bodies/gold/full traces.

| Proof | File SHA256 |
| --- | --- |
| `analysis/resident-cell105-source-bound-001.json` | `9da4e9ce5f21f780b0d1101878f0ca17e6292edbee2d3356827d8b81ab255e46` |
| `analysis/resident-cell106-source-bound-001.json` | `efd3c81675b9852d48620df387e91eeef4179dde91ee9eb9cce7a091339ecc24` |
| `analysis/resident-completed-107-108-source-bound-001.json` | `b299d6f192a4adf4857df6ba929d2cfb8f589303186afb6f91b720cadec8a645` |
| `analysis/resident-snapshot-026.json` | `e2f12102bb9c436486fed8ddcdb6b0a8ef60d572a69b5b2263e15287cb894a1f` |

Snapshot026 captured03:41:31Z verifies106effective/108settled attempts/1pending107
at that time, all sources/sidecars, same18tasks and two preserved Quote-confounded
originals. It is not relabelled as108-cell coverage. Later exact proofs verify
107/108; their Worker shutdown and residency receipts were independently checked.

At03:47:20Z Queue010PID3755889 and cell109atomic3879180 were verified live;
cell109MultiHop1/P2/Fast/B0 was reserved03:46:15Z and remains pending.
Current membership:108effective nominal cells/110settled attempts plus one pending,
not a completed168-cell block. No pruning, PhaseII, full private audit or final
Q1–Q10 claim. No measured runtime or experimental configuration changed.
