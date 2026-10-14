#!/usr/bin/env bash
set -euo pipefail

# Only public study input and an output directory cross this mount boundary.
# Call as: run_isolated_hypothesis_controller_v1.sh ROOT RUN_ID SCRIPT [ARGS...]
root="$1"
run_id="$2"
script="$3"
shift 3
[[ -d "$root/study" && -d "$root/out" ]] || exit 2
[[ "$run_id" =~ ^[A-Za-z0-9-]+$ ]] || exit 2
[[ "$script" =~ ^[A-Za-z0-9_.-]+\.py$ ]] || exit 2
[[ -f "$root/study/$script" ]] || exit 2

exec bwrap \
  --unshare-user --unshare-pid --unshare-ipc --unshare-uts \
  --new-session --die-with-parent --clearenv \
  --setenv PATH /usr/bin:/bin --setenv STUDY_RUN_ID "$run_id" \
  --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind "$root/study" /study --bind "$root/out" /out \
  --dir /tmp --proc /proc --dev /dev --chdir /study \
  /usr/bin/python3 "$script" "$@"
