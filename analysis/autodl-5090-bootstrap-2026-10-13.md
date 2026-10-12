# AutoDL dual-RTX-5090 environment bootstrap (2026-10-13)

The user-provided AutoDL instance in mainland China was prepared for future LLM-native work. This is a separate machine and workspace; the paused Skill Granularity Pilot v2 was not resumed or migrated. No model was downloaded or served, and no evaluation cell was run here.

## Hardware and installed stack

| Item | Observed state |
| --- | --- |
| OS | Ubuntu 22.04.5 LTS, x86-64 container |
| GPUs | 2 × NVIDIA GeForce RTX 5090, 32,607 MiB each, compute capability 12.0 |
| Driver | NVIDIA 595.71.05 |
| Memory | 754 GiB total; 630–631 GiB available during inventory |
| System / local data / shared file storage | 30 GiB / 150 GiB / 200 GiB |
| Base Python and CUDA toolkit | Python 3.12.3 in `/root/miniconda3`; CUDA toolkit 12.8 |
| Base PyTorch | `2.8.0+cu128`; both GPUs returned the expected result from a small CUDA tensor operation |

PyTorch 2.7 introduced official Blackwell support with CUDA 12.8 wheels; the installed 2.8.0+cu128 build was additionally verified on both GPUs. [PyTorch release note](https://pytorch.org/blog/pytorch-2-7/)

## Prepared paths

| Purpose | Path |
| --- | --- |
| Tracked source snapshot from branch commit `2d622c5` | `/root/autodl-tmp/xiaoming/infra-joint-planner/source` |
| Isolated project environment, inheriting base PyTorch | `/root/autodl-tmp/xiaoming/infra-joint-planner/.venv` |
| Environment variables and `PATH` setup | `/root/autodl-tmp/xiaoming/infra-joint-planner/env.sh` |
| Package and future model caches | `/root/autodl-tmp/xiaoming/cache/{pip,huggingface,modelscope}` |
| Source archive copy on shared file storage | `/root/autodl-fs/xiaoming/infra-joint-planner-2d622c5.tar.gz` |

The source archive SHA256 is `62e735418027653857f50ad93c927fb2375c476aa345ee075546b0b922da9ff9`; the local data disk and shared-file-storage copies matched. Source was transferred as a tracked-files archive, without local credentials, raw traces, `.git`, or virtual environments. SSH public-key login was configured; no password was copied into the repository or the prepared project tree.

The environment installed the project's `agents` and `dev` extras from the Tsinghua PyPI mirror. `pip check` reported no broken requirements, `infra_joint`, `agents`, and `torch` imported, and `tests/test_config_cli.py` plus `tests/test_heterogeneous_preflight_cli.py` passed (20 tests). A small CUDA tensor operation succeeded on each 5090 from this virtual environment. No GPU process remained after validation. This is a ready-to-use setup, **not** a frozen experiment environment: the installation resolved the current `pyproject.toml` ranges rather than replaying `uv.lock`.

To enter the prepared environment after login:

```bash
source /root/autodl-tmp/xiaoming/infra-joint-planner/env.sh
cd /root/autodl-tmp/xiaoming/infra-joint-planner/source
```

## Mainland network observations

Short HTTPS probes from this instance found ModelScope reachable quickly, the Tsinghua PyPI mirror reachable, and the PyTorch CUDA-wheel index reachable. Hugging Face and `raw.githubusercontent.com` timed out; the GitHub front page responded slowly. Official PyPI responded but was slow in this probe. The package install used the [Tsinghua mirror](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/) as a per-command index; no global package-manager configuration was changed. Model downloads should be planned against the actual model ID and its available domestic source before use.

The 150 GiB data disk provides fast working storage, while `/root/autodl-fs` is shared storage with better persistence characteristics and lower I/O performance according to [AutoDL's storage documentation](https://www.autodl.com/docs/fs/). Only the small tracked source archive was copied to shared storage; no large weights were downloaded.
