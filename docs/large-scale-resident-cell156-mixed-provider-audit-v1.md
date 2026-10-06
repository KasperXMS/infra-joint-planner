# Resident cell156: mixed token-rate and input-policy failure

2026-10-06. This is an external admission audit, not an Agent, method, prompt,
API-concurrency, deployment, benchmark or scheduler change. Historical original
admission, trace, result and hash-linked journal remain immutable.

## Actual execution

Cell `phase1-multihop_rag-1-29e45040dce39dae-p1-fast-E`, attempt1, used the frozen
resident pool and execution004. All four Worker stores started empty, Workers
exited, five resident identities passed validation and tc cleanup succeeded.
The actual26 SDK recipient contexts passed the existing isolation audit; this
does not substitute for the pending full private semantic audit after168cells.

| Metric | Actual |
|---|---:|
| Completion / evaluator | Failed / not invoked |
| Format / quality | Unknown / unknown, not score0 |
| Manager / specialist / Verifier API attempts | 8 / 10 / 8 |
| HTTP200 /400 /429 | 23 /2 /1 |
| Prepared physical actions / context rejections / physical inferences | 20 /3 /0 |
| Graph nodes / information edges / snapshots | 20 /23 /61 |
| E2E |127.756s|
| Complete action transfer |113,419bytes /0.085669s|
| Fixed initial placement, separate |7,696,522bytes /1.447217s|
| Successful tool work |2.220294s|
| Manager / specialist / Verifier work |72.673398 /44.150612 /22.756744s|
| API frozen list-price known subtotal |USD0.356974658180417,23calls|
| Complete API monetary cost |Unknown: three failed calls have unknown usage|

Service work overlaps and is not an additive E2E decomposition. The trajectory
also contains8phase-restricted and2semantic-validation observations. No quality
score is imputed, and no evidence/body/gold was copied to the development PC.

## Three independently preserved cloud failures

| Finished UTC | Actual recipient / model | Status / response |
|---|---|---|
|15:03:58.335001|bounded specialist / DeepSeek V4 Pro|429 `insufficient_quota`, allocated **token-rate** quota exceeded|
|15:03:59.040722|bounded specialist / DeepSeek V4 Pro|400 `data_inspection_failed`, input-policy refusal|
|15:04:04.016055|fixed Blind Verifier / Qwen3.8-Max|400 `data_inspection_failed`, input-policy refusal|

Both Planner providers use the existing Alibaba Cloud Model Studio Beijing
endpoint. The exact429message refers to `error-code#token-limit`; Alibaba's
[error documentation](https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit)
classifies this allocated-quota message as TPS/TPM throttling. It is not evidence
of exhausted balance. [Rate-limit documentation](https://www.alibabacloud.com/help/en/model-studio/rate-limit)
also distinguishes recharge from increasing the account's rate thresholds.
Neither billing nor account quota settings were changed.

The observed prior60s contains11successful DeepSeek responses totaling367,925
reported tokens (364,551prompt tokens). This is a **known account-activity
subtotal**, not the actual quota threshold or proof of TPS versus TPM. Other
account traffic and cached-token quota accounting are unknown.

The two failed specialists returned distinct error-bearing results; the final
Verifier400 is the immediate terminal failure. We cannot prove whether this
run would have completed or still hit a policy refusal without the429. It must
not be presented as a pure Planner failure, an inference OOM or a provider-wide
outage. Nor should it be hidden by filtering the429out of the policy reviewer.

## Admission and replacement boundary

An exact separate reviewer verifies every original HTTP triple and SDK
invocation receipt, unique call/scope identities, one HTTP attempt per SDK
invocation, all three exact public error responses, model/role provenance,
terminal trace correspondence, source freeze and complete evidence hashes.
Other findings, unknown errors, billing failures, missing evidence, SDK retries
and **policy-only failures fail closed**.

The source-bound sidecar classifies attempt1 as `operational_excluded`, with
token-rate throttling as the comparison confounder and input-policy refusal as
the immediate terminal failure. It preserves the original broad
`provider_outage` label in original evidence rather than silently rewriting it.
The sole replacement basis is the independently proved429, **not** either400
or a poor semantic result. Only the already authorized **one identical
operational replacement** is eligible. There is no prompt tuning, automatic
per-request retry, input censorship, concurrency change or quota increase.

Audit code commit `9c921b8`; remote immutable audit namespace
`audit-tools/resident-rate-policy-control-002`. Namespace001 and its initial
file-set review failure remain preserved;002 correctly includes the existing
SDK `model-attempt` metadata rather than ignoring it.

Tests:1670pytest pass /7Windows symlink skips; Ruff pass; configured strict
Pyright and explicit new-script strict Pyright0errors/0warnings. Actual4090:
54new tests pass in1.17s; unchanged execution004 archive preflight passed.

## Immutable receipts

- Diagnosis/telemetry: `analysis/resident-source004-cell156-mixed-provider-audit-001.json`,
  file SHA256 `20f1893a5e940a972e326a7f9268ab4b0bddbdf561545ecc77343d6348ad3d04`.
- Sidecar: `mixed-token-rate-policy-adjudications/<original-run-id>.json`, file
  SHA256 `ac852b358db5e47c8fe681ec5fa82c97e39b8c703d1b929fe63ab5df4738f7c5`.
- Reviewed admission canonical SHA256:
  `181ec14e02b6185af49812332d94b3fd545c1554e6e31790b1ca58e70114c0df`.
- Original admission canonical SHA256:
  `9ccc46e46c37a82197e539a254cfcbab8624ba87b1662ee861535b2bd94e5328`.
- Code-only002archive SHA256:
  `006e936b269368b60d6475a46f3bcc145587640f96c21a7ef93d36ecd5d25e81`.
- Remote validation002file SHA256:
  `81380ba7630b0c505acd3e9d3e4eac6a116d38f31ef826c4510f1e9e2339ec2f`.

Measured execution remains revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`,
canonical freeze `16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c`.
This audit does not complete a new cell or authorize pruning/PhaseII.155prior
effective nominal cells remain; whole-ledger continuation verification is a
separate step. All old42samples remain unpooled, and the420cap is unchanged.
