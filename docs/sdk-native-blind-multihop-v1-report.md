# SDK-native Blind MultiHop baseline v1

## Scope and freeze

This was exactly one resource-blind run of `multihop-multisource`. It used
`OpenAIAgentsNativeRuntime`, the existing SDK-native Manager instructions, native function
tools, bounded agents-as-tools, the existing physical scheduler/runtime, and the formal 32K
deployments. No formal DAG, prior workflow, whole-plan static-feasibility path, independent
Verifier, retry, replacement, prompt tuning, task replacement, network shaping, or matrix cell
was used.

- Code: `31f73d6bd9bf71a7328392af99c8427f22a1335d`
- Run ID: `01-multihop-multisource-blind-native`
- Profile visibility: `blind`
- Budget: 12 Manager turns, 8 specialist turns, 18 tool/model calls, 4 created specialists,
  2 active specialists
- Network: native/unshaped
- Initial placement: the three complete non-semantic corpus shards on A4, A5, and A28
- Deployments: A28 and strong-4090, both declared with 32768 context and 1024 reserved output
- Worker stores: isolated, empty stores created specifically for this run
- Repetitions: 1; retry: false; replacement: false

The corpus and queries were read on strong-4090 from the existing benchmark directory. No
dataset bytes were staged through the development machine.

## Result

| Field | Observed value |
| --- | --- |
| Execution completion | No |
| Final answer | None |
| Evaluator score / format validity | Not evaluated / not applicable |
| Manager reasoning turns | 11 |
| Specialist reasoning turns / calls | 0 / 0 |
| Successful tool executions | 14 |
| Model actions | 4, all rejected before inference |
| Context failures | 4 |
| Model inference calls reached | 0 |
| Final graph | version 54; 18 nodes; 15 edges |
| E2E latency | 21,767.97 ms |
| Initial materialization bytes | 7,696,522 bytes |
| Action-time transferred bytes | 0 bytes |
| Terminal failure | `logical_loop_failed: tool/model call budget exceeded` |
| Primary failure class | **context** |

The complete durable evidence is on strong-4090 under:

```text
/home/super/xiaoming/sdk_native_blind_multihop_v1/evidence/
  freeze/manifest.json
  private/task-contract.json
  private/private-evaluation.json
  runs/01-multihop-multisource-blind-native/result.json
  runs/01-multihop-multisource-blind-native/trace.jsonl
  summary.json
```

The trace has 184 JSONL events and reconstructs the logical decisions, graph growth, typed
observations, physical selections, and terminal budget failure.

## Execution graph summary

The observed evolution was:

1. Run three independent shard-local `bm25_retrieve` actions in parallel. All succeeded.
2. Request one model analysis over the three retrieved artifacts. Static model preflight rejected
   it.
3. Request three independent model analyses over individual retrieved artifacts. Static model
   preflight rejected all three.
4. Continue after the typed failures with three parallel `select_fields` reductions. All
   succeeded.
5. Read the three reduced metadata artifacts. All succeeded; the shard-3 result identified both
   target Polygon guides.
6. Run two focused BM25 retrievals on shard 3, one for each guide. Both succeeded.
7. Project each result to bounded body evidence. Both succeeded.
8. Read the Sorcerer evidence body successfully. Further calls were rejected after the fixed
   18-call budget was exhausted, before terminal synthesis.

All executed tools were placed data-locally, so there was no action-time worker-to-worker
transfer. The only recorded traffic was the initial placement of the three frozen corpus shards.

## Context-failure diagnosis

All four model actions made the same semantic request:

```yaml
modalities: [text]
min_context_tokens: 1
reserved_output_tokens: 2048
required_capabilities: [model]
quality_class: null
```

The Blind-visible static capability contract contained one anonymous model class:

```yaml
capability_class: model-class-01
context_window: 32768
reserved_output_tokens: 1024
modalities: [text, image]
```

Consequently every request had:

```yaml
matching_model_classes: []
static_feasible: false
classification: static_impossible
physical_selection_succeeded: false
reached_model_inference: false
failure_code: context_limit_exceeded
```

This was not a 32K input overflow, dynamic deployment outage, runtime truncation, tool failure,
or missing capability disclosure. The Manager saw the correct static output-budget constraint but
requested 2048 reserved output tokens anyway. It did react to the typed failures by switching to
smaller semantic tools and focused retrieval, but it never retried a model action with a legal
1024-token output reservation and exhausted the fixed budget before synthesis.

Under the requested taxonomy, the primary class is **context**. Budget exhaustion/stopping is a
downstream effect, and synthesis was never reached. Retrieval and tool execution are not the
failure source: all 14 materialized tool nodes succeeded and located the relevant guide evidence.

## Blindness and benchmark integrity

- `logical.loop.start` records `profile_visibility: blind`.
- The Manager input contains the sanitized task and anonymous static capability contract.
- No `PhysicalProfileView` was injected; all 21 logical observations have
  `physical_profile: null`.
- Worker/deployment selection appears only in physical trace events, not in logical
  observations.
- The logical task view contains no `source_ref`, evaluator ID, gold answer, or supporting-evidence
  metadata.
- The original private evaluator was retained but was not invoked because no terminal answer was
  produced.

## Stop decision

The requested single run is complete and failed. It was not retried. No Aware run, matrix,
formal-DAG modification, contract adjustment, or prompt change was performed.
