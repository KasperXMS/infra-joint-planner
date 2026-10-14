#!/usr/bin/env bash
set -euo pipefail

root="$1"
config_name="$2"
python_bin="$3"
if [[ -e "$root/worker.pid" ]]; then
    echo "worker.pid already exists; refusing to start another study worker" >&2
    exit 1
fi
nohup bash "$root/launch_evaluation_source_worker_v01.sh" \
    "$root" "$root/$config_name" "$python_bin" \
    > "$root/worker.log" 2>&1 < /dev/null &
echo "$!" > "$root/worker.pid"
