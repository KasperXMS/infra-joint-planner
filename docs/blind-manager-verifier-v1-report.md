# Blind Manager + Verifier v1 report

## Outcome

The explicit resource-blind Verifier made the SDK-native Manager terminate normally,
but the run did **not** obtain a positive benchmark score.

The accepted live run completed its execution graph, reached real model inference,
materialized a terminal answer, received a final `complete` verdict from the Verifier,
and invoked the unchanged private evaluator. The terminal answer was semantically
correct (`Yes`) and cited both required guide passages. The official evaluator still
returned `0.0` because the model rendered the answer as Markdown `**Yes.**`: the
benchmark's faithful scoring rule lowercases and splits on whitespace but does not
strip punctuation or Markdown, so `**yes.**` does not intersect the private gold token
`yes`.

Primary residual failure class: **synthesis/output-contract compliance**. Two earlier
model actions encountered recoverable context preflight failures, but they were not the
terminal cause. Retrieval, verification, tool execution, physical feasibility,
stopping, and hard-budget enforcement all behaved correctly.

No retry, replacement, prompt tuning, budget increase, Aware run, or matrix run was
performed after this accepted cell.

## Frozen setting

- Run ID: `05-multihop-blind-verifier-strict-state`
- Code revision: `f263aaa89174f047869c3ed865c5c0ba95cb942b`
- Task: `multihop-multisource`
- Benchmark task ID: `multihop-rag-train-9bae0079038050a37a1ae583`
- Task bundle SHA-256:
  `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`
- Runtime: `OpenAIAgentsNativeRuntime`
- Visibility: `ProfileVisibility.BLIND`
- Manager: unchanged `deepseek-chat`
- Verifier: independent `deepseek-chat`, temperature 0, required
  `submit_verification` function-tool transport
- Budget: 12 Manager turns / 18 physical tool-model calls / 12 Verifier calls
- Subagent limits: 8 turns / 4 created / 2 active
- Model deployments: unchanged 32,768 context / 2,048 reserved output
- Scheduler: unchanged AUTO locality-aware physical scheduler
- Network: native/unshaped
- Repetitions: 1; retry/replacement: false
- Worker stores: isolated `sdk-native-blind-verifier-v5` roots on all four workers,
  empty before materialization

The complete corpus and queries remained on strong-4090 and the experiment workers.
They were not downloaded to or relayed through the development PC. Only the sanitized
freeze manifest, result, trace, and summary were copied to the local ignored evidence
directory after the run.

## Verifier behavior

The Verifier ran after each completed Manager action batch. It received only the
sanitized task objective, logical graph, semantic action/observation views, produced
artifact metadata, typed failures, phase, and remaining logical budget. It did not
receive worker/device/deployment identity, placement, bandwidth, RTT, route, load,
queue, gold, supporting-evidence annotations, source references, or evaluator metadata.

The final three-state contract was:

1. evidence sufficient but no successful candidate: `ready_for_synthesis`;
2. successful task-answer candidate: `complete`;
3. a concrete remaining gap, conflict, failed synthesis, or recoverable blocker:
   `continue`.

The first verdict, after the six cross-shard BM25 calls, was
`ready_for_synthesis`. Two oversized synthesis attempts then failed before transfer at
68,872 and 69,721 estimated input tokens. The Verifier correctly returned `continue`,
and the Manager used generic projection, aggregation, and retrieval actions to create
smaller model-consumable evidence. The final model call consumed 3,381 input tokens,
produced 292 output tokens with `finish_reason=stop`, and the Verifier returned
`complete`.

Finalization deterministically selected that successful Manager-owned model output.
It did not call another LLM, rewrite the answer, normalize it, or consult the private
evaluator.

## Accepted run metrics

| Metric | Observed |
|---|---:|
| Execution completed | Yes |
| Terminal answer materialized | Yes |
| Format valid | Yes |
| Evaluator invoked / score | Yes / 0.0 |
| Manager reasoning turns | 6 |
| Verifier calls | 6 |
| First `READY_FOR_SYNTHESIS` | Manager turn 1 / graph version 18 |
| Tool calls before first synthesis | 6 |
| Successful tool executions | 15 |
| Model actions | 3 |
| Reached model inference | 1 |
| Context/preflight failures | 2 |
| Subagent calls / turns | 0 / 0 |
| Physical action calls | 18 / 18 |
| Final graph nodes / edges / version | 18 / 16 / 54 |
| E2E latency | 167,532.15 ms |
| Initial transfer bytes | 7,696,522 |
| Action transfer bytes | 5,204,596 |
| Total transferred bytes | 12,901,118 |
| Successful model service latency | 132,956.39 ms |

The terminal candidate began:

> **Yes.** Both guides are Polygon articles for Diablo 4 Season 2 ... and explicitly
> state they provide simplified versions of the builds.

The two cited evidence passages correctly stated that the respective Sorcerer and
Barbarian guides had "gathered and simplified" the best builds for season 2.

## Benchmark-score audit

The evaluator was not changed. Its current faithful benchmark rule is:

1. if the exact wrapper `The answer to the question is "..."` exists, extract its
   contents; otherwise evaluate the entire terminal output;
2. lowercase and split prediction and gold on whitespace;
3. score 1 only when the token sets intersect.

For this run:

```text
private gold token set: {yes}
prediction's first token: **yes.**
intersection: empty
score: 0.0
```

This is not evidence that the semantic answer was wrong. It is evidence that the
unchanged terminal model did not obey the benchmark's unusually narrow answer syntax,
and that the unchanged evaluator intentionally performs no punctuation or Markdown
normalization. Treating the run as score 1 would require changing the evaluator or
post-processing the terminal answer, both forbidden in this stage.

## Failure classification

- **Retrieval:** succeeded. Six independent BM25 calls covered both subjects across
  all three non-semantic corpus shards; later compact retrieval produced the two guide
  artifacts used by the final model.
- **Verification:** succeeded. It made a timely first-turn transition, diagnosed both
  context failures, and emitted `complete` after a real candidate existed.
- **Context:** two recoverable pre-inference failures occurred; the Manager adapted to
  inputs that fit the 32K/2048 deployment contract.
- **Tool execution:** all 15 tool calls succeeded.
- **Workflow composition:** recovered from oversized synthesis inputs without hidden
  repair or rollback.
- **Stopping:** succeeded at Manager turn 6; no post-completion expansion occurred.
- **Synthesis (primary residual issue):** semantically correct, but not compatible with
  the evaluator's literal whitespace-token syntax because of Markdown/punctuation.
- **Budget:** exactly 18 physical calls were used. The successful inference and
  deterministic terminal selection occurred within the fixed budget.

## Validation and durable evidence

At the accepted revision:

- full pytest: **298 passed**
- Ruff: **passed**
- strict Pyright: **0 errors, 0 warnings, 0 informations**

Sanitized evidence is retained at:

- freeze: `results/sdk-native-blind-verifier-v5/freeze/manifest.json`
- result:
  `results/sdk-native-blind-verifier-v5/runs/05-multihop-blind-verifier-strict-state/result.json`
- trace:
  `results/sdk-native-blind-verifier-v5/runs/05-multihop-blind-verifier-strict-state/trace.jsonl`
- summary: `results/sdk-native-blind-verifier-v5/summary.json`
- remote durable root:
  `/home/super/xiaoming/blind-verifier-v5-f263aaa/app/results/sdk-native-blind-verifier-v5`

The private task contract/evaluation files remain only in the remote private evidence
directory and were not copied into the local workspace. All four isolated Worker
processes were stopped after the result was persisted; their artifact stores and all
historical evidence were retained.

## Stop decision

The narrow research question has a split answer:

- **Control-plane completion:** yes. The explicit Blind Verifier caused the
  SDK-native Blind baseline to collect evidence, recover from context failures,
  synthesize once successfully, and stop normally.
- **Positive benchmark score:** no. The remaining failure is terminal answer-format
  compliance under the unchanged official evaluator.

Per the stage stop rule, no additional Blind run and no Aware experiment was started.
