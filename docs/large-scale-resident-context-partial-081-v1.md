# Model proposals, quotes and context: exact first81-run scope

2026-10-06. Offline bounded accounting, not method screening, semantic tuning,
an actual-model-capacity calibration or a complete PhaseI result. The scope is
the first81 new primary runs only; old42 results remain closed/unpooled.
Cell82 and later runs are not included. Different methods currently have
different task/Planner/network coverage; totals must not rank methods.

## Keep request and inference scopes separate

| Recorded population / event | Count |
| --- | ---: |
| Actual root `invoke_model` function requests | 253 |
| Prepared model actions, including specialists | 185 |
| Prepared-action static requirement support receipts | 183supported / 2impossible |
| Logical observation context-failure receipts | 81 |
| Returned successful inference telemetry | 100 |
| Separately proven JSON failures after inference | 3 |
| Confirmed actual inference lower bound | 103 |
| Other missing model physical receipts | 0 |
| Created model quotes | 68 |
| Model quotes with supported static requirements | 65 |
| Model quotes with unsupported static requirements | 3 |
| Context-rejected model quotes | 34 |
| Selection-feasible model quotes | 31 |
| Model quotes consumed / discarded / pending | 21 / 33 / 14 |
| Exact model cards visible in later Manager context | 63 |
| Pending model cards: visible / not seen later | 9 / 5 |

Root function requests exclude specialist requests; prepared actions include
them. Comparison calls can create candidate quotes without root `invoke_model`
calls. Phase/readiness rejection can prevent preparation. These are not a
partition of253requests and must not be blindly added or divided.

The81 context receipts are not81inferences. Rejected requests have no actual
backend tokenizer count: a frozen conservative artifact/context-envelope reject
does not prove actual model-architecture overflow. There are two static-impossible
prepared requests, with one binding failure and one context failure. Static
impossibility overlaps the context-failure category; it is not two extra failures.
The three failed JSON outputs have confirmed inference but unknown returned
service/token telemetry, retained as UNKNOWN rather than preflight failures.

The34 context-rejected quotes never reached inference merely by being quoted.
They must not be added to successful inference or physical preflight counts.
Physical selection feasibility also does not guarantee operator argument/size
legality, semantic quality, materialized output or eventual execution.

| Method | Scoped runs | Prepared models | Successful inference telemetry | Context observation receipts | Model quotes | Quote context rejects |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 10 | 32 | 16 | 16 | 0 | 0 |
| B1 | 15 | 35 | 16 | 16 | 0 | 0 |
| A | 16 | 49 | 26 | 22 | 0 | 0 |
| B | 15 | 34 | 14 | 20 | 0 | 0 |
| C | 11 | 15 | 15 | 0 | 44 | 23 |
| D | 7 | 6 | 6 | 0 | 24 | 11 |
| E | 7 | 14 | 7 | 7 | 0 | 0 |

A has one proven post-inference JSON failure; B1 has two. Successful-telemetry
columns exclude those failures. C/D's zero physical context receipts do not
establish greater competence or efficiency: they include uncommitted/rejected
quotes and may fail before terminal completion. Coverage is incomplete and
unbalanced, quality is not aggregated, and no method is pruned.

## Exact static misuse: exposure checked in actual API requests

The existing frozen matcher was independently applied to the original requested
requirements and each run's typed StaticCapabilityContract. Its one anonymous
class has context32768, reservedoutput2048, text/image support and no declared
quality tier. Model scale is not silently converted into `standard` capability.

| Cell / method / Planner | Invalid requests | Static incompatibility | Actual Manager requests with equal static contract |
| --- | ---: | --- | ---: |
| 53 / B1 / P1 | 1 | `quality_class=standard`, no matching declared tier | 6 / 6 |
| 64 / B1 / P1 | 1 | requested output4096 > reserved-output limit2048 | 13 / 13 |
| 71 / C / P1 | 2quotes | `quality_class=standard`, no matching declared tier | 20 / 20 |
| 79 / C / P2 | 1quote | `quality_class=standard`, no matching declared tier | 18 / 18 |

Allfive requests have an independently empty matching-model-class set. All57
actual raw Manager requests in these four runs contain the same typed static
contract as their attempt freeze. Raw serialized set order is not assumed
identical; typed equivalence is checked. Source trace/request/usage/freeze hashes
are bound in the exact receipt. No prompts, task text, gold or evidence bodies
were exported to the development PC.

Cell53's original model outcome is `infeasible_binding` with static_feasiblefalse,
physical_selection_succeededfalse and reached_model_inferencefalse. Cell64's
output4096 request returns `context_limit_exceeded` with the same false flags.
These particular action failures are **static capability misuse**, not dynamic
availability/network/load failures. The other three are quote-time static
rejections, not physical model calls. Exposure is not understanding or causal
use, and these action causes are not automatically the run's primary cause.

Full-input conservative context fit is distinct from abstract requirement
support. Context rejection alone does not prove a need for dynamic infra state;
it must be audited against actual artifact sizes, modality and the shared static
envelope. Conversely this partial audit does not claim that every feasibility
failure in the final matrix is static, or that no dynamic signal exists.

## Scope and append-only provenance

The read-only composition verified snapshot020's exact hash/prefix, every later
065–081summary/source binding and all81trace hashes. The first81primary journal
prefix remains intact after later reservations:
`b5aa4506ee28b654f96bef04aa0de39102a58ed2593be070630ccbf3c282261e`.
Old-journal/task/execution hashes were rechecked. This is not snapshot021 and
does not claim a newly recomputed whole-block admission or private semantic audit.

Remote `analysis/resident-context-proposal-first081-audit-001.json` fileSHA:
`b407aed6212014e63cfc36db9a375b2890381b0937100670afda8d12dcf0cdb8`.
Captured23:57:20.922037Z. Remote exact static-request receipt
`analysis/resident-static-request-053-064-071-079-audit-001.json` fileSHA:
`cacc354304309b0d5239f8bae338d3829b26e6e685ae05eaf322c90f6777195d`.
Captured00:01:11.592799Z;5invalidrequests/57actual Manager request checks.

Both operations made0modelcalls, opened no benchmark artifact bodies and
changed no execution, admission, scheduler, source, instructions, budget or
model contract. Results remain private offline audit data, never Agent feedback.
Execution001/control007 remain frozen; all168/failure/semantic/recipient/adoption
audits still precede screening/pruning and actual PhaseII. No quality aggregation
or method winner is claimed.
