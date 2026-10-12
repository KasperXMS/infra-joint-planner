#!/usr/bin/env bash
set -euo pipefail
RESEARCH_ROOT=/root/autodl-tmp/xiaoming/planning-skills-research-v1/run-001
export HF_HOME="$RESEARCH_ROOT/cache/huggingface"
export MODELSCOPE_CACHE="$RESEARCH_ROOT/cache/modelscope"
export MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS=8
export PIP_CACHE_DIR="$RESEARCH_ROOT/cache/pip"
export OMP_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=false
/root/miniconda3/bin/python -m venv --system-site-packages "$RESEARCH_ROOT/.venv"
"$RESEARCH_ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ 'transformers>=5.2,<6' 'accelerate>=1,<2' 'modelscope>=1,<2'
"$RESEARCH_ROOT/.venv/bin/python" -m pip freeze > "$RESEARCH_ROOT/environment-freeze.txt"
exec "$RESEARCH_ROOT/.venv/bin/python" "$RESEARCH_ROOT/code/prepare_models.py" --root "$RESEARCH_ROOT"
