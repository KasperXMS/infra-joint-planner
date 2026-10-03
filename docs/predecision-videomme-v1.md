# Video-MME pre-decision Raw-Aware v1

**RUNNING: FIRST THREE 795-3 CELLS CLEAN; 9/12 CONDITIONS PENDING.** Queue executes all LongBench cells first, then 795-3 / 848-1 /
795-2 in frozen order, four conditions each. Three questions on two intact original
AV1 videos, explicitly not three independent video draws.

Both full videos and original question/options/private answers are frozen before
execution. No smoke MJPEG representation, offline task-conditioned sampling or
dataset-specific operator. Native tools decide sampling and evidence selection at
runtime; original evaluator receives terminal canonical choice.

See [protocol](predecision-crossbenchmark-v1-protocol.md). No completed Video
task/family comparison or final quality/cost claim exists for this block yet.

## 795-3: first three clean trajectories

Original 2495.121-second AV1 video, 282442048 bytes, initially on A4. Both native
trajectories sample 32 frames with `every_seconds=5`, using the original video and
real AV1-capable FFmpeg. No contact sheet succeeds; both are single-Manager workflows
without specialists (allowed, not an acceptance gate). Model-device selection is
physical-layer A28, with actual A4→A28 image transfers and real visual inference.

| Condition | Answer / score | E2E s | Action bytes / transfer s | Initial placement s | Sampled / terminal input frames | Manager / Verifier | Model attempts / inference / context rejects | Graph N/E |
| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |
| Fast-Blind | B / 0 | 185.443 | 581538 / 0.813 | 26.066 | 32 / 4 | 5 / 5 | 2 / 1 / 1 | 3 / 20 |
| Fast-Aware | A / 1 | 252.371 | 1230240 / 1.908 | 24.539 | 32 / 8 | 3 / 3 | 1 / 1 / 0 | 2 / 8 |
| Slow-Blind | A / 1 | 1069.965 | 1562096 / 5.508 | 788.892 | 32 / 10 | 3 / 3 | 1 / 1 / 0 | 2 / 10 |

Fast-Blind's first model request consumes frame IDs 1–16; the declared static
2048-token-per-image bound alone consumes the entire 32768 context, so any prompt
and reserved output make it impossible under the frozen contract. This is static
capability misuse, not dynamic deployment unavailability or proof of OOM. It then
legally requests only frames 1–4 and returns the wrong label. Fast-Aware requests
frames 1–8 directly and returns the correct label. These are nominal frame indices
at the declared cadence; do not claim exact original PTS measurements.

The wrong Blind answer is a valid visual evidence-selection / answer-synthesis
failure, with context-recovery narrowing and Verifier/phase-restriction behavior
as contributors. The trace does not prove exactly which sampled pixel first shows
the decisive tool; no extra inference, task-specific repair or retry is performed.

| Condition | Manager / Verifier work s | Visual model service s | Decode/operator s | Actual input / output tokens | Terminal artifact / prompt bytes |
| --- | --- | ---: | ---: | --- | --- |
| Fast-Blind | 34.884 / 17.086 | 96.867 | 8.585 | 3871 / 2 | 581538 / 685 |
| Fast-Aware | 18.052 / 9.028 | 189.143 | 8.700 | 7562 / 2 | 1230240 / 585 |
| Slow-Blind | 20.191 / 9.130 | 236.090 | 8.696 | 9429 / 2 | 1562096 / 670 |

Both finish/evaluate with canonical choices; 24/28 probes pass, privacy/provenance,
persistence, Worker shutdown and tc restore pass. All three Aware Manager turns
have matching fresh profiles; Verifier remains Blind. Peak action concurrency is
one, no overlap. Service work is non-additive. Initial materialization is included
in E2E, not action transfer; the 282 MB original input is never hidden in the
0.58/1.23 MB action traffic. Slow-Blind has now clean completed/evaluated with
16/16 probes, three reconstructed Manager and Blind Verifier inputs, provenance,
privacy, persistence and operational checks passed. Its fixed initial materialization
took 788.892 s, approximately 74% of E2E; this must not be counted as an Agent's
workflow-choice benefit or failure. A4→A28 transfer metadata confirms terminal
input frames 1–10. Blind therefore also selects different evidence across Fast
and Slow despite no dynamic profile, underscoring the n=1 stochastic-confounding
limit. Slow-Aware is now materializing the same intact
source under 3 Mbps; do not mistake this live transfer for a stopped agent loop.

Remote merged audit: `audit-progress-010.json` under transport-patch root.
The two Fast trajectories do not establish rational network adaptation: Aware's
correct answer uses more frames, bytes and model service work. Wait for all four
conditions and the other two questions before cross-workload interpretation.
