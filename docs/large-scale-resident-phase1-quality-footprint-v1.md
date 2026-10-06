# Resident Phase I: reviewed quality-conditioned resource footprint

2026-10-07, Asia/Hong_Kong. This analysis covers the closed, reviewed168-cell
resident/diverse-pool Phase I, not the historical42 or the live held-out block.
It does not change pruning or the frozen experiment. Every condition remains n1.

## Populations and source checks

The owner-local projection binds snapshot053, comprehensive audit001, the final
Phase I journal and each admitted run's original trace/result/admission/Worker-exit
hashes. It contains168 per-cell cost vectors,84 task/Planner/method groups,42
benchmark/Planner/method groups and144 same-task/Planner/network contrasts to B0.
All original execution epochs remain attached. No rejected attempt is silently
substituted or counted as another nominal sample.

Every group's resource distributions are separated into completed original
score1, completed score0, and unevaluated. This is **evaluator-conditioned**, not
independently proved semantic correctness. MultiHop's token-overlap evaluator
remains unchanged and is not a semantic oracle. No accuracy is pooled across
benchmarks. Missing evaluation is not score0.

Known-only median/min/max explicitly report known_n and unknown_n; a complete
sum is null if any member is missing. Empty score1 populations are unknown,
not zero-cost successes. Complete Agent artifact movement is unknown in37cells;
successful transfer subtotals are not substituted. Initial materialization stays
separate, model preflight rejects are not inference, and failed/unmeasured model
work/tokens stay unknown. Returned inference telemetry is a measured receipt
count, not necessarily all backend inference attempts.

An independent sort/middle-index implementation rechecked9,072 population/metric
groups and all known matched deltas. The analysis source and validation are
preserved in an append-only provenance receipt. No support/corpus/store-body
read, new model call, runtime change or experiment retry was needed.

## Selected descriptive observations

These rows summarize only the original score1 population, not all runs' cost.
The full remote report contains all42 groups and componentwise contrasts.

| Family / Planner / method | score1 / score0 / unevaluated | Score1 API USD median | Manager median | Model requests median | Artifact movement median, known/n |
| --- | --- | ---: | ---: | ---: | --- |
| LongBench / DeepSeek / B1 | 1 / 3 / 0 | 0.780341 | 13 | 10 | unknown, 0/1 |
| LongBench / Qwen / B1 | 2 / 2 / 0 | 0.150245 | 7.5 | 2.5 | 113,493 bytes, 2/2 |
| MultiHop / Qwen / E | 4 / 0 / 0 | 0.179115 | 4.5 | 2.5 | 0 bytes, 2/4 |
| Video / Qwen / E | 4 / 0 / 0 | 0.141385 | 4 | 1 | 0 bytes, 4/4 |

These populations differ and are not direct cross-Planner causal comparisons.
For LongBench/B1, the one DeepSeek pair where both B1 and B0 completed with
score1 had seven more model requests and USD0.098024 more API work under B1.
Qwen's two such pairs had lower API estimates, with fewer model requests in
one and equal requests in the other. This supports heterogeneous observed
behavior, not a stable profile benefit or explanation of internal adoption.

Two complete MultiHop/Qwen/E versus B0 contrasts concern the same position2
task, hash2d3129ed85c03f62, in Fast and Slow:

| Network | B0 / E artifact bytes | B0 / E API USD | B0 / E model requests | Original scores |
| --- | --- | --- | --- | --- |
| Fast | 5,204,596 / 0 | 0.072642 / 0.082163 | 2 / 2 | 1 / 1 |
| Slow | 18,042 / 0 | 0.095161 / 0.075045 | 2 / 2 | 1 / 1 |

Artifact footprint is lower in both observed E trajectories, but API direction
differs. Zero registered artifact movement does not mean zero prompt/tool-result/
cloud HTTP traffic. Neither evaluator agreement nor movement reduction proves
semantic evidence retention, cost-induced revision or repeatable optimization.
The other two E runs have incomplete movement and are not filled with zero.

No method has been declared a winner. Lower cost of an unused-interface variant
cannot be credited to that interface. Quote protocol turn overhead does not
guarantee higher API dollars: token/cache/pricing and trajectory differences
remain separate. Componentwise cost directions are reported without a weighted
scalar or E2E online objective. Held-out characterization is still required.

## Immutable owner-local evidence

Root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.

| Artifact | SHA256 |
| --- | --- |
| resident-phase1-quality-footprint-001.json | `bd7fd6f4823624b0878f8c9e16527998e598ff3e471f15fa1a4bdc699066c612` |
| resident-phase1-quality-footprint-review-001.md | `7102478ecbd8c4a980f95cb0d6aee5e47ca27f973c0e3e61a8f679e14a9bd6dd` |
| resident-phase1-quality-footprint-provenance-001.json | `5a4fe5f2244431d96e140b669adf7918368b2a942615c39767486f9f47343b48` |
| Preserved analysis source | `8484088a1c303a708c9dd0296ce9e2c6fee802f0e0d7ae068881181e9a57ebc2` |

The source hashes and168-cell review are documented in the
[comprehensive audit](large-scale-resident-phase1-comprehensive-audit-v1.md).
This is additional descriptive evidence, not a new method, gate or rerun.
Final held-out semantic/adoption audit and Q1–Q10 are not yet complete.
