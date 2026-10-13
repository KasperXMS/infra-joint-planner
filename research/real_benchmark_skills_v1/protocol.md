# Real benchmark skill-assisted planning: protocol and execution record

This study asks whether native reusable skills compensate for Qwen3.5-4B/9B planning limitations on real agent tasks. **No model benchmark outcomes have been collected yet.** Infrastructure smoke checks are separate from development and held-out results. Historical synthetic results are excluded from every official success-rate denominator.

The attached research brief is the governing specification. Work began on 2026-10-13 at approximately 11:48 HKT. AutoDL must remain running after experiments, failures, or budget exhaustion. Only this study's model, runner, tunnel, and containers may be stopped. No whole-instance lifecycle automation is used.

## Official artifacts

- [SkillsBench v1.1 release](https://github.com/benchflow-ai/skillsbench/releases/tag/v1.1), exact commit `b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`.
- Release asset `skillsbench-v1.1-task-manifest.json`, SHA256 `0aa87c4d4f64c33db74b20e770f4b4a77dc21911e81a8ffd50cbb84ac7a4cc6f`, 87 active tasks; `tasks-extra` excluded.
- BenchFlow `0.6.3`, wheel SHA256 `e032bcb4894dd3f59f98204366a7282e5ae6058289d1bd8c2fce56e2c972efc6`. Dependencies locked with hashes in the WSL workspace.
- The release manifest agrees with the actual tag. The checkout's registry still names earlier snapshot commit `55bfe693...` in its v1.1 entry. Use the release manifest and explicit checkout above, rather than silently resolving the registry's different snapshot.
- Preserve `task.md`, all `environment/` files including skills/scripts/references, `oracle/`, and `verifier/` without changes. Windows checkout newline conversion was detected and eliminated by materializing Git archive bytes. All 24 package digests match the official release asset.

## Selection frozen before outcomes

`task-selection.lock.json` freezes 8 development and 16 evaluation task IDs, metadata, declared resource/time budgets, whole-package digests, and per-file SHA256 hashes. Skill, evaluator, and environment aggregate digests use the official digest algorithm with task-relative POSIX paths. These content pins are final for this selection; runtime feasibility remains unverified for most tasks. A task that cannot run is an infrastructure blocker, not a zero-scoring model outcome or a reason for outcome-based substitution.

Selection uses official metadata, domain coverage, multi-step file/code work, CPU-only environments, native skill availability, and distinct task/skill families. No small-model outcomes were consulted. The development set has 2 easy, 4 medium, and 2 hard tasks; evaluation has 1 easy, 11 medium, and 4 hard tasks. Seven official categories are covered across the selection. There are no shared task IDs or skill directory names across splits. Manual family labels are recorded; semantic and content-duplication review remains required before designing S2. Distinct names alone do not prove independence.

| Split | Task IDs |
| --- | --- |
| Development | dialogue-parser; azure-bgp-oscillation-route-leak; econ-detrending-correlation; crystallographic-wyckoff-position-analysis; adaptive-cruise-control; court-form-filling; dapt-intrusion-detection; civ6-adjacency-optimizer |
| Evaluation | spring-boot-jakarta-migration; tictoc-unnecessary-abort-detection; data-to-d3; sec-financial-report; xlsx-recover-data; lab-unit-harmonization; gravitational-wave-detection; glm-lake-mendota; radar-vital-signs; manufacturing-fjsp-optimization; manufacturing-codebook-normalization; pddl-airport-planning; bike-rebalance; software-dependency-audit; setup-fuzzing-py; offer-letter-generator |

## Sandbox alternative

The AutoDL container has no Docker daemon/client/socket, lacks CAP_SYS_ADMIN, and rejects both mount and user namespace creation. BenchFlow 0.6.3 registers Docker, Daytona, and Modal; no supported unisolated host fallback exists. Neither cloud provider is configured. The user requested an alternative, without authorizing additional cloud purchases.

The available local Ubuntu-22.04 WSL2 environment permits mount namespaces and has approximately 14.5 GiB RAM. A dedicated official Docker 29.9.0 daemon and Compose 5.6.0 plugin run under `/root/skillsbench-local-20261013`, without replacing an existing daemon or installing a system service. The Compose asset was checked against its release SHA256. Docker's hello-world container passed. The original `dialogue-parser` oracle and verifier passed with reward 1.0 through BenchFlow; this is an infrastructure check, not an agent success.

Official task containers run on WSL, and model inference will run on the existing AutoDL RTX PRO 6000 Blackwell. All treatments use the same split infrastructure. Record WSL CPU/RAM, image IDs, build durations, SSH transport latency, and local resource use separately. AutoDL rental does not include local electricity or hardware depreciation; those costs remain unmeasured unless reliable inputs become available. This topology changes the proposed all-on-AutoDL execution environment and must be disclosed in conclusions.

## Model and harness freeze gate

Intended models: official Qwen/Qwen3.5-4B and Qwen/Qwen3.5-9B, BF16, context 32,768, temperature 0, thinking disabled. Exact official repository commits and every downloaded file hash are recorded in `models.lock.json`. ModelScope downloads are accepted only for weight files whose SHA256 equals the official Hugging Face LFS SHA256. Other model files come from pinned official Hugging Face revisions.

Prepare a separate vLLM environment, leaving the existing PyTorch/project environments intact. Initial deployment candidate is vLLM 0.20.2 with Transformers 5.17.0; actual dependency versions, CUDA compatibility, model API behavior, and final launch command must pass the one-time smoke before configuration freeze. These are deployment choices, not additional backend benchmarks. Official Qwen tool parser: `qwen3_coder`; reasoning parser: `qwen3`; disable thinking through chat-template configuration. Explicitly record any decoding constraints; do not add schema repair or guided parameter decoding.

Use BenchFlow's supported OpenHands ACP adapter, CLI commit `3ca17446c5d9c1e35e054803478a3501ec251ecf`, SDK/tools 1.22.1 (the adapter's official pins), unchanged tools and permissions, and native skill paths. The SDK 1.22.1 wheel SHA256 is `0d77190ff1e4f5face22ed284cdc54927e6db708825d6b35c961e9410aebdd52`. `bench_with_frozen_openhands.py` preserves the official adapter and changes only its launch-time native LLM settings: temperature 0, top_p 1, context 32,768, output 4,096, and num_retries 0. This disables the SDK's default retry behavior, which can otherwise increase temperature after an empty response. The authenticated SSH model relay enforces the same generation settings without changing prompts, tools, or arguments, and keeps raw bodies privately. Actual context protection and parameter delivery remain pending the real agent smoke. Native skills must be discoverable/readable/executable through normal filesystem access. For S0, confirm that skill files are absent from all agent-visible copies, including copies baked into the image. For S1, retain the complete official package. Do not substitute arbitrary skill text in a system prompt.

## Runs and failure policy

Stage A: 2 models × 8 development tasks × S0/S1 = 32 runs. Stage B may develop at most one mechanism supported by actual development traces and a comparison to prior work. No intervention is currently proposed. Stage C: 2 models × 16 held-out tasks × S0/S1 = 64 runs; add all 32 S2 runs only if a method is frozen before held-out outcomes are inspected. No optional 27B or transfer runs are planned before the main study is complete.

One initial trial per cell; no answer-based automatic retries, verify-retry loop, best-of selection, or failure-only reruns. Use single-shot BenchFlow rollout strategy. Retain original task agent/verifier budgets consistently across treatments. Group by model and counterbalance S0/S1 ordering by task index. Cap concurrency by declared sandbox memory plus host headroom and observed GPU queueing. Infrastructure faults stop affected batches; log revisions, preserve old outcomes, and apply any correction equally to affected treatments. Task difficulty or poor scores never justify changing conditions or skipping long tasks.

Before launching agent batches, freeze one complete machine-readable run configuration and request capture policy. Confirm tool calls, skill loading, artifacts, context limit, official verifier, and input/output isolation. Keep oracle/verifier and private credentials inaccessible to the solver. Log per-request prompt/completion tokens, generation settings, wall latency, tool calls/errors, artifact paths, exit/timeout reason, official reward, model/service version, and immutable run ID. Redact credentials before publishing; original traces remain private.

## Analysis and inference limits

Primary outcome: original official task resolution reward, with exact numerator, denominator, missing-cell count, and infrastructure exclusions. Missing runs are missing, never fabricated passes/fails. Compare each model on paired tasks: S1 minus S0, rescue (0→1), regression (1→0), and per-domain/difficulty descriptive summaries. Compare 4B/9B treatment effects descriptively; one trial and 16 held-out tasks do not establish general scaling laws, statistical significance, or repeatability.

Secondary outcomes: workflow completion (separately defined from official reward), skill available/discovered/read/applied/executed, tool-call errors, planning turns, repeated failed operations, recovery, tokens, model latency, task E2E, setup/build time, and rental. File access alone is evidence of reading, not correct use. Failure categories must cite actual trace spans and distinguish knowledge, discovery, tool grounding, sequencing/state, recovery, and termination/artifact errors. Categories are provisional until development evidence exists.

RQ1–RQ8 require actual matched model runs and are presently unanswered. RQ2 repeatability requires predeclared complete paired repeats beyond the initial trial. RQ9 novelty is not established by reproducing a positive skill lift. Without a validated new mechanism, report an honest reproduction/diagnostic study.

## Literature gate

Verify and compare primary full texts before designing S2: [SkillsBench](https://arxiv.org/abs/2602.12670), [Skill granularity](https://arxiv.org/abs/2605.31408), [SkillLens](https://arxiv.org/abs/2605.08386), [SkillReducer](https://arxiv.org/abs/2603.29919), [SkillCraft](https://arxiv.org/abs/2603.00718), [SkillSmith](https://arxiv.org/abs/2605.15215), [SkVM](https://arxiv.org/abs/2604.03088), and [Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html). Landing pages and abstracts have been verified. This is not yet a full literature review or a novelty claim. Compiler/runtime interfaces, adaptive granularity/delivery, reduction, and workflow memory are existing directions; renaming them is insufficient.

## Preservation and delivery

Local official source/cache: `D:/Codes/infra-aware-mas-new/.code-staging/`. WSL jobs, private traces, Docker state, lockfiles and receipts: `/root/skillsbench-local-20261013`. AutoDL models, inference environment and logs: `/root/autodl-tmp/real-benchmark-skills-v1`. Source, public hashes, protocol, redacted results and conclusions go to the independent `real-benchmark-skills-v1` branch. Raw prompts, credentials, and sensitive traces must not be pushed. Back up final private evidence before task-process cleanup; leave AutoDL online at ¥7.35/hour.

Provisioning corrections before model trials: an initial config archive was copied before SFTP finished and was rejected with EOFError. The corrected launcher validates archive contents before starting. Configs and weights now use the accessible official ModelScope mirror whenever byte-identical to pinned Hugging Face files; only the differing official license files require the small transferred archive. Single-stream weight transfer was slow, so a bounded 16-worker HTTP-range downloader resumes verified full-file downloads. These changes affect provisioning only; no agent runs, evaluator changes, or answer retries occurred. Historical error receipts are retained rather than overwritten as successes.
