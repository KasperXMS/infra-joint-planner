# H1 quality and workflow feasibility

P1 passed before model trials. The initial four Hfast task executions and the two preregistered technical-invalidity replacement executions are all retained in [`trial-outcomes.jsonl`](trial-outcomes.jsonl). These are six unique executions, not six repetitions of the same matrix. The same resident Qwen3.5 27B Q4_K_M Ollama model, 32K effective context, deterministic sampling and short-answer prompt were used throughout; no serving switch occurred.

| Original task | Workflow | Completed | Native score / success | A4→A5 bytes | Resident E2E | Model API latency | Prompt tokens | Finding |
|---|---|---|---|---:|---:|---:|---:|---|
| MultiHop `a647807d…` | G0 | yes | 0 / no | 954,680 | 13.78 s | 3.99 s | 9,708 | `UNKNOWN`; both original annotated support artifacts are among four final evidence items. |
| MMQA `0ed62539…` | G1 | yes | 0 / no | 2,698 | 1.71 s | 1.49 s | 2,892 | `UNKNOWN`; three locally selected text records plus original table. |
| MultiHop `a647807d…` | G1 | no | unscored | 91,164 | 0.63 s | none | none | Source-selected output exceeded Source-B's 65,536-byte read limit; typed HTTP 413, no model call. |
| MMQA `0ed62539…` | G0 | yes | 0 / no | 6,416 | 2.23 s | 1.37 s | 2,818 | `UNKNOWN`; ten source text originals acquired, three centrally selected plus original table. |
| Replacement MultiHop `667f4ac4…` | G0 | yes | 0 / no | 1,150,708 | 21.58 s | 10.38 s | 25,191 | `UNKNOWN`; both original annotated support artifacts among six final evidence items. |
| Replacement MultiHop `667f4ac4…` | G1 | yes | 0 / no | 51,465 | 13.20 s | 11.71 s | 27,485 | `UNKNOWN`; eight locally selected records transferred, but retained trace references source shards rather than article IDs. |

All five completed model calls returned the literal short answer `UNKNOWN`, with two completion tokens each. All five were format-valid but scored 0 by the original independent evaluator. The 413 cell has no task score and is not counted as a model capability failure. Five of six cells completed; zero of five completed cells succeeded. The MultiHop G0 paths retained both gold-annotated supporting artifact IDs, which narrows the failure to evidence content/representation or final model/prompt interpretation rather than a complete miss of those articles. It does not prove the final prompt exposed every relevant sentence. MMQA evidence sufficiency and G1 record-level MultiHop provenance remain unresolved; no oracle labels entered a Worker or model input.

The information-flow distinction was realized: G0 fetched all question-scoped originals before Controller selection, while G1 selected at source before transfer. On the replacement MultiHop task, G1 transferred 51,465 bytes versus G0's 1,150,708 and finished in 13.20 versus 21.58 seconds. **Neither outcome was quality-acceptable**, so those differences are descriptive resource observations, not a successful workflow optimization. The replacement uses a revised study-only Worker read cap, so its times are not matched to the first task's cap.

Each cell's cleanup actions succeeded (HTTP 200/204). There were 227 recorded source actions, 2,257,131 A4→A5 transfer bytes, 68,094 prompt tokens and 10 completion tokens across six executions; five model calls occupied 28.94 seconds of observed API latency. Queue delay and cache state are unknown. The outcome field `study_max_model_concurrency=2` is a configured ceiling, not observed parallelism: all six calls were executed sequentially. No cloud API was used; local GPU monetary cost remains unknown, never zero. P1 setup, index construction and link calibration are separate one-time costs.

**H1 verdict: unsupported for the tested workload and model.** No original task produced two quality-acceptable logical alternatives. This is not a general impossibility result for distributed reasoning or other models. The H2 matrix was not started.
