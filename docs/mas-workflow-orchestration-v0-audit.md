# MAS Workflow Orchestration v0 Audit

## Scope and freeze

- Base: `main@bccef07` (`docs: record M4 real smoke audit`).
- Development branch: `mas-workflow-orchestration`.
- This work adds a plan-once workflow layer. It does not change the semantics of the
  frozen M4 RuntimeExecutor, resolver, Worker API, artifact store, model backend,
  benchmark adapters, evaluator, model preflight, or existing PlanningGraph.
- No M5 infrastructure-aware semantic planner, dynamic replanning, RL, migration,
  loading, prefetch, new deployment mechanism, benchmark expansion, 7-task baseline,
  sweep, or ablation was performed.

The implemented boundary is:

```text
TaskContract + WorkloadSpec + fixed model instances
  -> plan-once MAS Workflow Planner
  -> WorkflowPlan DAG
  -> B0/B1 Workflow Orchestrator
  -> unchanged RuntimeExecutor / Remote Workers
  -> unchanged finalizer / private evaluator
```

`git diff bccef07` contains only the new workflow contracts/package, its tests, and the
minimal experiment driver. There is no diff under `runtime/`, `worker/`, `benchmarks/`,
`planning/`, `evaluation/`, `infrastructure/`, or `operators/`.

## Implemented contracts and execution semantics

The following immutable contracts were added and tested:

- `LogicalAgent(agent_id, role, objective, model_instance_id, allowed_operations)`;
- `WorkflowNode(node_id, agent_id, operator, inputs, arguments, outputs)`;
- `WorkflowEdge(producer_node, consumer_node, artifact_id)`;
- `WorkflowPlan(agents, nodes, edges)`;
- `WorkflowState`, with exactly `PENDING | READY | RUNNING | DONE | FAILED`.

Validation rejects cycles, duplicate IDs and outputs, invalid agent/model/operator
references, invalid operator schemas, invalid edges, unresolved artifacts, output
collisions with task artifacts, and missing exact producer-consumer edges. A logical
agent is not a `DeploymentSpec`, and multiple logical agents may bind the same fixed
model instance.

`WorkloadSpec` exposes only operation schemas, fixed model identities/modalities,
artifact semantics/types, and generic agent-count bounds. It contains no DAG, solution
order, placement, links, devices, load, gold answer, supporting evidence, or evaluator
state. The Workflow Planner receives the existing sanitized logical task view; source
references and evaluator metadata are removed.

The orchestrator applies

```text
READY(v) iff every predecessor of v is DONE
```

and launches independent READY nodes with `asyncio.gather`. It refreshes live Worker
state at scheduling boundaries, serializes JSONL emission through one trace recorder,
validates returned artifact metadata against the post-execution Worker state, and stops
downstream execution after a node failure. It neither retries nor silently changes a
deployment. Model nodes always use the logical agent's fixed model instance via
`TARGET_DEPLOYMENT`.

To avoid concurrent store races and unobservable remote cancellation, at most one node
per physical Worker is admitted to a scheduling batch. This still permits real branch
parallelism across Workers.

## Schedulers

### B0 — Locality-Aware Myopic Scheduler

- Ordinary operators use the unchanged Runtime `AUTO` resolver.
- Resolution is capability-feasible, minimizes the count of required input transfers,
  and uses stable agent ID as the tie-break.
- It does not inspect bandwidth, RTT, future DAG nodes, or critical path.
- Model nodes are pinned to their logical agent's model instance.

### B1 — Myopic Cost-Aware Scheduler

For every currently READY node and feasible Worker, B1 records:

```text
C_hat(v, x) = transfer latency + compute profile + queue estimate
```

Transfer latency uses artifact bytes, directed bandwidth and RTT. Compute uses a frozen
operator/device estimate. Queue uses `queue_depth` when available, otherwise
`in_flight * compute profile`. B1 optimizes only the current node and performs no
look-ahead, global search, or RL. Model nodes remain pinned; their cost is telemetry and
cannot cause a deployment substitution.

The v0 experiment froze the following service-time estimates for all three identically
declared `AGX Orin` devices: BM25 retrieval 100 ms, artifact aggregation 25 ms, and model
invocation 1000 ms. These are scheduler inputs, not claims of calibrated device models.

## Exact real smoke setting

Task:

- MultiHop-RAG-derived task:
  `multihop-rag-train-9bae0079038050a37a1ae583`;
- source revision: `71ac0d0bd1f951d2d6b70311f7d2ae404e1ffa82`;
- representation: query-only BM25 ranks 1 and 2, split into two single-document JSON
  shards;
- setting label: derived execution smoke, not a formal MultiHop-RAG benchmark result;
- case manifest SHA-256:
  `83a00b3242a0426fa325fdd1f8e56ca7e9da13d1f898699ea6b5d72efc2ef7c8`.

Frozen raw documents:

| Document | Raw SHA-256 | Derived shard bytes | Initial placement |
|---|---|---:|---|
| `mhr-doc-92f18d01477dbdd58bf98ac0` | `534ecb2b941db306399bd3cafc78a935c88caf7200aefbbc66677d0356a8b4a8` | 20,538 | A4 |
| `mhr-doc-47e158bf93cbf3e6ee8c5ea6` | `7c4cbc6a6ea8eafcbf9a28bd51b4f9e27ce37bced12016e009e2e711c6ef8a12` | 20,684 | A5 |

Physical environment:

- A4, A5, A28: existing remote AGX Orin Workers and unchanged 12-operator surface;
- fixed synthesis model instance: `a28-deepseek-chat`, text, 64k context, 1024 reserved
  output tokens;
- Workflow Planner and finalizer: cloud `deepseek-chat` using the configured API key;
- workload operations: `bm25_retrieve`, `aggregate_artifacts`, `invoke_model`;
- exactly three logical agents were allowed;
- no Worker was restarted or replaced for this experiment.

Network regimes were application-layer link emulations around the unchanged Worker
client:

| Regime | Bandwidth | Added RTT |
|---|---:|---:|
| `H_fast` | 100 Mbps | 0 ms |
| `H_constrained` | 3 Mbps | 50 ms |

Artifact bytes still traversed the real worker-to-worker `/artifact/pull` path. The
wrapper made observed pull service time at least
`RTT + bytes * 8 / bandwidth`. It does not emulate shared-link contention or dynamic
bandwidth and must not be interpreted as kernel `tc/netem` measurement.

## Cloud-planned MAS smoke

Run ID: `mas-v0-smoke`.

The cloud Workflow Planner made one call and generated three logical agents and this
four-node DAG:

```text
retrieve-sorcerer @ logical retriever 1 --\
                                           -> merge-passages -> compare-simplification
retrieve-barbarian @ logical retriever 2 --/                         @ DeepSeek deployment
```

Both retrieval nodes were READY together and ran on A4/A5 in scheduling batch 0. Their
recorded intervals overlapped, `max_parallelism=2`, and `parallel_overlap=7.543 ms`.
The fan-in aggregation ran on A4, and the merged 41,286-byte artifact was then pulled by
A28 and consumed by the fixed DeepSeek deployment.

Smoke outcome:

| Metric | Value |
|---|---:|
| Format valid / benchmark score | true / 1.0 |
| Final answer | `Yes` |
| Runner E2E | 18,379.543 ms |
| Workflow E2E | 12,186.989 ms |
| Node-service critical path | 1,043.316 ms |
| Workflow transfer | 62,002 bytes / 127.412 ms |
| Total transfer including initial materialization | 103,224 bytes / 231.603 ms |
| Operator latency | 922.394 ms |
| Model service latency / tokens | 821.937 ms / 10,689 in / 20 out |
| Planner service latency / tokens | 3,365.789 ms / 1,143 in / 889 out |
| Finalizer service latency / tokens | 699.667 ms / 842 in / 1 out |

The Planner assigned Sorcerer/Barbarian role names before seeing artifact contents and
therefore had no basis for knowing which opaque shard contained which guide. Because
each shard contained one frozen candidate, both legal retrieval calls still returned
their complete document. This is a planner information-boundary observation, not a
harness failure or evidence leak.

## Four-cell scheduler pre-experiment

The exact cloud-generated DAG was frozen after the smoke. The four scheduler cells used
that plan through `ScriptedWorkflowPlanner` so that only scheduler and network regime
changed. A mechanical run namespace was applied to produced artifact IDs to prevent
persistent Worker stores from contaminating later cells; node/operator/dependency/model
semantics did not change.

All cells are `n=1` and completed without retry:

| Run | Score / format | Runner E2E ms | Node critical path ms | Transfer bytes | Transfer ms | Operator ms | Model service ms | Model tokens in/out | Parallel overlap ms | Fan-in Worker |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B0 / fast | 1.0 / valid | 16,359.956 | 1,691.961 | 62,002 | 121.878 | 1,581.668 | 1,546.225 | 10,702 / 57 | 12.512 | A4 |
| B0 / constrained | 1.0 / valid | 15,118.633 | 1,275.416 | 62,002 | 268.841 | 1,013.306 | 986.926 | 10,702 / 49 | 7.774 | A4 |
| B1 / fast | 1.0 / valid | 14,673.108 | 1,090.014 | 61,857 | 127.738 | 968.655 | 942.786 | 10,702 / 58 | 7.398 | A5 |
| B1 / constrained | 1.0 / valid | 14,981.317 | 1,218.767 | 61,857 | 266.772 | 963.572 | 904.674 | 10,702 / 23 | 11.871 | A5 |

Each run also materialized the same 41,222 initial bytes. Therefore total run transfer
was 103,224 bytes for B0 and 103,079 bytes for B1.

The physical path changed as intended:

- B0 treated the two-local-input candidates as a transfer-count tie and selected A4 by
  stable ID. It moved the 20,716-byte A5 retrieval result to A4, then moved the
  41,286-byte merged artifact A4 -> A28.
- B1 compared bytes and selected A5. It moved the smaller 20,571-byte A4 retrieval
  result to A5, then moved the same merged artifact A5 -> A28.
- The fixed DeepSeek model instance was used in every cell; no scheduler changed or
  substituted it.

The network effect is visible in transfer telemetry: fast cells measured 121.878 and
127.738 ms, while constrained cells measured 268.841 and 266.772 ms. End-to-end ordering
must not be used to claim scheduler speedup: the single-run model service time varied by
more than the network delta and dominated the observed E2E ordering. The experiment
supports real path selection and network-sensitive transfer cost, not a statistically
stable performance ranking.

`critical_path_latency_ms` in v0 is the longest sum of recorded node service intervals;
it excludes observation/scheduling gaps. Runner and workflow E2E retain those gaps.

## Invalid-run audit

The first attempted matrix cell, `mas-v0-b0-h_fast`, was stopped and excluded. The
run-local artifact namespace used `/`, so the source Worker had the artifact but FastAPI
decoded the quoted slash as a path separator during `/artifact/{artifact_id}` lookup.
The target Worker correctly surfaced the failed pull as HTTP 502 and the workflow marked
`merge-passages` FAILED without fallback or downstream execution.

Classification: **system/harness confounder**, not a scheduler result.

The fix changed only the mechanical namespace separator to URL-safe `--`, retained the
failed result and trace, and started the four primary cells under new `audit1` run IDs.
No failed cell was counted. The runner was also hardened so future workflow failures end
with an explicit `run.failed` event and top-level runner E2E latency.

## Trace, failure, and leakage audit

- The smoke and all four primary traces contain 28 events, start with `task.start`, end
  with `run.end`, use one run ID, and have a complete linear parent chain.
- Events include materialization, planner output, infrastructure snapshots, scheduler
  decisions and candidate costs, node start/end intervals, artifact transfers,
  finalization, evaluation, and aggregate telemetry.
- Runtime output artifacts were accepted only after ID, media type, bytes, checksum, and
  post-execution location matched live Worker state.
- All four model actions resolved to the declared fixed deployment. There was no silent
  fallback, model substitution, retry, or truncation.
- Existing runtime modality/context preflight remained active.
- Planner prompt tests prove that source refs, evaluator identity, worker/host/device
  state, placement, links, load, gold answer, and supporting evidence are absent.
- The private evaluator was constructed only after execution and was never serialized
  into `TaskContract`, `WorkloadSpec`, or the Planner prompt.
- The model-instance identifier is Planner-visible because fixed model binding is part
  of the requested semantic workflow contract; its physical agent mapping and live
  infrastructure state are not provided.

## Verification and conclusion

At audit time:

- full `pytest`: 102 passed;
- Ruff: passed;
- strict Pyright: 0 errors;
- M4 substrate directories: unchanged from `bccef07`.

The v0 stopping conditions are satisfied:

1. workflow contracts and validation pass;
2. a cloud Planner produced an explicit three-agent DAG;
3. two READY nodes executed concurrently on remote Workers;
4. the MultiHop-derived fan-out/fan-in smoke completed through the fixed model and
   original evaluator;
5. the four B0/B1 x network cells completed with reconstructable traces;
6. B0/B1 changed the real physical fan-in path and network regime changed measured
   transfer time;
7. no gold/infra/TaskContract leakage, silent fallback, or silent truncation was found.

What is established is the existence of a correctly modeled and executable research
object:

```text
MAS workflow synthesis + infrastructure-aware execution-path orchestration
over fixed deployments
```

What is not established is a superior scheduler, an E2E speedup, benchmark-level
quality, robustness across tasks, dynamic behavior, or a proposed method. Those claims
require later experiments and are outside this stage.
