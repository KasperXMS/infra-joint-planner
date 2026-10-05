# Resident model pool calibration v1

2026-10-05, Asia/Hong_Kong. **Calibration is complete; the new formal matrix has
not started (0/168).** This is an environment readiness result, not a benchmark
quality result. The user-directed restart retains the predecessor42 admitted
cells/two separate implementation-confounded attempts without pooling them into
the new environment.

## Actual pool and request contract

Three weight artifacts, two architecture families, five instances/four Workers:
A4 Qwen3-VL4B Instruct, A5 Qwen3-VL8B Instruct, A28 qwen35 27.3B, 4090GPU0 the
same27.3B, 4090GPU1 the same8B Instruct. All Q4_K_M. The historical tag
`qwen3.8-27b-v1` is a local alias, not evidence of an official release name.
Source weights, quantization, templates, parser/renderer and source parameters
remain identical. The derived tags change only num_ctx to32768; original tags
are not replaced. Earlier full recipient blob hashes remain bound by the
preparation manifest.

Installed Ollama0.34.0; one dedicated server/store per instance, q8_0 KV cache,
flash attention, parallel1, max-loaded1, infinite keep-alive. The two4090servers
disable Vulkan discovery and use separate actual GPU UUIDs. Jetsons use CUDA
on their integrated Orin GPUs. Both4090runner PCI addresses/GPU memory ownership
match their intended UUIDs. No CPU/software-renderer inference is admitted.
The workstation also has two pre-existing GPUStack `llama-box-rpc-server`
processes (PIDs3763/3764), each allocating386MiB on its GPU. These are not desktop
processes or experiment model instances. They are retained, separately recorded
in pre/post compute-process attestations, and not counted as part of the five
models. Point-in-time GPU utilization is unavailable (`-`), not assumed zero.

Requests use the **unchanged frozen Worker model backend/preflight source**
SHA-256 `3bf978e665f8703b6f30754fffdba5b2527ba85aae48a9a3f75a5184c84fc1d5`,
OpenAI-compatible API, reasoning_effort=none,
no request-level temperature override, output reservation2048, timeout1200s,
automatic retries0. Import paths are explicitly bound to the execution-fa19e0b
source on each node; the4090venv's historical default editable import is not
used. Source Modelfile parameters and actual sampler logs are retained separately;
absence of a request override is not a claim about effective sampling defaults.

## Synthetic checks

Every instance executes once each: short text/setup load,30,019-byte text
artifact,1920×1080 green image,1280×1440 red image,2048×2048 blue boundary image.
All25 admitted calibration requests have nonempty expected marker/color output,
finish_reason=stop, HTTP200 and correlated slot releases with truncated=0.
No benchmark task, private evaluator/gold or cloud Planner call is used.
First text loading and first vision initialization are preparation, not benchmark
work. No guessed startup constant is subtracted.

| Instance | Text setup response, s | Long-text service, s | Actual long-text input tokens | Frame/sheet service, s | Boundary service |
|---|---:|---:|---:|---|---|
| A4 /4B Instruct |113.977|74.833|21220|48.306 /10.439|PASS|
| A5 /8B Instruct |124.665|112.424|21220|56.292 /28.143|PASS|
| A28 /27.3B |29.619|375.824|21225|60.117 /51.366|PASS|
| 4090GPU0 /27.3B |4.616|8.386|21225|1.920 /1.307|PASS|
| 4090GPU1 /8B Instruct |17.671|3.510|21220|7.740 /1.614|PASS|

n=1/probe; image-frame service includes first vision initialization. These are
payload-specific calibration observations, not general model-speed rankings or
minimum-support-three empirical profiles. TTFT/peak memory are unknown in the
existing nonstreaming backend; point-in-time memory snapshots are retained.
Measured actual input reaches21225tokens, **not32768tokens**. Server state/slot
configuration is32768; the conservative UTF-8-byte preflight envelope is tested.
Do not claim an actual32K-input-token stress test from a30KB artifact.

## Required visual-envelope correction before the new block

The ordinary frame/sheet probes alone do **not** validate a universal2048-token
image bound. All five actual runners report patch_size16, merge2,
image_max_pixels4194304: the runtime visual ceiling is4096tokens/image.
The2048×2048 probe actually consumes4096visual tokens,4125total for Qwen3-VL
or4129total for qwen35, below the new preflight estimate4165. The five boundary
requests are included in the25total above, not25extra requests.

New deployment/Worker/static contract must therefore use:
`context32768 / output2048 / image_token_cost4096`, identically for every method.
No image resizing, tool semantic change, prompt tuning, quality-tier invention
or runtime truncation is introduced. Native model image preprocessing is recorded
as model behavior. The old2048-image contract/evidence remains historical.

The existing capability builder merges identical semantic signatures into one
anonymous class; it does not advertise three quality tiers from parameter sizes.
Model/deployment/device identity stays private. Measured27B samples are never
reassigned to4B/8B. Unmatched/insufficient service estimates remain unknown.

## Preserved preparation failures and exact evidence

Start001 failed an overstrict nonparameter-layer identity check. Start002 then
failed show.details identity: `/api/create` changes `parent_model` provenance.
The independent identity-audit003 proves only from/rootfs/parent provenance
changes; content, unknown execution fields and exact parent identity remain
strictly checked by regression tests. Both attempts were stopped before inference.

Start003 succeeded, but first4090calibration selected Vulkan: the8B instance
used the wrong physical card and the27B instance selected llvmpipe. Only the two
new owned4090servers were stopped; their original logs/partial requests remain
under `calibration/gpu-binding-confound-001`. Those timings are **excluded**, not
corrected by subtraction. Start004 disables Vulkan and repeats only the affected
4090calibration in synthetic002. Jetson synthetic001 is not repeated. This is
pre-experiment environment repair, not a benchmark retry/replacement.

4090 pool root: `/home/super/xiaoming/resident-model-pool-v1`.
Jetson pool roots: `/mnt/ssd/resident-model-pool-v1`.
Core receipts live at `calibration/core-audit-001/receipt.json`; boundary receipts
at `calibration/boundary-audit-001/receipt.json`. All calibration bodies and raw
server logs remain remote; no model/dataset payload transits the development PC.

| Node | Core audit SHA-256 | Boundary audit SHA-256 |
|---|---|---|
| A4 |832d16eb00a8c6b6e125bba390989348bf2b436bb39b2d6e3a8664f581c0a402|3b42dbb6bf8d5b18d344e0a29c16d2c560924828e830169fd706441ac363bb1c|
| A5 |ca702ed32632b27f87bf4c6a2807dfc4a22500ec94dddfb634897c4071b22f01|a62bde3cdd8e286d24eccc61f5ac4b6398ded076e5b65ee33af4181bb68e43cc|
| A28 |339653a7c05c6fdace3ec0e9a84f324adf4143d4b2bbc52cf2c4ac83d730774c|362b70d92bccc1acd6f991fab844f52b33ab7ad7ffc6dbefa2a133bf924873c8|
| 4090 |fc51d334454408a2b92e1f27ab2745cacaa237767e6973a9d5f25af54a5836e9|b3c477d86b8aa571f0bd9dd12c613ae0adb9384e59a8903659b6f6bbf53dd186|

Controller receipts are under the new experiment root's `provisioning/`;
calibration001 preserves the interrupted4090dispatch,002 the corrected4090,
003 the all-node boundary probe. Historical journal hash remains separately
bound by block-cutover001. No tc shaping/benchmark artifacts/Worker benchmark
processes were needed for these calibration checks.

## Remaining activation gates

[New physical configuration](../configs/experiments/resident-diverse-environment-v1.yaml)
is **not yet a runnable frozen block**: formal app/harness/source/profile/pricing/
balanced schedule freezes are still required. Fresh-Worker `/state` agreement
has passed: four isolated empty stores, all12 operators and all5 deployments,
including their exact operator schemas and32768/2048/4096 contracts. The four
readiness Worker processes were stopped and their exit verified; the five Ollama
instances remain resident. No readiness model/tool/benchmark calls were made.
Receipts are under the new root's `readiness/worker-surface-001` (including the
shutdown verification). The readiness receipt preserves its original raw
serialization hash `8c40d1aa11e8364f6609798edb96fddccd88af39c4f5701961c8d83ebba14896`.
The formal harness uses the existing order-normalized static-capability hash:
`1064a5e3446a1dbf0c99360751cc5e9604efa30cad9c548b650ac13d6963a4c0`.
This normalization changes no operator schema or model-class fields.
Per-cell pre/post residency must preserve the calibrated CUDA ownership and
catch eviction/reload. Original18tasks, all7methods, twoPlanners/fixedBlindVerifier,
operators, scheduler, instructions, budgets, initial placement and networks stay
unchanged. The new block still has zero benchmark cells.

Regression for this readiness snapshot:984 pytest pass in31.23s; Ruff,
strictPyright and diff check pass. The new environment/privacy regression proves
three physical artifacts/five instances reduce to one anonymous semantic class,
with no invented quality tiers or physical identity fields. No core
logical/physical runtime source is changed. The experiment protocol's cumulative
budget guard now explicitly counts the42 retained predecessor samples: four
complete PhaseII methods would total402, five450 and must be rejected. This does
not prune any of the seven PhaseI methods.

References: actual0.34.0 [Vulkan configuration](https://github.com/ollama/ollama/blob/v0.34.0/envconfig/config.go),
[derived creation](https://docs.ollama.com/api/create),
[keep-alive and concurrency](https://docs.ollama.com/faq).
