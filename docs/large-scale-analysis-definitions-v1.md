# Offline analysis definitions — Phase I in progress

2026-10-05 historical definitions, clarified2026-10-06. These are reporting
definitions, not Agent guidance or a method change. Historical execution was
fa19e0b / execution-freeze-003, following the
independently audited transport-receipt-only repair. Historical executions at
94c9bac / execution-freeze-002 remain preserved. Analysis code is deployed outside
the frozen app. No prompt, model, tool, budget, scheduler, representation or run
order is changed by these reporting definitions. Those42results are now closed
and unpooled. Current measured resident/diverse execution is90fd30c /
execution-freeze-001 in the separate `large-scale-cost-guidance-resident-v1` root;
five resident instances are three model artifacts, not five quality tiers.
Current progress belongs in the latest top-workspace RESEARCH-STATUS and
[new-block checkpoints](large-scale-resident-checkpoint-069-v1.md), not the
historical [Phase I results](large-scale-phase1-results-v1.md) or this definitions
document. Later dated checkpoints supersede counts, not immutable source hashes.

## Exposure, querying and adoption

- Count actual Manager function calls from private raw provider responses,
  including the last turn. Accumulated SDK history is deduplicated and reported
  separately as a lower bound, never as the definitive last-turn call count.
- Report how many actual Manager requests expose estimate_* tools. Lack of
  adoption only has meaning where the interface exists (B/E), not in B0/B1/A.
- The observable eligible/high-impact denominator is **selected schema-valid,
  input-ready root physical-action opportunities**: a root decision with accepted
  ready execution or a valid ready quote. Include the finite native operator/model
  space without an arbitrary scalar cost/byte cutoff. Exclude pure thought/finish,
  rejected readiness and specialist decisions. Multiple ready actions in a turn
  count as one decision. This is not a count of unobserved counterfactual choices.
- Report query attempts (including invalid), valid cards, decisions receiving
  valid optional cards, matched cards and valid-query decisions / eligible
  decisions. A zero denominator is unknown, not an invented 0%.
- C/D: distinguish proposals, created quotes, authorized commits, actually
  observed executions, discarded/stale and final pending/expired/consumed states.
  Authorization is not physical execution. Discarding an alternative is not
  automatically a semantic workflow revision or evidence of cost-induced change.
- D: retain the frozen legacy returned-set-cardinality counter, but do not
  interpret a returned list of length>=2 as proof of alternatives comparison.
  Separately report submitted candidates, actual consequence cards, multi-card
  comparisons and comparisons with multiple physically feasible alternatives.
  An all-error three-member set is an attempted set, not three cards or an
  exercised multi-consequence comparison. The independent tested auditor checks
  exact created-card/member/source bindings and complete SDK tool-result equality
  before choice; substring mentions do not establish exposure. Selection,
  authorization and execution are separate. The system does not choose a winner.
  See the [bounded first64 audit](large-scale-resident-comparison-partial-064-v1.md);
  that subset does not authorize pruning or replace full168adoption analysis.
- E: report the frozen rule-set hash and actual visibility. Do not infer internal
  rule use from prompt presence. Explicit action evidence is analyzed separately.

Causal quote-induced revision, evidence retention and explanations of quality
failure still require the comprehensive post-run trace/private audit. The
collector leaves these unresolved rather than equating discard with revision,
or arbitrary prose with evidence preservation. No pruning is allowed now.

## Calls, costs and missingness

Distinguish reasoning starts, actual HTTP calls, prepared physical actions,
successful tools, successful models, reported inference reach and successful
model-service telemetry. A context/binding/readiness reject is not model inference.
Keep failed calls and their typed codes; model-service failures can have incomplete
token/work information and must not be silently treated as measured zero work.
Post-inference invalid-JSON model output can lose returned telemetry. The frozen
inference flag is then false despite a proved completed backend call; report its
successful-telemetry lower bound and separately audited post-inference failures.
Failed model tokens/service remain unknown, not zero; successful service subtotal
is not complete total work. Failed physical lifetime/work is separate, not a
substitute measurement of model service. Online spent ledger already marks such
incomplete inference/work unknown; reporting does not alter it.

SDK-only failures (for example a phase-restricted specialist request) can occur
without a prepared physical action. Deduplicate typed function-output receipts
per logical recipient/call ID and report them separately as lower bounds. They
can overlap logical observations or quote rejections and must not be added as
new physical calls. Last-turn outputs absent from a later input are unobserved.

Provider raw usage supplies Manager/specialist/Verifier token counts and API USD.
Missing tokens/cache/price/FX remain unknown; zero calls have zero executed work.
Count reasoning output as part of output totals, not an extra billable charge.
API USD is a frozen regional list-price estimate, not an invoice amount.

Initial artifact placement is fixed setup movement before Manager reasoning.
Report its bytes/time separately from action transfers. Transfer bytes describe
artifact payload, not packet-level wire overhead, Worker read-result RPC bytes or
cloud request/response traffic. A prompt-only terminal model can consume evidence
from earlier tool reads without an explicit artifact handoff. Zero action-artifact
movement therefore does not mean zero total communication or prove quality-preserving
reduction. Summed transfer/operator/model/
cloud service work can overlap. invoke_model operator time includes model service;
do not add these into a purported E2E decomposition. No scalar objective is formed.

For failed runs, original result telemetry can be absent although the frozen
runner records explicit run.failed.e2e_latency_ms. A separate offline
trace_cost_receipts projection reports that persisted clock value, completed
initial-materialization receipts, successful execution transfer/operator receipts
and their completeness. Never derive elapsed time from arbitrary first/last trace
timestamps. Missing endpoints stay unknown; multiple endings or duplicate
physical receipts fail closed. Missing prepared-action outcomes or execution-stage
failures make complete movement unknown even when successful receipt subtotals
exist. A selection-only failure occurs before execution and adds no guessed
movement. Partial initial receipts are not assumed to equal requested placement.
Original result/trace/admission are not filled in or edited, and the projection
does not enter Agent feedback. Twelve synthetic regressions bring the full suite
to 793 passed at that historical projection checkpoint, Ruff/strict Pyright/diff pass.
Historical collector source SHA-256:
62da5882ff1d83ecc38b9df38475be896c643581eaf65b69735da0b1f04ee561.

## Admission, interpretation and stage gates

### Model residency and service-time scope

Fresh Worker processes/stores do not restart Ollama or establish either cold or
uniformly warm inference. The frozen OpenAI-compatible backend starts its service
clock immediately before chat.completions.create and stops at the complete
response. This includes loading, queueing and request initialization when they
occur, input/vision processing, generation and local HTTP/client overhead. It is
not pure decode time. Current receipts do not separately identify load duration,
prefill/decode duration, TTFT or request-entry residency. Those components remain
unknown; do not subtract a guessed fixed startup penalty retrospectively.

A read-only2026-10-05 check of the4090 experiment Ollama process found
OLLAMA_KEEP_ALIVE=30m, OLLAMA_NUM_PARALLEL=1 and OLLAMA_MAX_LOADED_MODELS=1;
its /api/ps was empty at that observation. This is a time-local deployment check,
not evidence of the loading state of every earlier call. Existing balanced order
does not prove this uncontrolled factor cancels. Report residency/cache state as
a limitation of E2E/model-service method comparisons; do not claim statistically
controlled warm-start performance.

The user's requested resident/diverse pool requires a separately versioned
environment: preload and synthetic warm-up before benchmark timing, explicit
resident-state/readiness attestation, and no silent model eviction or CPU spill.
Loading/warm-up are separate setup costs, not subtracted from old outcomes.
Normal prefill, visual processing, queueing and generation remain execution cost.
No runtime, environment, timing boundary or model-pool change is implemented by
this reporting clarification.

Every settled attempt remains visible, including the original excluded attempt.
Only valid admissions count as the 168 nominal Phase I samples. Failed/unevaluated
Agent trajectories are not score=0; quality, format and completion are distinct.
No pooled benchmark accuracy or method ranking is generated by the collector.

## Execution-grown structure and timing

`large_scale_graph_audit_v1.py` is a separate offline helper, deployed outside the
frozen execution app. It verifies monotonic versions, append-only action/edge
history, unchanged action metadata, finite operators, valid edge endpoints and
acyclic dependencies. It does not edit or admit a trajectory.

- A pending/running/finished snapshot changes status, not workflow structure.
  Count actual additions separately from snapshot/version count.
- Report nodes/edges, final states, owners with actions, fan-in/out and dependency
  depth/frontier width. Collapse multiple artifact edges between an action pair
  into one prerequisite only for topological ordering, not edge cardinality.
- Use an identity-free, creation-order descriptor hash for structural comparison.
  It removes opaque action/agent/artifact IDs but preserves operator, action type,
  ownership grouping, input/output cardinality and edges. It is **not** a graph
  isomorphism proof; query/prompt/argument changes can alter semantics without
  changing this descriptor. Different hashes do not establish an infra effect.
- Measure actual parallelism from timestamped action lifetimes, not graph width
  or the presence of two specialists. Report simultaneous-action peak and overlap
  wall time separately from summed service work. Missing/invalid lifetimes make
  complete graph timing unknown, not zero; completed preflight failures remain
  observed action lifetimes, not model inference.
- The action-duration-weighted dependency critical path covers only recorded
  artifact/control edges. It excludes Manager/Verifier reasoning, SDK/subagent
  information flow, scheduling gaps and initial placement. It is **not** complete
  execution E2E or a predicted online target. Dependency-order violations make
  this path unknown and require audit.

First remote graph audit covers eleven admitted settled runs. All have complete
action intervals and no dependency-order violations. Academic / DeepSeek / Slow /
B1 has 187 snapshots but 62 structural additions, peak eight physical actions and
9.665 s overlap. Those numbers prove observed concurrency, not an E2E benefit or
eight simultaneous reasoning agents. Twelve synthetic regression cases cover
integrity, unknown timing, identity-free descriptors and overlap/path accounting.

The subsequent graph-audit-002 covers all fifteen admissions in snapshot-012,
including the independently adjudicated invalid-JSON model-output trajectory.
Every action has a closed interval and no dependency-order violation is found.
This does not fill missing failed-inference token/service telemetry: a measured
physical action lifetime is not interchangeable with backend service time.
The three MultiHop trajectories have one logical action owner each, yet two
reach a physical-action concurrency peak of six. Same-owner ready-action
parallelism is therefore observable without claiming multi-agent topology.
Status-snapshot counts (43/79/22) differ from structural additions (14/26/7).
No private supporting-reference audit or semantic feedback is performed here.

Graph-audit-003 extends the unchanged helper to all 23 admissions of snapshot-019.
Original result/admission hashes and trace event counts are checked; reviewed
JSON attempts also retain their exact sidecar hashes. All graphs have closed
action intervals, terminal node states and no dependency-order violations.
MultiHop-2 / DeepSeek / Fast / B1 and Slow / B have equal creation-order
descriptors (eight nodes / six edges), while Qwen / Slow / A and Fast / C also
share a descriptor (three nodes / two edges). These pairs vary method and
network, and descriptor equality says nothing about query/prompt equivalence.
Their existence is not an infra-induced revision or a matched policy effect.
Video position 2's three settled graphs have one owner and physical peak one,
with zero observed action overlap. No architecture/topology acceptance gate is
added. File SHA-256: a67eb833056d4adcd1b73a6a35236a3c71686769f841b0d1805918c8b15f54db.

The live queue is not stopped for ordinary wrong answers, unadopted interfaces or
poor stopping. It stops for unresolved confounders/operational incidents according
to the preregistered repair/replacement rules. Original evidence is immutable.

After all 168 nominal admissions: comprehensive failure/recipient/private-evidence
audit, task/family/Planner/method tables, quality-conditioned comparisons, then
screen/prune and register Phase II. n=1 remains descriptive, not significance.

## Current offline projection lineage and narrow failure reviews

The latest base collector is the independently tested v1-9 source:
`813b5b0269cedb97aa4f69fe2c4393cafdf0de9ba38293780f809642665ac84a`.
Separate projections compose exact JSON-output, provider-policy, combined
JSON/policy and initial-corpus-field/policy reviews. All original admissions,
hash-linked journal entries, rejected findings and evidence stay unchanged.
Sidecars must reproduce complete admission and bind every original file; a new
review is not a generic validation_failed or HTTP400 allowlist. No review grants
an outcome-based replacement. New controllers preserve immutable parent sources
and freezes and execute only original authorized unstarted cells.

Initial-corpus field review rechecks actual prepared payload hashes/record types,
task content_schema, Worker metadata and the root's actual schema visibility.
It does not claim that a delegated specialist received the root task: the frozen
specialist interface carries Manager assignment plus static operator/model
capabilities. Preserve missing delegated schema information as a composition/
handoff limitation rather than silently supplying it or treating it as a dynamic
infrastructure signal. Model preflight population and cloud refusal costs remain
separate; proven zero physical inference does not imply zero cloud charges.

Physical action intervals can remain known when failed model service/tokens are
unknown. Execution-stage operator failures can also leave complete movement
unknown despite successful receipt subtotals. A selection-only context reject,
explicitly proved to occur before inference, belongs to an empty executed-model
population; do not apply that zero-work conclusion to interrupted or post-inference
parse failures. Unknown measurements continue to be null, never guessed.

Full latest offline suite:916 pytest passed, Ruff / strict Pyright / diff check
passed before the new control freeze. This validates the new offline proof/control
code, not an alteration of formal Agent behavior. Snapshot026 independently
verifies31 classified admissions before subsequent queue progress; its canonical
semantics remain incomplete Phase I, no score pooling, no pruning/Phase II.
See [field/policy audit](large-scale-field-policy-failure-audit-v1.md) for sources,
proof hashes and exact scope; later counts remain in the current results report.
