# Workflow variation and infrastructure sensitivity

The [36-cell structural export](../../results/harness-v2-baseline-stabilization/workflow-variation.json) contains ordered operators, multisets, collapsed repeated operators, normalized artifact input flow, explicit dependencies, model actions, specialist ownership, physical placement, transfer and cost. Random action IDs are removed from comparisons. An operator edit distance is the insertion/deletion/substitution count divided by the longer sequence length; it measures structural change, **not** semantic equivalence, answer quality or causal adaptation. The earlier H1 [classification](../harness-v2-baseline-requalification/harness-v2-workflow-difference-analysis.md) found 21/24 method-vs-Blind L2 differences; the finer metrics below refine that count.

| Paired comparison | Pairs | Median normalized operator edit | Changed operator sequence | Changed evidence-operator counts | Changed model input flow | Changed artifact graph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Same task/method/network, trial 1 vs 2 | 18 | .111 | 9 | 5 | 9 | 10 |
| Same task/method/trial, slow vs fast | 18 | .292 | 14 | 6 | 14 | 14 |
| Same task/network/trial, Aware or Ledger vs Blind | 24 | .250 | 17 | 12 | 19 | 20 |

**Trace-supported observation.** Method comparisons change model input flow in 19/24 pairs and the produced-artifact dependency graph in 20/24, so the L2 count is not merely random action IDs. No Stage 2 action declared an explicit `depends_on` edge; graph edges here arise from normalized artifact inputs. However, same-condition sampling alone changes operator sequence in 9/18 pairs, model input flow in 9/18 and artifact graph in 10/18. The infrastructure comparison median is higher than the sampling median, but pair membership, early failures and small n prevent a causal estimate. Aware changes operators in 4/6 slow/fast pairs, Blind 5/6, Ledger 5/6; there is no clear aware-specific excess. Physical placement also differs in many pairs, but the scheduler was identical and these placement differences are not logical adaptation.

Diagnostic labels, applied to individual differences rather than automatically to every L2 pair:

| Label | Evidence in this matrix | Interpretation |
| --- | --- | --- |
| L2a, stochastic/redundant | Repeated `bm25_retrieve` or `invoke_model` counts vary within the same condition. | Extra nodes alone are not a strategy. |
| L2b, information flow | 19/24 method pairs change model input flow; 12/24 change evidence-stage operator counts. | These may alter evidence consumed, though adequacy is unverified. |
| L2c, infrastructure candidate | Video frame/clip/contact-sheet paths and several retrieval/reduction choices differ across slow/fast. | No consistent within-task two-trial direction separates them from sampling or failure censoring. |
| L2d, quality-preserving cost improvement | One Slow Video trial 2 Aware/Blind pair has both score 1 and lower Aware costs. | Companion trial Aware scores 0; no repeated L2d result. |

MultiHop Ledger slow trials both stop after 6 retrievals and one logical model action at Verifier errors; fast trials perform 18 retrievals and three model actions, then finish with wrong answers. This is a repeatable *trajectory-length* difference, but slow termination is protocol-censored, so it does not establish an infrastructure-conditioned plan. LongBench Aware has the same 12-retrieval/3-model operator pattern on both networks and both trials yet different outcomes, showing why a structural signature cannot stand in for quality. Video paths change frame/model counts in both directions across trials. A normal workflow executed under slow versus fast network can have very different E2E time without a new logical policy; the roughly 282 MB source video transfer dominates slow Video E2E.

These are three anchor tasks with two stochastic trials, not 36 independent task samples. The data support meaningful structural variation, but no stable, quality-preserving infrastructure-conditioned optimization and no statistical significance claim.
