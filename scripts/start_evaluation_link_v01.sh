#!/usr/bin/env bash
set -euo pipefail

root="$1"
port="$2"
bandwidth_mbps="$3"
added_rtt_ms="$4"
if [[ -e "$root/link-$port.pid" ]]; then
    echo "link PID already exists; refusing to start another study proxy" >&2
    exit 1
fi
nohup "$root/.venv/bin/python" "$root/evaluation_source_link_v01.py" \
    --port "$port" --bandwidth-mbps "$bandwidth_mbps" \
    --added-rtt-ms "$added_rtt_ms" \
    > "$root/link-$port.log" 2>&1 < /dev/null &
echo "$!" > "$root/link-$port.pid"
