# Blind Baseline Smoke audit

## Outcome

The smoke stopped at workflow planning. Both selected MultiModalQA tasks received exactly
one `deepseek-chat` Planner call, with no retry, replacement, or prompt tuning. Both returned
a graph that violated its own logical-agent capability declaration, so plan validation failed
before artifact placement, orchestration, worker execution, terminal answer extraction, or
evaluation.

No benchmark run was started, no workflow was accepted/frozen, and no 3/10/30 Mbps replay
was attempted.

| Task | Modalities | Planner calls | Result | Runtime | Evaluator |
|---|---|---:|---|---|---|
| `09e997f80f700a93c2094af964de65e6` | image + table | 1 | `retrieval-agent` used undeclared `aggregate_artifacts` | not started | not called |
| `1e288b881eea53a6e3e3e56bd79f40e5` | image + text | 1 | `retrieval-agent` used undeclared `invoke_model` | not started | not called |

The second raw completion was preserved. Before external contract validation it described a
natural three-agent candidate with three model-using agents, two materialized cross-agent
model handoffs, two fan-in nodes, and one terminal synthesis node. It is still an invalid
`WorkflowPlan`, so none of those intended properties are counted as executed MAS evidence.
The first attempt used the initial harness, which preserved the exact validation error but not
the raw completion or exact prompt bytes; it was not retried.

## Benchmark and privacy preflight

- Source revision: `4dd14328c6d02a4daa357cc6032915a0b14602e3`.
- Both tasks use the original dev question and private answer/support/intermediate annotations.
- Adaptation materializes all ten candidate texts, the full table, and all candidate images
  losslessly; information, query, and evaluator equivalence are recorded as true.
- Planner input was limited to the sanitized task, opaque model instances, and generic
  operators. `max_agents=6`; `min_agents=null`; the prompt explicitly allowed one agent.
- Structural checks found no `source_ref`, evaluator ID, gold, supporting context, or
  intermediate answers in either Planner input. `AgentTaskView` excludes the same private
  fields.
- The MultiModalQA evaluator port was aligned with the upstream number-word normalization and
  alternative-reference semantics before the calls. It was not invoked because neither task
  reached a terminal answer.

Pinned dataset hashes:

| File | SHA-256 |
|---|---|
| `MMQA_dev.jsonl.gz` | `2e348ca574b2dc368e84671709689070f943a59f2e08e6b6e374705deb712d31` |
| `MMQA_texts.jsonl.gz` | `cae3808ccc6c258e91131a3ca3dce43e629936e1496c97a288c4abb04a6ef905` |
| `MMQA_tables.jsonl.gz` | `8d082d254fd0bfa19bca7e2da20369c15ccb25867db3edfe46b33d59e8dbf7b1` |
| `MMQA_images.jsonl.gz` | `691227e1758140c51a5617a904b5e363cd44b2582a0c0e9f9fe9153d4e62d5e7` |

Native-network preflight found no experiment HTB/netem shaping. A4, A5, A28, and
`strong-4090` were available and idle, and their operator/deployment surfaces matched the
configured environment. These checks do not constitute a benchmark run.

## Root cause and stopping decision

The observed failure is a repeatable failure class within the two no-retry samples: the LLM
created sensible-looking nodes but made each node's operator inconsistent with its owning
agent's self-declared `allowed_operations`. The runtime correctly rejected both graphs before
execution. This is a Planner self-consistency failure, not evidence about Agent Runtime
execution quality, model answer quality, the evaluator, physical scheduling, or network
sensitivity.

The audit also found that the initial failure-capture path did not preserve an invalid raw
completion and that modality-set serialization could change prompt byte ordering across
processes. Invalid completions are now persisted and modalities are deterministically sorted;
neither task was rerun after these evidence fixes.

The requested stopping rule is therefore active: no workflow replay or infrastructure sweep
should begin from this smoke. Evidence is under
`results/open-ended-mas-preliminary-v1/blind-baseline-smoke-v0/`.
