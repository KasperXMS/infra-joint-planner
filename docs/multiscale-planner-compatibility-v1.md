# Multi-scale Planner compatibility v1

All four frozen deployment slots completed their one bounded compatibility sequence in `run-001` and were admitted to the real benchmark. Admission required context integrity, fail-closed overflow, and execution safety; it did not require zero model/schema errors. These are synthetic protocol observations, not benchmark results or estimates of general competence. No compatibility scenario was selectively rerun because of a poor answer.

The `qwen35-27b` slot is actually **Qwen3.8-27B Q4_K_M**, established by matching official model/projector descriptors and original creation metadata. Its immutable alias is retained in traces. See [provenance correction](../analysis/multiscale-planner-evaluation-v1/model-provenance-correction.json). The Qwen3.5-27B survey reference was not deployed.

## Context integrity and overflow

Each deployment used a 32,768-token context and reserved 2,048 output tokens, leaving a 30,720-token input budget. Full native template/tools/history rendering with `truncate=false`, followed by resident `/tokenize`, produced exactly the following counts on **every candidate**:

| Target input tokens | Counted input tokens | Outcome | Inference requests per candidate |
| --- | --- | --- | ---: |
| 8,192 | 8,192 | Allow, exact native rendering/count | 0 |
| 16,384 | 16,384 | Allow, exact native rendering/count | 0 |
| 24,576 | 24,576 | Allow, exact native rendering/count | 0 |
| 30,720 | 30,720 | HTTP 200; provider usage exactly 30,720 | 1 |
| 30,721 | 30,721 | `context_limit_exceeded` before inference | 0 |

The smaller three tiers validate rendering/counting only; they are not three additional long-context inference trials. The 30K trial tests the provider's consumed prompt count and beginning/middle/end sentinel recall. Three models echoed all sentinels; Qwen3.5-4B did not, while its provider count still exactly matched the complete rendered prompt. Recall failure remains a model observation and was not reclassified as truncation. Overflow was blocked on all four deployments, and every successful inference response in the sequence matched its preflight count.

Qwen nonthinking requests require OpenAI `reasoning_effort: "none"` to correspond to native `think: false` in the preflight request. The adapter records that mapping; an extra Chat Completions `think: false` alone would not establish it. Ministral uses its nonreasoning Instruct variant without an unsupported reasoning-effort field. The Qwen resident 27B renderer reports `qwen3.8` while its parser reports `qwen3.5`; the full identity comes from provenance, not parser naming.

## Native function calling, recovery, and terminal behavior

The existing persistent native SDK runtime received the unchanged synthetic compatibility scenario, strict raw-call JSON Schema validation, a typed read failure, tool continuation, and terminal contract. Its Manager turn cap was six, tool/model-call cap six, and SDK/provider retries zero. Invalid raw calls could recover within that same cap and were not repaired or executed.

| Actual model | Schema attempts / valid / failed | Typed failure observed / recovered | Native terminal success | Model error | 30K all sentinels |
| --- | ---: | --- | --- | --- | --- |
| Qwen3.5-4B | 4 / 3 / 1 | Yes / Yes | Yes | None | No |
| Qwen3.5-9B | 6 / 4 / 2 | Yes / Yes | No successful terminal receipt | `AgentLoopError` | Yes |
| Ministral 3 3B Instruct | 2 / 2 / 0 | Yes / No | No successful terminal receipt | `UserError` | Yes |
| Qwen3.8-27B, frozen 27B slot | 3 / 3 / 0 | Yes / Yes | Yes | None | Yes |

The 4B trace records five Manager turns, three successful gateway calls (`read_artifact` twice, `invoke_model` once), and recovery after its invalid call. The 27B trace records four Manager turns with the same three-call sequence. Their successful native results both have zero Specialist and Verifier calls because this synthetic scenario does not exercise those roles. The 9B trace records six completed Manager reasoning events and four gateway calls (`read_artifact` twice and `invoke_model` twice), but no successful terminal result. Ministral records one completed Manager reasoning event and one gateway read before the recorded `UserError`. Absence of a native result is reported as unsuccessful terminal completion, not a fabricated usage record. Error class alone does not establish a more specific provider/model cause.

Strict schema validation recorded 15 calls in total: 12 valid and three rejected. All 20 inference responses were HTTP 200 with known token usage. Thus the recorded 9B/Ministral runtime errors are distinguishable from an HTTP provider rejection; no HTTP provider failure occurred in this compatibility set. Zero recorded schema failures for Ministral does not imply its tool loop or terminal contract succeeded.

Read-only inspection of the existing Ministral response establishes two allowed function names (`read_artifact`, `invoke_model`), both schema-valid, with distinct nonempty call IDs and `finish_reason: tool_calls`. Only the read reached the gateway. The captured receipt retains `UserError` but not its exception message or traceback, so its precise origin remains **unknown**: report it as an SDK/runtime/tool-execution error, not a proven model-ability or parser defect. For 9B, all six native Manager responses requested another tool call and exhausted the six-turn allowance without a terminal response. The runtime maps SDK `MaxTurnsExceeded` to `AgentLoopError`; legal turn-budget exhaustion is therefore the supported inference from the saved responses, counter, and source, while the original exception message was not retained. Neither diagnosis required new inference or replay.

## Measured sequence resources

These values cover the entire bounded compatibility sequence, including its one 30K inference, synthetic SDK continuation, and helper rendering/counting. Elapsed time excludes model download/load performed before the sequence. Cached tokens are included within input tokens. They are not steady-state per-request latency or benchmark cost estimates.

| Actual model | Inference / helper requests | Input tokens | Output tokens | Cached input tokens | Sequence elapsed seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3.5-4B | 6 / 103 | 59,011 | 266 | 22,398 | 15.806 |
| Qwen3.5-9B | 7 / 111 | 65,924 | 792 | 28,778 | 17.156 |
| Ministral 3 3B Instruct | 2 / 71 | 35,655 | 101 | 2 | 8.022 |
| Qwen3.8-27B, frozen 27B slot | 5 / 95 | 53,168 | 202 | 16,746 | 18.888 |

Every candidate stayed below its limits of eight inference requests, 512 helper requests, and 900 seconds. All four receipts have empty `safety_errors`. GPU prices, full monetary cost, and compatibility-specific per-kernel/service work are unknown in these receipts; inference-request count and token usage are not substituted for those missing measures. Synthetic gateway calls do not count as production Physical Scheduler inference work.

## Evidence and limits

Private requests, responses, rendered prompts, native results, and traces remain on the experiment machine under the isolated `run-001/compatibility` namespace. This report was prepared from numeric receipt fields and event counts; raw payloads were not downloaded. Receipt SHA-256 values are:

| Immutable slot | Receipt SHA-256 |
| --- | --- |
| `qwen35-4b` | `2f28642b2fb6b767b2427696d4d7fddbd99f636a09c6c737007f4e3ce69ac0bc` |
| `qwen35-9b` | `da967197f666004018d1c52c545375926fe21ad47ee1620715b83eb08ab2019a` |
| `ministral3-3b` | `89a01136c139ffd33de1036ee3775ff7e30ef4840cb989911d1b7fb2be87b169` |
| `qwen35-27b` | `793c2359cf37a125d260ecb05a7b26f3ef45424af8358c8c2e0ee36b8dffc0f2` |

This finite scenario set establishes safe admission for the recorded deployments. The 4B/9B errors remain part of evaluation, and the 27B result cannot be interpreted as a pure Qwen3.5 parameter-size effect. Compatibility success does not imply benchmark correctness or justify a general reliability threshold. Real benchmark outcomes are reported separately.
