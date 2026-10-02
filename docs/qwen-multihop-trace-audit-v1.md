# Qwen MultiHop Trace Audit v1

Date: 2026-10-02  
Audited base: `open-ended-mas-preliminary-v1@597ac337f18b1f6e5c02ff69464cf6871622a3bb`  
Mode: audit / instrumentation / offline analysis only.

## Scope

No Manager or Verifier prompt, model, budget, planner, scheduler, tool semantics,
profile schema, benchmark adapter, original evaluator, deployment, network setting,
or formal result was changed. Formal benchmark reruns = **0**. No new provider
calls, Worker experiment processes, tc shaping, or candidate method were used.

The SDK-native runtime and Verifier source files remain byte-identical to the
audited base, preserving the existing frozen harness source-hash checks. Observer
diagnostics are additive and private; existing scheduling/fail-closed behavior is
unchanged. Historical reports and score tables remain visible.

## Evidence set

One task: `multihop-multisource`,
`multihop-rag-train-9bae0079038050a37a1ae583`. Question: whether the Polygon
Diablo 4 Sorcerer Season 2 guide supplies simplified builds in a similar manner
to the Barbarian guide. Three non-semantic hash partitions form one corpus.

The counted block is Fast/Slow × Blind/Aware × 3 = 12 runs. Sanity/replacement and
the earlier wrong-model diagnostic are excluded. Cloud Manager and Blind Verifier:
`qwen3.8-max`; physical model: Qwen3.8-27B Q4_K_M Ollama, 32768 context / 2048
reserved output on A28 and strong-4090. All completed physical model inferences
selected A28 under the unchanged scheduler. A4/A5 are operator-only Workers.

Fast: 100 Mbps + 5 ms; Slow: 3 Mbps + 50 ms. Budgets: 20 Manager turns,
64 physical calls, 20 Verifier calls; specialist limits 8 turns / 4 created /
2 active. Initial artifact placement traffic: 7,696,522 bytes in each run.

Authoritative local archive:
`../qwen38max-multihop-traces-20261002.tar.gz`

SHA-256:
`6f1114d1dc2f530a8f2de04aa312ac5da161e3d2eb50b93bbeaf59144044f8af`

The analyzer reads members without extracting or modifying them. Each input
trace/result hash is stored in the new audit output; the archive hash is checked
again after analysis. Existing completion is 11/12, evaluation 11/12; the existing
privacy scans and exact tc restoration attestations remain 12/12. These scan
results do not imply the unpersisted full provider requests can be retrospectively
inspected.

New machine-readable audit (local, Git-ignored, not historical summary):
`results/qwen-multihop-trace-audit-v1-reviewed/audit-v1.json`.
The earlier local audit draft is retained separately. The new file includes
cost/concurrency/profile metrics, raw outputs, original evaluation objects,
reconstructed Verifier observation histories, anomaly timelines and source hashes.

Reproduce into a **new** directory:

```powershell
.\.venv\Scripts\python.exe scripts/qwen_multihop_trace_audit_v1.py --archive ..\qwen38max-multihop-traces-20261002.tar.gz --output results/qwen-multihop-trace-audit-v1-reproduction --private-reference yes
```

The reference is evaluation-private; it was checked against the existing private
evaluation file on strong-4090 and is used only by this offline secondary metric.
It is never passed to Manager, specialist, Verifier or model execution. No corpus,
benchmark artifact body or dataset was downloaded through the development machine;
remote checks returned bounded artifact metadata/title diagnostics only.

Analysis implementation hashes:

- `qwen_multihop_trace_audit_v1.py`: `736e2eff1b23ae6f916f40e40c89e98549eb7c2e352c56c186019221171af69b`
- `trace_audit.py`: `c8035c0c3606bf38a792f25878191d5dab56880ae07b9804e673bfca8e2b7fcb`
- `yesno_audit.py`: `defe65eb0d8a5682bedf82fcedb69f240cbf28d6ee1d4514ff175e7dab3d1494`

## Evaluator audit

The unchanged original evaluator in
`src/infra_joint/benchmarks/multihop_rag.py` first attempts the exact quoted-answer
pattern `The answer to the question is "..."`; otherwise it evaluates the entire
answer using lowercased whitespace-token intersection with the private reference.
It does not remove punctuation or Markdown.

Thus `Yes` contains the token `yes`, whereas `Yes.`, `Yes,`, `**Yes.**`
do not. The original SHORT_TEXT format check accepts these nonempty prose answers;
format-valid does not imply the evaluator accepts their serialization.

No original 0 was rewritten to 1. No historical result.json, summary.json, trace,
manifest or raw score table was overwritten.

## Semantic answer audit

Secondary metric: **`multihop_yesno_canonical_v1`**.
**Post-hoc audit metric, not original benchmark score.**

It deterministically recognizes a leading explicit yes/no label, optionally
with balanced bold/italic markup and limited punctuation. Immediate alternatives
(e.g. Yes/no, Yes or no), question-mark prefixes, missing labels, incomplete
markup and ambiguous openings are unresolved. It does not search the body,
interpret explanatory prose, consult supporting evidence, select extraction using
gold, or call an LLM. The private reference is consulted only after extraction.

| Run | Raw terminal prefix (verbatim output in Appendix A) | Original score | Canonical direction | Format category | Secondary audit score |
|---|---|---|---|---|---|
| Fast-Blind r1 | `"Yes, both guides explicitly state they have \""` | 0 | yes | punctuated yes | 1 |
| Fast-Aware r1 | `"Yes. Both guides explicitly state that they h"` | 0 | yes | punctuated yes | 1 |
| Slow-Blind r1 | `"no"` | 0 | no | negative/no | 0 |
| Slow-Aware r1 | `"Yes. Both guides explicitly state that they h"` | 0 | yes | punctuated yes | 1 |
| Fast-Blind r2 | `"**Yes.**\n\nBoth guides explicitly state that t"` | 0 | yes | markdown yes | 1 |
| Fast-Aware r2 | `"**Yes.**\n\nBoth guides explicitly state that t"` | 0 | yes | markdown yes | 1 |
| Slow-Blind r2 | `"Yes"` | 1 | yes | exact yes | 1 |
| Slow-Aware r2 | `null` | — | unresolved | no terminal answer | unresolved |
| Fast-Blind r3 | `"Yes. Both guides explicitly state that they h"` | 0 | yes | punctuated yes | 1 |
| Fast-Aware r3 | `"Yes. Both guides explicitly state their inten"` | 0 | yes | punctuated yes | 1 |
| Slow-Blind r3 | `"**Yes.**\n\nBoth guides use an identical struct"` | 0 | yes | markdown yes | 1 |
| Slow-Aware r3 | `"**Yes.**\n\nBoth guides explicitly state that t"` | 0 | yes | markdown yes | 1 |

The ten original zero-score completions divide into **nine affirmative
serialization/evaluator-format mismatches** and **one genuinely wrong negative
direction** (Slow-Blind r1). The remaining run has no terminal answer.
This is not a replacement benchmark accuracy claim, and canonical direction is
not a full reasoning/grounding metric.

Remote read-only inspection adds useful grounding evidence:

- Six of the nine affirmative zero-score terminals consume JSON evidence with
  target-guide titles: Fast-Aware r1/r2, Fast-Blind r2, Slow-Aware r1/r3,
  Slow-Blind r3.
- The other three (Fast-Blind r1/r3, Fast-Aware r3) have terminal model
  `inputs=[]`. Their Manager trajectories contain read/retrieval evidence, but
  historical model prompts were not persisted; their exact evidence-to-prompt
  injection cannot be independently reconstructed.
- Target-like titles establish presence of relevant documents, not the
  correctness of every explanatory statement.

## Artifact visibility anomaly

### Slow-Blind r2

- `000013-logical.observation`, 07:25:22.603764Z: aggregate action successfully
  produces `derived/1101d520f535499283e1fbc52540f889/full-corpus`,
  7,696,520 bytes.
- `000037-logical.observation`, 07:25:35.047819Z: BM25 using the exact same ID
  fails `missing_input`; physical trace `000038-physical.execution` reports
  **selection** failure, not Worker artifact-read failure.
- The Manager later performs additional aggregation/retrieval and reaches a
  score-1 terminal `Yes`. The anomaly therefore adds an observable recovery
  detour, but its counterfactual effect on quality/time is unknown.
- The preserved A28 blob and metadata remain readable and agree with production:
  SHA-256 `3783a6d718da70a411edc564ea78a2b1968bec4001e8b8d5e09bffa5e47d98c2`.

### Slow-Aware r2

- `000099-logical.observation`, 07:29:44.599925Z: successfully produces
  `derived/abf545eb9f8d4ba4926bc109048bdb01/barbarian-aggregated`,
  85,770 bytes.
- A subsequent bounded read sees that same artifact and rejects its size above
  the 65,536-byte limit: evidence that it was physically observable after creation.
- `000143-logical.observation`, 07:29:58.532988Z: BM25 on the same ID fails
  `missing_input`; `000144-physical.execution` again reports selection failure.
- Its anonymous profile has candidate_count=1 and input_bytes=0, unlike the
  earlier complete observation. This is consistent with losing visibility of
  remote Workers, but does not establish the precise probe exception.
- The preserved A28 blob and metadata still match production:
  SHA-256 `dee03c92d0029340fd5578bc794e3874318d6536f8f80b6587fdfb579eddd8ad`.
- This failure interrupts specialist recovery. It is a real trajectory
  confounder; whether removing it would have produced completion cannot be known.

Worker lifecycle/access logs were inspected on all four nodes. Available logs
contain successful /state responses and normal lifecycle records, but lack
per-probe timestamps, client-side exceptions and validation failures. They cannot
identify whether the historical failure was HTTP transport, response decoding,
schema validation, ID mismatch or another client-side probe problem.

**Narrowest historical conclusion:** canonical produced artifacts disappeared
from a later scheduling snapshot, not from the retained store. Their exact
historical disappearance trigger remains unknown. Neither affected run is a
pure Planner-failure sample.

## Observer semantics

`LiveWorkerObserver` catches each get_state exception and excludes that Worker.
It constructs artifact locations only from successfully decoded Worker states;
there is no scheduling-visible durable artifact registry/cache. Consequently a
known artifact disappears when every observed copy's host disappears.

Logical readiness is separate: Agent-accessible IDs and
SemanticActionValidator.known_artifacts may still contain the artifact. Gateway
semantic validation succeeds; the resolver then checks the fresh physical
snapshot and raises `missing_input`. This conflates “not in this snapshot” with
“truly absent” in the original logical failure code.

New private diagnostics record every observation ID/timestamp, correlated action
IDs, probe start/end/success/latency/error type/message, artifact IDs reported,
and deployment availability. They are written to
`runs/<run-id>/private/observer-diagnostics.jsonl`, not logical observations or
the anonymous Aware profile.

Diagnostic states:

- PRESENT: reported by at least one healthy observed host.
- HOST_UNREACHABLE: not currently reported and a previously reporting host is
  unobserved; physical nonexistence is **not** inferred.
- UNKNOWN: no known host and an incomplete observation census.
- ABSENT: not reported in a complete healthy census. This is an observation
  conclusion, not proof about storage outside the configured Worker set.

The diagnostic-only host history never restores availability or changes
placement, scheduling, typed failures or retry behavior. Action correlation uses
task-local context variables; diagnostic write errors are logged without changing
the physical result.

### Targeted reproduction

A synthetic file-backed artifact is persisted. Healthy /state reports PRESENT.
A simulated ReadTimeout leaves the blob intact while the existing snapshot omits
it; Gateway still accepts logical readiness and returns the unchanged physical
`missing_input`. Private diagnostics say HOST_UNREACHABLE and identify the
probe error. Restoring the probe makes the artifact reappear. Explicitly deleting
the synthetic artifact under a healthy census produces ABSENT; an unseen artifact
under failed probes is UNKNOWN.

This regression confirms the mechanism, **not** the exact historical trigger.
No MultiHop benchmark or model inference was run for reproduction.

## Parallelism audit

The old inference `parallel_batches=0 -> all sequential` is false.
For native singleton batches, logical.batch.started/completed bound each action's
gateway lifetime. Independent SDK tool calls can overlap even though every batch
has one action. The versioned analyzer also supports explicit action events.

Intervals are half-open; touching endpoints do not overlap. It counts overlapping
pairs, unique participating actions and same-decision parallel turns. Incomplete,
duplicate, reversed or ambiguous legacy multi-action lifetimes remain unknown;
no fake timing is supplied.

| Run | Max concurrency | Overlapping pairs | Parallel reasoning turns | Parallel actions | Overlap wall seconds |
|---|---|---|---|---|---|
| Fast-Blind r1 | 6 | 26 | 3 | 13 | 3.032 |
| Fast-Aware r1 | 6 | 25 | 2 | 11 | 0.898 |
| Slow-Blind r1 | 6 | 41 | 4 | 19 | 3.418 |
| Slow-Aware r1 | 2 | 2 | 2 | 4 | 4.247 |
| Fast-Blind r2 | 1 | 0 | 0 | 0 | 0.000 |
| Fast-Aware r2 | 1 | 0 | 0 | 0 | 0.000 |
| Slow-Blind r2 | 2 | 2 | 2 | 4 | 4.232 |
| Slow-Aware r2 | 6 | 37 | 5 | 20 | 4.803 |
| Fast-Blind r3 | 2 | 1 | 1 | 2 | 2.015 |
| Fast-Aware r3 | 6 | 15 | 1 | 6 | 0.769 |
| Slow-Blind r3 | 1 | 0 | 0 | 0 | 0.000 |
| Slow-Aware r3 | 1 | 0 | 0 | 0 | 0.000 |

**8/12** runs overlap, with max concurrency **6**. These are gateway/action
lifetimes, not proof of simultaneous GPU execution. All successful physical
inferences still run on A28, and inference counts should not be interpreted as
independent model-device parallelism. Detailed action IDs/groups are in the new
audit JSON.

The original report is preserved with an appended correction link rather than
silently rewriting its old sequentiality assertion.

## Infrastructure-profile timing

The installed native path calls Runner.run with
`_manager_input(task_view, static_capabilities)`. Its input object contains exactly
those two keys. No initial profile_overview call occurs on this path.

Actual sequence:

```text
task + static capability contract
  -> Manager chooses action
  -> Gateway observes Workers
  -> PhysicalProfiler.for_action builds an action-specific profile
  -> scheduler selects and RuntimeExecutor executes
  -> LogicalObservation carries the anonymous profile only in Aware mode
  -> SDK tool result becomes context for subsequent Manager reasoning
```

Thus **Case B** holds:

```text
a1 = P(task, semantic_state_0)
not a1 = P(task, semantic_state_0, initial_infrastructure)
```

Profile generation is pre-execution but **post action choice**; delivery is
post-execution. Later reasoning sees action-conditioned snapshots from previously
returned tool observations, not a guaranteed freshly measured H_t before each
decision. Independent calls in the same reasoning turn are all chosen before
their results return.

Deterministic integration tests preserve this timing for both Blind and Aware:
no profile in initial input, no physical call before initial reasoning, Aware-only
profile in the tool result available to the next turn. Blind Verifier remains
profile-free. SDK loop semantics are cross-checked with
[official Running agents documentation](https://developers.openai.com/api/docs/guides/agents/running-agents);
the initial-profile finding itself comes from repository source and tests, not
documentation or design intent.

## First-action analysis

| Run | First logical actions | First-action bytes | First profile event | First profile network class | Before decision 1? |
|---|---|---|---|---|---|
| Fast-Aware r1 | bm25_retrieve | 0 | `000013-logical.observation` | fast | No |
| Slow-Aware r1 | aggregate_artifacts | 5204596 | `000013-logical.observation` | constrained | No |
| Fast-Aware r2 | aggregate_artifacts | 5204596 | `000013-logical.observation` | fast | No |
| Slow-Aware r2 | bm25_retrieve | 0 | `000013-logical.observation` | constrained | No |
| Fast-Aware r3 | bm25_retrieve, bm25_retrieve, bm25_retrieve, bm25_retrieve, bm25_retrieve, bm25_retrieve | 0 | `000033-logical.observation` | fast | No |
| Slow-Aware r3 | aggregate_artifacts | 5204596 | `000013-logical.observation` | constrained | No |

Fast-Aware starts with shard retrieval in r1/r3 but full aggregation in r2.
All Slow-Aware first decisions occur without profile too: aggregation in r1/r3,
retrieval in r2. Therefore the early movement/reduction split cannot be attributed
to an infra profile the Manager had not yet received. The same alternative first
choices also occur in Blind trajectories. Model sampling, response variation and
subsequent execution feedback are not separately identified by n=3.

First-action 5,204,596 bytes are artifact movement A4/A5 -> A28, excluding the
fixed initial placement. Zero first-action transfer does not mean zero later
traffic.

Across the six Aware runs, raw JSONL contains 91 profiles; **all 91 have unknown
model-service latency ranges**. Slow-Aware r2 contains 39 profiles (38 constrained,
1 local), despite the historical compact summary's zero count. The old summarizer
read result.loop, which is None on failure. The new summarizer reads raw JSONL
first and explicitly labels its legacy incomplete-trace result-loop fallback.

Configured bandwidth/RTT and live Worker probes inform these profiles; they
are not independent throughput or backend-service calibrations.

## E2E cost decomposition

All latency columns below are seconds. Manager/specialist/Verifier, tool/operator calls,
model service and transfer are **work/service sums**, not an additive critical-path
partition. Concurrent tools/specialists overlap. invoke_model operator latency
includes service latency: it is not counted again as tool/operator call work.
RuntimeExecutor brackets the entire Worker HTTP operator call, so the tool column
includes request/response overhead and cannot be identified as pure Worker CPU
compute. Pure tool compute is explicitly unknown in the new audit JSON.

| Run | E2E s | Manager s | Specialist s | Verifier s | Tool/operator call s | Completed inference | Model service s | Action transfer s | Action bytes |
|---|---|---|---|---|---|---|---|---|---|
| Fast-Blind r1 | 166.909 | 68.221 | 21.505 | 51.074 | 8.107 | 1 | 13.845 | 1.821 | 5204596 |
| Fast-Aware r1 | 228.002 | 50.789 | 20.861 | 29.851 | 2.922 | 1 | 120.894 | 0.473 | 112712 |
| Slow-Blind r1 | 1007.161 | 92.293 | 10.282 | 70.225 | 9.066 | 6 | 800.483 | 1.174 | 79650 |
| Slow-Aware r1 | 193.064 | 30.512 | 0.000 | 19.721 | 6.430 | 1 | 98.737 | 15.044 | 5204596 |
| Fast-Blind r2 | 238.937 | 15.152 | 0.000 | 11.002 | 2.076 | 1 | 205.414 | 3.067 | 5204596 |
| Fast-Aware r2 | 194.482 | 14.587 | 0.000 | 14.094 | 2.127 | 1 | 159.686 | 1.428 | 5204596 |
| Slow-Blind r2 | 186.445 | 26.588 | 0.000 | 22.600 | 7.424 | 1 | 82.075 | 14.842 | 5204596 |
| Slow-Aware r2 | 654.509 | 102.581 | 20.666 | 82.545 | 8.956 | 4 | 406.905 | 3.284 | 171085 |
| Fast-Blind r3 | 99.892 | 33.225 | 25.172 | 22.129 | 3.147 | 1 | 22.302 | 1.632 | 5204596 |
| Fast-Aware r3 | 123.737 | 40.864 | 45.945 | 19.132 | 3.132 | 1 | 28.123 | 0.182 | 57351 |
| Slow-Blind r3 | 310.232 | 45.409 | 0.000 | 35.961 | 4.581 | 1 | 182.848 | 14.945 | 5204596 |
| Slow-Aware r3 | 232.591 | 16.651 | 0.000 | 13.775 | 2.351 | 1 | 160.434 | 14.817 | 5204596 |

The remaining model-call wrapper work is recorded separately in the machine
audit. Context/binding preflight rejections do not count as completed inference.

The following wall interval union combines reasoning, verification and action
lifetimes without counting overlaps twice:

| Run | Initial placement s | Measured activity wall union s | Unclassified wall s |
|---|---|---|---|
| Fast-Blind r1 | 0.800 | 165.827 | 1.082 |
| Fast-Aware r1 | 0.766 | 227.140 | 0.861 |
| Slow-Blind r1 | 21.845 | 985.015 | 22.146 |
| Slow-Aware r1 | 22.222 | 170.717 | 22.347 |
| Fast-Blind r2 | 1.337 | 237.492 | 1.444 |
| Fast-Aware r2 | 1.676 | 192.762 | 1.719 |
| Slow-Blind r2 | 22.548 | 163.768 | 22.678 |
| Slow-Aware r2 | 22.139 | 632.146 | 22.363 |
| Fast-Blind r3 | 1.327 | 98.426 | 1.466 |
| Fast-Aware r3 | 1.845 | 121.772 | 1.965 |
| Slow-Blind r3 | 22.144 | 287.952 | 22.279 |
| Slow-Aware r3 | 22.341 | 210.135 | 22.455 |

Unclassified wall time is E2E minus this measured union, not “idle time”.
It includes initial materialization, startup, unbracketed framework operations
and gaps. Exact idle/wait, error-recovery cost and other harness overhead are
**unknown**, because historical trace lacks independent spans for them. Do not
allocate these values by guessing. Initial transfer is shown separately but must
not then be added again to an overlapping/non-additive total.

Slow-Blind r1: six completed inferences, 800.483 s model service / 1007.161 s E2E
(~79.5%); action transfer 1.174 s. Slow-Aware r2: four completed inferences,
406.905 s / 654.509 s (~62.2%); action transfer 3.284 s.
Their long tails are directly supported as model/reasoning/recovery-heavy,
not transfer-dominated. This does not isolate an inference-count causal effect:
input sizes, backend latency and trajectory differ.

## Verifier sufficiency audit

The code gives Verifier sanitized task, current graph, accepted action intent
(including arguments/model prompt), accumulated typed observations, produced
artifact metadata, phase and remaining logical budget. Physical profiles are
removed. It does not independently fetch full artifact bodies.

Historical JSONL persists verdict/reason/tokens and observations, **not the exact
Verifier input or Manager/local-model prompt/tool arguments**. Therefore the audit
reconstructs available observations and artifact metadata, but marks exact
requests unknown. It does not invent queries, sorting keys or prompt text.
The full per-verdict observation history is in audit-v1.json.

All 12 runs reach READY_FOR_SYNTHESIS at least once. The first subsequent model
attempt is context-rejected in nine runs; the other three perform successful
inference. These context failures concern execution readiness and do not by
themselves prove semantic evidence is insufficient.

However, the two key negative trajectories show a more specific problem:

### Slow-Blind r1

1. Six initial BM25 outputs across all shards are materialized. **Retained
   shard-3 outputs already contain both target-guide titles** (five records per
   result); shard-1 sorcerer output lacks them.
   Remote body checks also confirm a chunk for each class contains both
   "season 2" and "simplified"; only those boolean diagnostics, not bodies, were returned.
2. Verifier #2, `000061-logical.verification`, declares sufficiency because
   all six retrievals succeeded and cover both sides across the corpus.
3. The combined model request is context-rejected. Subsequent evidence selection
   repeatedly favors unrelated shard-1 material rather than successfully using
   the already retrieved shard-3 guides.
4. First successful model `000120-logical.observation` explicitly describes
   QoL/news/game-list evidence as irrelevant. Repeated model calls document
   absence of the requested guides in their **selected** inputs.
5. Terminal model consumes five negative diagnostic notes and returns `no`.
   Verifier #15, `000331-logical.verification`, accepts completion because
   “extensive” collection consistently indicates absent guides.

This is **retrieved evidence not successfully used -> unsupported negative
reasoning -> erroneous completion**, not proof that the target corpus lacked the
guides. Missing relevant evidence in a chosen subset is not negative evidence
about the proposition. Confidence is high on this distinction; exact semantic
prompt intent remains unrecorded.

### Slow-Aware r2

1. Initial shard-3 retrievals already contain both target-guide titles (ten
   records per result); shard-1 results have no target-like guide titles.
   Remote boolean checks confirm the relevant Season 2/simplified passages are
   present for both classes, not merely similarly named unrelated documents.
2. Verifier #2, `000061-logical.verification`, declares readiness based on
   nonempty cross-shard coverage. Combined input estimate 172431 + 2048 exceeds
   32768 and fails before inference.
3. Aggregation/read/schema failures, the artifact-visibility anomaly and
   specialist turn exhaustion occur during recovery. Projection still leaves
   large bodies; the later estimated input 50122 + 2048 also exceeds 32768.
4. Four successful model calls consume irrelevant reductions/retrievals. The
   last call's two three-record inputs contain a game list and Diablo QoL
   articles, not either target-guide title. Later retrieval concentrates on
   shard-1 despite prior useful shard-3 artifacts.
5. Verifier #20, `000435-logical.verification`, correctly rejects repeated
   “No” answers as absence of evidence, not evidence of absence.
6. Manager reaches 20 turns; 39 physical calls are below the 64-call guard.
   There is no terminal evaluation.

The failure mixes evidence selection/composition, recovery inefficiency and
turn exhaustion **with a physical-observer confounder**. It is not a clean
budget-only or pure model-reasoning failure.

In both trajectories READY is initially optimistic about action success/coverage.
The final sufficiency judgments diverge: one accepts unsupported negation, the
other correctly refuses it. This supports a recurring **coverage-as-sufficiency
risk**, not a claim that every Verifier verdict or every retrieved artifact is bad.
No Verifier/Manager prompt, stopping transition or retrieval strategy was changed.

## Run-by-run reclassification

Secondary scores remain post-hoc direction audits. “None observed” does not
establish complete absence of unlogged faults. Inference counts include completed
backend calls only.

| Run | Completion | Original | Audit | Retrieval/evidence quality | Verifier behavior | Context recovery | Observer confounder | Max concurrency | Inference | Primary class | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Fast-Blind r1 | yes | 0 | 1 | Guide-related read/retrieval trajectory; terminal model inputs=[]; prompt unknown | READY then COMPLETE | 1 rejection; later inference legal | none observed | 6 | 1 | format/evaluator artifact; evidence injection not independently reconstructable | high on format/direction; moderate on grounding |
| Fast-Aware r1 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | 1 rejection; later inference legal | none observed | 6 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |
| Slow-Blind r1 | yes | 0 | 0 | Target guides retrieved in shard-3; later selected/consumed irrelevant evidence | Early READY; COMPLETE accepts unsupported no | 1 rejection; later inference legal | none observed | 6 | 6 | absence-of-evidence reasoning / evidence-selection failure | high on trajectory and wrong direction; exact prompts unknown |
| Slow-Aware r1 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | 1 rejection; later inference legal | none observed | 2 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |
| Fast-Blind r2 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | no context rejection | none observed | 1 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |
| Fast-Aware r2 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | no context rejection | none observed | 1 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |
| Slow-Blind r2 | yes | 1 | 1 | Target-guide titles present in terminal inputs | Recovered; COMPLETE on exact Yes | 1 rejection; later inference legal | yes; recovered | 2 | 1 | semantic/workflow trajectory with physical-observer confounder; completion | high on answer direction; causal impact unresolved |
| Slow-Aware r2 | no | — | unresolved | Target guides retrieved in shard-3; later model inputs use irrelevant shard-1 material | Early READY; later correctly refuses unsupported no | 2 rejections; 4 later inferences | yes; impact unresolved | 6 | 4 | semantic/workflow trajectory with physical-observer confounder | high on events; causal apportionment unresolved |
| Fast-Blind r3 | yes | 0 | 1 | Guide-related read/retrieval trajectory; terminal model inputs=[]; prompt unknown | READY then COMPLETE | 1 rejection; later inference legal | none observed | 2 | 1 | format/evaluator artifact; evidence injection not independently reconstructable | high on format/direction; moderate on grounding |
| Fast-Aware r3 | yes | 0 | 1 | Guide-related read/retrieval trajectory; terminal model inputs=[]; prompt unknown | READY then COMPLETE | 1 rejection; later inference legal | none observed | 6 | 1 | format/evaluator artifact; evidence injection not independently reconstructable | high on format/direction; moderate on grounding |
| Slow-Blind r3 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | 1 rejection; later inference legal | none observed | 1 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |
| Slow-Aware r3 | yes | 0 | 1 | Target-guide titles present in terminal input artifacts | READY then COMPLETE | no context rejection | none observed | 1 | 1 | format/evaluator artifact | high on format/direction; full semantic correctness not established |

The two disappearance runs remain **semantic/workflow trajectories with a
physical-observer confounder**. Their inclusion in an earlier descriptive
aggregate does not license a clean causal Blind/Aware comparison. No replacement,
post-hoc exclusion to improve averages, or revised headline benchmark accuracy
was produced.

## What the current preliminary does establish

- The Qwen cloud SDK-native loop executes finite tools, materializes evidence,
  continues after typed failures, performs terminal physical inference and invokes
  the original evaluator in 11 runs.
- Independent native tool calls overlap in eight runs; action batching alone is
  not a valid concurrency statistic.
- Ten terminals have a leading affirmative direction; nine original zero scores
  have a concrete formatting explanation, distinct from wrong-negative reasoning.
- Aware receives anonymous action-conditioned infrastructure profiles **after**
  action execution; first decisions are resource-blind.
- Both full-movement and local-reduction paths occur. They have different bytes
  and work, but are not systematically selected according to Fast/Slow.
- Two produced artifacts disappear from scheduling snapshots while surviving in
  retained storage; simulated probe failure reproduces this visibility mechanism.
- Model service and repeated evidence analysis dominate the two long tails.

## What it does not establish

- No stable “Aware improves execution while preserving completion/quality” claim.
- No proven infrastructure-caused first-action split or reliable Fast -> KEEP /
  Slow -> REDUCE implication.
- No formal accuracy reinterpretation using the post-hoc metric.
- No clean Planner-only attribution for Slow-Blind r2 or Slow-Aware r2.
- No exact historical Worker probe exception, counterfactual no-confounder result,
  complete semantic prompt reconstruction, GPU parallel speedup, or causal
  inference-count effect.

Answers to the Raw-Aware audit questions:

1. **Saw infra?** Yes, 91 anonymous observations in the six Aware raw traces.
2. **Saw relevant state before deciding?** Not decision 1; later decisions see
   returned, potentially stale/action-specific profiles, not assured fresh H_t.
3. **Systematic workflow/network relationship?** Not established.
4. **First-action/retrieval trajectory variation?** Strong alternative explanation;
   their relative causal contribution is not quantified.
5. **E2E drivers?** Physical model service dominates the two tails; cloud
   reasoning/verification and recovery add substantial work. Transfer is measured
   but is not their main recorded cost. Exact recovery/idle cost remains unknown.
6. **Aware improves execution?** Existing cleaned evidence is insufficient.

## Candidate method implications

Only implications, **not implemented mechanisms**: relevant pre-decision profile
timing, calibrated service-cost feedback, observable marginal work/transfer costs,
and preserved evidence relevance during reduction may matter. No cost estimator,
planner optimization guidance, scoring, search, RL, critic or routing heuristic
was added.

## Required fixes before next experiment

Completed in this cleanup:

- Versioned deterministic secondary yes/no audit with original-score preservation.
- Private per-probe diagnostics and distinct observational artifact statuses.
- Action-interval concurrency summary and failed-run JSONL profile accounting.
- Offline analyzer with immutable input hashes and new output namespaces.
- Targeted persistence/probe-loss/recovery, output-metric, overlap and initial
  profile timing regressions.

Still requires explicit follow-up decisions, not silent fixes:

- Determine the real probe failure from new action-correlated diagnostics; decide
  whether HOST_UNREACHABLE requires a different typed runtime reason. Existing
  fail-closed scheduling semantics remain unchanged.
- Decide benchmark-faithful terminal serialization for yes/no tasks **prospectively**.
  Do not replace original scores with this audit metric.
- To fully audit grounding/sufficiency, instrument exact sanitized tool arguments
  and model/Verifier input provenance without changing frozen Agent instructions.
  The frozen runtime source hash was deliberately not bypassed in this cleanup.
- If proceeding with a decision-aware claim, specify whether first-action
  resource blindness and delayed profiles are intended. No initial profile was
  injected here.
- Audit evidence selection and absence-of-evidence judgments before interpreting
  quality-preserving cost reduction; no semantic tuning was performed.

## Tests and stop

Full pytest: **389 passed**. Ruff check: **passed**. Strict Pyright with the
project Python interpreter: **0 errors, 0 warnings**. Targeted tests use synthetic
data and fake/ASGI backends; no provider or benchmark rerun is hidden in them.

Changed implementation files:

- `evaluation/yesno_audit.py`: new versioned secondary metric; original evaluator untouched.
- `evaluation/trace_audit.py`: interval concurrency, non-additive costs and JSONL profiles.
- `infrastructure/diagnostics.py`, `infrastructure/observer.py`: private per-probe diagnostics.
- `control/gateway.py`: diagnostic-only action correlation scope; execution order unchanged.
- `control/runner.py`: private sidecar wiring; no new logical input.
- `scripts/sdk_native_infra_preliminary_v1_3.py`: summarizer corrections, no execution-policy edits.
- `scripts/qwen_multihop_trace_audit_v1.py`: offline immutable-evidence audit CLI.

Regression coverage added in `test_yesno_audit.py`, `test_trace_audit.py`,
`test_observer_diagnostics.py`, `test_native_agents.py` and
`test_sdk_native_infra_preliminary_v1_3.py`: explicit/ambiguous labels, unchanged
original scores, persistence/probe loss/recovery, UNKNOWN/ABSENT distinction,
private sidecar/action correlation, overlapping/sequential/unknown intervals,
missing latency stays unknown, failed-run profile accounting and initial profile timing.

No historical evidence was deleted or overwritten. This audit stops here; no
Aware method, new benchmark, formal retry, repetition or new matrix follows.

## Appendix A — Verbatim terminal outputs

Each fenced block is JSON serialization of the original result.json final_answer
field, including newlines/Markdown and any original encoding artifacts. It is not
an extracted, normalized or corrected answer. Full run IDs are supplied.

### Fast-Blind r1

Run ID: `qwen38max-multihop-fast-blind-r1`

```json
"Yes, both guides explicitly state they have \"gathered and simplified\" the best builds for season 2 and follow an identical structure."
```

### Fast-Aware r1

Run ID: `qwen38max-multihop-fast-aware-r1`

```json
"Yes. Both guides explicitly state that they have \"gathered and simplified\" the best builds for Season 2 and link out to more detailed versions for complex ideas."
```

### Slow-Blind r1

Run ID: `qwen38max-multihop-slow-blind-r1`

```json
"no"
```

### Slow-Aware r1

Run ID: `qwen38max-multihop-slow-aware-r1`

```json
"Yes. Both guides explicitly state that they have \"gathered and simplified the best Diablo 4 [Class] builds for season 2\" and link out to more detailed versions for complex ideas, indicating they follow the same simplified approach."
```

### Fast-Blind r2

Run ID: `qwen38max-multihop-fast-blind-r2`

```json
"**Yes.**\n\nBoth guides explicitly state that they have \"gathered and simplified\" the best builds for Season 2. They use an identical presentation structure:\n1.  **Explicit Statement:** Both introductions contain the exact phrase: *\"In this Diablo 4 guide, we’ve gathered and simplified the best Diablo 4 [Class] builds for season 2. If you need even more information... we’ve been sure to link out to the more detailed versions...\"*\n2.  **Simplified Content:** Both provide a \"Best [Class] leveling build\" section that lists skills in a specific purchase order (simplified skill tree) and references external sources (IcyVeins) for complex details like item affixes.\n3.  **Consistent Format:** Both guides break down the class into key passives/elements (e.g., Lightning/Fire/Ice for Sorcerer; Fury/Bleed/Berserk for Barbarian) and provide simplified Paragon Board glyph pairings.\n\nThe manner and presentation of the simplified versions are nearly identical between the two artifacts."
```

### Fast-Aware r2

Run ID: `qwen38max-multihop-fast-aware-r2`

```json
"**Yes.**\n\nBoth guides explicitly state that they have \"gathered and simplified\" the best builds for Season 2 and link out to more detailed original sources for complex information like item affixes. Both follow an identical structure, starting with a simplified leveling build based on IcyVeins guides, followed by specific skill orders and Paragon board recommendations, while directing readers to external creators (like Northwar or AaronActionRPG) for in-depth stat priorities."
```

### Slow-Blind r2

Run ID: `qwen38max-multihop-slow-blind-r2`

```json
"Yes"
```

### Slow-Aware r2

Run ID: `qwen38max-multihop-slow-aware-r2`

```json
null
```

### Fast-Blind r3

Run ID: `qwen38max-multihop-fast-blind-r3`

```json
"Yes. Both guides explicitly state that they have \"gathered and simplified\" the best builds for Season 2 and use the same approach of presenting condensed information while linking out to more detailed external guides for complex ideas."
```

### Fast-Aware r3

Run ID: `qwen38max-multihop-fast-aware-r3`

```json
"Yes. Both guides explicitly state their intent to provide \"simplified\" builds for Season 2, and both employ the same structural approach: offering a dedicated leveling build (levels 1-50) with specific skill purchase orders, separating leveling from endgame content, and linking to external resources for complex details like item affixes and Paragon paths."
```

### Slow-Blind r3

Run ID: `qwen38max-multihop-slow-blind-r3`

```json
"**Yes.**\n\nBoth guides use an identical structural approach to present simplified builds.\n\n**Supporting Evidence:**\n1.  **Identical Introductory Language:** Both guides explicitly state their intent to simplify complex information.\n    *   **Barbarian Guide:** \"In this Diablo 4 guide, we’ve gathered and **simplified** the best Diablo 4 Barbarian builds for season 2. If you need even more information... we’ve been sure to link out to the more detailed versions...\"\n    *   **Sorcerer Guide:** \"In this Diablo 4 guide, we’ve gathered and **simplified** the best Diablo 4 Sorcerer builds for season 2. If you need even more information... we’ve been sure to link out to the more detailed versions...\"\n2.  **Identical Structure:** Both guides follow the same format:\n    *   A \"Best [Class] leveling build\" section based on a specific external guide (Lexyu’s guide at IcyVeins).\n    *   A \"Best skills for leveling\" section that lists skills in the exact order they should be purchased.\n    *   A disclaimer that the guide is for leveling (levels 1-50) and directs users to external sources for complex end-game details (item affixes, Legendary powers).\n3.  **Similar Presentation of Complexity:** Both guides acknowledge the complexity of the class (Barbarians: \"dizzying equation\"; Sorcerers: \"easy to get overwhelmed\") and position themselves as the simplified entry point, linking out to the original creators for deeper dives."
```

### Slow-Aware r3

Run ID: `qwen38max-multihop-slow-aware-r3`

```json
"**Yes.**\n\nBoth guides explicitly state that they have \"gathered and simplified\" the best builds for Season 2. In both cases, the simplification involves providing a streamlined skill allocation order and basic Paragon Board guidelines, while directing readers to external sources (such as IcyVeins or specific creators like Northwar and AaronActionRPG) for complex details like item affixes and stat priorities. The structure and methodology for simplifying the content are identical across both class guides."
```
