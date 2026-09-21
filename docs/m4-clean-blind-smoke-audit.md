# M4 Clean Blind real-smoke audit

Date: 2026-09-22 (Asia/Hong_Kong)  
Base revision: `main@029f483`  
Audited implementation revision: `efb2c19`

## Scope and result

M4 was advanced without starting M5 or running the seven-task baseline matrix. The four
requested real smokes completed through the YAML-configured Cloud Blind Planner, live worker
observer, remote workers, external evaluator, persisted result, and JSONL trace. All four final
runs produced format-valid output and benchmark score `1.0`.

| Smoke | Final run ID | Operator path | Model deployment | Materialized bytes | Worker transfer bytes | Runner E2E | Result |
|---|---|---|---|---:|---:|---:|---|
| simple text/model | `m4-smoke-01-simple` | `invoke_model` | `a28-qwen3-vl-m4-32k` | 65 | 65 | 19.460 s | `A`, score 1.0 |
| LongBench structured | `m4-smoke-02-longbench-structured-retry5` | `filter_records → derive_fields → top_k_records → select_fields → invoke_model` | `a28-deepseek-chat` | 5,310,800 | 60 | 22.808 s | `D`, score 1.0 |
| Video-MME | `m4-smoke-03-video-mme-retry2` | `sample_frames → make_contact_sheet → invoke_model` | `a28-qwen3-vl-m4-32k` | 59,245,110 | 185,358 | 46.128 s | `A`, score 1.0 |
| MultiHop-RAG | `m4-smoke-04-multihop-rag-retry3` | `bm25_retrieve → invoke_model` | `a28-deepseek-chat` | 41,221 | 41,286 | 14.436 s | `Yes`, score 1.0 |

The Video-MME smoke uses a question-independent 1 fps, 960 px MJPEG representation covering
the complete 2,038-second timeline. This was necessary because the target device FFmpeg build
exposed AV1/H.264 hardware decoders whose driver surface was unavailable, while its software
MJPEG decoder was executable. It is a real end-to-end modality/transfer/model-consumption smoke,
not a claim about baseline-quality Video-MME accuracy.

## Telemetry audit

Every selected trace has a complete linear parent chain and ends in `run.end`. The trace/result
pair records:

- runner and graph E2E latency;
- every Planner call latency, input/output tokens, and finish reason;
- operator latency;
- model-service latency, input/output tokens, and finish reason;
- initial materialization and runtime artifact transfer bytes, duration, source, and target;
- concrete deployment binding on every `invoke_model` execution;
- finalizer latency/tokens and external evaluator result.

Observed Worker model telemetry was:

| Smoke | Service latency | Input tokens | Output tokens | Finish reason |
|---|---:|---:|---:|---|
| simple | 15.206 s | 67 | 2 | `stop` |
| LongBench | 1.222 s | 111 | 1 | `stop` |
| Video-MME | 21.130 s | 1,235 | 2 | `stop` |
| MultiHop-RAG | 1.343 s | 10,707 | 66 | `stop` |

## Safety and blind-boundary audit

- Planner-visible decisions contain no agent, device, deployment, host, URL, network, or
  physical-location value. Runtime attaches only `AUTO` physical decisions.
- `TaskContract` contains logical artifacts only; placement and worker addresses remain in the
  ignored local runner configuration.
- The Planner does not receive structured plans, gold answers, supporting evidence, evaluator
  metadata, source refs, or infrastructure snapshots.
- `read_artifact` remains available as a size-limited Worker API but is not exposed as a Blind
  Planner tool. Runtime rejects content above the explicit limit with `artifact_too_large`.
- `PARALLEL_DATA_LOCAL` is absent from the physical policy surface.
- Runner startup validates exact Worker operator/deployment surfaces against `EnvironmentSpec`.
- Model actions resolve to a concrete available deployment. Runtime and Worker both preflight
  modality and conservative context bounds; neither path truncates or silently changes inputs.
- Artifact IDs were materialized, transferred between distinct workers, checksum-verified, and
  consumed by the selected model deployment in all four final runs.
- Model and media backend failures now cross the Worker API as typed `model_service_error` and
  `operator_failed` reasons. Pre-fix smoke attempts exposed these two missing boundaries; both
  were fixed and covered by tests before the final selected runs.

## Verification

- `ruff check .`: passed
- strict `pyright`: 0 errors, 0 warnings
- `pytest -q`: 82 passed
- `git diff --check`: passed
- final selected traces: JSON-decodable, parent-chain complete, no Planner decision infra leakage
- repository secrets/device addresses: absent from tracked changes

Persisted local evidence is under `runs/real-smoke/<run-id>/result.json` and `trace.jsonl` for
the four final run IDs above. Runtime outputs and local device configuration are intentionally
Git-ignored.
