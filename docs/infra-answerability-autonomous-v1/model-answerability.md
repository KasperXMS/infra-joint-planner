# Model answerability diagnostics

The resident Qwen3.5 27B Q4_K_M model was left unchanged. The backend was Ollama 0.34.0 with a 32,768-token context. Diagnostic conditions were frozen before scoring: grounded system instruction with `think=false`/128 output tokens; original system instruction with `think=true`/512; grounded system instruction with `think=true`/512. Temperature was 0 and top-p 1. Two replacement-MultiHop conditions were preregistered only if the first six had no success. The original H1 `think=false` calls were historical baselines, not rerun in this study. Complete request, prompt and model hashes appear in the [primary manifest](diagnostic-manifest-public.json) and [contingency manifest](contingency-manifest-public.json).

| Condition | Original MultiHop | Original MMQA | Replacement MultiHop |
|---|---|---|---|
| Grounded, no thinking | `UNKNOWN`, score 0 | `UNKNOWN`, score 0 | `UNKNOWN`, score 0 |
| Original, thinking 512 | Length stop, no final answer | `UNKNOWN`, score 0 | Not scheduled |
| Grounded, thinking 512 | Substantive wrong answer, score 0 | Length stop, no final answer | Substantive wrong answer, score 0 |

All eight task-level calls completed transport without error; six produced format-valid answers and two exhausted their 512-token output budget without a final answer. The two substantive answers were wrong under the independent original evaluator. Task-level totals: 88,028 prompt tokens, 1,800 completion tokens and 33.08 seconds summed HTTP wall time. This is request wall time, **not** GPU service time or task E2E. Local GPU monetary cost is unknown; no cloud API was used. Three short synthetic probes answered correctly; their 0.25–0.79-second request latencies and token counts are in [protocol-probes-public.json](protocol-probes-public.json).

The task diagnostic runner did not import or read the private evaluator. A separate scorer applied the original evaluator after each batch. Public redacted [primary outcomes](diagnostic-outcomes-public.jsonl), [contingency outcomes](contingency-outcomes-public.jsonl), and [scores](diagnostic-scores-public.json) preserve all results. Raw requests and responses remain at `experiment-machine:task-diagnostics/private` and `experiment-machine:task-diagnostics-contingency/private`; neither is in Git. The eight-call task diagnostic budget and three-of-20 short probes were consumed as planned. No task request used gold or hidden supporting-document lists.

**Gate result: fail.** No legitimate task-solving path passed the original evaluator. The synthetic probes establish basic protocol capability only; they do not meet the task answerability gate. Further task-level retries would exceed the fixed diagnostic budget or become correctness-driven tuning.
