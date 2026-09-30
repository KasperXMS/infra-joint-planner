# Blind three-family validation v1

## Outcome

Stage 2 stopped at **Success A**. The positive MultiHop Blind baseline was established
under `blind-harness-v1`, but validation exposed a generic terminal-format bug and the
required regression run under the corrected `blind-harness-v1.1` did not complete.
The regression failure is a valid workflow-composition/stopping failure, not a runtime,
privacy, evaluator, or physical-infrastructure confounder. Therefore LongBench was not
rerun under v1.1, Video-MME was not started, and no Aware experiment was run.

## Frozen harnesses

| Harness | Frozen revision | Purpose |
|---|---|---|
| `blind-harness-v1` | `f263aaa89174f047869c3ed865c5c0ba95cb942b` | Original positive MultiHop completion |
| `blind-harness-v1.1` | `ae052c00d30fddb0c25c8866efa37124945a1e02` | Same prompts, tools, models, budgets, scheduler, and Verifier; adds only conservative deterministic choice-label extraction from the successful terminal model output |

The v1 manifest was preserved byte-for-byte so historical run configs remain
reconstructable. The v1.1 manifest SHA-256 is
`eb6bd6d218d719c7edb6d7f47b47fbab6b5e670ec28436e01c1972b4865ac9d6`.
Both use `ProfileVisibility.BLIND`, 12 Manager turns, 18 physical tool/model calls,
12 Verifier calls, DeepSeek Manager/Verifier, 32,768 context, 2,048 reserved output,
the same 12 generic operators, and the same locality-aware physical scheduler.

## LongBench validation attempts

| Attempt | Revision | Outcome | Classification |
|---|---|---|---|
| adapter preflight | `3651410` | Rejected before materialization because the new Stage-2 runner called the existing adapter with the wrong argument order | invalid runner-wiring confounder; fixed generically |
| attempt 2 | `546b31c` | Four BM25 actions ran, then the Verifier used an obsolete `response_format` path | invalid environment confounder: the archive reused an editable venv importing another checkout |
| attempt 3 | `b5cbada` | Reached a successful terminal model candidate, but exact-string terminal validation rejected the model's leading choice plus explanation | invalid generic terminal-format confounder; fixed by v1.1 |

Attempt 3 used the faithful `longbench-multidoc` task and native/unshaped network. It
ran for 253,820.559 ms by trace timestamps, made 10 Manager turns, 13 tool calls and
4 model calls, reached inference once, invoked the Verifier 10 times, and grew a
17-node/25-edge graph at version 51. It transferred 1,576,998 bytes. Three earlier
synthesis requests failed context preflight at 1,083,287, 129,767, and 40,110
estimated input tokens. A fourth, bounded request reached inference and produced a
candidate beginning with `A` plus justification. The unchanged choice evaluator
requires a canonical label, but no evaluator ran because the harness rejected the
terminal text first.

The v1.1 change performs no semantic reasoning: it accepts only an exact declared
label or an unambiguous leading declared label with explicit formatting, emits whether
format extraction occurred, and fails closed on ambiguous text such as `A or B`.
The answer must still derive from a successful Manager-owned `invoke_model` result.

## Required MultiHop regression under v1.1

- Run ID: `06-multihop-blind-harness-v1.1-regression`
- Execution revision: `4c83d2cadd1b940e38fbcf9682ac22916241bb97`
- Task: the same benchmark-faithful `multihop-multisource` task used by the positive
  baseline
- Data: complete 609-document corpus and query file on strong-4090; no dataset bytes
  passed through the development PC
- Worker stores: four new `blind-3family-multihop-v1.1` roots, empty before
  materialization
- Network: native/unshaped
- Repetitions/retry/replacement: `1 / false / false`

### Observed trajectory

1. Turn 1 submitted six cross-shard BM25 actions with `text_field=text`. All failed
   with the typed validation error `document field must be text: text`; the static
   artifact schema exposed `body` as the valid text field.
2. Verifier call 1 identified the mismatch. The Manager corrected it without hidden
   repair and materialized six shard-covering retrieval artifacts.
3. Verifier call 2 first returned `ready_for_synthesis`.
4. The first synthesis request failed before inference at 139,051 estimated input
   tokens versus the 32,768 context window. A duplicate output ID also caused one
   typed semantic-validation failure.
5. A later bounded model action reached real inference but returned a non-answer,
   reporting that its selected evidence did not contain the Sorcerer guide.
6. The Manager then retrieved more targeted Sorcerer and Barbarian guide artifacts
   and projected their fields, but consumed the 18-call budget before a model could
   synthesize those new artifacts. The final Verifier verdict remained `continue`.

### Metrics

| Metric | Value |
|---|---:|
| Execution completed | false |
| Evaluator invoked | no |
| Manager reasoning turns | 12 |
| Specialist reasoning turns | 2 |
| Tool calls | 16 |
| Model calls | 2 |
| Calls reaching model inference | 1 |
| Subagent calls | 1 |
| Verifier calls | 11 |
| First `ready_for_synthesis` | verifier call 2 |
| Trace elapsed time | 183,229.413 ms |
| Initial transfer bytes | 7,696,522 |
| Action transfer bytes | 22,194 |
| Total transfer bytes | 7,718,716 |
| Final graph | version 54; 18 nodes; 9 edges |
| Logical privacy scan | pass; no findings |

Primary failure class: **workflow composition / stopping**. Secondary factors were a
recoverable context-sizing error and hard budget exhaustion. The physical scheduler
and Workers executed normally, the one feasible model call reached inference, all
failures were typed, and the logical trace contained no physical/private leakage.
Guaranteeing completion would now require prompt/strategy tuning, task-specific
retrieval guidance, a budget change, or a retry; all are outside the frozen Stage-2
protocol.

## Gate decision

The three-family gate did not pass. `blind-harness-v1.1` did not revalidate the
previous MultiHop completion in its single permitted run, so continuing to a new
LongBench v1.1 run or Video-MME would no longer satisfy the ordered validation gate.
The stopped cells are:

- LongBench-v2 representative under v1.1: **not run**
- Video-MME representative under v1.1: **not run**
- Blind/Aware Fast/Slow preliminary: **not run**

Durable evidence remains on strong-4090. Sanitized local copies (freeze, result,
trace, summary only) are under ignored `results/blind-3family-validation-v1-longbench-attempt3`
and `results/blind-3family-validation-v1.1-multihop-regression`; private task/evaluator
files and datasets were not copied locally.
