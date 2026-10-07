# Reviewed held-out private audit preparation

## Current combined-review entrypoint: source verified, not invoked

2026-10-07 15:03HKT. The old model-JSON-only invocation below is historical.
The current source-bound entrypoint is
`scripts/large_scale_resident_phase2_field_private_v1.py`, with the combined
field/model-JSON projection, not a raw-only or JSON-only ledger. Metadata-only
readback07:02:18Z confirms current controlSHA
`7205097e0197ca2719ecfda168b3fab8cb9222c9106ac63329559af306a8aa5e`,
ledgerSHA `00573c05346f1851b6b958bf18a692c42d163f105cd1db065172573c7437f2ae`,
all five current sidecar file hashes, disjoint membership and every source hash
against both frozen controls. Auditor sourceSHA
`9403987d745f51448a521007f767ba33f006ecfd6b5ebb009c2276fd11cd08da`.
The preserved live007 guard receiptSHA
`4bf22c701e49377f3c5e360e47d6d8adeff796243d4942d9195aa6a83224093c`
and unchanged original guard source were independently rechecked07:02:20Z;
this is source/receipt verification, not a new private-audit invocation.

After all192resolve and strict global inactivity is independently verified,
use the latest source-bound combined control/ledger and007audit Python paths:

```text
python -m large_scale_resident_phase2_field_private_v1
  --control-freeze <ROOT>/phase2-field-reviewed-control-freeze-003.json
  --ledger-freeze <ROOT>/phase2-field-ledger-freeze-003.json
  --output <ROOT>/analysis/<new-exclusive-audit-name>.json
```

If later reviews change the frozen control population, these003paths are not
automatically current. Rebind and verify the latest exact membership first.
The inherited scanner rejects multiple attempts/exclusions rather than silently
dropping them; if such attempts occur, preserve and explicitly audit all of
them before claiming full-study coverage. Currently the closed44have one
preserved attempt each, zero effective confounders/exclusions. This does not
prove the eventual192membership or authorize a partial private scan.
No runtime code/prompt/evaluator changes, new private bodies, model calls or
payload export; no new full-test claim for this documentation clarification.

This is preparation, not a completed192-cell audit or a new experiment.
At22:36:30Z on2026-10-06 the registered controller2146015 was owned/live,
no exit; journal33records/16effective outcomes/no new pending reservation.
Controller003 continues the unchanged frozen schedule and original execution004.

## Why a separate offline entrypoint is necessary

Cell16's raw original admission remains confounder for one exact known
post-backend invalid-JSON materialization. Its reproducible immutable review
sidecar supplies effective valid disposition, preserves original score0 and
forbids replacement. The original raw journal is not rewritten. A raw-only
collector cannot replay subsequent reservations past that preserved rejection.

`scripts/large_scale_resident_phase2_reviewed_private_v1.py` therefore binds the
existing exact reviewed projection and immutable read-once adapter receipt.
It invokes the historical private audit with a copied function namespace, not a
module/global mutation. The same owner-local scanner, artifact ownership,
annotation/source checks, Worker exit checks and unknown semantics remain intact.
Source/control/adapter hashes are captured separately from historical sources.
Original benchmark evaluation and all online Agent inputs are unchanged.

The **original global private inactivity guard** runs before control/metadata
reads and remains inside the original audit before/after private scans. This
entrypoint does not use the controller's startup self-identity exemption.
Partial blocks, pending attempts, unresolved findings, source drift or any
unverified Worker exit reject before private evidence reads. An unannotated
task's retention and semantic cause remain unknown, not guessed from score.

## Verification and remote preparation

Five new tests cover actual guard ordering, partial reviewed-block rejection,
completed synthetic reviewed membership with preserved raw rejection/score0/
unknowns, no historical global mutation and adapter/control drift rejection.
Full local:1761passed/7Windows platform skips,1768collected. Ruff, strict Pyright
with the explicit project interpreter and diff check pass.

Code-only remote archive SHA256:
`fa9af6e664aaa920a597e5d34c59179d70d052b7a91061674502b07d0eeb3825`.
Namespace: `audit-tools/resident-phase2-reviewed-private-control-001`.
New auditor source SHA256:
`5be5132ed389d8231d92616299383423c3dcaaf9bc1861ad241b5524fffe7599`.
Original scanner files are copied into this separate namespace where needed,
not overwritten in any archived execution/audit app.

Actual Linux suite122passed; log SHA256:
`55351dca20053d148cb65cf975ace23e36ea74a5bb8d6e695f06236421211107`.
An actual invocation while controller003 was live rejected at the original
inactivity guard, before private bodies. Preparation receipt SHA256:
`b76e2c982741fffbd1aff767e66c04615a59b9699f38fa152181a2e76ab6c141`.
Private bodies read0; Planner/model calls0; full private audit executedfalse.
These are synthetic contract tests and a negative admission check, not benchmark
repetitions, semantic tuning or measured execution changes.

## Later use, only after the full block is resolved and inactive

On4090 with the source-bound audit namespaces and archived original dependencies
on PYTHONPATH, pass the actual reviewed control and adapter freeze explicitly:

```text
python -m large_scale_resident_phase2_reviewed_private_v1
  --control-freeze <ROOT>/phase2-reviewed-control-freeze-001.json
  --ledger-freeze <ROOT>/phase2-ledger-read-once-freeze-002.json
  --output <ROOT>/analysis/<new-exclusive-audit-name>.json
```

Do not call this to audit a partial live block. Do not reuse an existing output
name. Do not place private corpus/support/answer bodies on the development PC.
Preparation does not satisfy the final private/manual semantic/failure/adoption
audit or Q1–Q10 report obligations; all remain required after192 outcomes.
