# Cost-guidance free exploration v1

Date: 2026-10-04. Status: **live exploration; partial results, no route winner**.
Branch: cost-guidance-exploration-v1. Completed primary cells:12/16;
global substantive cap:36. The Video block is still running at this checkpoint.
Baseline evidence: execution freeze3c3bd95, reports02518c7.
See [literature map](method-literature-map-v1.md),
[collision audit](method-novelty-collision-v1.md) and
[progress ledger](cost-guidance-exploration-plan-v1.md).

## Research question and non-goals

Which feedback representation makes an online Agent's semantic choices more
cost-rational without silently sacrificing task quality? A useful outcome can
be negative. Cost is a vector: traffic, transfer delay, operator/model work,
control-plane work and observed E2E. No dollar/energy estimate is invented when
the corresponding measured profile is absent.

Keep the SDK-native Manager/specialists, existing Blind Verifier, finite tools,
task representations, private evaluators,32K/2048 deployments, budgets and B0
scheduler. Do not restore whole-workflow search, modify completed actions,
train RL, add semantic repair, or insert task-specific strategies.

## At least four distinct routes

| Route | Information/control difference | Falsifiable hypothesis | Primary risk | Initial disposition |
| --- | --- | --- | --- | --- |
| A: spent-only Ledger | Completed execution costs and remaining budgets before Manager decisions | Explicit spending constrains unnecessary expansion without a next-action forecast | Past spending may not distinguish future choices; premature stopping | Implement first, attributed baseline |
| B: Action Cost Card | Structured consequences for concrete legal ready actions | Parameter-specific cards make raw profiles actionable without a mandatory round trip | Static templates may be vague or resemble a hand-written strategy | Design; use shared estimator, not task recipes |
| C: Quote-before-Commit | Agent proposes action; no-execution quote; Agent commits or revises | Concrete marginal consequences induce useful generic revisions | Extra cloud turn, myopic quotes, ignored estimates | Implement second, primary candidate only if evidence supports it |
| D: up to3 candidate consequences | Manager proposes ready candidates; comparable quote vectors | Alternatives address expensive first proposals that C still commits | Candidate omission, implicit topology pool, overhead | Conditional after observing C |
| E: trace-distilled heuristics | Separately versioned generic guidance from clean contrasting trajectories | Support/counterexamples yield transferable guidance | EnumGRPO collision, task memorization, quality hindsight | Conditional; do not inject initially |

These routes alter feedback/decision protocol, not executable primitives.
No route is a winner at this partial-results checkpoint. The design below remains
the frozen initial protocol; observed results are recorded separately at the end.

## Exposure contract

The principal A experiment is **semantic/static inputs + Ledger**, not a new
Blind run and not raw current-profile injection. Ledger contains measured past
costs but no future cost forecast. It is therefore called Ledger-only.
C shares A's Ledger and adds action-specific infrastructure-dependent quotes.
This isolates prospective consequences relative to spending awareness; existing
Blind and Raw-Aware remain reference points, not renamed variants.

Only Manager receives experimental cost feedback. Specialists and Verifier
retain their frozen Blind contract. Agent prompts/traces never receive worker,
device, IP, deployment identity, route, gold, supporting annotations or evaluator
metadata. Physical trace retains physical selections for audit. Anonymous
capability classes and quoted requirements are not concrete deployments.

Keep baseline semantic instructions unchanged. Any generic method supplement
must be separately hashed/versioned and must not name benchmark tasks, evidence
content, preferred first actions, or desired answers. Cost feedback is not a
permission to tune retrieval/sampling/stopping semantics after seeing quality.

## A: spent-only Ledger contract

Snapshot before each actual Manager reasoning input, with an as-of event ID:

- Successful/failed physical actions, tools versus models and reached-inference
  count; preflight refusal is not an inference.
- Action transfer bytes and transfer work; initial placement separately.
- Observed model-service and operator work, accumulated reasoning turns,
  specialist calls and remaining existing budgets.
- Measured E2E-so-far when available; no sum of overlapping work labeled E2E.
- Unknown telemetry stays unknown. Do not substitute zero or configured RTT.

Idempotent event accounting must survive multiple observations per action,
failed-action telemetry and parallel batches. Count completed receipts once;
failed partial transfers and failed backend calls remain visible where measured.
No action-specific or task-specific strategy is generated by the Ledger.

## C: proposal, quote, commit/revise

1. Manager proposes the same finite logical tool/model action and parameters.
2. Validate syntax, current artifact readiness and static requirements.
3. Estimator uses current observer/profile and the existing resolver/scheduler
   policy without executing an operator, transfer or inference.
4. Return sanitized consequence vector, support/uncertainty and opaque quote ID.
5. Manager either commits that exact action or revises with a new proposal.
6. At commit, revalidate readiness/current feasibility and resolve physically;
   a quote is not a reservation or deployment binding.
7. Execute through the existing ActionGateway; retain observed receipt and
   estimator residuals. The graph grows only from real physical executions.

Quote references must be owner-scoped, exact-action-hashed and single-use.
Revisions cannot silently mutate an old quote. Quote failure is typed feedback,
not hidden repair. No quote may create an output artifact, sample evidence,
call a model/evaluator or charge a physical execution as if it occurred.
Dependent actions still wait for producer observations in a later turn.
Independent ready actions may remain parallel; do not hide a dependent chain.

Record quote count, estimator wall time, input/output control tokens, additional
reasoning turns, revisions, ignored/high-cost commits and stale-quote refusals.
Keep20 Manager /64 physical /20 Verifier budgets unchanged. Do not raise the
horizon to conceal quote overhead. Add a separately frozen bounded quote-call
safety guard; it is not a new physical-call budget or a stopping heuristic.

## Estimator v0: deterministic and support-aware

Use only eligible clean historical records. Freeze an input manifest listing
run IDs, trace/result hashes, eligibility evidence and exclusion reason. Remove
benchmark answers, labels, private metadata and text bodies before estimator
fitting; service statistics need only measured token/modality/size/latency data.

| Consequence | Inputs / method | Unsupported case |
| --- | --- | --- |
| Movement bytes | Ready artifact sizes/replicas, resolver-selected destination internally; sum only missing required payloads | Unknown size/selection => unknown, not hypothetical0 |
| Transfer latency | Link category, observed size bucket/throughput, current measured/configured profile | Keep configured ideal-rate calculation separate from observed empirical interval |
| Model service | Abstract class, modality, actual token bucket where known, image count, output budget; empirical p50/p90/count | Insufficient bucket support => unknown; no extrapolation |
| Operator work | Operator/known input-size bucket, clean historical receipts | Insufficient support => unknown |
| Context | Existing runtime conservative envelope and32K/2048 contract | Unknown contributions => unknown; not actual tokenizer/OOM claim |
| Output size | Deterministic operator bound, actual observed support or schema limit | Future LLM output/unknown reduction => unknown, not fabricated compression |

Initial proposed minimum empirical bucket support is3 clean receipts, frozen
before fitting/reporting; report the count and empirical quantiles, not a
statistical confidence guarantee. Low-support samples can be displayed as
historical observations without promoted predictions. Exclude leaked or
hidden-retry attempts. Report cache/quantization/runtime comparability gaps.

Do not turn configured3 Mbps into an exact short-transfer prediction. Multiple
paths/replicas and concurrent work may differ from a scalar link estimate.
Service estimates must not use the UTF-8 conservative bound as actual input
tokens. If actual token count is unavailable before inference, retain a bound
or unknown bucket rather than secretly treating it as a tokenizer measurement.

No predicted answer correctness, inferred gold relevance, automatic model
substitution, new scheduling rule or quality ranking. Cheap is not necessarily
semantically adequate; Manager retains that responsibility.

## Initial exploration allocation

Use the existing four workloads if operations permit:

| Workload | Diagnostic role |
| --- | --- |
| MultiHop existing multisource | Full-shard movement versus bounded retrieval |
| LongBench Academic | Existing quality-preserving Slow signal |
| LongBench Financial | Model-service/decomposition cost dominates |
| Video-MME848-1 | Evidence representation and visual-model work |

Primary allocation: A and C ×4 workloads ×Fast/Slow ×n1 =16 cells.
If resources constrain, minimum is3 workload types with Academic or Financial:
12 cells. Do not silently drop a failed task or swap its representation.
No full Raw-Aware rerun. Historical references are descriptive, not newly
randomized causal controls; justify any matched control by a demonstrated
execution-contract mismatch. Every substantive rerun consumes the36-cell cap.
Up to20 cells remain conditional, not preauthorized as a mandatory sweep.

Fast100 Mbps/configured5 ms and Slow3 Mbps/configured50 ms reuse the existing
transactional tc regime; disclose HTB/netem asymmetry and measured probes.
Fresh isolated Worker roots/processes per run, no historical evidence reset,
no benchmark bodies through the PC. The4090 owns materialization/distribution.
Verify frozen task/representation/placement/models/tools/scheduler/budgets and
recipient visibility before admitting each run.

Run order is frozen before the first cell and includes failures. One attempt
per designated cell, no result-driven retries; genuine generic defects require
new regression, versioned repair, full tests and explicitly affected-only reruns.

## Analysis and failure audit

For every run preserve commit/config/method hashes, task freeze, roots, network
attestation, full trace/result, graph snapshots and recipient input hashes.
Report completion/format/evaluator quality independently; missing evaluator
stays missing. Record actual first actions, aggregation/local retrieval,
reductions, model inputs/calls, sampling/sheets, specialists, graph/parallelism,
turns, initial/action traffic, service/operator/control/quote work and E2E.

For each committed quote compare movement bytes, transfer delay, service time
and context classification with actual telemetry. Unexecuted proposals have
no realized counterfactual cost; do not claim they saved a measured amount.
Output-size guesses require an explicit empirical/bound label. Overlapping
service sums are work counters, not critical-path duration. Unknown critical
path remains unknown unless reconstructed from actual intervals/dependencies.

Investigate each high-impact decision from its **actual preceding input**:
what feedback was visible, whether it was accurate/ignored, whether revision
changed information flow, whether reduction added more service cost than the
transfer it avoided, whether quality dropped and whether control overhead
erased savings. Do not infer an internal causal rationale from prose alone.

Separate semantic reasoning, workflow composition, stopping/expansion, static
capability misuse, dynamic feasibility, budget and system/harness confounders.
Bad legal choices are method results; missing trace/profile/privacy invariants
are genuine defects. Preserve all originals in either case.

## Test gates before any substantive cell

- Ledger idempotency and parallel/non-additive accounting; failures do not
  become inference successes; unknown does not become0.
- Estimator exact payload/locality cases, profile support threshold, bucket
  boundaries, configured/observed distinction and unknown propagation.
- Quotes cause zero inference/transfer/materialization/evaluator calls.
- Commit executes the exact proposed action once; revise/stale/cross-owner
  quote handling fails closed; real readiness/context rechecked at commit.
- Native tool quote -> Manager continuation -> commit reaches ActionGateway;
  independent batches remain parallel and dependent chains remain rejected.
- Actual persistent specialist/Verifier contexts remain Blind, including tool
  results, failure paths and accumulated history.
- Full pytest, Ruff, strict Pyright and source-freeze parity. Existing substrate
  tests cannot be replaced by only new estimator unit tests.

## Decision rules and next steps

A useful route changes explainable high-impact decisions across more than one
workload without systematic quality loss or overwhelming overhead. Ledger can
be the recommended method if it is enough; Quote is not privileged by design.
Reject/narrow routes with no effect, unreliable estimates, quality regression,
task dependence or dominant control expense. D is conditional on a documented
bad-first-proposal/ignored-quote pattern, not a default new search mechanism.
E requires supporting/counterexamples/scope/overfit records and a separate
variant; do not use correct-answer labels as runtime guidance.

## Historical prototype checkpoint: Ledger-only-v0

The spent-only accountant and separate LedgerNativeRuntime adapter are
implemented and tested with the installed real SDK and deterministic synthetic
provider. They wrap returned ActionGateway receipts and the existing SDK input
filter. The original native runtime source, historical manifests, prompts,
Verifier, tools and physical substrate are unchanged. A trace marks the
experimental variant explicitly; underlyingBLIND profile visibility does not
relabel measured-cost feedback as an original Blind baseline.

Full486 tests pass, Ruff passes and strict Pyright has zero errors/warnings.
This is contract evidence, not semantic/performance evidence. No live Planner,
Worker or benchmark cell was launched. The estimator, Quote route and live
runner/manifests still need implementation/verification before the matrix.
See [prototype audit](cost-guidance-prototype-audit-v1.md).

Final ranking and Q1-Q10 remain **pending experimental evidence**. Required
recommendation/prototype audits will explicitly mark untested routes, failure
cases and estimator limitations. Stop at authorized success/useful-negative/
major-collision/persistent-blocker/36-cell conditions, not at a convenient
positive task or a literature-only checkpoint.

## Live checkpoint:12 primary cells

Execution is frozen at47fbe3b14196ea2b90c84597b75fa27f148b0b74 under
`/home/super/xiaoming/cost-guidance-exploration-v1-47fbe3b`. Protocol SHA256:
`f18bfff202a0314c29bdd673158ddcd875a08b084118df6a2b9df109bf1eec66`.
The controller has completed MultiHop, Academic and Financial blocks and entered
Video848-1. This supersedes the historical no-live-results prototype status,
not the frozen design or any retained evidence. Each cell has n=1/no replacement.

| Workload | H | Feedback | Completed/score | E2E seconds | Action bytes | Manager/specialist turns | Graph nodes |
| --- | --- | --- | --- | ---: | ---: | --- | ---: |
| MultiHop | Fast | Ledger | true/1.0 |250.012|57445|9/8|16|
| MultiHop | Fast | Quote | true/0.0 |203.999|27774|18/0|7|
| MultiHop | Slow | Ledger | true/1.0 |201.631|5204596|4/0|4|
| MultiHop | Slow | Quote | true/0.0 |228.329|27774|19/0|7|
| Academic | Fast | Ledger | true/1.0 |114.371|233303|7/0|5|
| Academic | Fast | Quote | true/1.0 |185.066|233323|18/0|5|
| Academic | Slow | Ledger | true/1.0 |162.897|28303|12/8|16|
| Academic | Slow | Quote | true/1.0 |61.482|0|14/0|3|
| Financial | Fast | Ledger | true/0.0 |243.291|495883|14/0|20|
| Financial | Fast | Quote | true/0.0 |97.570|470494|16/0|2|
| Financial | Slow | Ledger | true/0.0 |191.421|19116|8/0|15|
| Financial | Slow | Quote | true/0.0 |83.587|470494|10/0|2|

All12 complete with valid terminal format and original evaluator invocation.
The independently adjudicated first MultiHop schema misuse remains retained,
with its original gate stop preserved. Other completed cells pass operational
gates. No semantic failure is repaired or replaced. Action bytes exclude initial
placement:7696522/514789/1081150 bytes for MultiHop/Academic/Financial respectively.
E2E includes initial placement; transfer/service/reasoning work is not additive.

The useful-looking Academic Slow Quote result needs an important qualification:
its terminal model has **zero artifact inputs**, no read_artifact occurred, and
the two BM25 results expose metadata, not document bodies. After two context-
infeasible quotes were discarded, it invoked a prompt-only model and scored1.0.
This is a valid scored trajectory, not yet evidence of quality-preserving semantic
reduction or cost-caused first-action adaptation. Financial Quote takes the same
prompt-only escape in both networks and scores0.0. Do not rename these as bounded
evidence flows or successful information reduction.

The6 completed Quote cells create38 quotes; all38 exact cards appear in actual
subsequent Manager inputs before first commit/discard (or while still pending).
26 are consumed,10 discarded,2 pending. Thirteen proposals disclose context
selection failure:10 discarded,2 pending,1 knowingly committed and then rejected
before inference. This shows feasible-request feedback and occasional ignored
feedback, not reliable economic optimization. MultiHop C drops six proposed
input artifacts to two after a context refusal and loses quality in both H.

Fast Academic Quote adds substantial Manager work (96.515s versus21.251s Ledger)
without reducing traffic or graph size. Financial Quote reduces physical model
input/service but not demonstrated quality:both methods score0.0; Slow Quote
moves470494 bytes versus19116 Ledger despite being faster overall. Costs cannot
be reduced to network bytes. No causality, statistical significance or winner
is claimed from this fixed-order, cache-uncontrolled n=1 checkpoint.

Read-only action-level receipts, actual-input visibility and estimator errors:
[quote decision audit](cost-guidance-quote-decision-audit-v1.md).
Private MultiHop coverage audit remains deferred until all live queue handles
exit, to avoid adding artifact-scanning load during experiments. Final ranking,
Q1-Q10 and the next-method recommendation remain unfinished.
