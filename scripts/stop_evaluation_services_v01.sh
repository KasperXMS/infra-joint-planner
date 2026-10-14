#!/usr/bin/env bash
set -euo pipefail

root="$1"
for name in worker link-63105 link-63106; do
    pid_file="$root/$name.pid"
    if [[ ! -f "$pid_file" ]]; then
        continue
    fi
    pid="$(cat "$pid_file")"
    if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
        echo "invalid PID in $pid_file" >&2
        exit 1
    fi
    command_line="$(ps -p "$pid" -o args= || true)"
    if [[ -n "$command_line" ]]; then
        if [[ "$command_line" != *"$root"* ]]; then
            echo "PID $pid is not owned by this study; refusing to signal" >&2
            exit 1
        fi
        kill "$pid"
        echo "$name stopped PID $pid"
    else
        echo "$name already stopped PID $pid"
    fi
    rm -- "$pid_file"
done
