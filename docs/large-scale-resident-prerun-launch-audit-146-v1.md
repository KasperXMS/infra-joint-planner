# Resident pre-run launch failure146: no Agent execution, queue remains gated

2026-10-06. Queue019 attempted
`phase1-multihop_rag-2-2d3129ed85c03f62-p2-slow-B1`, attempt1,
reserved12:19:05.083454Z and stopped12:19:07.386524Z.
This is a system/harness confounder, not a valid Planner failure or score0.
145 prior nominal cells remain effectively admitted. No subsequent cell ran.

## Cause and preserved evidence

The new queue wrapper did not propagate the pinned archive variable
`INFRA_JOINT_CODE_REVISION`. This was a mistake in the continuation launch,
not an Ollama, Worker, Planner or provider outage. The unchanged atomic driver
calls `verify_freeze()` before `run_shaped()`; revision lookup failed there:

`code revision is unavailable; set INFRA_JOINT_CODE_REVISION for archive deploys`

Actual trace has exactly `run.start`, `run.failed`. Result reports
`attempt_prerun_failed`, RuntimeError, execution false, evaluation null. There
are no Worker starts, private/API records, attempt freeze or tc attestation.
Actual Manager/Verifier turns, physical actions and inferences are all0; no tc
shaping occurred. Missing setup/evaluation is not fabricated as successful or0.
The conservative original admission is `admission_unverifiable`/FileNotFoundError
because complete-run receipts do not exist. It and all seven original attempt
files remain preserved; no launch recovery or task repeat has been performed.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Original reservation SHA256: `1c23fdbf6b20c8a9b1cf82243de9d69619f72ccd9b9e320d4192cdc701a968b5`.
- Original settlement SHA256: `d39bae1563df47216d673994aa3a2f07cd22acc3d8f33427daf90c5e467b3b7f`.
- Admission canonical SHA256: `96d977ddfd2bfc7256537439838cec0631a9d9b4f45c87d1e7c8ab305e7c1b4c`.
- Immutable bounded proof `analysis/resident-source004-cell146-prerun-launch-audit-001.json`,
  SHA256 `0cb2d9b61b3914611a13f96cdf3470ab98d83aca019d11fc3465e134024f983c`.
- Current journal SHA256: `7cac8cfafe6951fe6a893dc473d0ce3b00a230ddf43e55142231d02469d260d5`.
- Queue019 exit receipt SHA256: `2f30fde88a16fca48c4422b2c492d44e4c42a33f038d7bbcfaad9f881ef42054`.

## Minimal launch repair prepared and independently checked

`large_scale_resident_launch_environment_v1.pinned_environment` reads the exact
immutable execution freeze and verifies all bound archive files before filling
a missing revision. An inherited conflicting/empty revision, malformed freeze,
escaped path or source drift is rejected, not silently corrected. Other inherited
environment settings and secrets are preserved, never printed. It does not edit
Agent instructions, Worker deployment, execution004, network, schedule or ledger.

Validation:

- Full pytest:1561passed109.19s, including15new launch regressions.
- Ruff and `git diff --check`:pass.
- Strict project Pyright using the actual `.venv` Python:0errors/0warnings.
  The initially unqualified invocation selected the wrong interpreter and reported
  dependency/stub errors; this was corrected by explicit `--pythonpath`, without
  source suppressions or dependency/model changes.
- Actual4090 Linux launch regressions:15passed0.03s.
- Actual read-only `verify_freeze()` under restored provenance passed, returning
  unchanged004 canonical `16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c`.
- That check used0Planner calls/0inferences/0Worker starts/0tc writes.

Separate code-only namespace:
`audit-tools/resident-launch-environment-control-001`.
Archive SHA256 `74fbc37b1d64f130badea27f890e23f8fd78b0a5906d6628931bfe3e69e023fe`.
Helper source SHA256 `1a8218970a31d4438815dd5d639b9c33b81c9659b75891970bed98d27a70b192`.
Remote validation SHA256 `8aa1918cd804536c194455c5655aaeba0e161f3525ee27d8589c441897ebf14b`.

## Unresolved continuation accounting

The repair is validated launch plumbing, **not** a completed repaired cell or
authorization to bypass the existing ledger. Its original unresolved confounder
still blocks continuation. The current operational reasons do not include this
launch mistake, and native generic repair requires a new execution freeze;
do not falsely label it provider outage/Worker crash, mark it valid, delete it,
change its settlement or quietly retry under the same receipt.

A narrowly checked external pre-execution repair admission/continuation remains
necessary before the one affected cell and original remaining schedule can run.
That follow-up must preserve the unchanged measured substrate and all old proof
scopes, distinguish this0-call setup failure from substantive samples, and maintain
the one-repair/no-semantic-retry discipline. No new matrix, prompt tuning, method,
pruning or PhaseII is authorized by this note. The overall goal remains active.
