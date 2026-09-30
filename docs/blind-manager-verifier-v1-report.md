# Blind Manager + Verifier v1 report

## Decision

The explicit Blind Verifier did **not** make the fixed-budget SDK-native Blind
baseline complete normally on `multihop-multisource`.

The first live attempt exposed an invalid verifier transport contract: the DeepSeek
endpoint rejected the Agents SDK `response_format` request before returning a
verdict. The generic transport was then changed to one schema-constrained,
required `submit_verification` function call. That change passed the full test and
type/lint suite and was frozen in commit `1a0d5b2` for a new, isolated run.

The second run removed the transport confounder. All 12 verifier calls completed,
but every verdict was `continue`. The Manager used all 18 physical action calls on
retrieval, aggregation, metadata projection/inspection, and document filtering. It
never invoked a model, never entered synthesis, and exhausted all 12 Manager turns.
There was no terminal answer and therefore the private evaluator was correctly not
invoked.

Primary failure class: **workflow composition**. Secondary classes:
**stopping/over-expansion** and **hard budget exhaustion**. This was not a context,
deployment, network, artifact-store, tool-execution, or evaluator failure.

## Frozen second-run setting

- Run ID: `02-multihop-multisource-blind-native-verifier-function-tool`
- Code revision: `1a0d5b27cba01cabca158f57be433961a51bbd4a`
- Task: `multihop-multisource`
- Benchmark task ID: `multihop-rag-train-9bae0079038050a37a1ae583`
- Benchmark setting: `official_equivalent`
- Task bundle SHA-256:
  `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`
- Runtime: `OpenAIAgentsNativeRuntime`
- Visibility: `ProfileVisibility.BLIND`
- Manager: unchanged `deepseek-chat`; instructions SHA-256
  `68b87058ba0a90549cd93a5e18a4a8def2f690e0df089545126a78718892a56e`
- Verifier: independent `deepseek-chat`, temperature 0, required function-tool
  result transport
- Budget: 12 Manager turns / 18 physical tool-model calls / 12 verifier calls
- Subagent limits: 8 turns / 4 created / 2 active
- Deployments: unchanged 32,768 context / 2,048 reserved output on A28 and
  strong-4090
- Scheduler: unchanged AUTO locality-aware scheduler
- Network: native/unshaped; no `netem` or `tbf` qdisc was present
- Repetitions: 1; retry/replacement: false
- Stores: new `sdk-native-blind-verifier-v2` roots on all four workers; all were
  empty before materialization
- Dataset materialization and execution occurred on strong-4090 and the remote
  workers. The dataset was not downloaded to or relayed through the development PC.

All four workers ran the same clean checkout and exact commit. Worker `/state`
reported identical operator-contract digests; A28 and strong-4090 both exposed the
expected 32K/2048 model contract.

## Verifier contract and isolation

The harness invokes the Verifier once after a completed Manager tool batch. The
Verifier is not a Manager-visible tool and its calls do not consume the 18-call
physical budget. Its required function tool accepts exactly `VerificationResult`
and stops after the first valid submission. Invalid or unavailable verdict
transport is now emitted as `logical.verification.failed` and surfaced as a typed
`AgentLoopError`.

The Verifier input contains the sanitized task view, execution-grown logical graph,
logical observations/failures, produced artifact semantic metadata, phase, and
remaining logical budgets. A scan of all second-run `logical.*` events found none
of `source_ref`, `evaluator_id`, `private://`, gold/supporting-evidence fields,
physical selections, deployment IDs, node IPs, bandwidth, or queue state.

`continue` feedback is returned to the next Manager turn. A
`ready_for_synthesis` verdict would restrict the following phase to
`invoke_model` or the final response. The private evaluator remains downstream of
a valid terminal answer only.

## Second-run execution

| Metric | Observed |
|---|---:|
| Execution completed | No |
| Final answer | None |
| Evaluator invoked / score | No / N/A |
| Manager reasoning turns | 12 |
| Specialist calls / turns | 0 / 0 |
| Verifier calls attempted / completed | 12 / 12 |
| First `READY_FOR_SYNTHESIS` turn | None |
| Physical action calls | 18 |
| Additional calls rejected at budget gate | 13 |
| Model actions / reached inference | 0 / 0 |
| Context/preflight failures | 0 |
| Graph nodes / edges / final version | 18 / 12 / 54 |
| Initial transfer bytes | 7,696,522 |
| Action transfer bytes | 92,107 |
| Total transferred bytes | 7,788,629 |
| Observed trace E2E | 53,350.33 ms |
| Manager reasoning latency | 23,654.55 ms |
| Verifier latency | 26,616.21 ms |
| Terminal failure | `manager turn budget exhausted` |

The 18 executed actions were:

| Stage | Calls | Result |
|---|---:|---|
| Cross-shard BM25 for Sorcerer and Barbarian | 6 | All succeeded |
| Aggregate the three hit sets per subject | 2 | Both succeeded; 92,107 transfer bytes |
| Filter candidate hits | 2 | Both succeeded |
| Project candidate metadata | 2 | Both succeeded |
| Read projected metadata | 2 | Both succeeded |
| Filter full shards by discovered document identity | 4 | All four admitted calls succeeded |

The Manager correctly discovered candidate Polygon Sorcerer and Barbarian guide
identities. It then spent the remaining physical budget locating their full records
across non-semantic hash shards. In the six-action extraction batch only four calls
could be admitted under the remaining budget; two were rejected. The resulting
evidence included one non-empty Sorcerer document artifact but no materialized
Barbarian body. The Verifier therefore continued to report missing body evidence.

After the physical budget reached zero, the Manager issued 13 more logical tool
requests across the remaining turns. All were correctly rejected before physical
execution with `budget_exhausted`. The Verifier continued to run after those failed
batches and never authorized synthesis. This post-exhaustion loop inflated latency,
but it did not change the completion outcome: no physical call remained for either
the missing evidence or terminal model synthesis.

## Failure analysis

- **Retrieval:** not the primary failure. Six-way BM25 succeeded and identified
  both target guide records.
- **Verification:** transport was healthy in the second run. Its semantic verdicts
  remained conservative because observations exposed metadata and incomplete
  document materialization, not both guide bodies.
- **Context:** no context or model-binding preflight was attempted; there were zero
  context failures.
- **Tool execution:** all 18 admitted physical actions succeeded. The 13 later
  failures were deliberate budget-gate rejections, not worker failures.
- **Workflow composition (primary):** the Manager used the complete action budget
  on a multi-stage retrieve/aggregate/filter/project/read/extract path and allocated
  no call to evidence analysis or final model synthesis.
- **Stopping/over-expansion (secondary):** after the budget was exhausted, the
  Manager continued requesting unavailable actions and the Verifier continued
  producing `continue` verdicts.
- **Synthesis:** never reached; no model inference occurred.
- **Budget:** the hard limits worked exactly as configured and were not raised.

The experiment therefore answers the stated question negatively for this fixed
harness and budget. The Verifier removed premature terminal completion, but did not
solve action-budget allocation or compel a timely transition to synthesis.

## Validation

- Full pytest: **293 passed**
- Ruff: **passed**
- Strict Pyright: **0 errors, 0 warnings, 0 informations**
- Added coverage verifies required function-tool verdict submission, deterministic
  model settings, JSON verdict parsing, typed verifier failure tracing, privacy
  isolation, CONTINUE feedback, synthesis gating, synthesis-failure recovery,
  independent verifier accounting, hard budgets, and evaluator-after-terminal
  ordering.

## Durable evidence and stop

- First attempt audit: `docs/sdk-native-blind-verifier-v1-report.md`
- Second freeze: `results/sdk-native-blind-verifier-v2/freeze/manifest.json`
- Second result:
  `results/sdk-native-blind-verifier-v2/runs/02-multihop-multisource-blind-native-verifier-function-tool/result.json`
- Second full trace:
  `results/sdk-native-blind-verifier-v2/runs/02-multihop-multisource-blind-native-verifier-function-tool/trace.jsonl`
- Second summary: `results/sdk-native-blind-verifier-v2/summary.json`
- Remote durable evidence:
  `/home/super/xiaoming/blind-verifier-stage1-1a0d5b2/app/results/sdk-native-blind-verifier-v2`

Historical v1 evidence and all v2 Worker stores were retained. The four v2 Worker
processes were stopped. No Aware run, matrix, retry, replacement, prompt tuning,
budget increase, or task substitution was performed.
