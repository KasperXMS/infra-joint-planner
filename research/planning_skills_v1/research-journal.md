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

Contract tests exercise all three templates, source-update/transient recovery, strict schema rejection with no side effects, incorrect-answer completion, and absence of private source values/branch choices in public prompts. Four tests passed, including thirty full reference recovery paths. The reference executor exists only in tests; inference does not import it.

### Next decision

After both development models finish, inspect aggregate failures and selected raw synthetic traces. Freeze a justified mechanism/control set before held-out inference. Do not select a successful single trajectory as evidence. Add matched length/content or execution-support ablations only when they resolve a concrete ambiguity. Stop a direction if new experiments cease to identify useful differences.
