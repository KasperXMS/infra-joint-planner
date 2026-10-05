# Resident checkpoint: Video cell81

2026-10-06. Frozen original Video-MME602-2 / P1 / Fast / B1, n=1.
Original attempt1 settled at23:46:30.084764Z, sequence162. Completed with a
canonical valid terminal answer and original evaluator score **1.0**. No retry,
replacement, prompt/budget tuning or interpretation as a cross-task winner.
Execution001/control007 unchanged; old42 results remain closed/unpooled.

| Measure | Original observed value |
| --- | --- |
| Manager / Verifier / physical calls | 4 / 4 / 3 |
| Model requests / actual inference / context rejects | 2 / 1 / 1 |
| Specialists / artifact handoff events | 0 / 0 |
| Actual path | Sample16frames -> context rejection -> invoke model with4frames |
| Actual deployment / input / output / finish | A4resident4B / 4,554 / 2 / stop |
| E2E | 144.286s |
| Fixed initial placement | 213,739,837bytes / 18.576s |
| Complete action transfer | 0bytes / 0s |
| Complete tool / model backend work | 45.249s / 25.245s |
| Manager / Verifier work | 43.885s / 10.288s; not additive E2E |
| Cloud API | All8 usages known, USD.1112426301173282, list-price not invoice |
| Actual SDK recipient contexts checked | 8; original privacy admission passed |
| Graph | 3nodes / 20artifact edges / 10snapshots;2success,1failure |
| Actual concurrency / overlap / action owners | 1 / 0s / 1 |

The same complete original213,739,837byte video (2,819.854s) was initially
placed onA4; it was not replaced by a pre-encoded MJPEG or smoke representation.
`sample_frames` used every_seconds176/max_frames16 and produced sixteen real
image/jpeg artifacts. The first model action referenced all sixteen and was
rejected before inference by the existing context preflight. A later action
selected four original sampled image artifacts and actually consumed them.
`make_contact_sheet` was attempted but phase-restricted: no contact sheet was
successfully produced or silently substituted. The rejected action remains
in the execution-grown graph, not erased or retried under the same action ID.

Both model selection requirements were statically supported. Requested
modality minima included text, but actual input media types were separately
checked by resolver/Worker preflight; four images entered the real multimodal
backend. Small declared output minima do not change the deployment's
32768context/2048reserved-output/4096image-envelope contract. Do not label
this as text-only inference or a preflight bypass.

Verifiercall1 entered synthesis; call3 returned to evidence_collection after
the rejected request and call4 completed the run. This is observed SDK-native
continuation, not a new stopping mechanism. B1's anonymous physical profile
was refreshed on the four actual root reasoning inputs; the Verifier remained
Blind. Exposure alone is not proof that profile information caused the frame
selection, routing or quality result. No optional cost-query/card or comparison
interface was used. Single-agent execution is valid, not an acceptance failure.

Zero action-artifact transfer is the complete measured movement between Workers,
not zero image reads, tool-return communication or cloud API traffic. Model and
decode work overlap other scopes and must not be added to E2E as independent
components. Correct official score does not prove temporal evidence sufficiency
or universal quality-preserving reduction. Private audit follows all168 cells.

All five model instances remained resident; Worker exit/tc cleanup/privacy checks
passed. No reload/OOM/truncation, hidden reduction, model substitution, runtime
retry or warm-start subtraction. Original evaluator/task/privacy boundary intact.

## Append-only provenance / remaining scope

Original admission canonical SHA-256:
`4784b467a183f8280ba3a5c1502006495454f97d4f92158b4dcd01bdcd704e95`.
Original journal settlement SHA-256:
`f378cc6d2e7e36f85282d862c3fb50f7d9333ce3d3e767a72fc35f5cdeaeae77`.
Exclusive remote analysis/resident-cell-081-summary-001.json file SHA-256:
`befe611bc65a6732e5d5f5e539fa438d2b25a51a5f6389d28be178b6a6faec11`.
Summary binds original result/trace/admission, journal and exit/residency proof.
No payload/gold/dataset/model export toPC or audit model calls.

Queue008PID2678456/cell82atomicPID2996079 verified live23:47:15.961986Z on
Video602-2/P2/Slow/A, reservedseq163at23:46:32Z.81classified of168; no82outcome
inferred. Slow video setup is fixed experimental transfer, not Agent-controlled
traffic or Ollama cold loading. Full168/audits/pruning/actual PhaseII/final
reports/Q1–Q10 remain unfinished; no early method pruning or goal completion.
