# Minimal resource-blind workflow replanning v1 audit

## Scope

This stage adds one bounded semantic replanning point before the terminal model node. It does
not add a critic, memory, RL, retry policy, model substitution, new operator, benchmark, or
network regime. The model pool, B0 scheduler, RuntimeExecutor, deterministic terminal-answer
extraction, and private benchmark evaluator are unchanged.

The execution form is:

`G0 -> execute immutable prefix -> semantic observation -> keep or revise -> G1 -> execute pending suffix -> terminal answer -> evaluator`

The current validation allows at most one replanner call. Completed nodes and materialized
artifacts remain live and are never replayed. A proposed revision fails before further execution
if it removes or changes a completed node, changes an agent that owns completed work, changes an
incoming edge of a completed node, violates the fixed action/model space, or exceeds a model
context contract.

## Planner-visible semantic contract

Full-corpus MultiHop artifacts now declare a common collection relationship:

- `collection_id = <task-id>:complete-corpus`
- `partition_method = sha256(document) modulo partition_count`
- `partition_semantics = non_semantic`
- `completeness = union_is_complete`

The initial planner, replanner, workload, and agent task view receive these logical fields. The
replanner also receives completed-node semantic outputs, pending node IDs, fixed operator/model
contracts, and conservative context-preflight guidance. The resource-blind validation receives
no future-path infrastructure feedback.

The replanner request contained no serialized source reference, evaluator ID, gold answer,
supporting evidence, artifact location, link, IP address, bandwidth, RTT, queue, or load value.
Physical scheduler decisions remain in the execution trace but never enter the replanner input.

## Contract-development attempts

All attempts are preserved; no evidence was overwritten.

| Attempt | Result | Classification |
|---|---|---|
| attempt 1 | Replanner correctly detected missing Barbarian evidence but tried to append new inputs to completed `notes-barbarian`; validator rejected it before G1 execution | Invalid contract-development run; immutable-prefix instruction was underspecified |
| attempt 2 | Replanner used fresh nodes, but new `notes-barbarian-2` had a 22,331-unit conservative input bound against a 16,384 context window | Invalid contract-development run; replanner lacked G0's system-derived context-preflight guidance |
| attempt 3 | Both required cases completed with one replanner call each | Valid minimal-loop validation |

The two corrections were generic contract alignment. No generated plan was repaired, no top-k
was silently lowered, and no task-specific query or routing rule was inserted by the runtime.

## Valid attempt-3 settings

- Network: native/unshaped on A4, A5, A28, and the dual-4090 host.
- Initial plans: exact previously frozen MultiHop plans.
- Replanner: DeepSeek `deepseek-chat`, temperature 0, semantic-only visibility.
- Replans: at most one per task; no automatic retry.
- Operators/model instances: unchanged from the competent Blind baseline.
- Evaluation: original private MultiHop-RAG evaluator.

Evidence is retained remotely under
`/home/super/xiaoming/minimal_replanning_v1/evidence-attempt3` and locally under the ignored
`results/minimal-replanning-v1-attempt3` directory. Attempts 1 and 2 are retained in the adjacent
`evidence` and `evidence-attempt2` directories.

## Results

| Task | G0 -> G1 SHA-256 | Decision | Answer / score | Runner E2E ms | Transfer bytes / ms | Operator / model-service ms | Replanner tokens / ms |
|---|---|---|---|---:|---:|---:|---:|
| MultiHop multi-source, previous failure | `9d139d964b225a966d40d8e202df98e642a5bf8a33f38ecaecf0ba071dbac9d5` -> `b842bf8cd50c87d2475f9c994e2e452ea485132a3e3ef1268ffe53f46fd1503d` | revise: `evidence_conflict_or_incomplete` | `Yes` / 1.0 | 68,081.7 | 22,734 / 186.6 | 59,541.0 / 56,846.7 | 6,924 in, 2,148 out / 6,652.1 |
| MultiHop reasoning, previous success | `88083572784f55d4c245d86a812909c6b819bb6287889b3a6209a5bc2cd1894a` -> unchanged | keep | `Will Smith and Jada Pinkett Smith` / 1.0 | 4,158.1 | 14,881 / 40.3 | 2,889.2 / 1,852.6 | 6,227 in, 55 out / 847.5 |

The failed case had previously produced `No` with score 0. Its completed Barbarian note explicitly
reported that the selected record was an unrelated controller article. G1 preserved every G0
node and added four retrieval nodes plus two bounded evidence-note nodes. The new Barbarian note
retrieved the actual Polygon Season 2 guide and quoted its statement that the builds were
simplified. Only the pending terminal node was modified to fan in the two new notes; it returned
`Yes` and the original evaluator scored it 1.0.

The successful control had sufficient, consistent evidence. The replanner returned `keep`; its
plan hash remained unchanged and no node was added, deleted, modified, or replayed.

## Reconstructability and invariants

- Failed-case trace: 178 events, valid parent chain, terminal `run.end`, SHA-256
  `b63c202e336ae0ecd326cbc134554266327229446b829bbcd27e85b70a027715`.
- Successful-control trace: 84 events, valid parent chain, terminal `run.end`, SHA-256
  `5f86319264572353ff2d74db631567c9062fd4fbf332d1abb072425f6a1b7638`.
- Every node in both final workflows has exactly one execution record.
- In the revised case, all five completed G0 evidence-prefix nodes executed exactly once; G1
  executed only the six added nodes and the modified, previously pending terminal node.
- The result records preserve every workflow version, canonical hash, trigger/reason, agent/node/
  edge change set, node and agent terminal states, placements, transfers, operator/model telemetry,
  terminal answer, and evaluator result.

## Conclusion

The minimal dynamic workflow loop is operational. Resource-blind semantic replanning recovered
the selected missing-coverage failure by using the newly visible non-semantic collection
relationship, while the successful control was left unchanged. This establishes the substrate
needed for a later controlled comparison between resource-blind and infrastructure-aware
replanning; it does not establish a general quality or latency improvement claim.
