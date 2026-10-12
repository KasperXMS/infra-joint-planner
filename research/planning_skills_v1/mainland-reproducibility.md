# Mainland deployment and reproducibility

The actual research instance is in mainland China. Preparation used the TUNA Python package index and official Qwen repositories on ModelScope, rather than making inference depend on reaching Hugging Face. Download transport, not model contents, was adjusted once: the installed ModelScope SDK's supported range-worker setting was raised to eight while preserving existing partial bytes. Both checkpoints completed and were hashed before evaluation.

## Actual environment

- Ubuntu 22.04.5, Python 3.12.3, PyTorch 2.8.0+cu128, Transformers 5.19.0.
- Two RTX 5090 GPUs, 32,607 MiB reported per GPU; driver 595.71.05.
- Container memory limit 180 GiB and CPU quota equivalent to 50 cores. Host `free` output is not the allocation limit.
- Qwen3.5-4B and Qwen3.5-9B official BF16 safetensors, direct Transformers/SDPA, no quantization. Their actual config/tokenizer/weight SHA256 records identify the bytes used. A mutable ModelScope `master` path is not a pinned upstream commit.
- `causal_conv1d` and `flash-linear-attention` were absent. The correct reference PyTorch fallbacks were retained, and measured work is specific to that implementation. No backend tuning occurred within a comparison.

## Access boundaries

Inference uses `local_files_only=True`, `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. No remote tokenizer/model fetch is necessary after preparation. No cloud API is part of these synthetic evaluations. Git operations and literature retrieval can occur from the local workspace; the instance needs only the prepared source, task/config files, dependencies and checkpoint files. This avoids assuming GitHub/arXiv connectivity from the instance itself.

Temporary download logs may contain signed CDN URLs and remain on the experiment machine. Public artifacts include sanitized metadata, file hashes, configuration, source, synthetic result tables and trace indices. SSH credentials, API keys and the local device-info file are excluded.

Do not silently substitute community repacks, quantization or a different checkpoint when a resource is inaccessible. Keep the official repository and verify actual bytes; record a transport/source change separately from the experimental treatment. The two models' identity records, not merely their display names, define this study's model boundary.

## Run separation and safety

This research occupies its own branch and namespace. Historical Skill Granularity v2 stays paused. No InfraMAS deployment, Physical Scheduler, external process or historical result is changed. One worker owns each GPU. Exact-token context preflight rejects oversized requests without truncation; schema rejection has no tool side effects. Per-task/request/turn quotas and a cooperative STOP mechanism coexist with an independent 20-hour whole-instance guard.

Resource records use the active goal's start time, including literature/setup/downloads and invalidated engineering work. The known rental estimate is CNY at 6.06/hour for the instance. Local GPU USD remains unknown; it is never entered as zero. Shared-storage checkpoints preserve raw evidence, while the hard guard also stops the owned instance's billing at its resource limit.
