# Primary held-out findings: completed and replay-validated

All **504/504** frozen workflows executed once. Exact reconstruction passed all **12,802** generated requests, including prompt hashes, tokenization, decoded outputs, actual tool observations and numeric evaluator results. The runtime fact-inventory check passed 2,690 joined/unjoined states. There were no schema failures, context rejections or request/task timeouts. The full [result tables](results/heldout-binding-v1/result-tables.md), [per-episode CSV](results/heldout-binding-v1/results.csv), [summary](results/heldout-binding-v1/summary.json) and [trace index](results/heldout-binding-v1/trace-index.json) retain every outcome.

These are 12 generated graph clusters with three paired update variants, seven conditions and two models, not 504 independent natural tasks. Mechanisms, tasks and order froze before inference. This primary study supplies topological node order; its independently frozen structural transfer is running and has no reported outcome yet. The present document is a complete primary-study finding, not the final autonomous-research recommendation.

## The main separation is completion versus correctness

| Condition | 4B completion | 4B numeric success | 9B completion | 9B numeric success |
| --- | --- | --- | --- | --- |
| No extra skill | 36/36 | 0/36 | 33/36 | 2/36 |
| Static / system | 36/36 | 1/36 | 36/36 | 0/36 |
| Same static / latest user | 6/36 | 0/36 | 29/36 | 1/36 |
| Local rule delivery | 26/36 | 1/36 | 29/36 | 2/36 |
| Static / system + ledger | 29/36 | 0/36 | 29/36 | 0/36 |
| Static / system + joined facts | 36/36 | 5/36 | 36/36 | 5/36 |
| Static / system + unjoined facts | 33/36 | 2/36 | 36/36 | 3/36 |

Runtime names ending in `_system` refer to the generic bank's system placement; the dynamic block is the latest user message. Joined and unjoined contain identical facts and repetition counts, matched to equal tokenizer length at each state. Realized histories and total tokens can diverge. Ledger contains historical artifacts/validity and is not the same-information joining control.

Joined facts improve numeric TSR over static/system by 11.11 percentage points for 4B and 13.89 points for 9B. The more diagnostic joined-minus-unjoined differences are smaller: +8.33 points (four rescues, one regression) and +5.56 points (two rescues, no regression). Their exploratory graph-cluster bootstrap intervals are respectively [0, 22.22] and [0, 13.89] points. Twelve selected synthetic graph clusters do not establish a generally reliable joining advantage.

Same-bank placement strongly changes completion: static/system versus latest-user improves 4B from 6/36 to 36/36 and 9B from 29/36 to 36/36. Correctness remains poor; 9B's numeric success actually changes from 1/36 to 0/36. Thus completion recovery cannot justify a broad task-success or capacity-compensation claim. Role, position and salience change together.

## Protocol reliability does not remove semantic failures

There are 430 valid terminal submissions and 74 legal turn-budget exhaustions. All 12,802 raw actions pass JSON/schema validation. Unexpected errors comprise 2,013 dependency mismatches, 1,498 non-root verification attempts and 14 invalid/stale artifacts. No phase or terminal-contract error occurs. These findings separate the earlier historical provider/serving problems from the semantic and dependency failures in this new controlled setting.

The failure partition separates 333 wrong answers without any unexpected tool error, 75 with such errors, 52 turn exhaustions with an observed policy error, and 22 turn exhaustions before any accepted computation. The last group incurs 1,342 dependency mismatches. Its empty decision sets make `all_executed_policy_choices_correct` vacuously true; this is not demonstrated operation competence. See the complete [failure decomposition](results/heldout-binding-v1/failure-analysis/failure-decomposition.md) and [ablation map](mechanism-ablations.md).

Both joined arms complete 36/36 yet give 31 wrong numeric answers. Their completed verifier counts are 60 against 60 structurally required attempts for 4B and 62 against 60 for 9B. Fresh provenance and near-minimal verification are compatible with low correctness. By contrast, 4B latest-user static makes 815 verification attempts across its 36 attempted workflows; 9B ledger makes 132, with 129 attempts among completed workflows against 47 required. Failed workflows remain in the aggregate tool/cost counts.

Conditional policy accuracy is computed against each executed decision's **actual observed parent values**, including values produced by earlier wrong choices. For 9B, joined pre-update correctness is 161/216 versus 114/216 for unjoined, but post-update it is 77/127 versus 61/132. For 4B the corresponding figures are 108/216 versus 114/216, and 64/135 versus 65/137. These are descriptive conditional-decision counts from diverging trajectories, not paired trials over identical inputs. They do not establish a universal model-size interaction. The paired TSR interaction, 9B minus 4B joining effect, is -2.78 points with interval [-16.67, 11.11].

## Fresh handles can coexist with an obsolete operation

Examples below use the first lexicographically indexed joined episode per model containing an eligible old-operation persistence event; they are not selected for an unusually large effect.

- 4B `case-1d820f4de7b2b667`: node `hn0_2` initially uses the correct `sum` on [13, 14] at turn 6. After actual source rebuilding, its observed inputs are [17, 14] and the policy requires `max`; turn 17 still chooses `sum`. The episode submits a wrong answer. Trace SHA256: `7147a4a3338bf15e88cf91042b6d18803e578ec4b6abcfa3c8e851f81f07b03c`.
- 9B `case-0dfe129feda66cd0`: node `hn1_0` correctly uses `difference` on [15, 2] at turn 7. On rebuilt inputs [82, 50], the policy requires `sum`, but turn 18 retains `difference`. The episode submits a wrong answer. Trace SHA256: `2434beb74585e1c14ccc8a6531a51b95f79b18b5f773f159ee6ae67b37f92afa`.

The joined groups contain 12 and 14 such events respectively, requiring a previously correct choice, changed observed inputs and a changed correct operation. This is observable persistence compatible with anchoring; it does not identify an internal cause or prove that prior actions caused the new mistake. The same behavior occurs despite explicitly displayed current values.

## Numeric success can mask a wrong submitted computation

Each joined arm has one numeric success whose submitted artifact ancestry contains a policy violation. In 4B `case-0ca29bf57b138176`, five wrong operations survive in the used depth-3 provenance, yet the root value equals the reference 24. In 9B `case-a266bf9e7726f4ac`, one retained wrong operation still leads to the reference 132. These are the **only two numeric successes across all 252 depth-3 episodes**. No depth-3 episode has a completely policy-compliant submitted ancestry. These arithmetic coincidences remain successes under the frozen evaluator; they are not retrospectively regraded.

Policy-compliant submission is therefore 4/36 rather than 5/36 in each joined group. Across all primary groups there are 22 numeric successes and 20 policy-compliant submissions. Six submissions have correct final policy provenance despite an earlier erroneous computation somewhere in history; rebuilding/discarding can explain that transition without the model recognizing its own semantic mistake.

The separately versioned final diagnostic analysis adds this ancestry check and covers unconditional/root operations. It verifies every original per-episode field outside the explicitly corrected diagnostic fields is unchanged. On this actual primary dataset even the three corrected legacy fields have zero changes. The initial analysis, source revision receipt and once-only exact-prompt audit remain preserved. No model request is repeated.

## Work and interpretation boundary

Primary inference uses 6,423 physical generation batches and 12,802 logical requests, 36,332,362 prompt tokens and 378,039 output tokens. Generation spans 5,548.171 seconds (92.47 minutes) across both GPUs; summed batch service wall is 10,783.491 seconds, counted once per physical batch. Neither measure is GPU kernel time. Peak PyTorch allocated bytes are 13,862,991,360 for 4B and 24,842,863,616 for 9B; reserved/NVML residency is a different quantity.

Joined versus unjoined reduces 4B turns from 781 to 639 and prompt tokens from 2,514,657 to 1,790,113. For 9B the corresponding changes are 637 to 633 and 1,770,069 to 1,746,728. Against static/system, joined uses more prompt tokens despite fewer turns: 1,790,113 versus 1,547,191 for 4B, and 1,746,728 versus 1,479,193 for 9B. Better TSR does not imply a free support mechanism. Separate renderer timing was not collected for the primary stage and stays unknown; the transfer stage measures it prospectively. Local GPU USD stays unknown, and whole-instance CNY rental includes setup, engineering exclusions and subsequent work separately.

Stable/flip public inputs are identical before their actual update, but exact pre-update prefixes match only 10/12 joined pairs for 4B and 12/12 for 9B; some other arms also differ. Greedy batching does not guarantee identical trajectories; the cause of these mismatches was not isolated. These are paired graph variants, not universally identical counterfactual trajectories. No traces are forced to match or rerun. See all prefix counts and per-update contrasts in the summary.

These findings currently support a bounded characterization: placement and observation rendering alter workflow reliability and cost, while branch correctness remains a separate bottleneck. They do not show that finer static skills solve small-model planning. The supplied graph, thinking-disabled greedy BF16 checkpoints and selected synthetic policies limit scope. State externalization/compiled interfaces are already close to StateMem, SkillSmith and SkVM; this result is not a new algorithm merely by naming its join operation. Independent structural transfer must finish before a final research recommendation.
