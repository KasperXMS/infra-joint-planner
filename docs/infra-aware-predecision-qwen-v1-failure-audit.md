# Pre-decision Qwen v1 — exception audit

Status: **completed**. All twelve primary runs completed/evaluated; the only zero
is Slow-Blind r2. No operational failures, affected reruns or replacements.
This is private-evaluation/offline analysis, never an input to planning.
Experiment root: `/home/super/xiaoming/infra-aware-predecision-v1-91f11ff`.
No result/trace/evaluator score is rewritten and no semantic retry is authorized here.

## Slow-Blind r2: valid wrong answer

Run: `predecision-qwen-multihop-slow-blind-r2`.
Completion true; exact terminal `No`; original score 0; format valid.
Manager 8 / Verifier 8 / physical calls 15 / specialist 1 (8 turns).
Two prepared model actions; one context rejection, one actual inference.
E2E 270.295 s; model service 125.554 s; action transfer 42,446 bytes / 0.602 s;
initial placement 7,696,522 bytes / 22.177 s. No failed observer probes;
fresh-store, privacy and tc gates pass.

### Evidence and decision timeline

- `000047-logical.verification`: correctly requires comparative Barbarian evidence.
- `000089-logical.verification`: READY based on six retrievals covering all shards;
  artifact coverage alone is not proof that the terminal model will select that evidence.
- `000105-logical.action.prepared`: first synthesis consumes all six shard retrievals.
  `000113-logical.model.outcome`: `context_limit_exceeded`, reached inference false.
- `000118-logical.verification`: CONTINUE, correctly identifies the context constraint.
- Specialist reads both target guides. Verifier `000239`, `000247`, `000256` explicitly
  recognizes that both texts say “gathered and simplified” and judges evidence sufficient.
  Exact sanitized Verifier inputs are in the corresponding input events, not reconstructed
  from design intent.
- `000263-logical.action.prepared`: terminal action
  `manager:call_38646d3a98714359b95ade8f` selects **only `sorcerer-shard1` and
  `barbarian-shard1`**, not the relevant shard-3 results.
- `000270-physical.execution`: real A28 inference, 7,287 input / 2 output tokens,
  finish reason `stop`. `000271-logical.model.outcome`: inference true, success true.
- `000276-logical.verification`: accepts `No` as a non-empty contract-valid answer
  without resolving its contradiction with the evidence already acknowledged.

### Artifact preservation check

Read-only checks ran on A28 via strong-4090; no dataset bodies were returned to the
development PC. Saved diagnostics: `slow-blind-r2-artifact-diagnostic.jsonl` under
the remote experiment root. Relevant `sorcerer-shard3` (14,537 bytes) and
`barbarian-shard3` (14,536 bytes) remain persisted with matching content hashes.
Both contain target-like Sorcerer/Barbarian build-guide records and the explicit
“gathered and simplified” phrase. Selected shard-1 artifacts (13,887 bytes each)
have neither target-like guide title. Title detection is supporting evidence, not
a substitute evaluator; original private score remains 0.

Thus relevant evidence existed, was retrieved, survived and became visible to the
specialist/Verifier, but was **not selected as terminal model artifact input**.
The terminal prompt mentions both classes (413 bytes), but cannot supply the missing
guide bodies. The original context rejection is a real preflight constraint, not
an inference or a silent truncation. Blind received no physical profile.

Primary class: **evidence-selection failure**. Secondary: context recovery followed
by wrong model answer and **Verifier semantic failure**. Absence-of-evidence reasoning
is a plausible explanation, not directly proven by the label-only model response.
Confidence: high for provenance/selection/contradictory verdict; medium for the
model's unrecorded internal reasoning. No observer/runtime/evaluator confounder
is evidenced. Do not tune prompt, retrieval, Verifier or budgets for this valid result.

## Fast-Blind r2: latency outlier, successful recovery

Run: `predecision-qwen-multihop-fast-blind-r2`. Exact `Yes`, score 1, normal completion,
9 Manager / 9 Verifier turns, 8 physical calls, no specialist. E2E 671.796 s.
Three completed physical inferences consume 588.661 s of service work (87.6% of
E2E numerically; not an additive causal partition). Action transfer 5,204,596 bytes
in 1.630 s. Four prepared model actions include one context rejection; the rejected
action is not counted as inference. Other typed failures are phase restriction and
invalid reduction arguments. All operational gates pass. The large latency is
trace-supported model-service work, not a shaper failure or demonstrated network
causality. `000120-physical.execution` summarizes Barbarian retrieval (7,587 input /
365 output tokens, 262.042 s); `000140` summarizes Sorcerer retrieval (7,619 / 450,
306.823 s); `000161` synthesizes both materialized summaries (1,040 / 2, 19.796 s).
All three finish with `stop`. Prepared actions `000113`, `000133`, `000154` prove
the producer-consumer path; no hidden reduction/truncation is involved. The failed
top-k action (`000100`) requested nonexistent `score`, an explicit legal-tool argument
failure, not a missing operator. The Agent then selects two legal summary calls.
Both retrieved inputs and materialized summaries remain hash-valid on A28;
retrievals contain target-like guide titles and both summaries mention simplified
builds. The terminal action selects those exact summary IDs. Private retained check:
`fast-blind-r2-artifact-diagnostic.jsonl`. Confidence high on cost/provenance/recovery.

## Fast-Aware r3: unusual high-call recovery, correct completion

Run: `predecision-qwen-multihop-fast-aware-r3`. Exact `Yes`, score 1, completion true;
9 Manager / 9 Verifier turns, 3 specialists (24 turns; peak active 2), 30 physical
calls; 30 graph nodes / 35 edges. First turn issues six independent BM25 actions.
All 9 Manager inputs contain the freshly observed anonymous Fast profile before
reasoning. Operational/privacy/tc gates pass; no observer probe incident.

Typed failures: 2 context rejections, 3 explicit 64 KiB read-limit rejections,
6 invalid field/schema operations, 3 phase restrictions and 2 within-run output-ID
collisions. Examples: `000108` context 172,759 estimated input tokens; `000174` /
`000181` oversized reads; `000196` / `000211` / `000247` absent text field;
`000277` absent selected fields; `000381` context 58,297; `000451` absent text field.
These produce sanitized observations, not silent truncation/fallback or hidden repair.
The specialists/Manager continue and eventually read the relevant guide text.

`000507-logical.verification` identifies the exact simplified-build phrase in
Sorcerer and Barbarian observations and permits synthesis. Terminal action
`000516-logical.action.prepared` has no artifact inputs: its 1,017-byte prompt
explicitly includes the observed “gathered and simplified” fact. It does not move
a raw corpus into the final model. `000529` accepts the successful model's exact
`Yes`. This is evidence-to-prompt information flow, not a private gold hint.

E2E 171.831 s; action transfer 112,712 bytes / 0.288 s; one physical inference
(234 input / 2 output tokens, 6.961 s). Manager/specialist/Verifier service work
62.355 / 81.403 / 43.537 s is **non-additive** because specialists overlap.
Primary class: correct completion with workflow-composition/context-recovery
inefficiency. Confidence high on recorded failure/recovery/quality; no claim that
anonymous profile visibility caused this specific trajectory.

## Maximum-traffic and other unusual trajectories

Eight equal maximum-traffic runs (FB r1/r2/r3, FA r1, SB r1, SA r1/r2/r3) all
begin with `aggregate_artifacts`, selecting A28 and pulling shard 1 from A4
(2,772,674 bytes) and shard 2 from A5 (2,431,922 bytes): exactly 5,204,596 bytes.
Transfer telemetry, declared sources and generated corpus lineage agree; there is
no unexplained repeated bulk transfer. Fast transfer costs 1.1–2.1 s; Slow about
14.8–15.0 s. Each Aware initial profile existed before this decision. All three
Slow-Aware H0 values say `constrained`; transfer/service estimates remain null.
This is observed full-data movement despite pre-decision visibility, not a late
profile or transfer bug. Confidence high. Do not substitute a local-first workflow.

FA r2 and SB r3 are additional local-first, specialist-heavy recoveries. They
retrieve target-like guide text, retain hash-valid outputs, recover after conservative
context/field/phase errors and finally incorporate observed guide facts into a
short terminal model prompt without artifact inputs. FA r2 uses 13 physical calls,
1 specialist / 6 turns, 57,445 action bytes and 138.353 s E2E; SB r3 uses 20 calls,
2 specialists / 14 turns, 57,351 bytes and 207.437 s. Final evaluator scores are 1.
Their expansion/cloud cost is not a hidden runtime repair. Confidence high on
events/quality, medium on any interpretation of motivation from network visibility.

## Run-by-run classification and evidence selection

Full IDs share prefix `predecision-qwen-multihop-`. `Prep` below is the exact terminal
`logical.action.prepared` step; `Verify` the final `logical.verification` step.
All rows have successful terminal model output, valid serialization, private evaluator
invocation and no observer/provider/runtime incident. Guide-title checks are supporting
offline diagnostics, not a substitute evaluator or proof of hidden model reasoning.

| Suffix | Relevant evidence selected for terminal | Prep / Verify | Primary interpretation | Confidence |
|---|---|---|---|---|
| fast-blind-r1 | two bounded retrievals with guide titles | 000127 / 000140 | correct completion; context recovery | high |
| fast-aware-r1 | two bounded retrievals with guide titles | 000136 / 000149 | correct completion; context/phase recovery | high |
| slow-blind-r1 | observed evidence encoded in prompt | 000205 / 000218 | correct completion; specialist/field recovery | high |
| slow-aware-r1 | read evidence paraphrased in prompt | 000158 / 000171 | correct completion; context recovery | high |
| fast-blind-r2 | two explicit materialized model summaries | 000154 / 000167 | correct completion; costly summary recovery | high |
| fast-aware-r2 | observed simplified-build fact in prompt | 000230 / 000243 | correct completion; expanded composition recovery | high |
| slow-blind-r2 | irrelevant shard-1 records; shard-3 ignored | 000263 / 000276 | evidence-selection + Verifier semantic failure | high on selection/verdict |
| slow-aware-r2 | two bounded retrievals with guide titles | 000134 / 000147 | correct completion; context recovery | high |
| fast-blind-r3 | two bounded retrievals with guide titles | 000140 / 000153 | correct completion; context/phase recovery | high |
| fast-aware-r3 | observed simplified-build fact in prompt | 000516 / 000529 | correct completion; excessive composition recovery | high |
| slow-blind-r3 | observed simplified-build fact in prompt | 000340 / 000353 | correct completion; expanded specialist recovery | high |
| slow-aware-r3 | two bounded retrievals with guide titles | 000150 / 000163 | correct completion; context/phase recovery | high |

## Verifier sufficiency boundary

All runs have READY before later context failure, demonstrating that semantic
coverage is not executable context feasibility. The existing runtime correctly
returns typed preflight failures; Verifier may then CONTINUE. This does not prove
that the rejected payload would overflow the actual tokenizer/backend: resolver
uses UTF-8 bytes as a conservative token upper bound, retaining 2,048 output tokens.
No preflight request is counted as inference, and this frozen rule was not relaxed.

More importantly, SB r2 shows that **globally available relevant evidence is not the
evidence actually selected for final synthesis**. The final Verifier accepted a
contract-valid contradictory label after earlier identifying affirmative evidence.
This is a semantic judgment error under the frozen Verifier, not a missing input
provenance defect: exact sanitized actions/observations/graph were supplied and saved.
There is no justification for prompt/Verifier tuning within this completed block.

## Preserved diagnostic provenance

The complete raw audit is remote `predecision-audit-v1.json`, hash
`40aa08d5cdc23ec64f642f75b411424a8297af6bb91906d59a2ee1780a7fde3c`.
Read-only A28 artifact diagnostics (metadata/boolean results only returned locally):

- `all-run-artifact-diagnostic.jsonl`:
  `75926b29f8e47c774ab7e13baad2a8e74a8d05a64ce21e8ca18c8c1fe3acec74`
- `slow-blind-r2-artifact-diagnostic.jsonl`:
  `af7abe1f01bbd8bc8d139a00c347b955d4a5db5059b944166fd49b770e7f9eeb`
- `fast-blind-r2-artifact-diagnostic.jsonl`:
  `4ba3255a4b588ddf6f1e1f902b0c21e35b21ef65f3a9f44b5e824de70b47de7d`

All checked selected/retrieved blobs match stored content hashes; relevant guide
signals exist in every run. No historical artifact is removed and no original trace,
result or evaluator object is modified. Diagnostic title/phrase detection is private,
post-execution analysis only; it never participates in Agent execution.

## Generic interpretation boundaries

Within-run output-ID reuse is distinct from historical cross-run pollution.
The unchanged semantic validator reserves output IDs for unique producers, including
failed graph nodes; requesting the same ID again produces an explicit collision.
Fresh pre-run Worker states prove that these are not old `barb-poly-2` store collisions.
Agents can recover with new IDs, as observed. No hidden reordering or repair occurs.

No cost/profile/model/prompt/budget/runtime semantics were changed during this block.
Read-only analysis handles model actions without an `operator` key, null failed-action
selection, and unknown cloud token usage; these analysis-only fixes do not require
formal reruns because the underlying raw evidence is preserved.
