# RTX PRO 6000 environment ready — 2026-10-13

Preparation and verification completed on **2026-10-13 at 11:40 HKT**. This continues the [initial new-instance inventory](autodl-rtx-pro-6000-2026-10-13.md). It prepares dependencies and tools, without restarting any experiment or downloading model checkpoints.

Remote workspace:

```text
/root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013
```

Two separate environments avoid replacing either the base CUDA stack or the project's locked dependencies:

| Environment | Purpose | Selected installed versions |
| --- | --- | --- |
| `venvs/inference` | Direct PyTorch/Transformers inference and research utilities; inherits the existing GPU PyTorch base | Python 3.12.3, torch 2.8.0+cu128, torchvision 0.23.0+cu128, Transformers 5.19.0, Accelerate 1.15.0, ModelScope 1.40.2, Safetensors 0.8.0, Tokenizers 0.23.3 |
| `venvs/project` | Installed editable `infra-joint-planner`, runtime, Agents SDK and development tools; independent site-packages | OpenAI 2.54.0, openai-agents 0.20.0, LangGraph 1.2.11, FastAPI 0.141.1, pytest 9.1.1, Ruff 0.16.8, Pyright 1.1.414, uv 0.12.7 |

Project runtime/development versions and artifact hashes were exported from the unchanged `uv.lock` with the `agents` and `dev` extras. Pip installed that export with `--require-hashes`; the project itself was installed editable with `--no-deps`. The inference environment uses the existing [14 selected requirements](../../research/planning_skills_v1/requirements-inference.txt) and [observed constraints](../../research/planning_skills_v1/constraints-observed.txt). It inherits base packages; this is not a claim that all base package bytes match the old instance. Full observed versions are recorded separately for [project](autodl-rtx-pro-6000-project-packages-2026-10-13.json) and [inference](autodl-rtx-pro-6000-inference-packages-2026-10-13.json).

TUNA served Python dependencies and Ubuntu packages. Global pip/apt sources and base Python packages were not changed. FFmpeg/ffprobe, tmux and iproute2 (`ss`) are installed as system tools; git, curl, wget, rsync, GCC and make were already present. Pyright's Node runtime is supplied locally by `nodejs-wheel-binaries==24.19.0`, avoiding a later nodeenv download. The extra tool wheels and hashes are retained in the [setup receipt](autodl-rtx-pro-6000-ready-2026-10-13.json) and [tool requirements](autodl-rtx-pro-6000-dev-tools-2026-10-13.txt). These development tools do not change the inference backend.

## Use the environments

```bash
source /root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/activate-inference.sh
# python now selects the inference environment; Hugging Face inference is offline by default.
```

```bash
source /root/autodl-tmp/infra-joint-planner-rtx6000/setup-20261013/activate-project.sh
infra-joint --help
```

`repo/` is a source snapshot, not a remote Git clone. Its base revision is `a92d52b7efe8d502f84453ba83a411c269757bf2`, with the two new preparation/check scripts additionally identified by SHA in `source-manifest.json`. All **798 source files** were checked after transfer. The source bundle SHA is `ec30b3ed017fe8bbbea65610936707949b8eb9989b6ec4704df25b816d789adf`. Credentials, local device-info and historical raw traces were not transferred. Model/cache/artifact/log directories are separate from the source.

The inference activation sets task-local HF/ModelScope caches, eight CPU threads, and `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`. A later explicitly authorized model materialization step must unset offline flags as appropriate, use the official repository and verify actual checkpoint bytes. No model is available yet; neither an Ollama nor a vLLM service has been installed or launched. Missing optional `causal_conv1d`/FLA kernels do not prevent the verified PyTorch path; no fast-kernel compilation or backend search was performed.

## Checks actually completed

- Both environments passed `pip check`; project and SDK imports and `infra-joint --help` passed.
- On the real GPU: CUDA reduction, BF16 matrix multiplication and SDPA passed. The Qwen3.5 model class imports without downloading/loading a checkpoint.
- All **6 existing microbenchmark unit tests** and **27 existing Worker/Workflow contract tests** passed. This is focused environment verification, not the complete repository test suite or a model benchmark.
- FFmpeg encoded a 32×32 synthetic video and decoded a frame; ffprobe and Pillow confirmed dimensions.
- uv, Ruff, Pyright and the bundled Node runtime report their versions successfully. No type-check or lint result for the entire historical repository is claimed.
- No CUDA compute applications remained at final verification. Zero model downloads, model services, experiment cells or cloud API calls were initiated by preparation.

The [readiness receipt](autodl-rtx-pro-6000-ready-2026-10-13.json) records actual checks, package versions and config hashes. Logs and the synthetic video smoke artifacts stay in the task workspace. The old research and paused pilot remain unchanged. No old whole-instance shutdown guard was enabled on this newly prepared instance; preparation subprocesses had bounded timeouts, and no persistent setup service remains necessary. The new instance lease price is still unknown; the previous CNY6.06/h rate is not reused.

## Reproduce preparation in a new task directory

Copy the matching source snapshot into `NEW_ROOT/repo`, and export the hashed project requirements alongside it:

```bash
# Run in the matching source checkout, using uv 0.12.7.
uv export --frozen --no-emit-project --extra agents --extra dev \
  --format requirements-txt --output-file NEW_ROOT/project-requirements.lock.txt
/root/miniconda3/bin/python NEW_ROOT/repo/scripts/bootstrap_autodl_rtx6000.py --root NEW_ROOT
```

`NEW_ROOT` must be a dedicated path under `/root/autodl-tmp`. The bootstrap refuses to silently replace a different base PyTorch stack and does not reinstall an already passed setup. It prepares the Python environments and checks only; install missing system tools from trusted Ubuntu sources separately. On this run a task-local TUNA Ubuntu jammy sources file and apt list cache supplied `ffmpeg`, `tmux`, and `iproute2`, without rewriting global source files. Optional development tool wheels can be installed from the hashed tool requirements after the primary project installation. A new machine/run must retain its own receipts, GPU allocation and actual versions; this preparation is not independent model-capability validation.
