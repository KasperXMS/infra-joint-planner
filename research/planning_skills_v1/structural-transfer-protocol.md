# Predeclared structural transfer, conditional on information value

This design is prepared before inspecting primary held-out success counts. It does not tune a skill to the primary tasks. All static rules, runtime joined/unjoined renderers, inference, strict schema, tools, numeric evaluator and budgets are unchanged.

## Why this resolves a remaining uncertainty

Primary tasks supply nodes in topological order and use names encoding layer/branch. An improvement there need not survive removal of those planning aids. Transfer changes source/node identifiers to opaque random labels and presents nodes in a fixed, non-topological permutation. The model must recover the execution order from declared parent relationships. Runtime support uses precisely that same public permutation; it does not restore private topological order or supply a frontier.

The private evaluator retains its original graph order. Presentation-aware `Task` merely overrides `public()`; numeric operations, source updates, invalidation, verifier and terminal contract call the identical original environment. `run_transfer_model.py` reuses the same inference function with that explicit task constructor. A focused reference-path regression verifies presentation/evaluation invariance and matched joined/unjoined facts.

## Frozen tasks and conditions

Relative/parity policies × depths 2/4 × four independent seeds (71017/71033/71059/71081) yield 16 graph clusters. Each cluster has paired no-update, policy-stable-update and policy-flipping-update variants, selected by the same pre-inference eligibility rule as the primary study. There are 48 variants, each under none/system-static/joined/unjoined support, on both models: **384 workflow episodes if launched**. Transfer is structural and synthetic, not an external natural benchmark.

Sampling remains greedy/thinking-disabled BF16 direct Transformers, batch two per model, 16K exact-token preflight, 256 output tokens, 64 turns, 300 seconds/request and 3,600 seconds/task. Cases and rotated condition order are fixed before any transfer model execution. No selective reruns or outcome-selected graph subsets are permitted.

## Predeclared launch and GPU handoff

Assess a primary model only after its complete 252-episode record exists and matches the frozen task/condition identity set. Trigger transfer when **either** completed primary model has an absolute joined–unjoined TSR difference of at least 0.10, or when its better runtime condition exceeds system-static TSR by at least 0.10. This is an exploratory information-value rule, not a significance test.

If triggered, run the entire transfer design on **both** models, including a model that did not trigger. A model can start transfer only after its primary worker has actually exited and its GPU has released the CUDA allocation. This allows the faster primary model to continue useful work on its own card while the slower model finishes. It adds neither another resident model nor competing requests on a card. Cross-model latency remains observational; logical calls/tokens and TSR are the primary comparisons.

If neither model triggers, preserve a skipped-study decision and reconsider the failure mechanism instead of automatically repeating a floor effect on harder graphs. System failures stop subsequent work; schema errors, wrong answers and legal budget exhaustion remain outcomes. Original primary workflows continue exactly as frozen.

## Analysis

Primary paired contrasts: joined–unjoined, joined–system-static, unjoined–system-static, and system-static–none. Report all task outcomes, conditional executed operation accuracy, stale-operation persistence, dependency/phase/terminal failures, recovery, verifier amplification, tokens and failure-inclusive work. Graph-cluster bootstrap retains all three variants and resamples 16 graph clusters, not 48 independent tasks. Role-placement/local/ledger conditions are not repeated here because this transfer tests current-fact presentation, not another skill-granularity sweep.

The uniform post-batch audit reconstructs exact prompts, token counts, raw outputs, support inventories and deterministic tool traces once, without additional inference. Resource accounting includes all preparation, invalidated engineering work and primary/transfer runs. No claim of algorithmic novelty follows merely from successful transfer; comparisons with StateMem, SkillSmith and SkVM remain mandatory.
