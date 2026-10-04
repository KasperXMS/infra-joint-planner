# B/D/E follow-up — prospective protocol v1

The previous A/C study (16 cells, execution revision `47fbe3b`) is preserved.
It did not implement or empirically reject B/D/E. The user explicitly requested
these remaining routes after the premature exploration stop. This is a separate
follow-up on `cost-guidance-exploration-v1`, not a revision of old outcomes.

## Scope frozen before new evaluation

- B/D/E × three existing tasks × Fast/Slow = **18 new primary cells**, n=1.
- Tasks: `multihop-multisource`, `longbench-multidoc-academic`, `video-mme-848-1`.
- Fixed task order above; within task: Fast B/D/E, then Slow B/D/E.
- Global cap 36, including all reservations and failed attempts. Existing 16
  plus planned 18 = 34. The remaining two slots are not scheduled repetitions.
- No replacement, retry, task-specific tuning, dataset expansion or new model.
- Same task/data/evaluator/representation/initial placement as A/C; same fresh
  Worker namespace discipline, native SDK loop, frozen semantic instructions,
  Blind specialists/Verifier, 20/64/20 budgets, 32K/2048, 1200s timeout,
  finite executable operators, scheduler and physical runtime.
- Only the root Manager receives method feedback. These cost-guided variants
  are **not** the original resource-blind baseline. No raw infra state is given.
- Fast: 100 Mbps, configured added delay 5 ms. Slow: 3 Mbps, configured added
  delay 50 ms. Reuse the existing tc implementation; Jetson endpoints do not
  support netem, so this is not a measured symmetric RTT guarantee.

## Routes

**B — optional ready-action cards.** Ordinary SDK execution tools remain direct.
Manager can call `estimate_<operator>` with the same schema to obtain a read-only
consequence card. No mandatory query or commit. Estimates use the unchanged
scheduler's prepared selection and the independently frozen numeric history.
Unknown values stay unknown. An optional prediction is matched to an execution
only if its normalized semantic request is exactly identical and still fresh;
matching alone is not proof of pre-decision visibility or influence.

**D — bounded candidate comparison.** Extend the existing single-use quote
route with `compare_ready_actions` accepting 1–3 Agent-proposed alternatives.
All inputs must already be materialized. Candidate cost vectors have no semantic
quality estimate and the system never picks an optimum or prunes on quality.
Manager chooses at most one alternative with `commit_quote`; other pending
quotes in that group are discarded. Normal single-action quote tools remain,
so comparison underuse is an observable result, not a reason to tune prompts.

**E — B plus frozen trace-distilled advisory rules.** One separate meta-agent
call using the existing cloud model, no retries or weight updates. Sources are
the already audited historical Financial/News LongBench and Video 795-3 runs,
disjoint from all three evaluation task IDs. Only allowlisted operator sequence,
input/output counts, typed failures and numeric execution receipts are supplied.
No task query, artifact content, answer, evaluator/gold or physical identities.
Every rule must have real support and distinct boundary/counterexample IDs,
scope and overfitting caveat. They are frozen before all B/D/E evaluations.
E is an in-context distillation variant related to Enum/GRPO-style trace
heuristics; it is not a novel RL claim or a guarantee of semantic correctness.

## Admission and analysis

Before the first cell freeze source hashes, harness/history/rule hashes, task
and capability hashes, placement and model provenance. Preserve full result,
JSONL trace, tc attestations, Worker state/store roots and shutdown evidence on
4090/owning nodes. The development PC receives source and bounded metadata only.

System/runtime/privacy/provenance defects stop the queue for audit. An ordinary
Agent/model failure or bad legal action does not invalidate a cell or trigger
prompt changes. Audited recovered schema/preflight failures are retained, with
the original operational gate and independent adjudication both preserved.

Report completion, format/evaluator quality, E2E, initial/action movement,
model service, Manager/specialist/Verifier work, cost-query/control overhead,
exact feedback exposure, candidate/rule use, unknown profiles and prediction
errors. Compare A/C descriptively only: the controls are historical, fixed-order,
single draws, with uncontrolled service/cache variation; no causal/sig claim.

Stop after the 18 primary cells or an unresolved system confounder. Do not spend
the remaining slots to rescue bad quality or optimize a trajectory.
