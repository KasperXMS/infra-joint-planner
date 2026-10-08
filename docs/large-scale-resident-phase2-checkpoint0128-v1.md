# Resident Phase II: full checkpoint 128

The existing controller 021 completed the ordinary 16-cell checkpoint at
2026-10-08T13:06:25.526687 UTC, before any original cell-129 reservation.
Receipt: `analysis/phase2-derived-companion-v3-environment-cadence-freeze-001-cell0128.json`.
SHA-256: `1fe9414361bb3f8014a38da97606fa3137b3e335ae53883d1cccf9a5d85a4a71`.

## Independent verification

The independent creator was submitted once and exited 0. Its owner
3899523/start199214598 is absent after completion. The exclusive receipt
`analysis/phase2-filtered-companion-v3-checkpoint0128-independent-readback-001.json`
was persisted at 13:10:15.128895 UTC; SHA-256:
`22639e07d3294a4b88be9ec945c4cc27236245382e069bec020684c17ff09530`.
An independent metadata readback and repeated actual-byte verification passed
at 13:10:58 UTC.

- 128 admitted cells; 129 preserved attempts; zero pending or unresolved;
  one operational exclusion. Original 71 and its sole authorized replacement
  remain separate and immutable.
- All 129 trace hashes and original admission provenance digests match.
  Admission provenance uses the existing sorted, non-ASCII-escaped JSON with
  default separators, not raw file bytes or compact ledger serialization.
- All 2,082 actual SDK request files match their recorded hashes and exact
  per-attempt populations: 941 Manager, 940 fixed Blind Verifier, 201 specialist.
  Original checkpoint recipient scans have no findings; fixed Verifier binding
  and non-Manager profile/ledger/rules isolation are verified.
- Exact root feedback matches: 239 profile, 478 ledger, 240 rules. These prove
  visibility, not causal adoption, semantic retention or optimization.
- All 151 actual source files match bootstrap 002's frozen closure; the
  checkpoint's 38 controller-source hashes match the current manifest.
  Manifest: `9d68b6af24554d2a977a8b38073df15f8a4908844513e75fe278888350979050`.
  Control 013: `21b9695c9dfd017c267ce5855e3f1582c7fe891f5616839b021bf7ae21271c0f`.
  Ledger 013: `b580ce1aa4f5b2f812665768bdf64a22411e81e7089d172abbe1a30cd797d304`.
  Bootstrap 002: `f866c70d07e9f1ec2d193bacae57b7636d236d4df1470259bfa3e04d40f2bf09`.
- The 147,216-byte checkpoint journal prefix has SHA-256
  `6c18c1366f5fb1440100a38d9741b179fd18e120bb3944c5428902935f73177a`.
  No later journal events existed at persistence or independent readback;
  therefore both verifications preceded cell-129 reservation.

The exact excluded original-71 admission is the only allowed missing
`api_audit` exception. Its original admission, trace and request hashes remain
included. There is no new exclusion, retry authority or scanner relaxation.

Independent verification hashes bytes on the owning 4090; it does not decode
SDK payloads, corpus/store bodies or private evaluator content. The ordinary
checkpoint uses the existing actual recipient scanner, not a replacement
hash-only privacy scan. No model calls, quality aggregation or new manual
semantic audit were performed.

## Continuing execution

At 13:11:12 UTC the same supervisor 3875600/start198979764 and controller
3875601/start198979767 are owned and live; no atomic action or cell-129
reservation exists yet. Controller CPU has advanced to 38,707 ticks. Continue
the same queue, never relaunch it or repeat the completed creators or cells.
Next ordinary full gates: 144, 160, 176 and 192; any new finding gates immediately.

This closes checkpoint 128, not the experiment. Admission validity is not
answer correctness. Final completion still requires all 192 cells resolved,
all 193 attempts preserved, strict inactivity, actual recipient/private scans,
manual semantic/retention/adoption/failure audits, quality-conditioned analyses,
Q1–Q10 and all named reports. The goal remains active.
