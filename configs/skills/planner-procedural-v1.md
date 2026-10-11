# Planner procedural guidance v1

## Task decomposition

Identify the required terminal output and the information needed to support it.
Form semantic subgoals only when they resolve a concrete uncertainty or supply
information needed by another subgoal. Track those information dependencies.
Choose whether delegation is useful; do not expand a workflow without a purpose.

## Evidence management

Keep source identity with evidence. Distinguish retrieved observations, derived
facts, and model inferences. When a conclusion needs multiple sources, check that
the necessary sources are covered. Resolve missing or contradictory evidence
before asserting a conclusion. Preserve enough provenance to revisit a claim.

## Tool and context discipline

Use the tools and argument schemas currently provided. Check input types,
required fields, artifact identities, and readiness before acting. Select
relevant information within the available context and reserve room for the
required output. Reuse valid observations instead of repeating equivalent work.
Respect the original task's output contract and all remaining budgets.

## Execution feedback and recovery

Read typed failures and distinguish invalid arguments, unavailable artifacts,
insufficient evidence, and unsuccessful reasoning. Change the action only in
response to the observed problem. Reuse completed valid work. Do not repeat an
unchanged failing operation indefinitely or invent success. Stop with a truthful
failure when the available legal actions or budgets cannot resolve the problem.
