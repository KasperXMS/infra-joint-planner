# Resident-block checkpoint033

The new resident block is still incomplete:33/168nominal outcomes admitted,
1pending and0unresolved confounders at snapshot015, captured
2026-10-05T19:41:41.245887Z. Four original rejection receipts remain preserved
with exact offline reviews (model JSON, absent record fields, two provider-policy
refusals). Admission does not imply completion or correctness. No score pooling,
method pruning or PhaseII expansion is performed.

Snapshot file: `analysis/resident-snapshot-015.json`, SHA
`6297bf1016bb8759ea06d9fd516e7a84d598c06cb1ad964cd96bcefede8f14b0`.
Earlier [checkpoint029](large-scale-resident-checkpoint-029-v1.md) and
[provider-policy audit](large-scale-resident-provider-policy-review-v1.md)
retain the preceding per-cell results, missing evaluation/usage and provenance.
The old42remain closed and unpooled, while counting toward the420-cell cap.

| Cell/task | Planner/network/method | Completed /format /original score | Manager/Verifier | Physical /model inference | E2E s | Initial bytes/work s | Action bytes/work s | Tool-only work s | Backend model work s | API estimated USD |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| 32/MultiHop1 | P2/Fast/C | yes/valid/1.0 | 13/6 | 6/3 | 306.482 | 7,696,522/0.981 | 5,204,596/1.719 | 2.086 | 248.327 | 0.1333021512 |
| 33/Video1 | P1/Fast/E | yes/valid/1.0 | 4/4 | 2/1 | 144.215 | 213,739,837/18.697 | 0/0 | 44.023 | 37.845 | 0.0939553635 |

P1=`deepseek-v4-pro`, P2=`qwen3.8-max`, fixed Blind Verifier=`qwen3.8-max`.
MultiHop1=`multihop-rag-train-4b6de4acbde051fee1f727f3`; Video1=`602-2`.
Both cells used fresh Worker processes/stores and passed actual SDK recipient,
original evaluator, Worker exit and5-instance residency gates. No retries,
replacements, semantic repair, prompt/budget changes or warmup subtraction.

Cell32created no specialists, performed aggregate +two BM25 +three physical
model invocations, and had no context rejects. Returned inference telemetry
reported8,125input/375output tokens. Six quotes were authorized and consumed,
none discarded/stale; one proposal was rejected. Measured quote control work
was1.476s, excluding cloud reasoning work already recorded separately. Its graph
has6nodes/6edges and maximum1observed concurrent action. Quote-induced semantic
revision and full required-evidence retention remain unproven, not set to0/1.

Cell33created no specialists, had one physical inference (6,701input/2output
tokens) and no context rejects. Frozen E rules were visible in4root inputs;
internal rule use is not observable. Its graph has2nodes/6edges and max1observed
concurrent action. This trajectory's44.023s tool work is significant despite
zero action artifact transfer. It is not model startup time, and no part of it
was removed from the outcome. Raw Worker operator work is82.000s including model
execution; do not add backend model work on top of that inclusive value.

These unmatched cells are not a causal comparison or method win. In particular,
cell30/P2/Slow/A was completed but wrong; cell32/P2/Fast/C was correct, with more
model/API work. Planner and task match, but method **and network** differ. Full
matched cells, private evidence audit and quality-conditioned analysis are still
needed. Cheaper/wrong and early provider rejection are not optimization successes.

Queue005 PID1997584 and cell34atomic PID2039021 were verified live at19:43:54Z.
Later process handles must be re-read, never inferred from earlier PIDs. Cell34is
`phase1-video_mme-1-7ea6434bc064f69c-p2-slow-B0`; at19:39:23Z the actual trace was
in initial materialization, before Manager reasoning. The213,739,837-byte video
under3Mbps entails a long fixed setup transfer. Report it separately, not as an
Agent decision, stalled reasoning or cold inference time.

Measured execution SHA remains
`4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`;
external continuation freeze004 SHA remains
`dbbc9d0a4752e31e07b0428cf911da3bcafccbf0d20b65c8f69a8af8e5bac6e4`.
All389measured app files remain frozen. Dataset/model payloads stay on4090/edges.
Only never-started cells continue; new unresolved findings stop the queue again.
Finish all168, then complete privacy/private evidence/failure/adoption audit,
freeze pruning and preregister PhaseII within `42+168+48m<=420`. Final reports
and Q1–Q10characterization remain unfinished; no new method has been introduced.

## Later checkpoint:34nominal outcomes,1pending

Snapshot016 captured2026-10-05T19:54:17.856719Z:34/168admitted,1pending,
0unresolved confounders; original findings/reviews remain4. File SHA:
`6f85634f0543e9297e9063327db11612291f935133ca2815d0b1a1f53990298d`.
This append does not relabel the earlier snapshot015or alter its evidence.

Cell34/Video602-2/P2/Slow/B0 completed with canonical validity and original
score1.0. Manager5/Verifier5,0specialists,3physical actions:1tool execution,
2model requests, only1actual inference and1explicit context preflight reject.
The Agent's legal continuation is not a harness retry/replacement. All10actual
SDK recipient contexts,5resident instances, Worker exits and tc cleanup passed.

E2E713.837s; initial213,739,837bytes/596.997s; complete action artifact transfer
0bytes/0s; tool-only work31.123s; backend model work19.866s. Returned model
telemetry:3,713input/2output tokens. Frozen-list-price API USD0.2216565740.
Raw inclusive Worker operator work51.070s must not be added to backend service
work. Fixed setup remains separate; no startup/cache subtraction or quality
aggregation. Graph3nodes/35artifact/control edges, max1concurrent action; edge
count is not the number of physical actions or parallel branches.

At19:54:19Z queue005 PID1997584 and cell35atomic PID2084188 were verified live
on Video602-2/P1/Slow/B1 initial materialization. Re-read later state. No app,
method, prompt, budget, deployment, schedule or benchmark change occurred; the
whole study remains unfinished. The [full completion audit](large-scale-completion-audit-v1.md)
explicitly lists the remaining168-cell audit, PhaseII execution and final reports.
