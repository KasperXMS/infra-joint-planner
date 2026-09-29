# Resource-Blind Live Validation v1 — Concurrency Contract Audit

## Outcome

The generic concurrency-contract conflict is resolved. A logical agent now has one
active reasoning turn, and that turn may submit a batch of independent, ready physical
actions. Artifact readiness and dependencies—not action ownership—determine whether
the batch is legal.

The same three frozen Blind cases were run once with no retry, replacement, prompt
change, benchmark change, tool-space change, or budget change. The live MultiHop run
executed six same-owner, cross-shard BM25 actions concurrently, proving that the old
`one logical agent may have only one active action` confounder is gone. A later
producer-consumer batch was rejected before execution, as required, rather than being
silently reordered or serialized.

None of the three runs reached a terminal answer or evaluator. Video-MME and
LongBench stopped on malformed Planner structured output; MultiHop stopped on a legal
fail-closed rejection of an invalid same-batch dependency. These are now observable
Planner decision/output-contract failures rather than the previous runtime ownership
confounder. No Aware run was started.

## Frozen setting

- Branch: `open-ended-mas-preliminary-v1`
- Code revision: `39fad2e003548f006e8fd36f365a7682ca3315ed`
- Configuration SHA-256:
  `6f551062918e38473a8f762646d7b1e38ada891b69c6ca4928c094d8b1657aaf`
- Visibility: resource-blind; no `PhysicalProfileView` was injected
- Runtime: persistent OpenAI Agents SDK Manager plus bounded specialists-as-tools
- Physical substrate: unchanged `ActionGateway`, resolver/scheduler,
  `RuntimeExecutor`, workers, operators, and evaluators
- Network: native/unshaped
- Repetitions: one per case; no retry or replacement
- Budget: 12 manager turns, 8 turns per specialist, 18 tool/model calls,
  4 created specialists, and 2 concurrently active specialists
- Finite operator vocabulary: the same 12 generic operators

The task views, initial placement, source hashes, public bundle hashes, action space,
budget, and task order are recorded in the new freeze manifest. Dataset access and
artifact materialization occurred only on the dual-4090 experiment host. Only
non-dataset result and trace evidence was copied to the development machine.

Public bundle SHA-256 values remained unchanged:

| Case | Bundle SHA-256 |
|---|---|
| Video-MME 848-1 | `713f6e1d945ca760d0080fd0dd4a74dc6a0dba1eaa4f44e09e4e157b677133ae` |
| LongBench multi-document | `6c22cd47f24cf3279fb317c752ff5c54ff49505aae9249251611ff0727bde341` |
| MultiHop multi-source | `54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e` |

The first Video run stopped the original fail-closed harness. The two unstarted cells
were then invoked from the same frozen code and configuration by selecting only those
remaining bundles. No completed case was retried.

## Contract implementation

Changed files:

- `src/infra_joint/control/validation.py`
- `src/infra_joint/control/loop.py`
- `src/infra_joint/control/physical.py`
- `tests/test_control_plane.py`

The implementation now provides these semantics:

1. A single reasoning decision may submit multiple actions owned by the same logical
   agent.
2. A batch is accepted only when every input was already materialized at decision
   time and no action consumes an output produced by another action in that batch.
3. Accepted actions enter the graph as one expansion, become running together, and
   execute concurrently through the gateway.
4. All action observations are collected before the agent becomes ready for its next
   reasoning turn.
5. A producer-consumer dependency in one batch raises typed
   `semantic_validation_failed` before graph mutation or physical execution.
6. Failed physical execution retains its scheduler/resolver selection and failure
   stage/duration in physical telemetry. The corresponding logical observation remains
   sanitized.
7. Trace events include decision and batch IDs, readiness/dependency validation,
   batch lifecycle, per-action physical execution, per-action observations, and batch
   completion.

No automatic reordering, implicit serialization, retry, replacement, fallback, or
semantic repair was added.

## Verification

The added tests cover:

- four independent, same-owner BM25 actions executing concurrently;
- six independent, same-owner cross-shard BM25 actions executing concurrently;
- rejection of `make_contact_sheet` plus an `invoke_model` consuming its output in
  the same batch;
- mixed success/failure batch state and observation-barrier behavior;
- preservation of physical selection/failure telemetry for a failed action; and
- absence of physical and evaluator-private data from Blind logical traces.

Validation results:

| Check | Result |
|---|---|
| Full `pytest` | pass, 223 tests |
| `ruff check .` | pass |
| strict Pyright | pass, 0 errors and 0 warnings |

## Run summary

| Case | Execution | Score / format | Logical progress | Physical actions | E2E (ms) | Initial transfer bytes / ms | Stop reason |
|---|---:|---:|---|---:|---:|---:|---|
| Video-MME 848-1 | failed | not evaluated | Manager created 1 specialist; specialist decision failed schema validation | 0 | 10,900.980 | 160,083,738 / 5,219.694 | missing action `action_type` discriminator |
| LongBench multi-document | failed | not evaluated | root decision failed schema validation | 0 | 3,845.660 | 1,081,150 / 410.772 | missing `decision_type` discriminator |
| MultiHop multi-source | failed after valid continuation | not evaluated | 6-action batch succeeded; specialist's next batch was rejected | 6 | 12,338.943 | 7,696,522 / 782.127 | same-batch producer-consumer dependency |

There were zero occurrences of the old ownership-invariant error across the three
new traces. No terminal answer, output-format result, or benchmark score exists because
all three stopped before terminal finalization and evaluation.

## Per-case trace summary

### Video-MME 848-1

The root Manager made one valid decision and created the bounded
`video-chapter-analyst` specialist. The graph was still G0 because the specialist's
first raw SDK decision could not be decoded: its proposed action omitted the required
`action_type` discriminator. Pydantic rejected the decision before logical batch
validation, graph mutation, or physical execution.

This run therefore does not exercise the revised concurrency path and does not provide
evidence about video sampling recovery. Its failure is a Planner structured-output
contract failure, not the removed same-owner concurrency restriction. It was not
retried.

- Manager decisions recorded: 1
- Created specialists: 1
- Physical actions/model calls: 0/0
- Graph evolution: G0 only
- Trace SHA-256:
  `290cfc3888ea1925ddb8470a5bea5a3be4a405d5b127f344fb388f918270638b`
- Result SHA-256:
  `f834c8f1f6cb2e76b022d3c21369be4acf48f20b6c932ffd8d209fef7e80cc0c`

### LongBench multi-document

The first root SDK response contained a proposed action structure but omitted the
top-level `decision_type` discriminator. The response failed `_DecisionEnvelope`
validation before it became a logical decision. No batch, graph node, physical action,
model invocation, terminal answer, or evaluator call occurred.

This is also a Planner structured-output contract failure. The live run cannot confirm
four-action concurrency because no valid batch reached the loop; the unchanged generic
four-BM25 integration test confirms that runtime path.

- Logical decisions recorded: 0
- Physical actions/model calls: 0/0
- Graph evolution: G0 only
- Trace SHA-256:
  `abcba8028347788926bd4646e4c2b735a92c339ed1841f0d8097e32d001a16d6`
- Result SHA-256:
  `01e4e2d71b15a270b5dd6b65d6f6e7b634c6fbf2fcae3118c1b11324cef9a79a`

### MultiHop multi-source

The Manager's first turn submitted six independent BM25 actions: Sorcerer and
Barbarian retrieval over each of the three non-semantic corpus shards. Batch
`manager:turn:1:batch` was accepted with all inputs materialized and no same-batch
dependencies.

All six actions ran successfully. The resolver selected the data-local worker for each
shard: two actions on A4, two on A5, and two on A28. No action-level transfer was
needed. The graph evolved as one parallel expansion:

```text
G0 empty
-> G1 six BM25 nodes pending
-> G2 six BM25 nodes running
-> G3 six BM25 nodes succeeded
```

The batch took 1,754.374 ms wall time. Individual operator latencies summed to
2,624.955 ms, with a maximum of 638.585 ms, so the live trace demonstrates actual
overlap rather than hidden serialization. All six observations were returned before
the next reasoning decision.

The Manager then naturally continued and created `retrieval-analyst` with the six
retrieval artifacts. On its first turn, the specialist submitted two independent
producer actions—`filter-polygon-records` and `aggregate-all-retrieval`—plus
`extract-comparison-evidence`, which consumed both proposed outputs and explicitly
depended on both producers. Batch
`retrieval-analyst:turn:1:batch` was rejected before graph mutation or execution with:

```text
semantic_validation_failed:
same-batch producer-consumer dependency is not allowed
```

The trace records both artifact-flow and control dependencies. The runtime did not
silently serialize, reorder, or execute the producers. This is the intended generic
contract behavior and exposes a real Planner composition error: the specialist needed
to submit the two ready producers, observe completion, and issue the dependent model
action in its next reasoning turn.

- Logical decisions: 3 (2 Manager, 1 specialist)
- Physical tool/model calls: 6/0
- Batch result: 6 succeeded, 0 failed
- Planner latency total: 9,675.228 ms
- Action-level transfer: 0 bytes
- Trace SHA-256:
  `c7b28cb15d49539649a90082b856de0692eec66331d0f8709903e360de85cc44`
- Result SHA-256:
  `1fd2d4d2f481d336ab21ff305cb72290c9d2dcaad4b237f0f77d17b346b1966e`

## Privacy and trace audit

- Every run used `profile_visibility=blind`.
- Every logical observation had a null physical profile.
- Logical events contain no worker/deployment identity, IP address, placement,
  network, queue, or load state.
- Logical events contain no `source_ref`, `evaluator_id`, gold answer, or supporting
  evidence metadata.
- Physical selections and transfers remain confined to physical/materialization
  telemetry.
- The MultiHop trace reconstructs decision IDs, batch IDs, readiness validation,
  G0→G3, all six physical selections, action outputs, the observation barrier,
  specialist creation, and the rejected dependent batch.
- Video and LongBench reconstruct the exact schema-validation boundary at which their
  raw Planner outputs were rejected.

The live runs did not produce a physical action failure after scheduling. The new
failed-action telemetry path is therefore verified by the integration test rather than
by these three traces: a fail-closed oversized `read_artifact` retains physical
selection, execution-stage failure, and duration, while its logical observation does
not expose physical identity.

## Acceptance assessment

| Criterion | Result |
|---|---|
| One active reasoning turn may issue multiple independent actions | pass |
| Four same-owner BM25 actions can run concurrently | pass in integration test |
| Six cross-shard same-owner BM25 actions can run concurrently | pass in test and live MultiHop run |
| Same-batch producer-consumer dependency fails closed | pass in test and live MultiHop run |
| No hidden serialization/reordering | pass |
| Batch state and observation barrier are correct | pass |
| Failed-action physical telemetry is preserved and logical view sanitized | pass in integration test |
| Old one-active-action ownership error absent | pass, zero trace occurrences |
| Blind/private isolation preserved | pass |
| All three reach terminal answer/evaluator | fail |

The requested control-contract confounder is eliminated. The rerun also exposes the
next semantic/control-output limitations without masking them: two malformed Planner
structured responses and one invalid producer-consumer batch composition. No prompt,
schema, budget, benchmark, or tool-space tuning was performed after observing these
results, and no Aware experiment was started.
