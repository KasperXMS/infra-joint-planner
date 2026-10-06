# Held-out offline projection: validation and actual first snapshot

This collector only projects original settled Phase II receipts. It cannot
initialize journals, run Agents, prune methods, repair outcomes or scan private
gold/supporting artifact bodies. Pending attempts are listed, never counted as
completed. Unicode JSONL uses physical newlines. Unknown work remains unknown;
original evaluator/result/admission files remain unchanged.

Source commit: `70d70c6`. Added only
`scripts/large_scale_resident_phase2_snapshot_v1.py` and its tests, outside atomic
execution004. It reuses existing settled-telemetry, graph and API-count helpers.
The actual gate, Phase I journal, 32-file control source closure, schedule and
execution hashes must match; original admission must match journal settlement.
Journal advancement rejects a stale collection, not the experimental cell.
New adjudication types require an independently reviewed collector revision.

Validation: 1706 pytest passes, 7 Windows platform skips, Ruff, strict project
and explicit script Pyright, and diff checks pass. Actual 4090 integration:
45 passes in 1.36 s. Test payload/body/gold-like sentinels do not appear in exported
telemetry, even with Unicode separators. Model/Worker/tc/Planner calls from this
validation and projection: zero.

Code-only archive SHA256:
`6b447bed21f87c3ebd2b76aa1f6779cf5a2c4d1a7ff02e88abcbb25e03ad86d3`.
Collector source SHA256:
`a5f88f5068829b22e1d88283ad6fe5dc94b98c8c43e336f06b016be4bbd3fad5`.
Remote isolated namespace: `audit-tools/resident-phase2-snapshot-control-001`.
Validation receipt SHA256:
`b7df7a3b7b0103ae35ddce39506b01ed1800babd3fadccdf7aafb612f3214b7f`.

The first Linux test invocation missed an existing rate-policy dependency in its
test-only import path and failed collection. Its log001 is preserved. Reusing
the owned controller's existing dependency path for the offline subprocess
resolved this; log002 passes. No code, controller environment, Agent source,
model, experiment configuration or cell changed. This was not a benchmark run.

Actual immutable metadata snapshots under the remote root's `analysis/`:

| Snapshot | SHA256 | Settled / pending |
| --- | --- | --- |
| resident-phase2-current-snapshot-001.json | `704125aec3b9d792936ef37d400949b91ba052d5aa8ca21d2940656eed0f22e3` | 2 / 1 |
| resident-phase2-current-snapshot-002.json | `0cb9a56a44ed0707482c237958a8ef9a760d2c27e85ab06a42ad01b54230bc9c` | 3 / 0 |

Snapshot002 captured 2026-10-06T18:58:26.060337Z, with zero confounded or excluded
attempts. Its 192-row coverage table explicitly leaves 189 unexecuted cells
without outcomes. This is an in-progress checkpoint, not a Phase II completion,
private semantic audit or final Q1–Q10 claim. No full trace/data/model/API bodies
were transferred through the development PC.
