# Blind Harness v1.3 Validation

Date: 2026-10-02  
Branch: `open-ended-mas-preliminary-v1`  
Frozen behavior revision: `15cdbc3db1ff8e06c1a66ffb934043cd8ebaf068`  
Execution archive revision: `3d9a7f5fd2428ed7aed0f7ae6f50bf412088ec3b`

## Scope

This transition made only the two authorized changes:

1. the Worker model-service HTTP deadline is frozen at 1,200 seconds; and
2. a multiple-choice terminal model request receives a generic requirement derived
   from the task's declared choice labels: its response must begin with exactly one
   canonical label. If the Blind Verifier incorrectly returns `complete` for prose
   that does not satisfy that rule, the verdict is deterministically treated as the
   existing `ready_for_synthesis` state so the Manager can perform another normal
   synthesis turn.

The terminal path never guesses a label from option prose, never consults gold or the
evaluator, and never adds an LLM call or a new Verifier state. Short-text tasks are
unchanged. Manager and Verifier models/instructions, tool schemas, scheduler,
32K/2048 model capability, Blind visibility, and the 20/64/20 budget are unchanged.

The frozen manifest is
`configs/experiments/blind-harness-v1.3.yaml`. Its native runtime SHA-256 is
`01fd1494ac2caeda42e6a523fbdeef1ed5f892ff3b9fbd44fc863929675f4a83`.

## Validation results

All runs used native/unshaped networking, isolated Worker stores, one repetition,
and no retry or replacement. Historical evidence was retained.

| Family / task | Run | Completed | Terminal | Format | Score | Manager / Verifier | Physical calls | Inference | E2E ms | Bytes |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| MultiHop-RAG `multihop-multisource` | `07-multihop-blind-harness-v1.2-gate` | yes | short-text answer | yes | 1.0 | 7 / 7 | 16 | 1 | 171,824.720 | 7,708,104 |
| LongBench-v2 `longbench-multidoc` | `10-longbench-multidoc-blind-harness-v1.2-timeout1200` | yes | `A` | yes | 0.0 | 6 / 6 | 15 | 1 | 189,902.718 | 1,100,195 |
| Video-MME `video-long-payload` | `11-video-long-payload-blind-harness-v1.3` | yes | `A` | yes | 1.0 | 9 / 9 | 10 | 4 | 432,364.444 | 283,666,515 |

All three private evaluators were invoked. Accuracy is reported separately from
execution completion: the LongBench answer was benchmark-valid but semantically
wrong.

### LongBench timeout result

The authorized 1,200-second rerun completed normally in about 190 seconds and reached
one actual model inference after recovering from two typed static context failures.
The earlier 900-second `ReadTimeout` is therefore classified as a transient
model-service failure, not a Planner or budget failure. No additional LongBench run
or debugging was performed.

### Video terminal-contract result

The run sampled the real 282,442,048-byte AV1 source on A4 and performed four real
visual model inferences on A28. The trajectory used additional evidence to resolve
conflicting early candidates, entered synthesis, produced the canonical terminal
label `A`, and received score 1.0. There were no context, tool, or runtime failures.
Logical privacy auditing found no physical/private leakage.

## Regression and freeze decision

The full suite passed (317 tests), Ruff passed, and strict Pyright passed. Tests cover
arbitrary declared choice labels, recovery from an invalid prose completion on a
subsequent normal Manager turn, deterministic extraction, and an unchanged
short-text path. Because the MultiHop terminal contract is short text, its shared
path is unchanged; the cheap regression is covered by the non-choice unit test and
the successful preserved MultiHop execution was not rerun.

The cross-family completion gate is satisfied:

```text
MultiHop -> terminal synthesis -> evaluator
LongBench -> terminal synthesis -> evaluator
Video-MME -> terminal synthesis -> evaluator
```

`blind-harness-v1.3` is therefore the frozen positive Blind baseline. Blind baseline
engineering stops here.
