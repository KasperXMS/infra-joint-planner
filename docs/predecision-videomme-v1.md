# Video-MME pre-decision Raw-Aware v1

**RUNNING: 795-3 COMPLETE; FIRST THREE 848-1 CELLS CLEAN; 5/12 CONDITIONS PENDING.** Queue executes all LongBench cells first, then 795-3 / 848-1 /
795-2 in frozen order, four conditions each. Three questions on two intact original
AV1 videos, explicitly not three independent video draws.

Both full videos and original question/options/private answers are frozen before
execution. No smoke MJPEG representation, offline task-conditioned sampling or
dataset-specific operator. Native tools decide sampling and evidence selection at
runtime; original evaluator receives terminal canonical choice.

See [protocol](predecision-crossbenchmark-v1-protocol.md). The first task comparison
is complete; the Video family and final cross-workload characterization are not.

## 795-3: completed four-cell task comparison

Original 2495.121-second AV1 video, 282442048 bytes, initially on A4. All four native
trajectories sample 32 frames: `every_seconds=5` except Slow-Aware's 10 s, using
the original video and real AV1-capable FFmpeg. No contact sheet succeeds; all are single-Manager workflows
without specialists (allowed, not an acceptance gate). Model-device selection is
physical-layer A28, with actual A4→A28 image transfers and real visual inference.

| Condition | Answer / score | E2E s | Action bytes / transfer s | Initial placement s | Sampled / terminal input frames | Manager / Verifier | Model attempts / inference / context rejects | Graph N/E |
| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |
| Fast-Blind | B / 0 | 185.443 | 581538 / 0.813 | 26.066 | 32 / 4 | 5 / 5 | 2 / 1 / 1 | 3 / 20 |
| Fast-Aware | A / 1 | 252.371 | 1230240 / 1.908 | 24.539 | 32 / 8 | 3 / 3 | 1 / 1 / 0 | 2 / 8 |
| Slow-Blind | A / 1 | 1069.965 | 1562096 / 5.508 | 788.892 | 32 / 10 | 3 / 3 | 1 / 1 / 0 | 2 / 10 |
| Slow-Aware | A / 1 | 1071.594 | 1471756 / 5.507 | 788.481 | 32 / 10 | 3 / 3 | 1 / 1 / 0 | 2 / 10 |

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
| Slow-Aware | 17.058 / 8.474 | 235.830 | 14.637 | 9402 / 2 | 1471756 / 520 |

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
limit. Slow-Aware has also clean completed/evaluated, with 28/28 probes and all
three fresh anonymous profile/input hashes passing. Its terminal uses frames 1–10
at 10 s cadence; doubled sampling spacing is an observed semantic parameter change,
not an enforced policy. Images are transferred to A28 and consumed by inference.

## Task-level interpretation and validity

Slow-Aware transfers **5.8% fewer action bytes**, but its E2E is **0.15% higher**
than Slow-Blind (both correct). Model service work is nearly equal; wider sampling
increases decode/operator work. This is not a clear latency benefit. Fixed initial
placement accounts for approximately 74% of each Slow E2E. Initial placement and
action bytes together differ by only about 0.032% between Slow workflows.

Fast-Aware is correct while Fast-Blind is wrong, but uses 111.6% more action bytes
and takes 36.1% longer. This is a quality-cost trade-off, not uniform efficiency.
Aware Fast→Slow changes sampling cadence and terminal frame count (5 s / 8 frames
→ 10 s / 10 frames), without reducing sampled-frame count or changing the two-node
operator sequence. Both Blind and Aware sample locally in all conditions; there is
no observed move-whole-video-versus-local-sample topology reversal. Sparse early
sampling does not establish coverage of the whole 2495 s timeline or temporal
evidence adequacy; do not infer exact original PTS or causal decisive-frame effects.

Durable remote `video-795-3-four-cell-audit-001.json` (SHA-256
`7b38c083e4e41af20e3d356f753bc3f553ac072436324e1fe5a16ebc0aad25d4`)
verifies all four unique trace chains/run IDs/single run ends, empty initial stores,
16 exited Worker processes, shutdown and tc cleanup, shared task/capability/harness
hashes, terminal provenance, persistence/privacy and normal-stop model finishes.
All **96/96 probes**, **14 Manager / 14 Blind Verifier hashes** and **six fresh Aware
inputs** pass. All model deployments expose 32768/2048; all four actual inferences
select A28. No semantic retry or prompt/budget/scheduler change.

Merged audit: `audit-progress-011.json` under transport-patch root: 18 preserved
attempts / 16 effective cells / eight remaining conditions. Queue is now in 848-1
Fast-Blind. Wait for that task and 795-2 before final cross-workload interpretation;
n=1 cannot establish stable infrastructure-conditioned causality.

## 848-1: first three clean cells (four-condition comparison pending)

The intact original 2037.781 s / 160083738-byte AV1 video starts on A4.
Fast-Blind naturally samples 31 frames at 64 s cadence. Its first model request
selects indices 1/3/5/.../31 (16 images), rejected by static context preflight;
it recovers to indices 1/4/7/.../31 (11 images). This is temporally distributed
input, not just the early prefix used for 795-3. Original frame PTS and decisive
chapter-boundary visibility are not asserted by the index/cadence metadata alone.

| Condition | Completion / format / score | Answer | E2E s | Initial placement s | Action bytes / transfer s | Manager / Verifier | Model attempts / inference / context rejects | Graph N/E |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| Fast-Blind | yes / valid / 0 | B | 442.512 | 13.921 | 798787 / 1.429 | 6 / 6 | 2 / 1 / 1 | 3 / 27 |
| Fast-Aware | yes / valid / 0 | A | 226.982 | 13.973 | 380788 / 0.287 | 6 / 6 | 2 / 1 / 1 | 4 / 63 |
| Slow-Blind | yes / valid / 0 | A | 871.266 | 446.971 | 981232 / 3.885 | 4 / 4 | 1 / 1 / 0 | 2 / 12 |

Manager work 72.368 s, Blind Verifier 20.477 s, operator/decode 73.009 s,
physical model service 259.739 s; terminal artifact/prompt 798787/671 bytes,
actual input/output tokens 10377/2. No specialists or parallel action overlap.
All 24 probes, six Manager/Blind-Verifier input hashes, privacy/persistence,
terminal model provenance, shutdown and tc cleanup pass. Other typed observations
are two semantic-validation and four phase-restriction failures; they are retained
Agent trajectory behavior, not hidden retries or new runtime defects.

This is a **valid semantic visual evidence-selection / temporal synthesis failure**,
with context recovery and readiness/composition contributors. It completes and
reaches the original evaluator; not a budget, format or deployment outage. The
trace does not distinguish inadequate chapter evidence from erroneous ordering
reasoning without inspecting decisive visual content; no repair/tuning is made.

Fast-Aware samples 31 frames at 65 s cadence. An initial request for all 31 images
fails static context preflight; the Manager naturally continues with a real
`make_contact_sheet` call, columns 8 / cells 320×180, then invokes the model on that
single output. This adds a semantic reduction node instead of selecting a subset
of individual frames. It produces canonical A, also wrong. No new tool, prompt,
heuristic, retry or hidden summary was introduced.

Its Manager / Verifier work is 59.144 / 19.791 s, decode/sheet tool work 74.411 s,
physical model service 57.891 s, terminal prompt 1001 bytes, actual input/output
tokens 2113/2. One actual inference, no specialists or action overlap. All 56 probes,
six fresh Aware Manager inputs / six Blind Verifier hashes, provenance/privacy,
persistence and cleanup pass; two semantic-validation failures are recorded.

Contact sheet provenance was checked **on remote A4 and A28**, without transferring
pixels to the PC: both copies are readable JPEG, 2560×720 / 380788 bytes, SHA-256
`05534551d06425ba32eeb667fb2f8d6c934e8bc66b4d11eaf7ff11213c059a31`.
All 31 input frames are placed row-major, downscaled into declared cells and encoded
at generic operator JPEG quality 90. This is an explicit **lossy Agent-selected
execution reduction**, not a modification of the intact benchmark input and not
silent truncation. Thumbnail legibility may limit evidence, but decisive-frame
or OCR loss as the exact error cause is not proven.

Fast-Aware action bytes are 52.3% lower and E2E 48.7% lower than Fast-Blind; both
scores are zero, so do not present this as successful quality-constrained adaptation.
The major service-work saving comes from 11 individual image inputs → one composite
image (259.739 → 57.891 s), not just the ~1.1 s transfer difference. It is a genuine
execution-grown graph/representation difference, but not yet a Fast→Slow response.

Durable partial audits: `video-848-1-fast-pair-audit-001.json` (trace/provenance and
unchanged original task), `video-848-1-contact-sheet-content-integrity-001.json`
(actual image metadata/checksums). Full evidence stays remote.
Slow-Blind samples 31 frames at 64 s cadence and directly invokes the model with
12 frames (indices 1/7/8/9/15/16/17/23/24/25/30/31). No context failure occurs;
the terminal still returns A/0. Actual model input/output tokens 11349/2, model
service work 283.732 s, Manager / Verifier 49.939 / 12.344 s, decode 73.003 s;
terminal prompt 902 bytes. No specialists or overlap. All 16 probes, four input
hashes per Manager/Blind Verifier, provenance/privacy/persistence and cleanup pass.
Four phase restrictions / one semantic-validation rejection are retained.

Its first model call is statically feasible and enters actual inference. This zero
cannot be attributed to context rejection, budget exhaustion, backend outage or
output format; primary class remains temporal evidence selection / synthesis.
Sparse/selected visual evidence versus ordering-reasoning attribution remains
unproven. Fixed initial placement accounts for 51.3% of E2E; do not call the
446.971 s initial-transfer component an Agent-choice inefficiency.

Budget accounting is read from `loop.usage`: all current Video cells use 2–4 charged
physical calls, not the 64-call ceiling. Immediate schema/phase rejections are
separately recorded observations, not additional model inference.
Merged `audit-progress-014.json`: 21 preserved attempts / 19 effective cells / five
pending. 848-1 Slow-Aware is active. The four-condition task audit follows only
after its completion or valid failure.
