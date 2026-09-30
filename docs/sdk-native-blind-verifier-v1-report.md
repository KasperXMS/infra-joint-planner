# SDK-native Blind Verifier v1 audit

## Outcome

The single authorized live run did **not** reach terminal synthesis. The Manager's
first reasoning turn and all six requested BM25 actions completed successfully, but
the first harness-owned Blind Verifier request was rejected by the DeepSeek API
before a verifier result was produced:

```text
HTTP 400: This response_format type is unavailable now
```

Primary failure class: **verification**. This is a verifier/backend structured-output
contract confounder, not a retrieval, context, physical-tool, synthesis, stopping, or
benchmark-quality failure. Per the stop rule, no retry, fallback, prompt change,
budget change, Aware run, or replacement run was performed.

## Frozen setting

- Run ID: `01-multihop-multisource-blind-native-verifier`
- Task: `multihop-multisource`
- Benchmark task ID: `multihop-rag-train-9bae0079038050a37a1ae583`
- Benchmark setting: `official_equivalent`
- Logical runtime: existing `OpenAIAgentsNativeRuntime`
- Visibility: `ProfileVisibility.BLIND`
- Manager: unchanged `deepseek-chat`; unchanged instructions hash
  `68b87058ba0a90549cd93a5e18a4a8def2f690e0df089545126a78718892a56e`
- Verifier: independent `deepseek-chat`, temperature 0, SDK structured output,
  no tools, no evaluator/gold access
- Manager/action budget: 12 Manager turns / 18 physical tool-model calls
- Verifier budget: 12 separate calls
- Model deployments: unchanged 32,768 context / 2,048 reserved output on A28
  and strong-4090
- Network: native/unshaped
- Scheduler: unchanged AUTO locality-aware scheduler
- Repetitions: 1; retry/replacement: false
- Fresh stores: new `sdk-native-blind-verifier-v1` roots on A4, A5, A28, and
  strong-4090; historical stores and evidence were not modified
- Dataset materialization and execution occurred on the remote machines. No dataset
  was downloaded to or distributed through the development PC.

The freeze records task/config/data hashes, the static capability contract, and the
exact runtime/verifier source hashes. The live code hashes were:

- `native_agents.py`: `da7c937b2f1009ac85c105235e26a4220331ecd9eb9c352b4d379e4feb5dfcdb`
- `verification.py`: `edf23d0f78435c98757551d3a17a59105c105ab752e364ed43aee620b539db53`

## Implemented verifier contract

The verifier receives only the sanitized `AgentTaskView`, execution-grown logical
graph, sanitized logical observations and failures, produced artifact semantic
metadata, current logical phase, and remaining logical budgets. It receives no
physical profile, worker/device/deployment identity, placement, network state,
load/queue, routes, source references, gold, supporting-evidence annotations, or
private evaluator metadata.

The verifier is invoked by the harness once after a complete Manager tool batch via
the Agents SDK batch-level tool-use callback. It is not exposed as a Manager tool.
Its calls have an independent `max_verifier_calls` budget and do not increment the
18-call physical budget.

- `continue`: its diagnosis and semantic missing requirements are attached to the
  completed batch result for the next Manager turn.
- `ready_for_synthesis`: changes phase from `evidence_collection` to `synthesis`.
  Only `invoke_model` or a terminal response is then legal.
- A failed synthesis model call can be verified as `continue`, restoring
  `evidence_collection`; no automatic repair occurs.
- A terminal answer is rejected unless the verifier has authorized synthesis and it
  exactly matches a successful Manager-owned `invoke_model` result.
- The private benchmark evaluator remains downstream of a valid terminal answer.

## Single-run trace summary

| Metric | Observed |
|---|---:|
| Execution completed | No |
| Final answer | None |
| Evaluator invoked / score | No / N/A |
| Manager reasoning turns | 1 |
| Specialist calls / turns | 0 / 0 |
| Successful tool calls | 6 BM25 |
| Model actions / reached inference | 0 / 0 |
| Verifier calls attempted / completed | 1 / 0 |
| First `READY_FOR_SYNTHESIS` turn | None |
| Tool calls before synthesis | 6 |
| Graph nodes / edges | 6 / 0 |
| Final graph version | 18 |
| Initial transfer bytes | 7,696,522 |
| Action transfer bytes | 0 |
| E2E to typed run failure | 3,922.04 ms |

The Manager requested two independent retrieval intents (Sorcerer and Barbarian)
over every one of the three non-semantic corpus shards. All six ready actions ran in
parallel and succeeded data-locally:

| Branch | Shard worker | Output bytes | Operator latency (ms) |
|---|---|---:|---:|
| Sorcerer shard 1 | A4 | 22,194 | 316.28 |
| Sorcerer shard 2 | A5 | 23,541 | 275.42 |
| Sorcerer shard 3 | A28 | 23,484 | 289.69 |
| Barbarian shard 1 | A4 | 22,193 | 308.64 |
| Barbarian shard 2 | A5 | 23,541 | 538.64 |
| Barbarian shard 3 | A28 | 23,483 | 559.12 |

No action transfer was necessary because B0 selected each shard's data-local worker.
The verifier request happened only after the full six-action batch completed. The
DeepSeek endpoint rejected the SDK structured `response_format`, so there is no
`VerificationResult`, no phase transition, no synthesis action, and no evaluator
event. The persisted `run.failed` event contains the HTTP 400 typed exception.

## Verification

- Full pytest: **291 passed**
- Ruff: **passed**
- Strict Pyright: **passed**
- Added tests cover resource/private isolation, batch-level CONTINUE feedback,
  READY synthesis gating, allowed synthesis model invocation, synthesis-failure
  return to evidence collection, independent verifier accounting, verifier hard
  budget, and evaluator-after-terminal ordering.
- Existing SDK-native tests remain green.
- The 27 live `logical.*` events contain none of `source_ref`, `evaluator_id`,
  `private://`, physical selection IDs, node IPs, bandwidth/RTT, or queue depth.

## Decision

This run does **not** answer whether an explicit Blind Verifier makes the baseline
complete normally. It establishes that the Manager and six-way retrieval batch were
healthy, but the selected `deepseek-chat` endpoint cannot currently serve the
required Agents SDK structured-output verifier request. A future authorized step
must first resolve that generic verifier transport/structured-output contract; this
run must not be counted as a semantic Blind result.

## Durable evidence

- Freeze: `results/sdk-native-blind-verifier-v1/freeze/manifest.json`
- Result: `results/sdk-native-blind-verifier-v1/runs/01-multihop-multisource-blind-native-verifier/result.json`
- Full trace: `results/sdk-native-blind-verifier-v1/runs/01-multihop-multisource-blind-native-verifier/trace.jsonl`
- Summary: `results/sdk-native-blind-verifier-v1/summary.json`

The same evidence remains on strong-4090 under
`/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/app/results/sdk-native-blind-verifier-v1`.
All four experiment Worker processes were stopped after evidence capture; the fresh
artifact stores were retained.
