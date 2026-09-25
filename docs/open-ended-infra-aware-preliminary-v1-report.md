# Open-ended infra-aware preliminary v1

## Outcome

The 18 planned cells are accounted for. Fourteen cells produced valid benchmark
executions, three LongBench multi-document cells failed plan validation before
execution, and one 3 Mbps MultiHop multi-source cell failed replanning validation.
The validation failures are Planner/Replanner contract failures, not runtime or
evaluator failures.

The preliminary provides a limited positive signal for infrastructure-conditioned
initial planning, but not for successful online workflow evolution:

- Video-MME 795-3 used a 16-frame, 199,282-byte path at 3 Mbps and a 32-frame,
  381,507-byte path at 10/30 Mbps. All three answers scored 1.0. The 3 Mbps path
  finished in 32.2 s versus 117.0/122.0 s for the two 32-frame paths.
- MultiHop reasoning used direct three-shard retrieval plus one terminal model call
  at 3/30 Mbps, but inserted an extra evidence-model stage at 10 Mbps. Quality stayed
  1.0, while the extra stage increased E2E from 8.0/7.7 s to 20.2 s. This is an
  observable wrong-cost/over-processing failure rather than a benefit.
- No valid run changed its pending graph at the evidence checkpoint: every valid
  Replanner decision was `keep`. The only `revise` attempted to expand a five-agent
  graph to nine agents and was correctly rejected against frozen `max_agents=6`.

Therefore the experiment observes `G(H_low) != G(H_mid/high)` for some fresh G0
plans, including one quality-preserving system difference, but does **not** establish
a causal or stable `H -> G` effect and does **not** demonstrate a successful
`G0 -> G1` infra-aware revision. Each regime invokes the cloud Planner once and
`n=1`; residual model-generation variance is inseparable from the infrastructure
condition in this preliminary.

## Exact setting

- Frozen semantic substrate: `c39565d799d5a02c00eeef07024c536cbdc6a3ad` on
  `open-ended-mas-preliminary-v1`; no semantic prompt tuning was performed during or
  after these runs.
- Tasks: Video-MME 795-3 and 848-1; frozen LongBench multi-document and structured
  tasks; frozen MultiHop multi-source and reasoning tasks.
- Network regimes: 3, 10, and 30 Mbps; added RTT 0 ms. HTB filtering covered all
  worker data paths. Every included cell has four shaped-class counter snapshots,
  zero tc cleanup error, and zero artifact cleanup error.
- Initial artifacts, hashes, representation, placements, evaluator, output contract,
  operator vocabulary, model pool, and B0 locality-aware scheduler match the frozen
  Blind baseline. Dataset materialization and worker distribution occurred only on
  the 4090 host; no dataset passed through the development machine.
- Planner/Replanner infrastructure view: artifact locations/sizes, link
  bandwidth/RTT, worker availability/in-flight state, deployments, and 24 frozen
  service-profile points. All agents selected the strong-4090 model instance; B0
  kept data operators near their initial artifacts and transferred derived evidence
  to the bound model deployment.
- Replanning: one checkpoint after materialized semantic evidence and before the
  terminal model node; completed nodes and artifacts are immutable.
- No candidate workflow/path/topology pool, heuristic routing strategy, automatic
  retry/replacement, RL, critic, or memory was added. The one manually isolated
  continuation after an audited infrastructure confounder is disclosed below.

The system cost contract evaluates the arbitrary Planner DAG. It uses:

```text
transfer_ms = rtt_ms + size_bytes * 8 / (bandwidth_mbps * 1e6) * 1000
node_ms = input_transfer_ms + profiled_service_ms
          + profiled_service_ms * current_queue_units
critical_path_ms = max source-to-sink sum(node_ms)
```

The lexicographic objective is: preserve benchmark semantics/evidence/output
contract; minimize predicted critical path; then minimize transfer latency and bytes.
Unknown routes, sizes, or profiles are explicitly marked unknown and are never
treated as zero. Generic operator placement remains B0 AUTO; model placement is the
fixed logical-agent model binding.

## Primary cells

`Pred` is the pre-execution system estimate for G0. `Model` excludes Planner and
Replanner service. `Node` is the sum of executed node latencies and may exceed the
critical path when branches overlap.

| Run | Outcome; G0→G1 | Pred CP ms / bytes | Actual E2E / CP ms | Transfer bytes / ms | Planner / Replanner ms | Model / Node ms | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| 01 795-3 / 3 | valid keep; `cb010c41→cb010c41` | 47,817 / unknown | 32,175 / 24,174 | 199,282 / 554.2 | 5,292 / 1,391 | 3,079 / 23,618 | 1.0 |
| 02 795-3 / 10 | valid keep; `c0b0fa40→c0b0fa40` | 47,817 / unknown | 117,050 / 108,067 | 381,507 / 325.0 | 6,185 / 1,425 | 4,363 / 107,740 | 1.0 |
| 03 795-3 / 30 | valid keep; `bb7c006d→bb7c006d` | 47,817 / unknown | 122,040 / 111,815 | 381,507 / 121.8 | 6,631 / 1,631 | 8,226 / 111,691 | 1.0 |
| 04 848-1 / 3 | valid keep; `246d3377→246d3377` | 45,050 / unknown | 87,646 / 78,393 | 429,488 / 1,218.7 | 7,124 / 1,132 | 1,985 / 77,173 | 0.0 |
| 05 848-1 / 10 | valid keep; `78816776→78816776` | 47,817 / unknown | 100,649 / 91,080 | 422,142 / 358.8 | 7,007 / 1,375 | 15,524 / 90,719 | 1.0 |
| 06 848-1 / 30 | valid keep; `55f61c50→55f61c50` | 47,817 / unknown | 98,069 / 89,192 | 422,142 / 131.6 | 6,792 / 1,335 | 13,927 / 89,059 | 0.0 |
| 07 LongBench multidoc / 3 | `workflow_plan_invalid`; no G0 | — | 6,468 / — | 0 / 0 | 5,613 / 0 | 0 / 0 | — |
| 08 LongBench multidoc / 10 | `workflow_plan_invalid`; no G0 | — | 6,706 / — | 0 / 0 | 5,974 / 0 | 0 / 0 | — |
| 09 LongBench multidoc / 30 | `workflow_plan_invalid`; no G0 | — | 7,266 / — | 0 / 0 | 6,930 / 0 | 0 / 0 | — |
| 10 LongBench structured / 3 | valid keep; `d2969290→d2969290` | 15,161 / 4,457,124 | 6,099 / 1,021 | 294 / 11.8 | 2,622 / 1,707 | 781 / 1,007 | 0.0 |
| 11 LongBench structured / 10 | valid keep; `92c6da3c→92c6da3c` | 6,841 / 4,457,124 | 6,577 / 974 | 294 / 11.3 | 2,907 / 1,594 | 711 / 961 | 1.0 |
| 12 LongBench structured / 30 | valid keep; `8e0cfbe5→8e0cfbe5` | 4,464 / 4,457,124 | 6,288 / 891 | 294 / 9.4 | 2,808 / 1,546 | 721 / 879 | 0.0 |
| 13 MultiHop multi-source / 3 | `workflow_replan_invalid`; `a18db9c4` retained | 6,189 / 12,288 | 18,470 / 6,272 | 7,924 / 309.6 | 4,055 / 6,712 | 5,502 / 6,664 | — |
| 14 MultiHop multi-source / 10 | valid keep; `95f1473e→95f1473e` | 6,424 / 24,576 | 20,605 / 6,825 | 15,808 / 82.9 | 5,169 / 1,104 | 11,195 / 13,394 | 1.0 |
| 15 MultiHop multi-source / 30 | valid keep; `0dbd45d1→0dbd45d1` | 6,417 / 24,576 | 17,085 / 4,539 | 17,468 / 291.2 | 5,292 / 1,017 | 6,888 / 9,126 | 1.0 |
| 16 MultiHop reasoning / 3 | valid keep; `874bcf8e→874bcf8e` | 3,423 / 12,288 | 7,951 / 2,354 | 8,968 / 38.1 | 3,703 / 1,125 | 1,905 / 3,075 | 1.0 |
| 17 MultiHop reasoning / 10 | valid keep; `3f3f1836→3f3f1836` | 6,166 / 12,288 | 20,192 / 13,117 | 8,968 / 144.9 | 4,476 / 1,613 | 12,571 / 13,750 | 1.0 |
| 18 MultiHop reasoning / 30 | valid keep; `6f049c6b→6f049c6b` | 3,394 / 12,288 | 7,733 / 2,445 | 8,968 / 43.0 | 3,357 / 1,404 | 2,005 / 3,188 | 1.0 |

## Workflow differences and failure modes

### Video-MME 795-3

All regimes used `sample_frames -> make_contact_sheet -> invoke_model ->
invoke_model` and executed deterministic media operators on A4, then moved the
contact sheet to strong-4090. At 3 Mbps the Planner selected 16 frames every 30 s;
at 10/30 Mbps it selected 32 frames every 78 s. This is the clearest
quality-preserving infrastructure-conditioned difference. The lower E2E came mostly
from lower media-operator work, not only from the lower transfer time.

### Video-MME 848-1

The 3 Mbps plan collapsed evidence analysis and terminal answering into one model
node; 10/30 Mbps used a separate visual-evidence call followed by a terminal call.
Scores were 0/1/0. The non-monotonic quality and similar 10/30 topology show that the
result is not a reliable cost-quality policy. This is evidence selection/reasoning
variance and quality-cost conflict, not a system failure.

### LongBench multi-document

All three Planner outputs were rejected before execution. A generated notes node had
an estimated input of 15,526–15,566 tokens plus 1,024 reserved output tokens against
a 16,384-token context. The Planner was given the context limit and operator/schema
contract, and the runtime performed no truncation. This is repeated context-budget
planning failure.

### LongBench structured

All regimes produced the same material workflow:
`filter -> derive ratio -> select -> top-k -> invoke_model`. B0 ran the four data
operators on A4 and transferred a 294-byte result to strong-4090. The only structural
difference was one versus two logical agents. Scores of 0/1/0 arose from terminal
model output variation; the canonical hashes also include names and prompt wording,
so hash inequality here is not an infrastructure-relevant topology change.

The conservative G0 estimator propagated the full 4.46 MB input size through the
generic reductions, while the actual top-k artifact was 294 bytes. This did not
silently understate cost, but it exposes a calibration limitation: derived artifact
size profiles are required before predicted transfer magnitude can be considered
accurate.

### MultiHop multi-source

At 3 Mbps G0 used one BM25 query per shard, an evidence model, and a terminal model.
The evidence model correctly reported insufficient Sorcerer coverage. The Replanner
then proposed a second three-shard retrieval/evidence branch, but expanded the graph
from five to nine agents and violated `max_agents=6`; fail-closed validation rejected
G1. This is the only semantically useful replan trigger and demonstrates both
evidence-aware revision intent and constraint-ignorant composition.

At 10/30 Mbps G0 directly used separate Sorcerer and Barbarian queries over all three
shards, two evidence notes, and terminal synthesis. Both scored 1.0. The two plans
differed in logical-agent decomposition, but not in the material operator topology.

### MultiHop reasoning

The 3/30 Mbps plans used three parallel shard retrievals followed directly by the
terminal model. The 10 Mbps plan inserted an extra evidence-model node. All answers
scored 1.0, but the extra model stage increased model service from about 1.9–2.0 s to
12.6 s and E2E to 20.2 s. This is a clear myopic/over-processing failure: greater
workflow complexity did not improve quality or traffic.

Across all valid runs the Planner never bound a logical agent to the much slower A28
model deployment. Physical operator placement nevertheless used A4/A5/A28 for local
data processing, and all model nodes executed at the fixed strong-4090 binding.

## Validity and confounder audit

- All 18 included JSONL traces have a valid parent chain and exactly one terminal
  `run.end` or `run.failed` event. Planner failures contain three events but remain
  fully reconstructable.
- Planner/Replanner prompts contain none of `source_ref`, `evaluator_id`, gold-answer
  fields, or supporting-evidence fields. Agent prompts are generated from the
  sanitized task view.
- All successful evaluations used the original benchmark output contract and
  evaluator. There was no hidden finalizer, fallback, retry, model substitution, or
  truncation.
- Every included cell recorded four shaped HTB class snapshots at its requested
  bandwidth. After the final run, A4/A5/A28 roots were restored to `mq` and the 4090
  root to `noqueue`.
- An earlier queue attempt stopped before cell 02 because the 4090 self-SSH host key
  was missing. Its evidence was preserved and excluded.
- Primary attempt2 stopped at the original cell 15 when one execution snapshot
  transiently reported A4 unavailable and therefore could not materialize shard-1.
  The Planner snapshot five seconds earlier contained A4 and shard-1; the worker did
  not restart, tc recorded no packet drops, and A4 immediately recovered. A separate
  shaped 30 Mbps stability check made 20 concurrent worker-state probes with zero
  failures. Cells 15–18 were then run in a separate continuation directory; the
  invalid original cell 15 remains preserved and is not counted as a Planner result.

Local evidence locations (ignored by Git):

- `results/open-ended-infra-aware-preliminary-v1/evidence-primary-attempt2`
- `results/open-ended-infra-aware-preliminary-v1/evidence-continuation-attempt3`

## What this supports—and what it does not

This preliminary supports method work on three concrete problems:

1. constrained, valid graph revision: the useful MultiHop replan exceeded the agent
   budget;
2. calibrated derived-artifact size/service models: conservative estimates can be
   far above actual reduced traffic;
3. cost-to-action discipline: the 10 Mbps reasoning plan added a costly model stage
   without quality gain, while every valid Replanner chose `keep`.

It does not yet support a claim that infra-aware replanning improves latency,
traffic, cost, or quality. It also does not establish that bandwidth caused the G0
differences, because the open-ended Planner was called independently once per cell
and there are no repetitions. A formal comparison needs a paired/frozen source of
planner stochasticity or repeated generation, plus explicit handling of invalid
plans; neither was added here.

No additional benchmark, bandwidth regime, repetition, semantic tuning, RL, critic,
memory, or proposed method was run.
