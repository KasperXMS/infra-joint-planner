# Resident Phase II: full checkpoint112

The existing owned controller020 completed the ordinary16-cell checkpoint at
2026-10-08T09:31:52.397808UTC, before any original113 reservation. Receipt:
`analysis/phase2-derived-companion-v2-environment-cadence-freeze-001-cell0112.json`,
SHA256 `b02d164a714b4eb79fe08f1394a8d4fdaf0b97529fa1b7d1c996c05a6a85c481`.

## Independent verification

Owner-local independent readback completed at09:34:48.907951UTC. New exclusive
receipt `analysis/phase2-derived-companion-v2-checkpoint0112-independent-readback-001.json`,
SHA256 `5caa70e96b8f7e1209d538f7a659ea4bebdaa036de8426fb953a5acfcf3584c9`.

- 112 admitted cells,113 preserved attempts,0 pending/unresolved,1 operational
  exclusion. Original71 and its sole authorized replacement remain distinct.
- All113 trace hashes, original admission provenance digests and attempt
  identities match the checkpoint. Original admission provenance uses the
  existing `provenance_sha256` serialization; it is not the byte-level file
  SHA256 or the compact JSON serialization used by the ledger's own digest.
- All1831 actual SDK request files match their checkpoint hashes and exact
  per-attempt file populations:825 Manager,824 fixed Blind Verifier,182
  specialist. The checkpoint's actual original recipient scans have no findings;
  fixed Verifier binding and non-Manager feedback isolation are verified.
- 208 profile/418 ledger/211 rules exact feedback matches prove visibility,
  not causal adoption, semantic retention or successful optimization.
- All147 actual frozen source hashes remain equal to the closed all110 bootstrap
  source closure; checkpoint controller map35 equals current manifest. Current
  manifest SHA256 `e8bb0da95be286e1e6255a39d9dfe4d66757900f653704e141801c0ba0bf0a8e`,
  control012 `21b9695c9dfd017c267ce5855e3f1582c7fe891f5616839b021bf7ae21271c0f`,
  ledger012 `b02fd8fd4730d3810dc2bda1848da1e9a13ef7969ac29500b69056e3242510df`.
- Checkpoint journal130193-byte prefix SHA256
  `ea2c523665ee17c5018ecadacfd4722223f37cb57be8111b41dd3fbcc36c0db9`.
  No later journal events or original113 reservation existed at independent
  readback. Source, runtime, tasks, budgets and prompts are unchanged.

The original71 raw admission intentionally lacks ordinary `api_audit` fields;
its exact exclusion is handled by the unchanged owning-node original exclusion
review and checkpoint wire scan. The independent readback recognizes only that
exact run, while preserving its original admission hash and all24 request files.
No wildcard relaxation, retry authority or new exclusion is introduced.

Independent verification hashes request and trace bytes on the owning4090,
without decoding SDK payloads or corpus/store/private-evaluator bodies. The
checkpoint itself runs the existing actual recipient/admission scanner, not a
replacement hash-only privacy scanner. No model call, quality aggregation or
new manual semantic audit occurred. Final audit still requires all192 resolved,
all193 preserved and strict global inactivity. Admission validity is not answer
correctness. Next ordinary full gate is128, with immediate gating for any new
finding.
