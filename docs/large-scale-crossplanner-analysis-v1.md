# Cross-Planner characterization — in progress

2026-10-07, Asia/Hong_Kong. This is a reviewed Phase I descriptive table, not the
final cross-Planner result. The frozen 192-cell held-out block is still running.
Its complete execution, private failure/semantic/adoption audit and Q1–Q10 remain
required. Old42 and held-out results are not pooled into this table.

## Population and verification

P1 = deepseek-v4-pro; P2 = qwen3.8-max. Verifier is fixed Qwen and Blind in both.
Each family/Planner/method group comprises the two screening tasks times two
networks: four distinct task-conditions, n1 each, not four repeated trials.

The owner-local table binds the closed168-cell quality-footprint projection and
its original snapshot/comprehensive-audit/journal bindings. An independent
statistics.median readback checked all42 group memberships and1,008
population/metric combinations against original per-cell records, including
unknown counts and empty populations. No new model calls, task evidence-body
reads, method changes or experiment retries were made.

## Evaluator-conditioned resource table

Quality column = completed score1 / completed score0 / unevaluated.
All resource entries are medians **within completed original score1 runs only**.
Different rows can contain different task/network subsets; they are not matched
causal comparisons. MultiHop token-overlap score1 is not a semantic oracle.
Unknown is never filled with zero. Partial-known byte medians include known/n;
their complete group total remains unknown. Fractional request/byte medians are
possible for even-sized populations and are not fractional actual executions.

| Family | Planner | Method | Quality 1/0/unknown | API USD | Manager turns | Model requests | Returned inference receipts | Tool requests | Artifact bytes | Context rejects | E2E s |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| longbench_v2 | P1 | B0 | 2/2/0 | 0.858952 | 9.5 | 3.5 | 1.0 | 26.5 | 0.000000 (1/2 known) | 2.5 | 202.180 |
| longbench_v2 | P1 | B1 | 1/3/0 | 0.780341 | 13 | 10 | 3 | 32 | unknown | 5 | 365.188 |
| longbench_v2 | P1 | A | 1/3/0 | 0.157389 | 9 | 3 | 1 | 14 | unknown | 2 | 127.160 |
| longbench_v2 | P1 | B | 2/2/0 | 0.581242 | 10.0 | 2.5 | 1.0 | 16.0 | unknown | 1.5 | 162.330 |
| longbench_v2 | P1 | C | 0/1/3 | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown |
| longbench_v2 | P1 | D | 1/0/3 | 0.127498 | 19 | 1 | 1 | 2 | 0.000000 | 0.000000 | 129.062 |
| longbench_v2 | P1 | E | 1/3/0 | 0.968750 | 16 | 4 | 1 | 49 | unknown | 3 | 297.201 |
| longbench_v2 | P2 | B0 | 2/2/0 | 0.209840 | 11.0 | 4.0 | 1.0 | 8.5 | 11077.5 | 3.0 | 113.066 |
| longbench_v2 | P2 | B1 | 2/2/0 | 0.150245 | 7.5 | 2.5 | 1.0 | 9.5 | 113493.0 | 1.5 | 88.600 |
| longbench_v2 | P2 | A | 2/2/0 | 0.350011 | 13.0 | 5.5 | 2.0 | 14.0 | 217558 (1/2 known) | 3.5 | 170.729 |
| longbench_v2 | P2 | B | 2/2/0 | 0.097857 | 8.0 | 2.5 | 1.0 | 3.0 | 217558.0 | 1.5 | 68.161 |
| longbench_v2 | P2 | C | 2/2/0 | 0.136309 | 14.5 | 1.0 | 1.0 | 4.5 | 108779.0 | 0.000000 | 81.199 |
| longbench_v2 | P2 | D | 2/2/0 | 0.136727 | 14.0 | 1.0 | 1.0 | 1.5 | 108779.0 | 0.000000 | 118.587 |
| longbench_v2 | P2 | E | 2/2/0 | 0.260751 | 8.5 | 4.0 | 1.0 | 13.0 | 44199.0 | 3.0 | 127.663 |
| multihop_rag | P1 | B0 | 3/1/0 | 0.109309 | 7 | 2 | 1 | 9 | 0.000000 (2/3 known) | 1 | 194.679 |
| multihop_rag | P1 | B1 | 2/0/2 | 0.089121 | 6.0 | 2.0 | 1.0 | 6.0 | 17960.5 | 1.0 | 194.347 |
| multihop_rag | P1 | A | 2/0/2 | 0.123492 | 6.0 | 5.5 | 4.0 | 6.0 | 18058 (1/2 known) | 1.0 | 377.029 |
| multihop_rag | P1 | B | 2/1/1 | 0.124346 | 7.5 | 2.5 | 1.0 | 7.5 | 18072.0 | 1.5 | 208.382 |
| multihop_rag | P1 | C | 1/1/2 | 0.102901 | 14 | 1 | 1 | 3 | 0.000000 | 0.000000 | 123.066 |
| multihop_rag | P1 | D | 2/1/1 | 0.104568 | 14.5 | 1.0 | 1.0 | 3.0 | 0.000000 | 0.000000 | 112.858 |
| multihop_rag | P1 | E | 2/1/1 | 0.151819 | 7.0 | 3.0 | 1.0 | 9.0 | 18009.0 | 2.0 | 213.786 |
| multihop_rag | P2 | B0 | 2/2/0 | 0.083901 | 6.0 | 2.0 | 1.0 | 4.5 | 2611319.0 | 1.0 | 187.755 |
| multihop_rag | P2 | B1 | 2/2/0 | 0.069370 | 4.5 | 1.5 | 1.0 | 4.0 | 2611327.0 | 0.500000 | 185.641 |
| multihop_rag | P2 | A | 2/2/0 | 0.073693 | 5.0 | 1.5 | 1.0 | 4.0 | 2611327.0 | 0.500000 | 177.412 |
| multihop_rag | P2 | B | 2/2/0 | 0.069869 | 5.0 | 1.5 | 1.0 | 2.5 | 5204596.0 | 0.500000 | 159.906 |
| multihop_rag | P2 | C | 4/0/0 | 0.104187 | 10.5 | 2.0 | 2.0 | 3.0 | 5204596.0 | 0.000000 | 235.374 |
| multihop_rag | P2 | D | 2/2/0 | 0.083951 | 8.0 | 1.0 | 1.0 | 2.5 | 2602298.0 | 0.000000 | 138.070 |
| multihop_rag | P2 | E | 4/0/0 | 0.179115 | 4.5 | 2.5 | 1.5 | 9.5 | 0.000000 (2/4 known) | 1.0 | 118.817 |
| video_mme | P1 | B0 | 4/0/0 | 0.133795 | 4.5 | 1.5 | 1.0 | 1.0 | 0.000000 | 0.500000 | 115.025 |
| video_mme | P1 | B1 | 4/0/0 | 0.094732 | 4.0 | 1.5 | 1.0 | 1.0 | 0.000000 | 0.000000 | 122.329 |
| video_mme | P1 | A | 4/0/0 | 0.109694 | 4.0 | 1.5 | 1.0 | 1.0 | 0.000000 | 0.500000 | 103.470 |
| video_mme | P1 | B | 4/0/0 | 0.119246 | 5.0 | 2.0 | 1.0 | 1.0 | 0.000000 | 1.0 | 145.594 |
| video_mme | P1 | C | 3/1/0 | 0.081907 | 7 | 1 | 1 | 1 | 0.000000 (2/3 known) | 0.000000 | 154.381 |
| video_mme | P1 | D | 4/0/0 | 0.131340 | 10.0 | 1.0 | 1.0 | 2.0 | 0.000000 (3/4 known) | 0.000000 | 180.019 |
| video_mme | P1 | E | 4/0/0 | 0.124837 | 4.0 | 1.5 | 1.0 | 1.0 | 0.000000 | 0.500000 | 132.265 |
| video_mme | P2 | B0 | 4/0/0 | 0.162411 | 5.5 | 2.0 | 1.0 | 1.0 | 0.000000 | 1.0 | 136.854 |
| video_mme | P2 | B1 | 4/0/0 | 0.125591 | 5.0 | 2.0 | 1.0 | 1.0 | 0.000000 | 1.0 | 121.673 |
| video_mme | P2 | A | 3/1/0 | 0.142709 | 6 | 3 | 2 | 1 | 0.000000 | 1 | 97.999 |
| video_mme | P2 | B | 3/1/0 | 0.150574 | 6 | 2 | 1 | 1 | 0.000000 | 1 | 125.095 |
| video_mme | P2 | C | 3/1/0 | 0.105662 | 7 | 1 | 1 | 1 | 0.000000 (2/3 known) | 0.000000 | 115.247 |
| video_mme | P2 | D | 3/1/0 | 0.150101 | 11 | 1 | 1 | 3 | unknown | 0.000000 | 126.325 |
| video_mme | P2 | E | 4/0/0 | 0.141385 | 4.0 | 1.0 | 1.0 | 1.0 | 0.000000 | 0.000000 | 132.280 |

API dollars are frozen list-price usage estimates, not provider invoices.
Requests are not successful executions. Preflight rejects do not count as
inference. Returned telemetry is not necessarily every attempted backend call;
unmeasured failed work/tokens remain unknown. E2E includes separately recorded
initial materialization and is not an online optimization target. Registered
artifact bytes exclude HTTP prompt/control traffic. No scalar cost objective,
pooled benchmark accuracy, significance or method winner is inferred.

## What the closed screening block supports

- B optional interface: P1 made0/68 observed eligible queries; P2 made1/58.
  One valid Qwen query is evidence of occasional use, not useful adoption across
  workloads. Lower cost in a no-query trajectory cannot be credited to querying.
- D: zero multi-feasible comparisons in24cells. Four multi submissions and one
  genuine two-card request do not change this: both cards were context-rejected,
  with neither selected. Multi-submission is not optimization over feasible paths.
- C/D: root-turn overhead appears in both Planners. The table also shows why
  greater turn work is not universal greater API dollars: token/cache/pricing,
  Verifier cadence, specialist use and trajectory quality remain separate.
- B1: matched score1 comparisons exhibit heterogeneous observed behavior.
  The one DeepSeek LongBench B1/B0 pair had seven extra model requests and
  USD0.098024 extra API work. Two Qwen pairs had lower API estimates, with fewer
  requests in one and equal requests in the other. This does not establish a
  repeatable raw-profile benefit or internal causal adoption.
- E: resource direction and quality must be audited jointly. The two observed
  MultiHop/Qwen/position2 score1 matches reduced registered movement, but API
  direction differed between networks. Unknown semantic retention and a weak
  evaluator prevent a quality-preserving optimization claim. An old-pool
  evidence-loss case is not evidence of new-pool systematic regression.

The frozen B0/B1/A/E survivor set is unchanged. Full held-out results must decide
whether these descriptive tendencies recur on tasks3–6. No early pruning,
prompt tuning, new optimizer or architecture change follows from this table.

## Source-bound evidence

Owner-local root:
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.

| Artifact | SHA256 |
| --- | --- |
| resident-phase1-crossplanner-table-001.json | `8709d19c37dd707c016b80df2dbb27e9b39fcd611c4c47c268f010e94ab23083` |
| resident-phase1-quality-footprint-001.json | `bd7fd6f4823624b0878f8c9e16527998e598ff3e471f15fa1a4bdc699066c612` |
| resident-phase1-quality-footprint-provenance-001.json | `5a4fe5f2244431d96e140b669adf7918368b2a942615c39767486f9f47343b48` |
| resident-comprehensive-phase1-audit-001.json | `f9a7f25e9ca737b95c201735c346d8cf8099f4fa4959f97a1a689ac55612a036` |

See [source-bound review](large-scale-resident-phase1-comprehensive-audit-v1.md),
[matched contrasts and unknown policy](large-scale-resident-phase1-quality-footprint-v1.md)
and [actual held-out outcomes](large-scale-phase2-results-v1.md).
Final per-task/benchmark/Planner/method and Q1–Q10 synthesis remains incomplete.
