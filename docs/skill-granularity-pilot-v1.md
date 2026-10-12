# Skill Granularity Pilot v1

This exploratory pilot runs **30 formal cells on three new tasks**, with one
attempt per cell. It compares frozen Manager guidance at different levels of
detail. There is no additional model capability Gate, training, dynamic Skill
retrieval or automatic follow-up experiment. Historical experiments and their
conclusions remain separate.

The authoritative plan is
[skill-granularity-pilot-v1.json](../configs/experiments/skill-granularity-pilot-v1.json),
based on commit `1813266`. Public task receipts are in
[skill-granularity-tasks-v1.json](../configs/experiments/skill-granularity-tasks-v1.json).
The running application's source, configuration, task and Skill freezes are
immutable; this document does not change that application.

## Matrix and fixed execution order

| Manager | Skill conditions | Tasks per condition | Cells |
| --- | --- | ---: | ---: |
| Qwen3.5-4B | S0, S1, S2, S3 | 3 | 12 |
| Qwen3.5-9B | S0, S1, S2, S3 | 3 | 12 |
| Actual Qwen3.8-27B | S0, S3 | 3 | 6 |
| Total | | | **30** |

Task indices are t1 = MultiHop-RAG, t2 = LongBench-v2, t3 = Video-MME.
Each family uses frozen position 1. Models run in the order 4B, 9B, 27B to reduce
model loading. Conditions rotate within each task in the following exact order;
the schedule was fixed before inference and is not reordered using outcomes.

| Cell positions | Manager | Task | Conditions, left to right |
| --- | --- | --- | --- |
| 1–4 | Qwen3.5-4B | t1 | S0, S1, S2, S3 |
| 5–8 | Qwen3.5-4B | t2 | S1, S2, S3, S0 |
| 9–12 | Qwen3.5-4B | t3 | S2, S3, S0, S1 |
| 13–16 | Qwen3.5-9B | t1 | S0, S1, S2, S3 |
| 17–20 | Qwen3.5-9B | t2 | S1, S2, S3, S0 |
| 21–24 | Qwen3.5-9B | t3 | S2, S3, S0, S1 |
| 25–26 | Qwen3.8-27B | t1 | S0, S3 |
| 27–28 | Qwen3.8-27B | t2 | S3, S0 |
| 29–30 | Qwen3.8-27B | t3 | S0, S3 |

The nominal key `qwen35-27b` is retained for compatibility, but its actual frozen
checkpoint is **Qwen3.8-27B**, not Qwen3.5-27B. This pilot has no new strong-cloud
Manager baseline. The strong model is retained for Specialist and Verifier roles.

## New task selection and novelty evidence

Selection takes the first source row not excluded by the historical-reference
census, without filtering by answer, difficulty or outcome. Video selection also
excludes previously referenced source videos, including their other questions.
The selection record was frozen before task adaptation. Answers are sealed into
the original evaluator's private data and are not supplied for Skill design.

| Task | Original source ID | Zero-based source row | Initial artifact bytes |
| --- | --- | ---: | ---: |
| t1 | `multihop-rag-train-c384ed264fb5a5112e8e0d7e` | 10 | 7,696,522 |
| t2 | `66ec0c4c821e116aacb1994a` | 2 | 258,133 |
| t3 | `490-1` | 1,467 | 21,696,914 |

The bounded census covered **41,226 files, 19,533 distinct scanned contents and
713 recorded run IDs** across the existing related research-project roots.
It examined run results, trace task-start records, selection/freeze receipts and
repository scripts, configuration and documentation, including Skill design
material. API payload directories, rendered contexts, dependency trees, model
blobs and raw dataset directories were excluded. No whole-machine search was
required. The policy conservatively excludes historical ID or question-text
references even when those references alone do not prove a completed experiment.

One explicit exception is `scenario_mining_report.json`: this source inventory
listed the entire cached LongBench source set. Inventory presence alone does not
establish testing or Skill design use. Its scanned-content hash is retained in
the private novelty receipt, but its inventory-only references do not mark every
cached sample as previously used. This distinction and the preceding-row
exclusions are recorded rather than inferred from evaluation results.

Novelty means absence from the recorded project evidence under this policy. It
does not establish absence from model pretraining or unrecorded external use.
The sources comprise 2,556 MultiHop questions, 208 cached LongBench samples and
2,700 original Video-MME annotations. The video is extracted losslessly from the
pinned original archive, with its size, CRC and SHA256 checked; no clip substitutes
for the original task video.

The task representations reuse the existing adapters: full MultiHop corpus in
three shards; complete, byte-reconstructable LongBench context in one logical
container with lossless chunks; and full original Video-MME video without
subtitles. The LongBench container is not claimed to be an audited natural-source
document count. Initial placements remain A4/A5/A28 for the three MultiHop shards,
and A4 for LongBench and video. Adapter, original evaluator, input, task-view and
bundle hashes are recorded; all three bundles passed the original `frozen_task`
reload checks without inference.

| Evidence | SHA256 |
| --- | --- |
| Task manifest | `e0e242db5140d75f5d3c9f8559db205994eeb0cfba17797325d0b53545fc212a` |
| Private novelty receipt | `5b3dc06a00451ba84febc06e58d086182927f4a5e411b8c2a1316fa38db359b9` |
| Selection before adaptation | `663f9367e4e02999e67932c2d9f4732399b46ba94b7894188700c74abc277d83` |

## Frozen Skill conditions

| Condition | Guidance | UTF-8 bytes | Frozen file |
| --- | --- | ---: | --- |
| S0 | Original base Manager instructions | 0 added | None |
| S1 | Original procedural Skills, unchanged bytes | 1,555 | [planner-procedural-v1.md](../configs/skills/planner-procedural-v1.md) |
| S2 | Expanded procedure and explicit tool reference | 11,342 | [planner-procedure-v1.md](../configs/skills/planner-procedure-v1.md) |
| S3 | Atomic condition/action SOP and explicit tool reference | 12,565 | [planner-atomic-sop-v1.md](../configs/skills/planner-atomic-sop-v1.md) |

S1 retains SHA256
`d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422`.
All condition hashes are pinned in the plan. The complete frozen condition text
is appended only to the Manager's original instructions and remains fixed for
that cell; no retrieval mechanism selects or changes guidance during execution.
Synthetic JSON examples in S2/S3 were checked offline against the existing tool
schemas, without reading evaluation tasks, invoking tools or probing a model.

S2/S3 explicitly describe required call fields, artifact materialization and
handoffs, phase restrictions, input-size limitations, recovery and final-answer
ownership. Their extra tool knowledge and substantially greater length are
**confounders**, alongside their procedural granularity. This is not an
equal-length or equal-information comparison. A change cannot be attributed to
atomic SOP structure alone. UTF-8 bytes are not token counts: deployed tokenizers
measure standalone Skill tokens and the increment in full Manager instruction
tokens without generation. Those measured values remain pending until exported.

## Fixed roles and execution semantics

All Managers use the previously verified Q4_K_M weights on Ollama 0.34.0,
`num_ctx=32768`, output reserve/max tokens 2,048, temperature 1, top_p 0.95 and
`reasoning_effort="none"`. Qwen3.5-4B/9B use the pilot-owned independent A28
Planner service; Qwen3.8-27B uses the existing controller GPU0 resident endpoint.
The latter endpoint also remains part of the fixed Executor pool, so its service
work must not be double-counted as independent Planner work.

Specialist and blind Verifier retain `qwen3.8-max`, their original instructions
and native settings. Verifier retains temperature 0, required function calling
and its existing turn limit. Physical Scheduler, five resident Executor
instances, model pool, operator behavior, benchmark and evaluators are unchanged.
Agents remain blind to physical resource profiles. Each cell gets fresh Worker
processes and isolated artifact stores; model caches remain warm.

Raw function-call JSON Schema validation applies identically to every condition.
Invalid calls produce observable failures and are not silently repaired or
executed. The existing phase machine is unchanged: synthesis admits only
`invoke_model` or a final response. Skills add guidance, not new guards,
permissions, operations or phase transitions. The existing fail-closed Manager
preflight renders and tokenizes the real complete request before forwarding it,
and verifies accepted provider prompt usage. Physical model input admission uses
its existing conservative payload-size proxy; that proxy is not a tokenizer
measurement.

The fixed Fast network regime is 100 Mbps with 5 ms added RTT. One unchanged
shaping transaction covers the continuous batch and restores the original
configuration in `finally`; any authorized continuation has a separately retained
network receipt.

## Budgets, stop policy and continuation

| Per-cell control | Limit |
| --- | ---: |
| Manager turns / Specialist turns | 20 / 8 |
| Tool model calls / Verifier calls | 64 / 20 |
| Created / active Specialists | 4 / 2 |
| Control / physical / context-helper HTTP requests | 72 / 64 / 4,096 |
| Serialized control input | 134,217,728 bytes |
| Task budget | 3,600 seconds |
| Worker/model drain | 1,260 seconds |
| Cell wall ceiling | 5,100 seconds |
| Entire matrix wall ceiling | 216,000 seconds (60 hours) |

The execution wrapper also bounds the task coroutine at 3,840 seconds. Cloud
requests retain a 180-second timeout and zero automatic SDK retries. Request
hooks charge the actual shared counters and check STOP/deadlines. Resource
admission requires at least 512 MiB free on each controller GPU and 8 GiB available
A28 RAM, using cached samples refreshed approximately every 10 seconds. Low
reserves cause bounded waiting, not changes to foreign processes. Sampling is not
a continuous peak-memory measurement.

Score0, incorrect answers, schema/phase violations, failed recovery and legitimate
turn/request/context/time-budget exhaustion are recorded outcomes. They do not
authorize selective reruns or additional capability Gates. The remaining queue
continues when execution boundaries remain sound. System failures—such as
unverified/truncated context, budget protection failure, authentication failure,
controller implementation errors, evaluator inconsistency, isolation/cleanup
failure or insufficient resource reserves after the bounded wait—stop subsequent
dispatch. These failures do not become evidence of model incompetence.

Startup performs the full source/history/task/Skill and resident-identity freeze.
Cell boundaries perform lightweight budget, context, resource, authentication,
owned-Worker cleanup and resident-log checks. The final pass compares source and
protected hashes, evaluator results, resident identities, network restoration
and all executed Worker cleanup. It produces sanitized results once; partial
receipts retain an interrupted batch's evidence without rewriting the original
conclusions or launching historical Phase II.

Continuation uses the original frozen source, tasks, Skills, order, resident
deployment and absolute matrix deadline. Finished cells are skipped. A claimed
but interrupted cell consumes its attempt, is drained and recorded, and is never
inferred again. Only cells not previously claimed may execute. A partial stop
unloads the owned Planner model and tokenizer tunnel while preserving the idle
owned server/API tunnel and evidence for continuation. Completion shuts down
those owned services. Foreign processes and original resident Executors are not
stopped or reconfigured.

## Launch and STOP

The batch has been launched. The following commands document the controller
entry point; they are not an instruction to launch a duplicate batch. `ROOT`
denotes the deployed pilot's `run-001` directory, and the interpreter is its
existing compatible Python environment. Supply private paths locally, never in
published metadata.

```bash
export ROOT='<experiment-root>/run-001'
export PYTHON='<compatible-python-interpreter>'
export KEY_FILE='<private-api-key-file>'
cd "$ROOT/app"
PYTHONPATH="$ROOT/app/src:$ROOT/app/scripts" \
  "$PYTHON" scripts/run_skill_granularity_pilot_v1.py \
  --api-key-file "$KEY_FILE"
```

Create the owned STOP file for a cooperative stop; the next budget/resource or
dispatch check prevents further work and the runner follows its cleanup path:

```bash
touch "$ROOT/STOP"
```

SIGTERM/SIGINT also create that STOP file. Stop/cleanup can take time while
in-flight work drains. An explicitly authorized continuation requires the STOP
request to have been revoked and uses the same command with `--resume`; it does
not reset attempts or the frozen matrix deadline. Do not run concurrent runners.

## Analysis and pending results

Report Completion and original-evaluator TSR as counts out of three tasks for
each model/condition, with per-task paired changes, schema/phase/recovery and
terminal failures, workflow operators/owners/edges, and representative failure
chains. Keep completion distinct from answer correctness and distinguish system
errors from model or lawful budget outcomes.

Report Manager/Specialist/Verifier turns, input/output/cache tokens and known
cloud API charges; physical inference calls, measured model-service/runner work,
E2E/operator timing, transfers, deployment and sampled resource usage. Runner
reported work is not measured GPU busy time; overlapping intervals are not
automatically additive. Missing token/cost/work observations remain unknown.
Cloud subtotals do not establish full resource savings: local GPU/CPU pricing,
energy and full monetary costs are unknown, and no GPU price is invented.

With three distinct tasks and one stochastic attempt per cell, all findings are
exploratory. Rotated order reduces one simple order imbalance but does not remove
warm-cache, service drift, hardware or sampling variability. The 27B condition
also differs in generation and placement; it cannot establish a pure model-size
effect. No significance or general benchmark-level TSR claim is supported.

**Completed: 30/30 formal cells, one execution each.** The original prospective
analysis specification above is preserved. Final observations and the next-step
No-Go decision are in [the results report](skill-granularity-results-v1.md), with
the complete [sanitized delivery](../analysis/skill-granularity-pilot-v1/skill-granularity-report.md).

## User-directed shared-resource concurrency amendment

After launch, the user explicitly authorized concurrent execution on shared
resources and clarified that TSR evaluation need not preserve isolated E2E
timing. This is a prospective execution amendment. The original serial protocol,
execution freeze and records above remain the historical preregistration; they
are not rewritten to describe concurrency as the original design.

The first two cells, `qwen35-4b-t1-S0` and `qwen35-4b-t1-S1`, retain their original
serial placement in the execution history. Handoff occurs after the running S1
cell finishes and cleans up. Neither cell is rerun. The remaining **28 cells**
use an administration runner outside the frozen application, with at most
**three concurrent cells**. Dispatch follows their original fixed order, in
bounded waves within the same Manager-model block. A wave drains before the next
wave starts, and all work in one model block drains before a model switch.
Completion order may differ from dispatch order. The matrix remains exactly 30
cells with one attempt each; the amendment adds no model capability Gate.

Concurrency overlaps cell pipelines: control-plane requests, artifact operations,
Verifier/Specialist work and model-service waits can overlap across cells. Model
serving parallelism remains `np=1`. Context stays 32K, and backend, quantization,
sampling, frozen Skills, semantic prompts, tools, phase/schema validation,
evaluators, Physical Scheduler and original resident Executor process identities
remain unchanged. Independent cell processes isolate mutable Python globals,
Worker ports and artifact namespaces. The three-cell bound, existing request and
resource budgets, STOP mechanism and cleanup requirements still apply; shared
resources do not authorize changes to foreign processes.

The administrative handoff and placement metadata must distinguish the two
original serial cells from the shared-resource continuation. This changes the
execution treatment, so E2E, operator timing and log-reported model/runner work
are **diagnostic observations under contention**. They do not establish isolated
latency, exclusive per-cell resource consumption or a clean resource-cost
comparison. Shared service log intervals can overlap; summing them across cells
can double-count work. Missing or inseparable attribution remains unknown.

TSR and Completion retain the original evaluator and denominator, with every
claimed attempt preserved. Interpret them as exploratory observations from the
amended execution conditions. Cache reuse, shared-service scheduling, concurrent
numerical variability and the serial-versus-parallel transition are potential
confounders even when timing is not an optimization target. In particular, the
two serial t1 conditions and their concurrent t1 counterparts do not provide a
fully matched execution comparison. Record any provider, resource or system
failures separately rather than silently attributing them to Skill granularity.
The existing three-task, one-attempt limitations and unknown full monetary cost
remain in force. The completed matrix and final export retain this amendment
and both original serial cells.

### Administrative continuation after a model transition

After all 12 formal 4B cells had finished, the first concurrent daemon stopped
at 2026-10-12 10:34:38 UTC during the next model-group transition with
`OSError: [Errno 98] Address already in use`. The tokenizer forwarding port
subsequently became bindable. The preserved partial integrity receipt reports
unchanged frozen sources, protected history and tasks, original five Executor
instances, restored network settings and drained Workers, with no system
integrity findings. No 9B cell had been claimed at this interruption.

At 10:39:32 UTC, the unchanged administrative runner was launched with `--resume`.
Its recovery receipt records 12 completed cells preserved, zero unfinished
claims, no runtime changes and zero semantic retries. The remaining 18 cells
retain their frozen order and conditions. This administrative interruption is
kept separately from model capability outcomes. A transient port lifecycle
conflict is consistent with recovery without code changes; the failure-time
socket state was not captured, so a specific TCP state is not established.
