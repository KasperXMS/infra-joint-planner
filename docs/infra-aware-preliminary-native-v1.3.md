# SDK-native Infra-Aware Preliminary v1.3

Date: 2026-10-02  
Branch: `open-ended-mas-preliminary-v1`

## Scope and frozen controls

The research question is: **How does infrastructure status change the agent
workflow?** The pre-registered comparison is `Fast / Slow x Blind / Aware` on the
same `multihop-multisource` task.

The following remained frozen:

- Manager turns / physical calls / Verifier calls: `20 / 64 / 20`;
- model context / reserved output: `32768 / 2048` tokens;
- Manager model and instructions, Blind Verifier, finite tool space, scheduler,
  terminal contract, benchmark adapter, evaluator, task representation, and model
  deployments;
- Fast: 100 Mbps and 5 ms added RTT;
- Slow: 3 Mbps and 50 ms added RTT; and
- one run per cell, no semantic retry, no prompt tuning, and fresh Worker stores.

The task bundle SHA-256 is
`54ef8ddbe4a3379254345f307b3f0ef6b95fe92e0b28ac4c89124bb6b7ebfe8e`.
The static capability contract SHA-256 is
`8d46d9b941a08380a00fdab1e7c151c25affd589ec4444864f3c5c925a2089a4`.

Fast-Blind replicate 1 uses frozen `blind-harness-v1.3`. The other counted cells
use `blind-harness-v1.3.1`, whose only behavior difference is that an Aware Manager
may coexist with the same Blind Verifier. It does not change Blind inputs, Manager
or Verifier prompts, budgets, tools, scheduler, or model/runtime behavior. The
Verifier never receives a physical profile.

Every counted cell has a transactional `tc` attestation. All cleanup errors are
null, A4/A5/A28 restore to their original `mq` roots, and strong-4090 restores to
`noqueue`. Logical privacy scans pass in all Blind traces.

## Matrix

The following is the counted replicate-1 matrix. The pre-existing Fast-Blind run
specified by the protocol is retained; it was not replaced by a later trajectory.
Initial materialization is 7,696,522 bytes in every cell. Action bytes exclude that
fixed initial placement traffic.

| Network | Method | Run | Complete | Score / format | Manager / Verifier | Physical calls | Tool / model | Inference | Context failures | First ready | Graph nodes / edges | E2E ms | Action bytes |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fast | Blind | `12-multihop-fast-blind-v1.3` | yes | 0.0 / valid | 12 / 12 | 25 | 23 / 2 | 1 | 1 | 1 | 25 / 28 | 106,405.283 | 0 |
| Fast | Aware | `17-multihop-fast-aware-v1.3.1` | yes | 0.0 / valid | 13 / 13 | 22 | 18 / 4 | 2 | 1 | 1 | 22 / 16 | 214,865.608 | 10,006 |
| Slow | Blind | `18-multihop-slow-blind-v1.3.1` | yes | 0.0 / valid | 9 / 9 | 23 | 21 / 2 | 1 | 1 | 1 | 23 / 13 | 303,102.954 | 33,966 |
| Slow | Aware | `19-multihop-slow-aware-v1.3.1` | yes | 0.0 / valid | 13 / 13 | 43 | 41 / 2 | 1 | 1 | 1 | 43 / 33 | 217,485.620 | 5,598 |

Facts observed in trace:

- all four runs completed terminal synthesis, produced format-valid short text, and
  invoked the private evaluator;
- all four scores are 0.0; this is a semantic-quality outcome, not a harness
  failure;
- none of the four used a specialist or a same-decision parallel action batch; and
- every run first reached `ready_for_synthesis` at Verifier call 1, later returned
  to evidence collection, and eventually completed.

## Replicate-level results

The extension to `n=3` was pre-registered at commit
`0b7149a128f223c54a49f1478da0bcafa73ab8ca`. Replicate 2 stopped at its first
cell because the cloud Manager provider failed before processing the request.

| Attempt | Run | Outcome | Manager actions | Inference | E2E ms | tc cleanup / restore |
|---|---|---|---:|---:|---:|---|
| Fast-Blind r2 original | `20-multihop-fast-blind-v1.3.1-r2` | provider admission timeout | 0 | 0 | 902,539.784 | null / exact |
| Fast-Blind r2 replacement 1 | `20r-multihop-fast-blind-v1.3.1-r2-replacement1` | same provider admission timeout | 0 | 0 | 902,627.122 | null / exact |

Both provider payloads state that processing could not start within the provider's
900-second timeout. Both traces stop at `logical.reasoning.started` for Manager turn
1, before any completed Manager turn, tool/model action, workflow node, device-model
inference, or evaluator call. Initial artifacts were materialized, but action bytes
are zero. These are operational attempts, not semantic replicates.

The protocol permits at most one operational replacement. Because the replacement
failed in the same way, this is a repeated persistent model-service failure and an
overnight hard-stop condition. No r2 Aware/Slow cell, r3 cell, LongBench matrix, or
Video-MME matrix was started.

## Workflow comparison

Compact final-graph signatures for the completed matrix are:

| Cell | Retrieval | Reduction / projection | Model | Graph snapshots / max version | Action-transfer ms |
|---|---:|---|---:|---:|---:|
| Fast Blind | BM25 12 | select 3, aggregate 2, filter 2, read 4 | 2 | 76 / 75 | 0.000 |
| Fast Aware | BM25 10 | select 4, filter 2, read 2 | 4 | 67 / 66 | 222.367 |
| Slow Blind | BM25 9 | filter 9, aggregate 1, select 1, read 1 | 2 | 70 / 69 | 1,436.008 |
| Slow Aware | BM25 18 | top-k 10, filter 5, select 5, read 3 | 2 | 130 / 129 | 199.100 |

The observed action ordering, compacted by phase, is:

- Fast Blind: distributed retrieval -> infeasible model request -> more retrieval
  -> select/aggregate/read/filter -> terminal model;
- Fast Aware: retrieval/model probes -> more retrieval -> select/read/filter ->
  terminal model;
- Slow Blind: distributed retrieval -> infeasible model request -> distributed
  filtering -> aggregation/projection/read -> terminal model; and
- Slow Aware: wider distributed retrieval -> infeasible model request ->
  select/filter -> ten local top-k reductions -> more retrieval/read -> terminal
  model.

Physical execution facts:

- retrieval and reduction remained distributed over A4/A5/A28;
- every successful terminal inference ran on A28 under the unchanged physical
  scheduler;
- Slow Blind aggregated remote evidence on A28 and moved 33,966 action bytes; and
- Slow Aware used a larger distributed reduction graph and moved only 5,598 action
  bytes before terminal inference.

## Infra-response observations

Facts observed in Aware traces:

- Fast Aware received 22 anonymous `PhysicalProfileView` observations: 21 `fast`
  and 1 `unknown`;
- Slow Aware received 43 observations: 42 `constrained` and 1 `local`;
- Fast predicted transfer upper bounds reached 226.814 ms, while Slow bounds
  reached 7,443.797 ms;
- all 65 service-latency fields remained explicitly unknown; no value was guessed;
  and
- Aware Fast and Aware Slow produced different workflows: 22 versus 43 nodes,
  BM25 10 versus 18, and top-k reduction 0 versus 10.

Interpretation:

- the Slow-Aware trajectory is consistent with responding to transfer pressure by
  doing more bounded reduction near data; and
- this is a workflow-response signal, but `n=1` cannot isolate infrastructure as
  the cause because Blind Fast and Blind Slow also produced materially different
  legal workflows without seeing infrastructure.

Within Slow, Aware versus Blind reduced E2E by 85,617.334 ms (28.2%), action bytes
by 28,368 bytes (83.5%), and action-transfer latency by 86.1%. Both scores remained
0.0. Across Aware conditions, Slow transferred 44.1% fewer action bytes than Fast
but had 1.2% higher E2E because it executed substantially more actions.

## Quality comparison

Observed quality for the counted matrix is uniform:

- completion rate: 4/4;
- evaluator invocation rate: 4/4;
- format-valid rate: 4/4; and
- evaluator scores: `[0.0, 0.0, 0.0, 0.0]`.

Therefore there is no observed quality difference between Blind and Aware, but
there is also no positive-quality result in this matrix. "No degradation" here
means equality at score 0 and must not be interpreted as preserved correct quality.

## Runtime incidents

All incidents and unsuccessful trajectories remain preserved:

1. The original Fast-Aware construction attempt at revision `e41f39e` failed before
   Manager execution because Aware visibility was incorrectly coupled to the Blind
   Verifier. It is excluded from the matrix. The compatibility-only fix is frozen
   in v1.3.1.
2. `16-multihop-fast-blind-v1.3.1` is an already executed, valid agent trajectory
   that exhausted 20 Manager turns / 64 calls. It is retained as a supplemental
   run, not substituted for the protocol-designated Fast-Blind replicate 1.
3. Before r2 execution, one Worker startup check found the required
   `OLLAMA_API_KEY` environment variable absent. This happened before tc application
   and task execution, created no artifact store, and consumed no experiment
   attempt. The normal Worker environment was restored without changing a frozen
   setting.
4. Fast-Blind r2 original and its sole operational replacement both encountered
   the same provider admission timeout. This triggered the required hard stop.

## Evidence provenance

| Run | Code revision | Config SHA-256 | Harness manifest SHA-256 |
|---|---|---|---|
| `12-multihop-fast-blind-v1.3` | `e41f39e8eef9028484c025786aeb14f903c300ec` | `f8c2cb2fb5b7120c3256ec86b86945cf863ba5ce21f2074fe0d698f6360c0258` | `26bd5c37e73052c820b7a5d9ab69dfe3c52d9ff25278d51042b9c2e712ad97d6` |
| `17-multihop-fast-aware-v1.3.1` | `205de7d9607704bcf5efaaa56eed4da6bf7f4295` | `524f35cd30c52c09a8cbf1cafbbd96a34cd7b2eae83f01857b97226e0825ebbc` | `ab7f548a047bd24c97b561a564467e8c6d46f1d4380a9effa3d431469be0d643` |
| `18-multihop-slow-blind-v1.3.1` | `205de7d9607704bcf5efaaa56eed4da6bf7f4295` | `23db715b336bdf670ce5b872616b13eb04ca6a9a6251fa3dd998f187e546e4b6` | `ab7f548a047bd24c97b561a564467e8c6d46f1d4380a9effa3d431469be0d643` |
| `19-multihop-slow-aware-v1.3.1` | `205de7d9607704bcf5efaaa56eed4da6bf7f4295` | `9ffb22e34ccd1e9b09361a0498c759e6ea466cfbe882507a4a6eea8b7277380e` | `ab7f548a047bd24c97b561a564467e8c6d46f1d4380a9effa3d431469be0d643` |
| `20-multihop-fast-blind-v1.3.1-r2` | `0b7149a128f223c54a49f1478da0bcafa73ab8ca` | `9d2f39b4806634dccf6e8c09bf02cc23dac6a2a22b6bcf8a102708df9e35db01` | `ab7f548a047bd24c97b561a564467e8c6d46f1d4380a9effa3d431469be0d643` |
| `20r-multihop-fast-blind-v1.3.1-r2-replacement1` | `e642a1cfbd3f6d9147d6e9b75f6dd845890fafbb` | `1c38e29e3df92971b0e347cc4eabe4bea1845d34572632f3a3bef284442fd73d` | `ab7f548a047bd24c97b561a564467e8c6d46f1d4380a9effa3d431469be0d643` |

The authoritative remote evidence retains each freeze manifest, fresh-store roots,
trace, result, summary, evaluator outcome when applicable, and tc before/applied/
restored snapshots. Sanitized local copies contain no private task/evaluator files.

## Preliminary interpretation

The completed replicate-1 matrix provides preliminary evidence that the Aware
Manager can observe an anonymous fast/constrained distinction and generate a
different, more reduction-heavy workflow under Slow infrastructure. In the Slow
cell this coincided with lower action traffic and E2E at the same measured score.

It does not establish a stable method advantage or causal effect. The evidence is
limited by one completed replicate, stochastic workflow differences in Blind, all
scores being zero, unknown service-cost profiles, and the cloud-provider outage
that prevented r2/r3.

Per the frozen protocol, no prompt, budget, model, scheduler, operator, evaluator,
or task was changed to manufacture a result. The remaining queue is stopped rather
than retried a third time.
