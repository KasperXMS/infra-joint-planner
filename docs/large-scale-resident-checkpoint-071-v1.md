# Resident checkpoint: LongBench cells71–72

2026-10-06. Bounded new-block audit, n=1, no old42pooling, retry, tuning or
screening/pruning. Actual execution remains90fd30c/execution001/control007.

| Measure | Cell71: P1 /Slow /C | Cell72: P2 /Fast /D |
| --- | --- | --- |
| Original admission | valid execution failure | valid completed quality failure |
| Completed /canonical format /original score | false /UNKNOWN /UNKNOWN;unevaluated | true /true /0.0 |
| Manager /Verifier turns | 20 /3 | 12 /5 |
| Specialists /specialist turns | 0 /0 | 0 /0 |
| Prepared physical /model actions | 5 /0 | 5 /1 |
| Successful tools /actual model inference | 4 /0 | 4 /1 |
| E2E | 161.719s | 75.318s |
| Fixed initial placement | 2,119,778bytes /5.989s | 2,119,778bytes /0.236s |
| Complete action transfer | UNKNOWN;successfulsubtotal0 | 0bytes /0s |
| Successful tool /complete tool work | 2.772s /UNKNOWN | 0.673s /0.673s |
| Complete model backend work | 0s;no prepared model action | 0.593s |
| Executed model | none | strongGPU0residentQwen3.5-27B |
| Actual model tokens /finish | no inference | 432input /2output /stop |
| Cloud API list-price USD;not invoice | 0.1349332730969054;all23known | 0.3271807318726000;all17known |
| Actual SDKrecipient contexts audited | 23 | 17 |
| Graph nodes /artifact edges /snapshots | 5 /0 /16 | 5 /2 /16 |
| Node final states | 4succeeded,1failed | 5succeeded |
| Logical action owners /handoffs | 1 /0 | 1 /0 |
| Actual maxconcurrent /overlap | 4 /1.128s | 1 /0s |
| Created /authorized /observed quotes | 11 /5 /5 | 6 /5 /5 |
| Final quote states | consumed5,discarded5,pending1 | consumed5,discarded1 |
| Quote-control work | 4.742s | 1.492s |

Receipts describe measured work, not additive E2E components. Model action wall
time includes backend service; do not count both as independent costs. Complete
movement/tool work in71 remainsUNKNOWN because an oversize read failed during
execution; failed-action walltime0.400s does not fill missing breakdown. Context/
selection checks inside quotes do not constitute actual inference or physical
model actions. Allfive instances resident, Workerexit/tccleanuppass, original
recipient/private admission checks passed. No warm-start subtraction.

## Cell71: exact terminal and visible quote trajectory

Original run.failed is `logical_loop_failed /AgentLoopError /
manager turn budget exhausted`.20Manager starts,5physical actions,3Verifier
calls: **primary hard Manager-turn budget exhaustion**;not the64physical-call
ceiling, a timeout, provider outage or deployment crash. Keep the failure and
missing evaluation; do not encode it as score0 or enlarge the budget.

The executed path is onefailed oversized read followed by four successful BM25
actions; those four ready retrievals overlapped. No model action was prepared.
Verifier's second decision changed evidence_collection->synthesis. The quote
protocol emitted17control-only batch receipts (not asserted to be17distinct
Manager turns), without adding new physical observations or invoking Verifier
for those batches. Manager/cloud work141.752s;Verifier work8.893s. This records
intrinsic interaction work, not a matched causal estimate of C's overhead.

Exact quote feedback available to Manager before disposition:

| Quote population | Count | Verified status /disposition |
| --- | ---: | --- |
| read_artifact/BM25cards | 5 | all exact-card-visible;all authorized/executed;readtoo_large,4retrievalsuccesses |
| Model cards asking quality_class=standard | 2 | static_request_supported=false,infeasible_binding;visiblethen discarded |
| Model cards with supported abstract requirements but overlarge full inputs | 2 | static supported,context_limit_exceeded;visiblethen discarded |
| Prompt-only model card | 1 | static/selectionfeasible;visiblethen discarded,not inferred |
| Final one-artifact model card | 1 | static supported,context_limit_exceeded;pending,no later recorded root input |

Thus10of11createdcards had exact SDK pre-disposition exposure. The final card
must not be called consumed, visibly considered or successfully recovered.
Two unsupported quality-class requests are **static capability misuse**, not a
dynamic availability signal. Three complete-input context failures are quote
predictions, not three inference failures. Presence of a feasible discarded card
does not prove abandoning it was semantically wrong: sufficiency of a prompt-only
answer requires private evidence analysis. Phase-restricted attempted tools and
five quote rejection receipts are retained separately; they can overlap SDK
observations and do not add physical calls.

Contributing observed factors: repeated infeasible model proposals, static
capability misuse, composition/stopping and quote/discard/control interaction.
No claim that network state alone caused failure, C is generally dominated,
evidence was sufficient, or Verifier made an incorrect semantic decision. Those
claims require complete matched/private audit; no method pruning before168.

## Cell72: legal terminal, wrong answer, comparison not exercised

Actual sequence: BM25 ->read reduced artifact ->BM25 ->read reduced artifact ->
prompt-only real model inference ->canonical terminal ->original evaluator.
No physical/SDK failure receipt, no context reject or missing model outcome.
Six ordinary quotes were created, fiveauthorized/executed, one discarded.
However candidate sets/compare_ready_actions responses/post-comparison choices
are **0**: ordinary quote use is not D's alternatives-comparison adoption.
Do not count five commits as five multi-candidate comparisons.

The432input-token terminal request is not proof of evidence loss or faster
hardware. Manager may inline facts learned via reads; complete private evidence
path must determine adequacy. Low service work and score0 do not demonstrate
quality-preserving optimization. This cell did not exhaust20Manager/64physical
limits; its primary semantic/evidence/Verifier quality attribution is pending.

## Immutable provenance and continuation

| Proof | Cell71 | Cell72 |
| --- | --- | --- |
| Settlement UTC /sequence | 2026-10-05T23:14:41.393681Z /142 | 2026-10-05T23:16:54.224617Z /144 |
| Original admission canonical SHA-256 | `82beebd332f172a2bd6c328c1e8c58ad5dd3a154fcffd8837c26a2b26a2f5c1b` | `4030bb1463e4863afc460e9c5adf8197b1f59e0fa840416a78a509822e349416` |
| Original journal settlement SHA-256 | `86bc0c75372317070347a5dacc7e6765d896914d2011a70f2f17e8d61198ba20` | `c38744c674d461f8ee7a7987f6932e5a8ea282baf1dd1adbdf9fd0159a8a4214` |
| Exclusive summary file SHA-256 | `37d1cdb8c8826c46f42a6e6d64a53f43753d0cbb75328a1dec7dabc0d93dfb0e` | `90519d8f5351059f6ce1719af6404610cd9406fdac68279613d867897bd3c020` |

Remote `analysis/resident-cell-071-summary-001.json` and072summary bind original
admission/result/trace, hash-linked journal, source, Workerexits/residency. Exact
quote visibility/lifecycle diagnostics are already in71summary; original
failure and all typed refusals remain unchanged. No raw payload/gold/prompt/
dataset/model export to development PC; no additional Planner/model call.

At23:16:57.696898Z queue008PID2678456 verified live after72settled; do not infer
a next atomic PID from the queue lease.72classified,stable snapshot020 remains
the earlier64boundary. Full168, complete private/recipient/failure/adoption
audits, frozen pruning, actual PhaseII and all finalreports/Q1–Q10 unfinished.
