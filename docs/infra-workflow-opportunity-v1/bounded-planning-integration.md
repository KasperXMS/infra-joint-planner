# Bounded planning integration

The SDK-native Manager currently proposes executable next calls, which are
dispatched immediately. Its execution-grown graph records history, not a
revisable future. Harness v2's opt-in `NativeFormalWorkflowBridge` can record
accepted calls in an `OpenSemanticWorkflowPlan`, but the two earlier live H2
checks did not produce a useful natural pending suffix. The offline
`BoundedLookahead` is a scripted interface test, not a live LLM result.

The narrow integration contract is:

1. At a quiescent frontier, ask the SDK-native Manager for one to three
   concrete semantic actions and explicit artifact/control dependencies,
   with the expected plan version. One action remains valid when future
   information is unavailable.
2. Validate the fragment against current task, finite operators, model
   capabilities and known artifact provenance before dispatch. Append to the
   versioned open plan. Do not fabricate future actions or a terminal node.
3. Dispatch only `ready_action_ids()` through the existing action gateway.
   Reserve, start and settle every action using durable receipts and physical
   observations. Preserve the completed/running prefix.
4. After an observation, assess only a known pending suffix. `KEEP` leaves
   it unchanged; a proposed `PATCH` uses `apply_workflow_patch()` via
   `VersionedPendingWorkflow.keep_or_patch()` with exact expected version,
   dependency validation and a quiescent frontier. Unknown free-text
   provenance blocks any rewrite that would require proof of independence.
5. Seal the plan only when the Manager explicitly supplies a valid terminal
   model action and its dependencies. Evaluate the final answer with the
   original benchmark evaluator.

The existing formal validator already rejects stale versions, edits to
running/completed actions, missing artifact edges and illegal terminal
revisions. It does not choose a patch or guarantee semantic quality. A future
selector would need to make its cost estimate, quality risk and extra
Manager/Verifier overhead observable. This package intentionally leaves it
unimplemented. Before an adapter study, a small live feasibility test should
measure how often the current Manager can naturally propose at least two
dependency-valid pending actions, and whether an observation creates a legal,
beneficial pending rewrite. The scripted fixed workflows in this package
make no claim about autonomous proposal capability.
