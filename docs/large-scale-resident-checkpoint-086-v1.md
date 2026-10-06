# Resident PhaseI checkpoint: original cell86

2026-10-06. Source-aware individual result, not complete168-cell analysis or
method screening. Measured execution remains955fe8f/execution002; offline audit
and documentation commits are not extra measured runtime revisions.

## Actual completed cell

MultiHop1/P2(Qwen3.8-Max)/Slow/C, first and only attempt. Reserved02:18:23Z,
then settled valid before original cell87was reserved02:26:10Z. No problems,
operational incidents, context rejects or physical-action failures in admission.
Residency, actual recipient-context checks and all four owned Worker exits pass.

| Metric | Actual |
| --- | ---: |
| Execution / terminal format / original evaluator | completed /valid /score1 |
| Manager / specialist / Verifier calls | 15 /0 /6 |
| Physical actions / tools / returned model inferences | 6 /3 /3 |
| E2E | 418.061s |
| Fixed initial placement | 7,696,522bytes /22.192s |
| Complete action-artifact transfer | 5,204,596bytes /14.847s |
| Complete tool-only Worker execution | 2.258s |
| Returned model backend work | 308.537s |
| Model input/output tokens / finish reasons | 15,272 /154; stop3 |
| Manager / Verifier cloud work | 47.035s /18.086s |
| Frozen regional list-price APIUSD | 0.1394537596832273; all21calls known |
| Graph nodes / information edges / snapshots | 6 /6 /19 |
| Logical owners / max actual concurrency / overlap | 1 /1 /0s |

Tool-only work2.258s is the exact separate tool receipt sum. Operator work311.201s
includes308.943s of successful model-action wrapper work; backend service work
308.537s is overlapping scope and must not be added again. The initial draft's
2.665s tool-only value was an incorrect backend-subtraction residual; the immutable
projection's actual tool receipts above correct it without modifying evidence.
The6nodes all succeeded. The dependency-path178.358s
excludes cloud reasoning, Verifier/control and scheduling waits, not full E2E.
Configured Slow delay is not a measured symmetric RTT.

Observed path: `aggregate_artifacts -> bm25_retrieve -> bm25_retrieve -> three
invoke_model actions`. All selections wereA28; all three actual inferences used
its resident27.3B Qwen3.5 artifact. No specialist or model-output handoff occurred.
Correct evaluator quality does not prove complete evidence retention or establish
cross-method/cross-Planner performance. That needs the complete private audit.

C created7quotes, authorized6commits, retained1pending quote, with0mutation
rejections;13timed control calls took2.782s. Two phase-restricted SDK observations
remain visible and are not counted as failed backend inference. Actual raw
provider response has6commit_quote calls, not the lower-bound5in the replayed
SDK history. Quote control timing alone omits associated API/turn overhead and
is not the method's entire intrinsic cost. No causal quote-induced revision is
inferred from the sequence or score.

## Durable source and result proof

`analysis/resident-cell086-source-aware-projection-001.json` fileSHA:
`8dfddcfc00dd45f28f481db44dfaf440cb6d36000813a80b85be763ef728ea29`.
SettlementSHA:
`899d42bc33f85601f98db47ce5cf332b24a5b8fc7fd6e6e3ac448710d5ce1654`.
Admission canonicalSHA:
`771a86c1f6d56756d48c5bda24302fc7dd7e6764a97235b8242d090177517529`.
TraceSHA:
`71b0835ea2c2a5a9d37d6994567a1ee39c0bcbcda7f4eac2ca3244ff773767e5`.
No artifact body/private annotation/prompt was exported to the development PC.

86effective nominal cells now settled; both original Quote-confounded attempts
remain visible/excluded. All168/complete private evidence-failure-recipient-
adoption audit/pruning/actualPhaseII/finalQ1–Q10are still outstanding. No scores
are pooled across benchmarks, no method is screened early, no normal failure is
repeated, and no prompt/model/budget/operator/evaluator change occurred.
