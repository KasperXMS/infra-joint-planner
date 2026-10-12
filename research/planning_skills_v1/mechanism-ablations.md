# Mechanism ablations and what they identify

This map concerns the completed development and 504-episode primary studies. Independent structural transfer and the frozen 338-decision follow-up remain unfinished; their outcomes cannot be inferred here. All primary comparisons retain the same model, tools, sampling, task population, turn contract and frozen procedural bank. Figures/counts below come from [validated primary results](results/heldout-binding-v1/summary.json), not a new model execution.

| Contrast | What changes | What is controlled | Observed primary result | Attribution limit |
| --- | --- | --- | --- | --- |
| No support → static/system | Generic procedural knowledge is repeated explicitly | Model, tasks, tools, inference and terminal contract | 4B success 0→1/36; 9B 2→0/36 | Added content and prompt length both change; no consistent correctness gain |
| Static/latest user → same static/system | Message role and position | Identical skill text and knowledge | 4B completion 6→36/36; 9B 29→36/36; success 0→1 and 1→0 | Role, position and salience are not individually isolated |
| Static/system → ledger | Latest observed artifacts/validity are projected into an extra user block | Same generic bank/system placement, no action execution by support | Completion 36→29/36 and success 1→0 for 4B; completion 36→29 and success stays 0 for 9B | This tests a particular bookkeeping representation, not all external memory |
| Static/system → local rules | An event category selects one rule, delivered as latest user text | Same source rule knowledge; no next-node/operator choice | Both local groups complete 29/36 or fewer; success 1/36 and 2/36 | Selection, amount of visible content and placement change together |
| Static/system → joined facts | Every public policy is accompanied by current observed ordered inputs | Same generic bank; no gold operator, action repair or tool execution by adapter | Both models succeed 5/36 versus 1/36 and 0/36 | Additional current-fact repetition and prompt work remain explanations |
| Unjoined → joined facts | Serialization puts values/handles next to their policy | Same facts, repetition multiplicities, parent order information, current-output records, standalone support token length and common receipt contract | Success 2→5/36 for 4B; 3→5/36 for 9B | Strongest organization control; padding, serialization and attention locality are inseparable; histories subsequently diverge |
| Stable update ↔ policy-flipping update | New source value changes whether the reference path needs an operation change | Paired graph/policy template and public prefix before replacement | Joined pre-update exact prefixes match 10/12 for 4B, 12/12 for 9B | Some actual greedy trajectories differ before update; no universal identical-trajectory counterfactual claim |
| Depth 1 ↔ depth 3 | More dependent computations and opportunities for error | Fixed task family, width, policies and contracts | Numeric success 20/252 versus 2/252; policy-compliant submission 20 versus 0 | Graph/depth changes more than a single cognitive variable; composition difficulty, not a universal capacity threshold |

The joined-minus-unjoined TSR differences are +8.33 pp for 4B and +5.56 pp for 9B. Exploratory graph-cluster intervals include zero; the cross-model effect interaction is -2.78 pp with interval [-16.67, 11.11]. This does not establish that one model capacity systematically benefits more. The primary uses 12 generated graph clusters with three variants each; 504 episodes are not 504 independent task samples.

## Decision support versus autonomous execution

The development probe supplies a specific target and its ordered handles in every arm. Full-history/card operator accuracy is 45/48 (4B) and 44/48 (9B), versus 28/48 and 26/48 for full-history/target; 9B joint target-and-operator accuracy is 42/48. These are conditional decisions, not autonomous workflow success. Full-card repeats relevant values/policies and adds tokens; it is not a length-matched test. Isolated-card removes both history and other task context. Its lower 39/48 score for each model rules out a simple claim that removing history always improves these development decisions, but it cannot isolate history interference.

The independent follow-up retains the same wording on 338 observed relative/parity decisions. It will resolve whether the development contrast persists on that query pool, not estimate workflow TSR or provide independent held-out validation. The structural transfer instead keeps autonomous workflows and removes topological naming/order cues with new depth-2/4 graphs. Both were frozen before their inference and must finish before final recommendations.

## An operation cannot be correct if none was executed

The [failure partition](results/heldout-binding-v1/failure-analysis/failure-decomposition.md) accounts for every primary episode:

| Recorded outcome/history | Episodes |
| --- | --- |
| Wrong numeric answer without an unexpected tool error | 333 |
| Wrong numeric answer with an unexpected tool error | 75 |
| Turn exhaustion after at least one wrong accepted policy choice | 52 |
| Turn exhaustion before any accepted computation | 22 |
| Numeric success with entirely correct executed-policy history | 14 |
| Numeric success with compliant submitted ancestry after an earlier policy error | 6 |
| Numeric success with a retained policy violation | 2 |

Every one of the 22 no-valid-computation failures has `all_executed_policy_choices_correct=true` only because its scored decision set is empty. Together they incur 1,342 dependency mismatches. They offer no evidence of correct branch reasoning. The lexicographically first such episode is 4B `case-5d5e34b87505a592__local`: three fetches followed by 61 rejected compute attempts, zero accepted computations, 64 turns. Its trace SHA256 is `f74e787aca33cb03d4cebfacc7401b71921ab2ac794bd8fda74a199264841ac2`.

An exhaustive [localization of all 22 traces](results/heldout-binding-v1/failure-analysis/dependency-dead-ends.json) shows that all 1,342 rejected calls already supply the correct **set** of source artifacts, but in the wrong declared parent order. None requests the root or needs an unbuilt derived parent. Every one of the 1,320 adjacent rejection-to-retry transitions repeats identical argument objects; none changes only its operation. Thus this subset is specifically ordered-input binding and failure-to-react to rejection, not missing data or premature root computation. The tool reports a dependency mismatch without choosing/repairing the action for the model. No joined or unjoined primary episode belongs to this zero-valid-computation subset; that descriptive fact is compatible with current-state rendering helping lookup/binding, but does not by itself isolate its cause.

Conversely, the 333 wrong-answer episodes with no unexpected tool error show that successful dependency execution and legal termination can coexist with wrong policy choices. These observational partitions do not identify a causal first error. They preserve the original numeric evaluator, including two arithmetic collisions. Correct final provenance after an earlier wrong operation does not establish intentional semantic recovery; a source update may discard that old computation.

## Cost boundary

Joined versus unjoined reduces 4B prompt work from 2,514,657 to 1,790,113 tokens (28.8%) and turns from 781 to 639 (18.2%). The 9B reductions are much smaller: 1,770,069→1,746,728 tokens (1.3%) and 637→633 turns (0.6%). Against static/system, joining adds prompt work for both models despite fewer turns. Thus neither a universal efficiency gain nor a free representation follows from higher success.

E2E depends on the frozen mixed-condition tensor batches. Prompt work and summed request latency are not GPU kernel time or prices. Primary renderer wall was not measured and remains unknown; transfer prospectively records it. Local GPU USD remains unknown. Whole-instance CNY rental includes preparation and engineering-invalidated work separately.

The existing [mechanism scope](mechanism-scope.md) and [literature ledger](literature-novelty-ledger.md) explain why state rendering, compiled interfaces and generic granularity are not themselves new algorithms. These ablations support bounded characterization rather than a claim that static skills solve small-model planning.
