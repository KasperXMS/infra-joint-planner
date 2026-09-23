# Competent resource-blind baseline: six-task audit

## Scope and frozen settings

This audit stops before any 3/10/30 Mbps replay. The six tasks used the original
Video-MME, LongBench-v2, and MultiHop-RAG task/evaluator contracts, native unshaped
networking, the B0 locality-aware scheduler, and the finite generic operator vocabulary in
`configs/experiments/blind-baseline-6task-competent-v2.yaml`.

The Planner saw the sanitized task, benchmark output format, artifact schemas, opaque model
instances and their modality/context contracts, and system-derived feasible operators. It did
not see bandwidth, RTT, physical placement, load, queue, source references, evaluator metadata,
gold answers, or supporting evidence. DeepSeek `deepseek-chat` was called once per task with
temperature 0. No plan was repaired, retried, summarized, or truncated by the runtime.

The plans were frozen at `d05466e38637122cd465c92e9f1fda20f76dce5c`. The first five valid
executions used that revision. Task 6 first encountered an invalid infrastructure observation
failure. Its recovery used the identical frozen plan (no Planner call) at
`996550714ea071c0fe181140ac3732f1d8e4459f`, whose only relevant runtime change made `/state`
metadata-only and fail-closed on metadata/blob-size corruption.

Primary evidence:

- `/home/super/xiaoming/blind_baseline_6task_competent_v2/evidence`
- `/home/super/xiaoming/blind_baseline_6task_competent_v2_recovery1/evidence`

The original invalid task-6 result and trace remain in the primary directory. Recovery
provenance, including parent result and plan hashes, is recorded in
`recovery-provenance.json` in the recovery directory.

## Task outcomes

| Task | Frozen plan SHA-256 | Agents | Workflow summary | Score | Format | E2E ms | Transfer B / ms | Execution |
|---|---|---:|---|---:|---|---:|---:|---|
| Video-MME 795-3 | `6ff3577083b9e85ea093f28f082d4b98f1db3e74ff7bf8a6654988b247a6c16a` | 2 | 8-frame sample → contact sheet → visual note → terminal answer | 1.0 | valid | 171500.6 | 127578 / 627.5 | valid |
| Video-MME 848-1 | `9f3abf62b721b3caa8f8d2f2ab31cc289d2e0c7e62b2f529e91bd4c20f17d11d` | 1 | 16-frame full-timeline sample → contact sheet → terminal answer | 0.0 | valid | 134189.3 | 189602 / 839.6 | valid |
| LongBench multi-document | `85d9cd7d52a3955a3581e6810e04c0ede616625b00eb7f42cede5c1a3c384ea3` | 5 | 4 parallel BM25→model-note branches → terminal fan-in | 0.0 | valid | 341542.9 | 41452 / 1080.1 | valid |
| LongBench structured | `1f43162f7ed79def625631fbce0fbb751b580a07316d5f26bb1cba21cf525f4f` | 3 | filter → project → derive ratio → top-1 → terminal answer | 1.0 | valid | 60983.2 | 112 / 413.2 | valid |
| MultiHop multi-source | `9d139d964b225a966d40d8e202df98e642a5bf8a33f38ecaecf0ba071dbac9d5` | 3 | 3 local retrievals → 2 evidence notes → terminal fan-in | 0.0 | valid | 85287.2 | 9565 / 632.1 | valid |
| MultiHop reasoning | `88083572784f55d4c245d86a812909c6b819bb6287889b3a6209a5bc2cd1894a` | 2 | 3 local retrievals → aggregate → terminal answer | 1.0 | valid after confounder recovery | 3808.1 | 14881 / 88.6 | valid |

Each retained task has a result JSON, reconstructable JSONL trace, node/agent final states,
actual placements, InformationObject handoffs, transfer telemetry, operator/model latency and
token telemetry, critical-path latency, and parallel overlap. The observed topology distribution
was one single-agent plan and five multi-agent plans. Multi-agent topology was not an acceptance
gate.

## Natural workflow characteristics

- Video naturally produced both patterns: 795-3 used an explicit model-output handoff between
  two agents, while 848-1 stayed single-agent. Both reduced the full original AV1 video near A4
  and transferred only a contact sheet to A28.
- LongBench multi-document produced the widest workflow: four evidence branches, five agents,
  four model-output handoffs, and a terminal fan-in. The nominal parallelism yielded only about
  10.0 seconds of overlap because two branches shared slow A28 model service.
- LongBench structured used multiple semantic roles but an essentially serial operator chain.
  The 112-byte reduced artifact was the only payload sent to the terminal model.
- MultiHop placed retrieval on the three data-local workers. The multi-source task materialized
  model evidence notes; the reasoning task aggregated three top-1 records and invoked the
  terminal model on the 4090 deployment.

## Quality failures

All three zero-score cases were plan-valid, format-valid, and execution-valid; they are retained
semantic/planning failures rather than harness failures.

- Video-MME 848-1: the 16-frame uniform representation was legal and full-timeline, but it was
  too sparse for the exact chapter-order evidence. This is evidence-selection/temporal-resolution
  failure.
- LongBench multi-document: all four evidence-note calls ended at the declared 256-output-token
  limit, and the final choice was wrong. This is a retrieval/compression/model-reasoning failure;
  the runtime did not truncate any artifact or response.
- MultiHop multi-source: the legal top-1-per-shard retrieval and two-note comparison led to the
  wrong short answer. This is evidence selection plus cross-source reasoning failure.

The task table is intentionally not presented as a benchmark accuracy estimate at `n=1`.

## Invalid attempts and environment audit

Two invalid attempts were excluded from semantic quality analysis and remain fully preserved:

1. `competent-v1` stopped during freeze because the Video 848-1 Planner response hit the cloud
   8192-output-token limit while enumerating roughly one hundred frame outputs and edges. The
   generic `sample_frames` contract is now bounded at 32 frames, preventing an unbounded
   serialisation fan-out without adding task-specific logic.
2. `competent-v2` task 6 initially observed A4 as unavailable after preload, so shard 1 appeared
   unmaterialized. `/state` had been reading and hashing every full blob merely to report
   metadata (about 4.4 seconds on A28 with retained calibration artifacts). It now reads verified
   sidecars and blob sizes only. Post-fix `/state` was 0.01–0.11 seconds, and 200 concurrent live
   probes across the four workers had zero failures. The unchanged task-6 workflow then passed.

Additional environment fixes were verified on all four workers:

- A4, A5, and A28 use the same isolated FFmpeg 8.0.1 build and decode a real AV1-derived
  Video-MME probe before exposing media operators. Full-video `sample_frames` executed in the
  retained Video runs.
- Artifact HTTP routes accept hierarchical deterministic IDs such as
  `clipframe/frame-000001.jpg`; PUT/GET/DELETE were tested on A4, A5, A28, and the 4090 worker.
- The harness now stops on any incomplete runtime result instead of silently retaining it as a
  Planner failure.

## Replay readiness

The strongest later frozen-workflow infrastructure candidates are Video 795-3, LongBench
multi-document, LongBench structured, and MultiHop multi-source because they contain real data
movement or competing local/model placements. This audit does not authorize or start replay.

Because task 6 required one explicitly recorded harness-confounder recovery, this combined set
is suitable for substrate and failure-mode validation but is not claimed as a pristine
publication one-shot matrix. A future publication run should start from the frozen post-fix
runtime and a new untouched evidence directory.
