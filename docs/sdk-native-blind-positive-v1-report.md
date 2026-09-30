# SDK-native Blind positive-baseline attempt v1

## Outcome

The 2048-output deployment calibration passed on both formal model deployments, and the formal
deployment/static-capability contract was updated from 32K/1024 to 32K/2048. The subsequent
single `multihop-multisource` Blind run did **not** produce a positive terminal answer.

The new primary failure is **stopping (over-expansion)**, with hard **budget exhaustion** as the
terminal condition. There was no context/preflight failure, but the Manager never submitted a
model action, so the benchmark run itself never reached model inference.

No retry, replacement, prompt change, task change, budget increase, Aware run, or matrix run was
performed.

## 2048-output calibration

Both nodes used the current official `qwen3.8-27b-v1` tag, the same model/blob and Q4_K_M
quantization, the same Ollama OpenAI-compatible runtime, and `num_ctx=32768`. Each node received
one clean deterministic synthetic request with a 30,720-byte conservative input envelope and
`max_output_tokens=2048`.

| Deployment | Formal preflight | Backend inference | Actual input/output tokens | Output / finish | Service latency | OOM/error | Truncation signal |
| --- | --- | --- | ---: | --- | ---: | --- | --- |
| A28 | PASS | yes | 21,092 / 2 | `OK` / `stop` | 396,097.22 ms | none | none observed |
| strong-4090 | PASS | yes | 21,092 / 2 | `OK` / `stop` | 123,823.93 ms | none | none observed |

Raw calibration evidence remains on the model nodes:

```text
A28:
/mnt/ssd/sdk-native-blind-positive-v1/calibration/a28-output-2048.json

strong-4090:
/home/super/xiaoming/sdk_native_blind_positive_v1/calibration/strong-output-2048.json
```

Both records report `status=pass`, non-empty output, `finish_reason=stop`, no OOM, no backend
failure, and no observed silent truncation. Planner/benchmark calls during calibration were zero.

## Contract update

The current formal source environment now declares both deployments as:

```yaml
context_window: 32768
reserved_output_tokens: 2048
```

The new isolated A28 and strong-4090 Worker configurations declare the same values, and their
live `/state` surfaces were verified before the run. Ollama `num_ctx` remains 32768.

The projected Blind-visible contract is still anonymous and contains no quality tier:

```yaml
capability_class: model-class-01
context_window: 32768
reserved_output_tokens: 2048
quality_classes: []
```

An `ExecutionRequirements` request for text, `min_context_tokens=1`, model capability, and
`reserved_output_tokens=2048` now returns:

```text
matching_model_classes = ('model-class-01',)
```

Thus the previous static 2048-output incompatibility is removed.

## Single Blind baseline run

- Configuration/code commit: `0d2ec17d197af0fbac2bf4c1b20220c453f228c6`
- Runtime: `OpenAIAgentsNativeRuntime`
- Visibility: `ProfileVisibility.BLIND`
- Task: the same frozen `multihop-multisource` task and three-shard representation
- Network: native/unshaped
- Scheduler: unchanged locality-aware physical scheduler
- Budget: 12 Manager turns, 18 total tool/model calls, 8 specialist turns, 4 created and 2
  active specialists
- Worker stores: new isolated empty stores
- Repetitions: 1; retry/replacement: false

| Metric | Observed value |
| --- | --- |
| Execution completed | no |
| Final answer | none |
| Evaluator score / format validity | not evaluated / not applicable |
| Manager reasoning turns | 10 |
| Successful tool executions | 18 |
| Model calls | 0 |
| Reached model inference | 0 |
| Context/preflight failures | 0 |
| Subagent calls | 0 |
| E2E latency | 21,156.39 ms |
| Initial materialization | 7,696,522 bytes |
| Action-time transfer | 0 bytes |
| Final graph | version 54; 18 nodes; 8 edges |
| Terminal failure | `logical_loop_failed: tool/model call budget exceeded` |

The graph's 18 successfully executed nodes were:

- 10 `bm25_retrieve` calls;
- 3 `select_fields` calls;
- 3 `read_artifact` calls;
- 2 `filter_records` calls.

The Manager first searched all three shards, repeated broader Sorcerer/Barbarian retrieval,
inspected projected metadata, found the relevant shard-3 documents, then issued additional
focused retrieval and filtering branches. All physical tool executions succeeded and stayed
data-local. After using all 18 calls, it continued requesting more actions, which were returned as
typed `budget_exhausted` observations. It never switched from evidence expansion to a model
synthesis action.

There are therefore no `logical.model.requirements` or `logical.model.outcome` events in this
benchmark trace. The new 2048 contract is demonstrably feasible from calibration and static
projection, but this particular Blind Manager trajectory did not exercise it.

## Failure classification

Primary: **stopping** — specifically over-expansion and failure to transition from sufficient
evidence acquisition to synthesis.

Terminal/secondary: **budget** — all 18 available action calls had already been spent on successful
tools when the loop terminated.

Not observed:

- context failure;
- retrieval execution failure;
- tool execution failure;
- deployment/runtime failure;
- synthesis failure after inference (synthesis was never attempted).

The positive baseline objective was not achieved. The requested stop rule was applied without a
second run or semantic tuning.

## Durable evidence

```text
/home/super/xiaoming/sdk_native_blind_positive_v1/evidence/
  freeze/manifest.json
  private/task-contract.json
  private/private-evaluation.json
  runs/01-multihop-multisource-blind-native/result.json
  runs/01-multihop-multisource-blind-native/trace.jsonl
  summary.json
```

Evidence digests:

```text
result.json  7849c00faf82112a36ce92b156eefa9db646aa1eb70e56fad8c94312771b0fb4
trace.jsonl  a4ecdf24c1100528eb1cde683a6be876cc346ac5b43e5970a5042b5fba257793
```
