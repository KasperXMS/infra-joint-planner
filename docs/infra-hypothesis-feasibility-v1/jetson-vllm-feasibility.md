# Jetson vLLM feasibility (read-only inventory, 2026-10-14)

All three Jetsons are AArch64 AGX Orin on L4T `R39.2.1`, corresponding to JetPack 7.2.1 according to [NVIDIA's release guide](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/setup_bsp.html). No vLLM executable or system Python `torch` installation was found on these hosts. Their currently resident Ollama models and other shared services were left untouched. Memory is shared CPU/GPU memory, so `free -h` available is not dedicated GPU headroom; Jetson `nvidia-smi` does not report GPU memory usage in the workstation format.

| Host | RAM total / available | SSD free | Largest resident model process RSS | Immediate vLLM assessment |
|---|---:|---:|---:|---|
| A4 `192.168.0.104` | 29 / 10 GiB | 18 GiB | ~17 GiB | No safe concurrent 7B-class vLLM deployment; disk is also tight. |
| A5 `192.168.0.105` | 29 / 8 GiB | 46 GiB | ~19 GiB | No safe concurrent 7B-class deployment. It now owns source-b for this study, so serving experiments would introduce resource interference. |
| A28 `192.168.0.128` | 61 / 27 GiB | 88 GiB | ~31 GiB | Best candidate for a separately scheduled compact model trial; current residual memory is still shared and insufficient evidence for a 32K-context 27B vLLM service. |

vLLM upstream [lists Orin SM 8.7 in its AArch64 build targets](https://github.com/vllm-project/vllm/blob/main/.buildkite/release-pipeline.yaml), so GPU architecture is not categorically excluded. However, its [CUDA installation guide](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/) describes nontrivial AArch64/CUDA builds, and a [vLLM 0.28.0 JetPack 7.2.1 Orin build issue](https://github.com/vllm-project/vllm/issues/53890) remains open. These are compatibility risks, not proof that deployment is impossible. A matching JetPack CUDA/PyTorch/vLLM wheel or controlled source build, followed by a real startup and 32K request test, is required before declaring any host usable.

For this H1/H2 study, do **not** add vLLM to the Jetsons: A4/A5 provide the protected source data path and A28 has a shared resident model. A parallel vLLM deployment would change source-local compute availability and potentially confound H2. The workstation's existing Qwen3.5 27B and Qwen3-VL 8B Ollama services remain active; the same-weight vLLM replacement assessment is recorded separately. A later Jetson-specific serving study should measure actual unified-memory pressure and model latency before making a placement decision.
