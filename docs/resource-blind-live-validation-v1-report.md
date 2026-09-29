# Resource-Blind Live Validation v1 Audit

## Outcome

The three frozen primary runs were executed once, with no retry or replacement. All
three entered the persistent OpenAI Agents SDK manager loop. The validation did not
meet its acceptance target: none reached a terminal agent answer or the original
evaluator.

The common stopping cause was a logical-control contract mismatch. The SDK decision
schema admitted an `actions` array with multiple actions, while
`PersistentManagerLoop` rejected more than one active action owned by the same
`LogicalAgent`. LongBench and MultiHop encountered this on the first manager turn.
Video-MME first demonstrated a real observation-driven recovery, then encountered the
same mismatch in a specialist turn. These are control-contract confounders, not valid
benchmark-quality failures, so the results must not be reported as baseline scores.

No Aware run or infrastructure sweep was started.

## Frozen setting

- Code revision: `72b876543ed12a5b1983ac707c4260a231d55ea6`
- Configuration SHA-256:
  `6f551062918e38473a8f762646d7b1e38ada891b69c6ca4928c094d8b1657aaf`
- Runtime: OpenAI Agents SDK 0.20.0, persistent manager plus bounded
  specialists-as-tools
- Planner model: `deepseek-chat` through the OpenAI-compatible SDK model adapter
- Visibility: resource-blind; no `PhysicalProfileView` was injected
- Network: native/unshaped
- Physical execution: existing `ActionGateway`, physical resolver/scheduler,
  `RuntimeExecutor`, workers, operators, and benchmark evaluators
- Repetitions: one per task; no retry or replacement
- Finite operator vocabulary: 12 frozen generic operators
- Uniform budget: 12 manager turns, 8 turns per specialist, 18 total tool/model
  calls, 4 created specialists, and 2 concurrently active specialists

The freeze manifest records source hashes, public bundle hashes, sanitized task views,
initial placements, action space, budget, and task order. Private task contracts and
evaluators remained on the 4090 experiment host. Dataset loading and artifact
materialization were performed on that host; no benchmark dataset was transferred
through the development machine.

Public bundle SHA-256 values:

| Case | Bundle SHA-256 |
|---|---|
| Video-MME 848-1 | `713f6e1d945ca760d0080fd0dd4a74dc6a0dba1eaa4f44e09e4e157b677133ae` |
| LongBench multi-document | `6c22cd47f24cf3279fb317c752ff5c54ff49505aae9249251611ff0727bde341` |
| MultiHop multi-source | `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e` |

## Run summary

`Tool/model calls` counts physical actions that actually reached the gateway. Planner
SDK calls are shown separately. E2E for failed runs comes from the terminal
`run.failed` trace event.

| Case | Execution | Score / format | SDK decisions | Active logical agents | Specialists | Tool / model calls | E2E (ms) | Initial transfer bytes / ms | Failure class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Video-MME 848-1 | failed | not evaluated | 4 (1 manager, 3 specialist) | 2 | 1 | 2 / 0 | 89,526.234 | 160,083,738 / 5,817.060 | control-contract confounder after natural recovery |
| LongBench multi-document | failed | not evaluated | 1 manager | 1 | 0 | 0 / 0 | 3,623.443 | 1,081,150 / 595.095 | control-contract confounder on first decision |
| MultiHop multi-source | failed | not evaluated | 1 manager | 1 | 0 | 0 / 0 | 5,007.232 | 7,696,522 / 1,360.494 | control-contract confounder on first decision |

All three typed failures were:

```text
logical_loop_failed / AgentLoopError:
one logical agent may have only one active action
```

No terminal answer, format-validity result, benchmark score, physical model selection,
or model-service latency exists because no `invoke_model` action was executed.

## Per-case trace summaries

### Video-MME 848-1

The manager created one bounded `chapter-transcript-specialist`, giving it the original
video artifact. This was genuine manager-plus-specialist behavior rather than an
up-front complete DAG.

Observed graph evolution:

```text
G0 empty
-> G1 read-meta-1 pending
-> G2 read-meta-1 running
-> G3 read-meta-1 failed (artifact_too_large)
-> G4 sample-frames-1 pending
-> G5 sample-frames-1 running
-> G6 sample-frames-1 succeeded (32 image artifacts)
-> next decision rejected before graph mutation
```

The first `read_artifact` failed closed with the correct typed reason: the 160,083,738
byte video exceeded the 65,536 byte read limit. The specialist observed that result and
naturally continued with `sample_frames`; this is the requested evidence of an
observation-driven recovery. `sample_frames` ran data-locally on A4, took 70,651.206 ms,
and materialized 32 frames.

On the next turn, the specialist selected both `make_contact_sheet` and
`invoke_model` in one decision. Its rationale described them as sequential steps, but
both were emitted as same-owner actions. The runtime rejected the batch before either
action ran. Thus Video demonstrated continuation after an execution failure, but it
did not reach evidence analysis, terminal answer, or evaluation.

Trace SHA-256:
`dd6ac47fd8ee76cbb80a7d558a6d61ce368338072387846eec3a20296a940aa1`.

### LongBench multi-document

The manager correctly identified the four document artifacts and selected targeted
BM25 retrieval. It emitted four independent, same-owner retrieval actions in one turn,
apparently intending parallel retrieval across the four documents. Because the loop
permits only one active action per logical agent, the decision was rejected before G0
could grow. No retrieval, specialist, model call, terminal answer, or evaluator call
occurred.

This does not demonstrate failure to decompose a long-context task: the decision did
decompose it into legal generic operators. It demonstrates that the planner-visible
decision schema and runtime concurrency invariant disagree about how parallel work
must be expressed.

Trace SHA-256:
`c8b9e4642432a2867925d10666891c657597a7d2ed3edc1f7af5c2c8d5a20832`.

### MultiHop multi-source

The manager read the collection metadata correctly: three non-semantic hash shards
whose union forms the complete corpus. It attempted six targeted BM25 actions—Sorcerer
and Barbarian queries over each shard—in one parallel step. The same-owner action batch
was rejected at G0, before any shard retrieval or evidence observation.

Therefore this run cannot answer whether the manager would expand retrieval after
irrelevant or insufficient evidence. The initial intent covered all shards, but the
control-contract mismatch prevented the requested continuation diagnostic.

Trace SHA-256:
`b0c0e61f7ddd714f6adb9b22606d73b3c11ef4286a1585c0beaf1cf847a2d7e6`.

## Privacy and trace audit

- Every logical loop started with `profile_visibility=blind`.
- Every emitted logical observation had a null physical profile.
- Logical trace events contained no worker/deployment/network/placement/queue
  identifiers.
- Logical trace events contained no `source_ref`, `evaluator_id`, gold answer, or
  supporting-evidence metadata.
- Physical placement and transfer telemetry remained in physical/materialization
  events only.
- The Video trace reconstructs decisions, specialist creation, typed failure,
  recovery, graph states G0 through G6, physical sampling placement, and outputs.
- LongBench and MultiHop reconstruct G0 and the rejected first decision. Their graph
  cannot contain the proposed actions because rejection occurred before graph mutation.

The failed physical `read_artifact` event has a typed logical observation but does not
retain the scheduler selection in its `physical.execution` payload. This is a telemetry
gap for failed physical actions, although it does not affect the root-cause conclusion.

## Acceptance assessment

| Criterion | Result |
|---|---|
| All three enter the persistent loop | pass |
| No old complete-DAG planner or fixed-checkpoint replanner | pass |
| Blind logical layer has no infrastructure/private leakage | pass |
| Natural continuation/recovery is observable | partial: Video only |
| Complete or end in an interpretable semantic failure | fail: contract confounder dominates all three |
| No plan-invalid/control-rigidity failure | fail |
| Original evaluator reached | fail for all three |

The experiment supports one narrow positive observation: the Video specialist used a
typed observation to revise its next action without rollback, retry, or an external
replanner. It does **not** establish baseline semantic competence, MultiHop evidence
recovery, LongBench constraint recovery, or benchmark quality.

Before any Aware experiment, the system-owned decision contract must unambiguously
choose and expose one of two semantics: schema-limit each agent decision to one action,
requiring parallel work to be expressed via bounded specialists; or permit a validated
same-owner ready-action batch. This is a generic control-contract issue, not a reason
for task-specific prompt tuning. No such fix or rerun was performed in this stage.
