# Resident PhaseI checkpoint131: D completes without comparative adoption

2026-10-06. Partial/unbalanced block; not method screening or an efficacy claim.

Cell `phase1-video_mme-2-e48bef6f0e60e753-p2-slow-D`, attempt1, Video-MME131-3.
Reserved10:46:45.834283Z, settled valid10:49:31.088752Z; original terminal format
valid, original benchmark score1.0. No nominal retry or measured004 change.

| Metric | Actual value |
| --- | --- |
| Manager / specialist / Verifier turns |12 /0 /4|
| Prepared actions |read_artifact,extract_clip,sample_frames,model|
| Actual inference |1A4VL4B; `stop`|
| Typed failure |1artifact_too_large; preserved fail-closed read limit|
| E2E |126.325s|
| Fixed initial placement |7,037,220bytes /19.707s|
| Recorded action transfer |0bytes /0ms; no completeness claim from subtotal alone|
| Model service / tokens |37.556s /6,653input /2output|
| Successful tool work |0.861s; failed read work not included|
| Manager / Verifier work |53.410s /12.041s|
| API frozen list-price estimate |USD0.150101393853;16calls with known usage-cost|
| Graph snapshots / nodes / edges |13 /4 /7|
| Actual max concurrency / overlap |1 /0ms|
| Full actual SDK recipient contexts |16; no admission findings|

## Interface visibility is not adoption

Independently inspected actual persisted root SDK requests/responses on4090:

- All12root requests exposed `compare_ready_actions`.
- **Zero** actual comparison tool calls and zero comparison events.
- Four quote creations and four `commit_quote` calls/authorizations occurred.
- Four quote rejections were preserved.
- Eight timed quote-control calls,1.644s summed control work, not additive E2E.

The actual root tool-name histogram was1extract_clip,4commit_quote,4sample_frames,
1invoke_model,1make_contact_sheet,1read_artifact. Requested tool names are **not**
successful physical execution counts. The Agent completed via single-action quotes
without comparing alternatives. This is a valid natural D trajectory; no prompt
was adjusted to force comparison and no early pruning decision follows.

## Original evidence independently verified

Raw admission was independently reconstructed and exactly matched, valid with no
problems or operational incidents. Exact reserve/settle records bind attempt1 and
frozen004. All four stores started empty; all Workers exited; residency and tc
cleanup passed. Benchmark/artifact/SDK bodies stayed on experiment owner machines.

Remote root: `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

- Reservation SHA256:
  `40f27814be77f38da69662194efd99a8f23417a4daacc247d69b041fe938def1`.
- Settlement SHA256:
  `2cafcd25436c447ebf505764f20136c328f691caa51daef44de6f06057f11bb7`.
- `analysis/resident-source004-cell131-video-D-settlement-audit-001.json` SHA256:
  `0bdef0e4104e62c017127e7c2f59b82b927db6959f13ff5d7cdf35d2ea0c4545`.
- Actual request/response interface/adoption proof
  `analysis/resident-source004-cell131-D-interface-adoption-001.json` SHA256:
  `37ae7c15969d0f6311d0e168f6cd64986608115ccfaa8f190b673c25f11d1e96`.

Immutable126snapshot plus exact valid127–131settlements yields131effective cells.
Full168/comprehensive private/failure/recipient/adoption audits/frozen pruning/
actualheld-outPhaseII/Q1–Q10remain required. Correctness does not prove temporal
evidence retention, and non-adoption is not silently repaired.
