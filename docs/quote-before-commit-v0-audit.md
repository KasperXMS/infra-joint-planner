# SDK-native Quote-before-Commit v0 implementation audit

2026-10-04. Branch `cost-guidance-exploration-v1`. **Implementation/test checkpoint,
not live method evidence.** New substantive cells0/36, model/provider calls0,
Worker launches0, tc applications0.

## Protocol and attribution

RouteC is Ledger+Quote, not the original resource-blind baseline. RouteA is
Ledger-only. Both retain semantic instructions, finite physical primitives,
model pool, static capability view, Blind Verifier, budgets and B0 scheduler.
The literature/protocol baseline is [free exploration](cost-guidance-free-exploration-v1.md).
Spent-budget feedback is attributed to Budget-Aware Tool-Use; empirical cost
profiles have clear Abacus/semantic-optimizer lineage. Neither accountant nor
percentile estimator is claimed as novel.

Manager's original SDK function tools keep their names and argument schemas.
In C, their **descriptions** disclose a generic proposal protocol: a tool call
returns an anonymous cost quote, not an execution result. Two control tools
`commit_quote`/`discard_quote` accept only an opaque quote ID. They are protocol
operations, not new executable operators or a fixed topology pool. A revision
means discard and a new explicit normal proposal, never mutation of an old quote.
No benchmark name, preferred first action, strategy hint or answer is added.

Specialists retain the original tool descriptions and direct Blind execution;
they have neither control tools nor prospective cost feedback. Manager still
owns global context and terminal synthesis. No extra LLM/Verifier component,
provider retry, physical policy or semantic repair is introduced.

## Files and guarantees

- `control/quote.py`: owner-scoped, exact-effective-action-hashed quotes; no
  reservation/materialization/inference at proposal. TTL120s, max128 proposal
  attempts per run. Readiness is validated using the original gateway.
- `control/quote_native.py`: isolated native adapter over the frozen base.
  Calls original normalization/output contracts, stores the original SDK
  parameters, and executes with the original semantic action ID. Authorization
  hashes are checked at the gateway before any physical action.
- `control/method_usage.py`: shared pass-through per-agent SDK model accounting
  for A and C. It returns the same provider response without altering requests.
  Manager/specialist tokens and service work are separated. SDK default zeros
  from missing provider usage are unknown, not measured zero. Frozen runs are
  non-streaming; an unmetered streaming path is rejected.
- `control/consequence.py`: card explicitly states current queue/cache and
  operator-parameter effects are unmodeled. Unknown future outputs remain
  unknown. No quality oracle, full-plan feasibility or compression guess.
- `tests/test_cost_quotes.py`: protocol and real installed-SDK integration tests.
  Ledger integration now exercises the same pass-through usage accounting too.

At commit, readiness and the anonymous consequences are recomputed. A changed
card or expired/consumed quote is a typed refusal requiring an explicit new
proposal. This is not a physical reservation: the ordinary gateway observes
again and the original scheduler resolves at actual execution. Changes that do
not alter the coarse card may still occur; actual selection and estimate errors
are recorded, not concealed or enforced by pinning a deployment.

Only committed physical actions grow the execution graph. Quote-only batches
do not invoke Verifier because no new semantic result exists. After an actual
tool/model/subagent result or original execution failure, the **unchanged**
Verifier callback runs. This protocol-level invocation timing distinction is
recorded and must not be described as identical numbers of Verifier calls.
20 Manager/64 physical/20 Verifier and specialist8/4/2 remain unchanged; proposal
and commit consume ordinary Manager reasoning turns. Any lost reasoning horizon
or extra cloud latency is a method cost, not grounds to increase budgets.

## Trace and privacy

`logical.cost_quote.*` records creation, discard, rejection, stale refusal,
authorization, numeric actual-versus-predicted receipts and final quote states.
`physical.cost_quote.prepared` alone records concrete selections/snapshot hashes.
Failed/unknown execution receipts are not synthesized as zero costs. A consumed
authorization means the gateway was entered, **not inference or successful work**.

Proposal/authorization work is timed on both success and failure and reported as
non-additive work, separately from physical execution. Argument parsing/discard
housekeeping is not included in those timer totals. Shared
`logical.method.reasoning_usage` captures actual SDK Manager/specialist latency
and nonzero provider token usage; the frozen Verifier's telemetry remains separate.
Later analysis must join actual Manager turns to control-only versus execution
batches to identify quote-associated cloud overhead, not add all overlapping work.

Manager receives Ledger and cards, not raw `PhysicalProfileView` or concrete
identity. Base dynamic-profile/privacy filters are composed, not weakened.
Specialist input filters also reject inherited structured quote objects. Actual
specialist/Verifier contexts are integration-tested for absence of quote/Ledger
and private/physical identity. This structured guard is not a proof that an LLM
cannot paraphrase cost facts into free-form specialist instructions; live audit
must check actual assignments as well. No gold/evaluator is used by cost code.

## Verification evidence

Full pytest: **526 passed**. Ruff:pass. Strict Pyright:0 errors/0 warnings.
Whitespace check:pass. Eleven new quote tests plus existing Ledger controls cover:

- No execution/reservation/materialization at quote; explicit single-use commit.
- Owner mismatch, unknown/expired/discarded quote and bounded proposals.
- Changed consequences require requote; changed action arguments reject.
- Concurrent duplicate commit cannot execute twice.
- Future quoted outputs are not materialized/readable dependencies.
- Real SDK two-BM25 commits overlap; dependent reasoning happens afterward.
- Exact quoted/actual actions match and terminal comes from successful model output.
- Actual physical failure returns to Manager for explicit continuation, no retry.
- Real SDK Manager -> Blind specialist recovery/note/handoff -> Manager continuation.
- Inherited quote in child context fails closed before its model call.
- Estimator implementation defects propagate as harness failures, not Agent refusal.

Synthetic provider doubles drive the **real SDK dispatch**, not a new live task.
All requests and responses are synthetic and no API key/cloud call is required.
Official SDK sources used: [running agents](https://developers.openai.com/api/docs/guides/agents/running-agents),
[manager-style agents-as-tools](https://developers.openai.com/api/docs/guides/agents/orchestration).
Installed `agents/models/interface.py` and function-tool definitions were checked;
no package upgrade/model replacement.

Original native runtime SHA remains
`b6112f2fda45add527e54a5924c9a5693a94f4439e37785846bafbca32a15985`;
original isolation manifest remains
`444db21f3d7aa0db13af993854e77318a29bddee1aee438f27d4a4f7c25affbf`.
No Worker/scheduler/benchmark/evaluator or historical evidence changed.

## Still required before live exploration

Build the append-only cell runner/new manifest with frozen history hash,
method supplement/tool-description hashes, task/source/capability equality,
fresh isolated stores and verified network configuration. Then run A/C on the
selected existing workload types, retain failed results, audit actual recipient
contexts and estimator accuracy, and rank methods from evidence. No effectiveness
or final novelty recommendation is established by this checkpoint.
