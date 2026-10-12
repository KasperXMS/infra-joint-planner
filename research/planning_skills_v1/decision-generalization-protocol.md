# Frozen follow-up: conditional decisions beyond the development templates

The complete primary study shows reliable raw JSON but low numeric success even with current values displayed beside policies. The earlier development probe improved one-step decisions on comparison policies. The remaining uncertainty is whether that decision-context effect extends to the primary relative/parity policies, or whether even a supplied target and explicit observed values leave branch errors. This follow-up is a post-hoc mechanism diagnosis, not a capability Gate or another claim of held-out workflow performance.

## Frozen population and selection

Use every no-extra-skill trajectory from the fully audited **Qwen3.5-9B primary study**, regardless of its final score. For each task/node/pre-or-post-update phase, select the first actually executed conditional computation with valid ordered inputs. Include correct and wrong original operations. Do not use reference intermediate values; the card contains actual previously observed values, even when earlier model choices were wrong. Do not sample based on model errors or outcomes.

The resulting population is **338 decisions**, from 36 considered source trajectories across 12 source graph clusters. Three source trajectories contain no eligible computations, so queries cover **11 observed graph clusters**. Their missing decisions are not imputed or quietly treated as successful; all three original failures remain in primary workflow results and the coverage ledger. No later duplicate node/phase computation occurs in this actual source pool. Selection/configuration freeze precedes all new inference.

Exact history-bearing configuration SHA256: `7ae597b3ef5ccde3c7a86e3b67adc05e1928f1e0eda09552241096e107e2325f`. The [public freeze](configs/decision-generalization-v1.public.json) contains query/source identities, trace hashes, coverage and configuration parameters; histories, card values and scoring labels remain in the private config/archive. The generator reconstructs that config from indexed primary traces.

## Intervention and inference

Reuse the **unchanged development probe runner and prompt wording**. Both models receive the same 338 queries under three conditions:

1. `full_target`: complete observed task/history plus a requested node and its ordered handles.
2. `full_card`: the same context/target plus its observed input values and public policy.
3. `isolated_card`: common API/schema instructions plus the identical target/card; other task/history is removed.

All conditions supply the target. This removes next-node scheduling and measures conditional operation choice and target fidelity, never autonomous planning TSR. The correct operation/scoring label is not passed to the prompt. Full-card and full-target differ in repeated facts and token length; this follow-up does not replace the primary/structural transfer's same-fact/token-matched joining control. Isolated-card removes both history and other task context, so a contrast cannot identify history interference alone.

Use the same official BF16 4B/9B checkpoints, direct Transformers/SDPA, greedy thinking-disabled generation, 256 output tokens, actual-token 16,384 context preflight, 300-second cooperative request deadline and zero retries. Batch two per exclusive GPU; all within-study conditions share this setting. Development used batch four, so differences between stages do not isolate a template effect alone. There are **1,014 requests/model; 2,028 total**, with zero model-directed tool executions. Wrong tools/targets/operations, schema errors and legal deadlines remain results.

## Queue and final analysis

Start each model only after its corresponding structural-transfer worker actually exits, has a complete result marker and releases GPU memory. Verify PID/start identity; never kill competing processes. Run all queries on both models regardless of transfer outcomes. The independent 20-hour resource guard and STOP mechanism remain active. Record every raw generation and physical batch once; no selective reruns or per-query audit/report.

After both models finish, perform one CPU-only audit: expected query-condition sets, frozen source/configuration hashes, public-policy label derivation (including equality/negative parity), exact prompt/token/output reconstruction and independent schema/target/operation scoring. Compare all three conditions, pre/post updates, and original wrong-choice rescues/correct-choice regressions. Overall scores weight queries; exploratory paired effects first average within the 11 observed graph clusters then weight those graphs equally. Report that conditional coverage explicitly. Missing query states cannot establish success or failure under an unexecuted intervention.

Record actual batch service wall/tokens, not overlapping latency as GPU time; local GPU USD stays unknown and cloud calls remain absent. This test changes neither primary/transfer skills, prompts, evaluator nor outcomes. Final recommendations will combine independent workflow transfer with this diagnostic, then judge whether additional experiments offer enough information to justify their cost.
