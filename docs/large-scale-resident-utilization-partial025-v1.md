# Resident pool utilization — held-out first25 effective outcomes

2026-10-07, Asia/Hong_Kong. This is a bounded PhaseII metadata checkpoint,
not the final192 population or the closed PhaseI168/old42. No scheduler,
model-routing, prompt, capability or experimental configuration was changed.

## Actual returned physical inference

| Deployment | Model artifact | Returned receipts | Distinct effective runs | Returned service work, s | Input / output tokens | Finish reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| A4 | Qwen3-VL4B Instruct |28 |15 |789.213 |153,348 /1,342 |28stop |
| A5 | Qwen3-VL8B Instruct |5 |3 |250.555 |31,256 /676 |5stop |
| A28 | Qwen3.5-27.3B |14 |9 |3,357.221 |84,960 /5,929 |13stop /1length |
| strong4090GPU0 | Same27.3B artifact |7 |7 |9.886 |2,785 /624 |7stop |
| strong4090GPU1 | Same8B Instruct artifact |0 |0 |0 in returned population |0 /0 in returned population |None |

Run counts overlap and must not be added. All54returned receipts are distinct
action IDs and agree with the immutable original projection's54telemetry
receipts,272,349input/8,571output tokens,4,406.875s returned service work and
53stop/1length. Three failed model outcomes lack returned telemetry; this
does not establish that all three reached inference. Their token/service work
is unknown, not zero. Returned-work subtotals are not complete backend-work
accounting and are not an E2E decomposition. Known length termination is
reported, not silently treated as a full semantic completion.

The environment has three distinct weight artifacts, five resident instances
and four Workers. Five warmed available instances do not imply that every
instance is selected in each task or even this partial population. GPU1 is
resident and calibrated but has no returned benchmark inference here. The
frozen locality scheduler is not a load balancer; this checkpoint does not
authorize forced routing just to equalize device use. Different model weights,
payloads and trajectories confound any naive device-speed/quality comparison.

## Source-bound verification

Owner-local snapshot023SHA:
`b054749dabdecfac32d4856112899825cb63ec33a0deb2519c71f7b73923de95`.
Utilization receipt `analysis/resident-phase2-utilization-partial025-001.json`,
SHA `9bd5235bf7e708d99a95cc9a93b5592d1c475f7ec9ec05f7cee962af576ebe28`.
Independent group-subtotal/token/service/finish-reason readback against the
original settled projection:
`analysis/resident-phase2-utilization-partial025-validation-001.json`, SHA
`d7dfa2265de540fda2248c1e508b014cc752b8a131be43e804fec2451dcfb2fb`.
Raw trace hashes and per-action selection/telemetry bindings remain on4090.
No support/corpus/store-body decoding, model/Planner call, raw trace/API/artifact
payload export or development-PC data distribution occurs in this audit.

## Current execution boundary

Cell26 MultiHop3/DeepSeek/Slow/B0 attempt1 is live, atomic2501460; the same
005controller2434640/supervisor2434639 are owned/live at01:25:08Z.
Start receipt `analysis/resident-phase2-cell026-live-start-001.json`, SHA
`9fc32c2cadec51cb57f503b0d6035c94984bb9803b0bf79628fb06b07cff08a4`,
verifies four empty Worker stores, five resident instances and unchanged
atomic004 imports. No result yet; count remains25/192settled, not26.
All remaining outcomes and strict-inactive post-block private/manual failure,
recipient/adoption, quality-conditioned analyses and Q1–Q10 remain required.
