# Multi-scale Planner model survey v1

Survey date: 2026-10-11. This document records official model facts and the finite selection made before new benchmark scores. It does not report measured compatibility, latency, memory, or accuracy. The machine-readable companion is `configs/experiments/multiscale-planner-candidates-v1.json`.

## Verified requested candidates

All requested names below have official checkpoints and Apache-2.0 licensing permitting local deployment subject to their license terms. Parameter counts describe different components and must not be interchanged with active parameters or deployment memory.

| Official checkpoint | Architecture and parameter claim | Native context | Deployment evidence |
| --- | --- | --- | --- |
| [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | Dense hybrid DeltaNet/attention; nominal LM 2B; 24 layers | 262,144 | Official Ollama default is Q8_0, not Q4; advertised LM 1.88B plus vision 0.331B |
| [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | Dense hybrid; nominal LM 4B; 32 layers | 262,144 | [Ollama Q4_K_M](https://ollama.com/library/qwen3.5:4b-q4_K_M): LM 4.21B plus vision 0.334B; approximately 3.3 GB package |
| [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | Dense hybrid; nominal LM 9B; 32 layers | 262,144 | [Ollama Q4_K_M](https://ollama.com/library/qwen3.5:9b-q4_K_M): LM 8.95B plus vision 0.456B; approximately 6.6 GB package |
| [Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B) | Dense hybrid; nominal LM 27B; 64 layers | 262,144 | [Ollama Q4_K_M](https://ollama.com/library/qwen3.5:27b-q4_K_M): LM 26.9B plus vision 0.461B; approximately 17 GB package; existing resident provenance must be attested separately |
| [Ministral-3-3B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512) | Dense; 3.4B LM plus 0.4B vision | 256K | Official FP8 checkpoint; [Ollama](https://ollama.com/library/ministral-3) approximately 3.0 GB package |
| [Ministral-3-8B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512) | Dense; 8.4B LM plus 0.4B vision | 256K | Official FP8 checkpoint; Ollama approximately 6.0 GB package |
| [Ministral-3-14B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512) | Dense; 13.5B LM plus 0.4B vision | 256K | Official FP8 checkpoint; Ollama approximately 9.1 GB package |
| [Gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) | Dense with per-layer embeddings; 4.5B effective, 8B embeddings-inclusive | 128K | [Official model card](https://ai.google.dev/gemma/docs/core/model_card_4); [Ollama E4B](https://ollama.com/library/gemma4:e4b) Q4_K_M package approximately 6.6 GB |
| [Gemma-4-12B-it](https://huggingface.co/google/gemma-4-12B-it) | Dense unified multimodal, 11.95B | 256K | Official model card; [Ollama 12B](https://ollama.com/library/gemma4:12b) Q4_K_M package approximately 8.0 GB |
| [GPT-OSS-20B](https://huggingface.co/openai/gpt-oss-20b) | MoE; 20.9B total, 3.6B active | 128K | Native MXFP4; [Ollama 20B](https://ollama.com/library/gpt-oss:20b) approximately 14 GB; [official model card](https://deploymentsafety.openai.com/gpt-oss) gives a 16 GB memory deployment claim |

Package sizes are official listing estimates, not measured VRAM. Exact downloaded manifest digests, blob hashes, quantization, projector/draft components, template, parser, and resident context belong in deployment evidence. Dense models have no expert-routing active-parameter reduction; an exact per-token active count is not inferred from marketing names. Gemma E4B is not a 4B-total model, and GPT-OSS needs all expert weights resident for normal GPU inference.

## Native tool protocol and SDK integration

Qwen's model cards document `qwen3_coder` tool parsing for vLLM/SGLang and `qwen3` reasoning parsing. The official [9B template](https://huggingface.co/Qwen/Qwen3.5-9B/resolve/main/chat_template.jinja) uses its native function/parameter representation. The 4B, 9B, and 27B checkpoints default to thinking; 2B defaults to nonthinking. The experimental configuration disables thinking explicitly. In [Ollama 0.34.0 OpenAI conversion](https://raw.githubusercontent.com/ollama/ollama/v0.34.0/openai/openai.go), Chat Completions `reasoning_effort: "none"` maps to native `think: false`; an unsupported extra `think` field on Chat Completions is insufficient. Context preflight must render the corresponding native nonthinking request.

Ministral Instruct has native function calling and JSON output. Its official card recommends vLLM >= 0.12.0, `mistral_common >= 1.8.6`, and `--tokenizer_mode mistral --config_format mistral --load_format mistral --enable-auto-tool-choice --tool-call-parser mistral`. The Ollama listing requires at least 0.13.1. This experiment uses its nonreasoning Instruct variant without adding a reasoning-effort field when unsupported.

Gemma 4 has native system and tool support with its own special-token call/response representation. Use the official template and serving parser, not a Qwen template; see [official function calling documentation](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4). GPT-OSS requires Harmony, including tool channels and configurable reasoning effort; see the [official repository](https://github.com/openai/gpt-oss). These protocol differences are deployment factors, not parameter-scale effects.

OpenAI-compatible endpoints permit the existing persistent native SDK runtime to remain in use. They do not establish actual schema reliability: original function calls still pass strict JSON Schema validation before execution. No invalid-call repair, benchmark-specific prompting, or tool-vocabulary changes are authorized.

## Frozen finite shortlist and hardware policy

The four candidates are **Qwen3.5 4B, 9B, 27B, and Ministral 3 3B Instruct**. This covers a same-family size sequence and one small cross-family comparison. Selection precedes benchmark scores. The finite cap is four candidates; no replacement downloads, parameter search, or score-dependent reruns are allowed.

The hardware inventory reported 13,542 MiB spare on strong GPU1 at selection time. New 4B, 9B, and Ministral weights use a separate Planner endpoint/store and load one Manager at a time; actual loading plus 32K context/runtime headroom must be checked. The 27B candidate reuses the existing GPU0 resident service only after matching its actual manifest/blob/template provenance. It shares GPU resources with Executor; contention and model-service work must be recorded. Existing Executor processes, tags, contexts, and weights must not be overwritten or unloaded. Orin 32/64 GB feasibility depends on measured unified-memory headroom and backend support; nominal node RAM alone establishes no admission.

All selected Managers use a 32,768-token effective context, 2,048-token output cap, and nonthinking mode. Fail-closed preflight reserves output and counts the fully rendered template/tools/history; at most 30,720 input tokens fit before any stricter backend limit. Specialist, Verifier, fixed Skills, semantic prompts, physical pool/Scheduler, benchmark, and evaluator remain frozen. Only context integrity, safety, or budget-boundary failures block subsequent benchmark execution. Schema errors, model errors, wrong answers, and legal budget exhaustion remain evaluation observations.

Ministral 8B/14B, Gemma E4B/12B, GPT-OSS 20B, and Qwen 2B remain surveyed but are not deployed in this finite round. Their exclusion reflects the four-candidate cap, available independent memory, and execution time; it is not a negative competence finding. This round cannot characterize MoE/reasoning scaling or establish a universal parameter threshold. Full GPU prices remain unknown unless an actual price source is supplied.
