# Same-weight vLLM replacement assessment (2026-10-14)

The dual RTX 4090 workstation currently has two resident, study-shared Ollama 0.34.0 services:

| GPU | Ollama endpoint | Exact resident tag | Original weight format | Context | Observed VRAM |
|---|---|---|---|---:|---:|
| 0 | `127.0.0.1:11436` | `qwen35-27b-resident-32k-v1:latest` | Qwen3.5 27B Q4_K_M GGUF, blob `sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`, separate projector | 32,768 | ~20.1 GiB |
| 1 | `127.0.0.1:11437` | `qwen-vl8b-resident-32k-v1:latest` | Qwen3-VL 8B Q4_K_M GGUF, blob `sha256-1329cd5ab37e5ef6faef37cd8ff8660ffc96ed5b47b34fddf8eb0912e6c82466` | 32,768 | ~10.9 GiB |

The Ollama `/api/ps` and `/api/tags` responses established the live names, family, quantization and effective context. The `llama-server` process arguments established the weight blob and projector. These are original resident models, not the Qwen2.5 checkpoints present in the workstation's Hugging Face cache.

[vLLM's GGUF documentation](https://docs.vllm.ai/en/latest/features/quantization/gguf/) calls GGUF support experimental and requires the separate [vLLM GGUF plugin](https://github.com/vllm-project/vllm-gguf-plugin). The plugin has a generation-tested Qwen3.5 vision-language Q4_K_M example, but does not list Qwen3-VL as tested. [Qwen-VL GGUF support is still an open plugin pull request](https://github.com/vllm-project/vllm-gguf-plugin/pull/140). General [vLLM Qwen3-VL architecture support](https://docs.vllm.ai/en/latest/models/supported_models/) does not establish that this specific original GGUF plus projector loads correctly. The 27B GGUF path may be feasible, but the local-file route also had a documented [qwen35 metadata loading failure](https://github.com/vllm-project/vllm/issues/36456); compatibility of this exact blob is unverified.

Therefore a **complete same-weight replacement of both resident Ollama services is not qualified**. The services were not stopped. A study-owned exploratory vLLM 0.28.0 environment and two attempted *different-model* startups were stopped; neither served a request and neither was used for task results. Their logs remain on the workstation. Before any future cutover, build/install the GGUF plugin, prove both exact original blobs and multimodal projectors on spare capacity or a maintenance window, verify tokenizer/context/tool behavior, then switch endpoints with a rollback plan. Downloading a BF16 or AWQ checkpoint would change weights or quantization and require a new experiment condition.

For the H1/H2 feasibility study, keep the resident 27B Ollama backend fixed across all cells. This avoids a serving change inside the infrastructure comparison and still tests the preregistered logical workflow and network hypotheses.
