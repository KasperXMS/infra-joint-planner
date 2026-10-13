#!/usr/bin/env bash
# Resume the preregistered sequence after the already-running H1 batch completes.
set -euo pipefail
umask 077

root=/home/super/xiaoming/harness-v2-baseline-requalification/run-001
app="$root/app"
key=/home/super/xiaoming/resource_blind_live_validation_v1/api_key.txt

while [[ ! -f "$root/stage1-attempt-002/complete.json" ]]; do
  [[ ! -f "$root/STOP" ]] || exit 4
  sleep 5
done

cd "$app"
export PYTHONPATH=src:scripts
.venv/bin/python scripts/harness_v2_analyze.py \
  --output "$root/stage1-boundary-summary.json"
.venv/bin/python - "$root/stage1-boundary-summary.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
rows = [row for row in data["cells"] if row["stage"] == "stage1"]
if len(rows) != 18 or data["incomplete_claims"]:
    raise SystemExit("Stage 1 batch is incomplete")
for row in rows:
    cleanup = row["worker_cleanup"] or {}
    if row["system_problems"] or row["context_integrity_failures"]:
        raise SystemExit("Stage 1 systemic integrity failure")
    if not cleanup.get("drained") or not cleanup.get("verified_exited") or cleanup.get("error_count"):
        raise SystemExit("Stage 1 Worker cleanup failure")
PY

.venv/bin/python scripts/harness_v2_bridge_feasibility.py --api-key-file "$key"
.venv/bin/python scripts/harness_v2_stage2.py --api-key-file "$key"
.venv/bin/python scripts/harness_v2_analyze.py \
  --output "$root/final-sanitized-analysis.json"
