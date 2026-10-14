#!/usr/bin/env bash
set -euo pipefail

root="$1"
config="$2"
python_bin="$3"
export PYTHONPATH="$root/src"
export INFRA_EVAL_SOURCE_TOKEN="$(cat "$root/source-token")"
exec "$python_bin" -m infra_joint.cli worker --config "$config"
