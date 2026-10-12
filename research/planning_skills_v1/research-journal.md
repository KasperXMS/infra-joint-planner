# Research journal

## 2026-10-13 — Initial landscape, historical evidence, independent provisioning

The autonomous objective is preserved verbatim in `objective.md`. Earlier Skill Granularity v2 remains paused. This research uses branch `planning-skills-research-v1` and an independent AutoDL namespace. No laboratory Executor or historical result is modified.

Historical evidence motivates diagnosis, not a held-out claim. The 18-cell pilot mixes severe protocol/parse failures with planning outcomes. The 42-cell failure metadata separately identifies provider XML-parser failures before application schema validation, phase-restricted reads and physical-context rejection. The 30-cell report explicitly acknowledges unequal skill contents/lengths and single-slot contention; its 11 provider timeouts are not direct evidence of weak planning. These limitations rule out treating past scores as a clean capacity-by-granularity interaction.

Primary-paper reading shows broad candidate mechanisms are substantially covered. The first experimental question is therefore deliberately narrow: knowledge delivery versus state bookkeeping under a common observable tool contract. Reading and novelty decisions are recorded separately in `literature-novelty-ledger.md`.

Provisioning began at remote epoch 1791825620 (UTC recorded by the runtime guard). Official Qwen3.5-4B and Qwen3.5-9B are downloading through ModelScope; Python packages use the TUNA index. The measured container limit is 180 GiB RAM/50 CPU cores, despite host-level `free` reporting 754 GiB. Base PyTorch is 2.8.0+cu128; isolated Transformers resolved to 5.19.0. Actual weight/config/tokenizer files will be hashed before inference. Mutable ModelScope `master` is explicitly not described as a pinned repository commit.

The backend is direct Transformers BF16 on one exclusive GPU per model, with four active workflows batched per GPU. This changes quantization/backend from the historical Ollama Q4_K_M pilots, so scores are not interpreted as a controlled historical comparison. New comparisons within each model share exactly the backend, precision, greedy decoding, thinking-disabled template, tools and budgets. No strong model, constrained decoding or native-provider tool parser is used. The strict raw JSON/schema boundary remains observable; malformed actions have no side effects.

### Development experiment diagnostic-v1, frozen before inference

Eight deterministic tasks: depth 1/3 × unchanged/updated evidence × two source/value seeds. Each task runs none/static/local/ledger on both models (64 episodes). Task-major condition order rotates deterministically. Greedy decoding avoids unpaired sampling noise in the first diagnosis. Maximum 48 turns, 256 generated tokens/request, 16,384 context tokens with exact-token preflight, one hour/task. These are new microbench budgets, not an assertion that the old 32K deployment was reused.

Tools really fetch hidden numeric source records, compute requested operations, verify provenance/freshness and submit. The task's natural-language branch policies are evaluated by the model; compute does not choose operations. Verification cannot reveal the correct answer. A first verification can explicitly invalidate a changed source and its descendants. Workflow completion and final numeric success are separately scored. Deterministic verifier/tool work is measured; this is a microbenchmark, not the old multi-agent benchmark with LLM Specialists/Verifier.

The ledger is reconstructed from observations only. It contains no action recommendation, dependency frontier, branch evaluation or expected answer. Local rule selection uses only the last visible event category, from a fixed task-independent rule bank. No held-out task has been run or used to design these rules. Development templates use numeric threshold comparisons; later independent templates will use relative/parity conditions and new seeds if the mechanism remains worth testing.

Contract tests exercise all three templates, source-update/transient recovery, strict schema rejection with no side effects, incorrect-answer completion, and absence of private source values/branch choices in public prompts. Six tests passed, including thirty full reference recovery paths and a separately hand-calculated branch-flip case (root 16 before source update, 20 after). Premature verification cannot trigger a source update: recovery requires constructing a valid root first. The reference executor exists only in tests; inference does not import it.

The resource baseline was corrected before any model inference to active-goal creation (epoch 1791824705), including approximately fifteen minutes of earlier reading/preparation. The guard's own PID/start identity was checked before its one restart; inference/download jobs were not restarted. Soft/hard deadlines are 1791860705/1791896705. Rental estimates therefore include setup time rather than starting only when weights finish downloading.

### Next decision

After both development models finish, inspect aggregate failures and selected raw synthetic traces. Freeze a justified mechanism/control set before held-out inference. Do not select a successful single trajectory as evidence. Add matched length/content or execution-support ablations only when they resolve a concrete ambiguity. Stop a direction if new experiments cease to identify useful differences.

### Mainland transport adjustment before inference

The official ModelScope SDK resolved to `modelscope-hub`, whose installed primary source sets one range-download stream per file by default. Most files progressed around 1–3 MB/s, but one 9B shard lagged markedly. At epoch 1791827515, the owned downloader was identity-checked and stopped once, before any evaluation manifest existed. Its 18,987,614,208 already-downloaded prefix bytes were preserved into the SDK's resumable range parts. Download resumed with the SDK's supported `MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS=8`; repositories and revisions were unchanged. This is transport optimization, not model/backend/hyperparameter search or an evaluation rerun. The SDK source inspection and exact prefix bytes are recorded in administration metadata. Temporary prefixes are retained until completed weights can be checked.

## Engineering exclusion: chat EOS framing, followed by complete diagnostic-v2

The first actual 4B generation exposed a harness mistake: the checkpoint generation configuration uses endoftext (248044), while the tokenizer's chat EOS is im_end (248046). Generated actions were valid JSON followed by the chat terminator, a newline and endoftext. The decoder removed only the latter, causing spurious strict JSON failures. All conditions were affected. Diagnostic-v1 was stopped as a system issue; its entire namespace, raw tokens, traces and exact source were retained and explicitly marked **not ability evidence**. There are 404 recorded requests/101 service batches, eight finished episodes and additional interrupted episodes; unrecorded in-flight work is not inferred. These costs remain part of total rental/work accounting.

The corrected decoder stops at both configured endoftext and tokenizer chat EOS at the token boundary. It still performs no JSON/argument repair, fence removal, tool substitution or constrained decoding. A new `diagnostic-v2` repeats **all eight tasks × four conditions × two models**, not a result-selected subset. The tasks, rules, model bytes, precision, budgets and evaluator are unchanged. Both models completed 32/32 episodes; deterministic replay validated every recorded observation and final evaluator result. The exact executing source was copied into each stage before subsequent development.

| Model | Condition | Completion | Success | Turns |
| --- | --- | --- | --- | --- |
| 4B | none | 8/8 | 2/8 | 108 |
| 4B | static | 4/8 | 1/8 | 240 |
| 4B | local | 8/8 | 2/8 | 104 |
| 4B | ledger + static | 5/8 | 1/8 | 195 |
| 9B | none | 8/8 | 2/8 | 107 |
| 9B | static | 8/8 | 2/8 | 108 |
| 9B | local | 8/8 | 2/8 | 108 |
| 9B | ledger + static | 8/8 | 2/8 | 107 |

These eight-task/two-seed development figures do not support a universal capacity or skill claim. There were no raw JSON/schema failures after framing correction. The 4B static/ledger arms instead looped on dependency mismatches or non-root verification. Completion cannot stand in for correctness: 9B completed every workflow but its aggregate success was only 8/32.

Selected raw traces reveal a more specific hypothesis: refreshing artifact handles does not necessarily refresh the **operation choice**. On development s11/depth1/update, the 9B baseline refetched the changed input from 16 to 38, yet reused difference where the observed policy now requires max, submitting 68 rather than 76. The verifier correctly certified provenance, not semantics. This is action-policy anchoring, not stale-handle reuse or a provider parse failure. Similar initial multi-level policy mistakes occur without refresh.

Two confounds require targeted development checks before held-out validation: (1) static rules were appended as the latest user message, so placement/recency may explain 4B regressions; (2) source values, policies and handles are available but spread across history, so incorrect binding may resemble inability to evaluate a simple condition. The next low-cost experiments will compare static placement and identical observed compute decisions under full-history versus locally bound input/policy cards. Cards will contain only already observed values and the public policy, never the correct operation or answer. These are diagnostic decision probes, not whole-workflow TSR or a new capability Gate.

## Development ablations completed: placement and observed-value binding

`role-placement-v1` executed 48/48 full workflows: all eight development tasks on both models under none/latest-user-static/system-static. The 4B latest-user arm reproduced 4/8 completion and 240 turns; putting the **identical rule bank** in the system instructions restored 8/8 completion and 106 turns, but success remained 2/8. The 9B arms all completed 8/8 and succeeded 2/8. This is a placement confound in the apparent capacity interaction, not evidence that more explicit skills intrinsically harm 4B. These are repeated development tasks, not independent held-out replication.

`decision-context-probe-v1` froze all 48 valid non-root compute decisions from the eight 9B no-skill trajectories, including correct and incorrect decisions. Both models answered the same queries under full history + target node/handles, full history + observed current values/public policy card, and isolated card. No correct operation, private source or evaluator answer entered a prompt. The cards use actual observed intermediate values even where an earlier model operation was wrong; scoring is therefore local decision correctness conditional on observed inputs, not global task success. All 288 requests completed with valid schemas; these probes execute no tools and are not presented as workflow TSR.

| Model | Full target | Full history + card | Isolated card |
| --- | --- | --- | --- |
| 4B operator accuracy | 28/48 | 45/48 | 39/48 |
| 9B operator accuracy | 26/48 | 44/48 | 39/48 |

9B full-card target fidelity was 46/48, so its joint decision score is 42/48 rather than 44/48. All other target-fidelity scores were 48/48. Full-card post-update operator correctness was 16/16 (4B) and 12/16 (9B), versus 8/16 and 6/16 for full-target. Full history with a card outperformed a shorter isolated card on this development set; the gain is not explained simply by removing all history. A card can still change salience or repeat relevant facts, so joined-binding versus equally informed/unjoined length-matched support is required before attribution.

### Chosen next hypothesis and controls

Test **runtime value–policy binding**, not a new static granularity scale. An observation-only adapter can instantiate each public node policy with its currently observed ordered parent handles/values, without selecting a next node or operation and without executing or repairing any action. A matched unjoined table will contain the same current artifact facts and policies, with per-state token length matched. Conventional system-static, latest-user-static, local rules, and ledger-only variants separate placement, generic procedural prompting and bookkeeping.

Held-out tasks will use new relative/parity policy templates and seeds, with matched no-update, genuine-value-update/policy-stable, and genuine-value-update/policy-flipping variants. The stable/flip distinction is constructed and scored by the private generator/evaluator, never disclosed to the planner. This isolates semantic re-decision from provenance rebuilding. All mechanisms and tasks will freeze before held-out inference. The generator's selection of policy-sensitive graphs will be disclosed; this is a diagnostic stress distribution, not a natural benchmark prevalence estimate.


## Held-out study launched after one freeze

The formal `heldout-binding-v1` config was committed as a7dca64 before execution. Its exact executed SHA256 is `986e59d12388a4ec0948e9819cd28879105c40cb1638ceefb2e0b21f566aabab`. The initial 310xx graphs were structural renderer fixtures; final held-out seeds are 43017/43033/43059, selected before any final model query. There are 12 graph clusters and 36 paired update variants, seven frozen conditions, and 504 real workflow episodes across two models. Both exclusive-GPU workers launched together under supervisor PID 7807, with batch size two per GPU. Exact source snapshots were retained immediately after their frozen manifests appeared. No runtime mechanism, prompt, model, evaluator or order will change within this study.

The post-batch analysis records conditional operation accuracy only for actually executed non-root computations, distinguishing old-operation persistence from stale-handle use. Planned uncertainty resamples graph clusters, retaining paired variants. It additionally checks whether stable/flip trajectories have identical prefixes before observing the differing replacement; numerical/batching divergence will be reported rather than forcing an artificial matched trace. This analysis code is separate from the frozen inference source. A focused regression replayed all 64 development episodes; exact prompt/token/output reconstruction independently passed all 776 calls in the 48 placement episodes. Neither check performs model inference.


## Structural transfer prepared before primary outcome inspection

While the 504 primary workflows continue, a separate transfer design was prepared and frozen without reading their success counts. It removes topological presentation and layer-name hints using a public node permutation and opaque identifiers. Private evaluator order, arithmetic, tools, static skills, runtime renderers and the inference engine remain identical. New seeds 71017/71033/71059/71081 and depths 2/4 define 16 graph clusters, 48 update variants, four conditions and 384 potential episodes. The presentation wrapper is separate from the unchanged primary task class. A focused reference-path check verifies numeric/contract invariance, public stable/flip identity and identical support fact inventories.

The predeclared information-value trigger is an absolute joined?unjoined TSR gap >=10 percentage points or a best-runtime-minus-system-static TSR gain >=10 points on either fully completed primary model. If triggered, BOTH models run the ENTIRE transfer set; if neither triggers, preserve a skipped-study decision and reconsider the mechanism rather than expand a floor effect. This is an exploratory sequential-design rule, not a significance threshold. GPU-wise handoff occurs only after the corresponding primary worker exits and releases its CUDA allocation, so it can reduce idle time without increasing per-GPU contention. Primary conditions/order are untouched. No post-hoc model or task subset is permitted. The protocol and launcher are committed before any transfer inference.


## Evidence/export preparation while inference continues

Observed active worker environments confirm GPU0/GPU1 assignment, HF/Transformers offline flags and eight OpenMP threads per worker. The environment receipt records 176 package versions; actual core versions are PyTorch 2.8.0+cu128, Transformers 5.19.0, ModelScope 1.40.2, modelscope-hub 0.4.6, Accelerate 1.15.0 and safetensors 0.8.0. Both GPUs report compute capability 12.0 and driver 595.71.05. Only selected nonsecret environment variables were retained. Version records are not falsely called package-wheel hashes.

A final-only evidence exporter now refuses incomplete model cohorts or unfinished final postprocessing, verifies frozen source and result/trace hashes, preserves all explicitly engineering-invalidated partial traces, and creates a byte-exact private raw archive plus public metadata index. It excludes weights, caches, credentials and root download logs. A focused fixture checks unfinished-study rejection, interrupted-engineering retention, exact archive bytes and overwrite refusal. This preparation performs no model calls and no intermediate per-cell report.

One analysis-only correction fixes the resource-summary classification of the early EOS run: its exclusion marker resides in the model stage, not the experiment parent. Recorded batch work/rental totals were always included and are unchanged; the final classification will now explicitly mark it as engineering-invalidated. The correction is local analysis code and does not change executing inference or any frozen treatment. A scope check against baseline a8da9a76fdcc13611c8e596bd28e03446ea5e1d1 found only the new research namespace and two scoped .gitattributes entries changed. The final requirement map records what remains unproven rather than treating running jobs as completed research.

## Final-analysis correction prepared without changing live inference

Independent deterministic fixtures exposed an overbroad diagnostic label: the held-out analyzer's `all_executed_policy_choices_correct` previously covered conditional nodes only, omitting the unconditional root operation. Its historical error flag also could not distinguish a discarded wrong intermediate from a wrong operation retained in the submitted artifact's ancestry. The final analyzer now scores every actually executed computation, follows the actual submitted provenance, and separately reports policy-compliant completion, numeric success despite a retained policy violation, and recovery by discarding an erroneous computation. Numeric collisions remain successes under the original frozen numeric evaluator; no scoring rule, task, prompt or inference outcome changes.

The three fixtures cover a wrong unconditional root, a corrected replacement computation, and a numerically correct collision produced by the wrong operation. All 15 focused contract/control/export/provenance tests pass. The correction remains local while the already frozen primary/conditional-transfer pipeline runs. Preserve its original analysis outputs, then produce a separately versioned final diagnostic analysis and verify that completion, task success, turns and token totals are unchanged. Existing inference-source snapshots remain authoritative. This additional analysis executes no model requests and does not select episodes for rerunning.
